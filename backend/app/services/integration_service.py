"""
Integration API business logic
"""

import csv
import io
import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.integration_auth import generate_api_key, hash_api_key, ALL_SCOPES
from app.core.integration_errors import ErrorCode, raise_integration_error
from app.models.integration_models import IntegrationApiKey, IntegrationAuditLog
from app.models.question_models_v2 import QuestionBankV2, QuestionV2, QuestionOptionV2, QuestionType
from app.schemas.integration_schemas import (
    IntegrationQuestionCreate,
    IntegrationQuestionUpdate,
    IntegrationBatchResult,
    IntegrationImportResult,
    IntegrationErrorDetail,
    ApiKeyCreateRequest,
)
from app.services.integration_csv_parser import parse_csv_row, build_external_id_safe
from app.services.integration_import_helpers import (
    make_error,
    error_from_exception,
    finalize_import_result,
    finalize_batch_result,
)
from app.services.question_bank_service import QuestionBankService

IMPORT_BATCH_COMMIT_SIZE = 100


class IntegrationService:
    def __init__(self, main_db: Session, qbank_db: Session):
        self.main_db = main_db
        self.qbank_db = qbank_db
        self.qbank_service = QuestionBankService(qbank_db)
        self._defer_file_sync = False
        self._bulk_import_active = False
        self._existing_by_code: Dict[str, QuestionV2] = {}
        self._import_bank: Optional[QuestionBankV2] = None
        self._import_pending_rows = 0

    def _sync_to_file(self, bank_id: str) -> None:
        if not self._defer_file_sync:
            self.qbank_service._sync_questions_to_file(bank_id)

    @contextmanager
    def _bulk_import_mode(self, bank_id: str):
        """导入专用：预加载 external_id、批量 commit、结束后再 sync 文件一次。"""
        bank = self.get_bank_or_404(bank_id)
        existing_rows = self.qbank_db.query(QuestionV2).filter(
            QuestionV2.bank_id == bank_id,
        ).all()
        self._import_bank = bank
        self._existing_by_code = {
            q.question_code: q for q in existing_rows if q.question_code
        }
        self._defer_file_sync = True
        self._bulk_import_active = True
        self._import_pending_rows = 0
        try:
            yield
            self.qbank_db.commit()
        except Exception:
            self.qbank_db.rollback()
            raise
        finally:
            self._bulk_import_active = False
            self._defer_file_sync = False
            self._existing_by_code = {}
            self._import_bank = None
            self._import_pending_rows = 0
            self.qbank_service._sync_questions_to_file(bank_id)

    def _maybe_batch_commit(self) -> None:
        self._import_pending_rows += 1
        if self._import_pending_rows >= IMPORT_BATCH_COMMIT_SIZE:
            self.qbank_db.commit()
            self._import_pending_rows = 0

    def _replace_options(self, question_id: str, options: List[Dict]) -> None:
        self.qbank_db.query(QuestionOptionV2).filter(
            QuestionOptionV2.question_id == question_id,
        ).delete(synchronize_session=False)
        for i, opt in enumerate(options):
            self.qbank_db.add(QuestionOptionV2(
                id=str(uuid.uuid4()),
                question_id=question_id,
                option_label=opt.get("label", chr(65 + i)),
                option_content=opt["content"],
                is_correct=opt.get("is_correct", False),
                sort_order=i,
            ))

    def _apply_import_item_to_question(
        self, question: QuestionV2, item: IntegrationQuestionCreate,
    ) -> None:
        qtype = QuestionType(item.type.value)
        difficulty = (
            item.difficulty.value if hasattr(item.difficulty, "value") else item.difficulty
        )
        question.stem = item.stem
        question.type = qtype
        question.difficulty = difficulty
        question.category = item.category
        question.explanation = item.explanation
        question.question_number = item.question_number
        question.meta_data = item.meta_data or {}
        question.tags = item.tags
        question.score = item.score
        question.updated_at = datetime.utcnow()
        options = self._options_to_dicts(item.options)
        if options and qtype in (QuestionType.single, QuestionType.multiple):
            self._replace_options(question.id, options)

    def _upsert_import_row(
        self,
        bank_id: str,
        item: IntegrationQuestionCreate,
        result: IntegrationImportResult,
    ) -> None:
        options = self._options_to_dicts(item.options)
        qtype = QuestionType(item.type.value)
        difficulty = (
            item.difficulty.value if hasattr(item.difficulty, "value") else item.difficulty
        )

        if item.external_id and item.external_id in self._existing_by_code:
            question = self._existing_by_code[item.external_id]
            self._apply_import_item_to_question(question, item)
            result.updated_count += 1
        else:
            question_id = str(uuid.uuid4())
            question = QuestionV2(
                id=question_id,
                bank_id=bank_id,
                question_code=item.external_id,
                stem=item.stem,
                type=qtype,
                difficulty=difficulty,
                category=item.category,
                explanation=item.explanation,
                question_number=item.question_number,
                meta_data=item.meta_data or {},
                tags=item.tags,
                score=item.score,
            )
            self.qbank_db.add(question)
            if options and qtype in (QuestionType.single, QuestionType.multiple):
                for i, opt in enumerate(options):
                    self.qbank_db.add(QuestionOptionV2(
                        id=str(uuid.uuid4()),
                        question_id=question_id,
                        option_label=opt.get("label", chr(65 + i)),
                        option_content=opt["content"],
                        is_correct=opt.get("is_correct", False),
                        sort_order=i,
                    ))
            self._import_bank.total_questions += 1
            self._import_bank.updated_at = datetime.utcnow()
            if item.external_id:
                self._existing_by_code[item.external_id] = question
            result.created_count += 1

        result.imported_count += 1
        self._maybe_batch_commit()

    def create_api_key(
        self, data: ApiKeyCreateRequest, created_by: int
    ) -> Tuple[IntegrationApiKey, str]:
        invalid = set(data.scopes) - ALL_SCOPES
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid scopes: {sorted(invalid)}")

        key_id, raw_key, prefix = generate_api_key()
        record = IntegrationApiKey(
            id=key_id,
            name=data.name,
            key_prefix=prefix,
            key_hash=hash_api_key(raw_key),
            scopes=data.scopes,
            allowed_bank_ids=data.allowed_bank_ids or None,
            rate_limit_per_minute=data.rate_limit_per_minute,
            ip_whitelist=data.ip_whitelist or None,
            owner_user_id=data.owner_user_id or created_by,
            created_by=created_by,
            expires_at=data.expires_at,
        )
        self.main_db.add(record)
        self.main_db.commit()
        self.main_db.refresh(record)
        return record, raw_key

    def revoke_api_key(self, key_id: str) -> None:
        record = self.main_db.query(IntegrationApiKey).filter(IntegrationApiKey.id == key_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="API Key not found")
        record.is_active = False
        record.updated_at = datetime.utcnow()
        self.main_db.commit()

    def log_audit(
        self,
        api_key_id: str,
        method: str,
        path: str,
        status_code: int,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request_summary: Optional[str] = None,
        commit: bool = True,
    ) -> None:
        log = IntegrationAuditLog(
            api_key_id=api_key_id,
            method=method,
            path=path,
            status_code=status_code,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            request_summary=request_summary,
        )
        self.main_db.add(log)
        if commit:
            self.main_db.commit()
        else:
            self.main_db.flush()

    def list_accessible_banks(
        self, owner_user_id: int, allowed_bank_ids: Optional[List[str]], skip: int, limit: int
    ) -> List[QuestionBankV2]:
        query = self.qbank_db.query(QuestionBankV2)
        if allowed_bank_ids:
            query = query.filter(QuestionBankV2.id.in_(allowed_bank_ids))
        else:
            query = query.filter(QuestionBankV2.creator_id == owner_user_id)
        return query.order_by(QuestionBankV2.created_at.desc()).offset(skip).limit(limit).all()

    def get_bank_or_404(self, bank_id: str) -> QuestionBankV2:
        bank = self.qbank_service.get_question_bank(bank_id)
        if not bank:
            raise_integration_error(
                404, ErrorCode.BANK_NOT_FOUND,
                f"题库不存在：{bank_id}",
                suggestion="请调用 GET /api/integration/banks 确认可用题库 ID",
                bank_id=bank_id,
            )
        return bank

    def _options_to_dicts(self, options) -> List[Dict]:
        if not options:
            return []
        result = []
        for i, opt in enumerate(options):
            if hasattr(opt, "label"):
                result.append({
                    "label": opt.label,
                    "content": opt.content,
                    "is_correct": opt.is_correct,
                })
            else:
                result.append(opt)
        return result

    def create_question(
        self, bank_id: str, data: IntegrationQuestionCreate, owner_user_id: int
    ) -> QuestionV2:
        bank = self.get_bank_or_404(bank_id)
        if data.external_id:
            existing = self.qbank_db.query(QuestionV2).filter(
                QuestionV2.bank_id == bank_id,
                QuestionV2.question_code == data.external_id,
            ).first()
            if existing:
                raise_integration_error(
                    409, ErrorCode.QUESTION_DUPLICATE,
                    f"external_id「{data.external_id}」已存在",
                    suggestion="使用 POST .../questions/upsert 或 batch upsert=true 进行更新",
                    external_id=data.external_id,
                    bank_id=bank_id,
                )

        question = self.qbank_service.add_question(
            bank_id=bank_id,
            stem=data.stem,
            type=QuestionType(data.type.value),
            options=self._options_to_dicts(data.options),
            meta_data=data.meta_data or {},
            difficulty=data.difficulty.value if hasattr(data.difficulty, "value") else data.difficulty,
            category=data.category,
            explanation=data.explanation,
            question_number=data.question_number,
            tags=data.tags,
            score=data.score,
            question_code=data.external_id,
            sync_to_file=not self._defer_file_sync,
            auto_commit=not self._bulk_import_active,
        )
        return question

    def update_question(
        self, question_id: str, data: IntegrationQuestionUpdate, owner_user_id: int
    ) -> QuestionV2:
        question = self.qbank_db.query(QuestionV2).filter(QuestionV2.id == question_id).first()
        if not question:
            raise_integration_error(
                404, ErrorCode.QUESTION_NOT_FOUND,
                f"题目不存在：{question_id}",
                suggestion="请确认 question_id 或改用 by-external-id 接口查询",
                question_id=question_id,
            )

        update_data = data.model_dump(exclude_unset=True)
        external_id = update_data.pop("external_id", None)
        options = update_data.pop("options", None)

        for key, value in update_data.items():
            if key == "type" and value is not None:
                value = QuestionType(value.value if hasattr(value, "value") else value)
            if key == "difficulty" and value is not None and hasattr(value, "value"):
                value = value.value
            if hasattr(question, key):
                setattr(question, key, value)

        if external_id is not None:
            question.question_code = external_id

        if options is not None:
            self.qbank_db.query(QuestionOptionV2).filter(
                QuestionOptionV2.question_id == question_id
            ).delete()
            for i, opt in enumerate(options):
                label = opt.get("label") if isinstance(opt, dict) else opt.label
                content = opt.get("content") if isinstance(opt, dict) else opt.content
                is_correct = opt.get("is_correct", False) if isinstance(opt, dict) else opt.is_correct
                self.qbank_db.add(QuestionOptionV2(
                    id=str(uuid.uuid4()),
                    question_id=question_id,
                    option_label=label or chr(65 + i),
                    option_content=content,
                    is_correct=is_correct,
                    sort_order=i,
                ))

        question.updated_at = datetime.utcnow()
        if self._bulk_import_active:
            self._maybe_batch_commit()
        else:
            self.qbank_db.commit()
            self.qbank_db.refresh(question)
            self._sync_to_file(question.bank_id)
        return question

    def upsert_question(
        self, bank_id: str, data: IntegrationQuestionCreate, owner_user_id: int
    ) -> Tuple[QuestionV2, bool]:
        if not data.external_id:
            raise_integration_error(
                400, ErrorCode.EXTERNAL_ID_REQUIRED,
                "upsert 操作必须提供 external_id",
                suggestion="在请求体中设置 external_id 字段作为远端题目唯一标识",
            )

        existing = self.qbank_db.query(QuestionV2).filter(
            QuestionV2.bank_id == bank_id,
            QuestionV2.question_code == data.external_id,
        ).first()

        if existing:
            update = IntegrationQuestionUpdate(**data.model_dump(exclude_unset=True))
            return self.update_question(existing.id, update, owner_user_id), False

        return self.create_question(bank_id, data, owner_user_id), True

    def batch_questions(
        self,
        bank_id: str,
        questions: List[IntegrationQuestionCreate],
        owner_user_id: int,
        upsert: bool = False,
    ) -> IntegrationBatchResult:
        result = IntegrationBatchResult(
            success=False, success_count=0, created_count=0, updated_count=0, failed_count=0, errors=[]
        )
        for index, item in enumerate(questions):
            try:
                if upsert:
                    _, created = self.upsert_question(bank_id, item, owner_user_id)
                    if created:
                        result.created_count += 1
                    else:
                        result.updated_count += 1
                else:
                    self.create_question(bank_id, item, owner_user_id)
                    result.created_count += 1
                result.success_count += 1
            except Exception as exc:
                result.failed_count += 1
                err = error_from_exception(exc, row=index, external_id=item.external_id)
                result.errors.append(err)
        return finalize_batch_result(result, total=len(questions))

    def delete_question(self, question_id: str) -> None:
        question = self.qbank_db.query(QuestionV2).filter(QuestionV2.id == question_id).first()
        if not question:
            raise_integration_error(
                404, ErrorCode.QUESTION_NOT_FOUND,
                f"题目不存在：{question_id}",
                question_id=question_id,
            )
        bank = question.bank
        bank.total_questions = max(0, bank.total_questions - 1)
        self.qbank_db.delete(question)
        self.qbank_db.commit()
        self.qbank_service._sync_questions_to_file(bank.id)

    def get_by_external_id(self, bank_id: str, external_id: str) -> QuestionV2:
        question = self.qbank_db.query(QuestionV2).filter(
            QuestionV2.bank_id == bank_id,
            QuestionV2.question_code == external_id,
        ).first()
        if not question:
            raise_integration_error(
                404, ErrorCode.QUESTION_NOT_FOUND,
                f"题库 {bank_id} 中未找到 external_id「{external_id}」",
                suggestion="确认 external_id 与导入时使用的 ID 前缀一致",
                bank_id=bank_id,
                external_id=external_id,
            )
        return question

    def _upsert_or_create(self, bank_id: str, item: IntegrationQuestionCreate, owner_user_id: int, result: IntegrationImportResult):
        if self._bulk_import_active:
            if item.external_id:
                self._upsert_import_row(bank_id, item, result)
            else:
                self.create_question(bank_id, item, owner_user_id)
                result.created_count += 1
                result.imported_count += 1
                self._maybe_batch_commit()
            return

        if item.external_id:
            _, created = self.upsert_question(bank_id, item, owner_user_id)
            if created:
                result.created_count += 1
            else:
                result.updated_count += 1
        else:
            self.create_question(bank_id, item, owner_user_id)
            result.created_count += 1
        result.imported_count += 1

    async def import_json_to_bank(
        self, bank_id: str, file: UploadFile, owner_user_id: int,
        external_id_prefix: str = "import",
    ) -> IntegrationImportResult:
        import time
        start = time.time()
        content = await file.read()
        if not content:
            raise_integration_error(
                400, ErrorCode.IMPORT_EMPTY_FILE, "JSON 文件为空",
                suggestion="请上传包含 questions 数组的有效 JSON 文件",
            )
        try:
            data = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise_integration_error(
                400, ErrorCode.IMPORT_JSON_INVALID, f"JSON 格式无效：{exc}",
                suggestion="确认文件为 UTF-8 编码，且结构为 {\"questions\": [...]} 或数组",
            )

        questions_data = data if isinstance(data, list) else data.get("questions", [])
        if not questions_data:
            raise_integration_error(
                400, ErrorCode.IMPORT_JSON_INVALID, "JSON 中未找到 questions 数组",
                suggestion="根节点应为数组，或包含 questions 字段的对象",
            )

        result = IntegrationImportResult(success=False, bank_id=bank_id, imported_count=0, source_files=["json"])

        with self._bulk_import_mode(bank_id):
            for i, q_data in enumerate(questions_data):
                try:
                    if not q_data.get("stem"):
                        result.skipped_count += 1
                        result.errors.append(make_error(
                            ErrorCode.IMPORT_ROW_ERROR, "题干 stem 为空", row=i + 1,
                            suggestion="每题必须包含 stem 字段",
                        ))
                        continue
                    ext = q_data.get("external_id") or q_data.get("id")
                    if ext and external_id_prefix and not str(ext).startswith(external_id_prefix):
                        ext = f"{external_id_prefix}-{ext}"
                    item = IntegrationQuestionCreate(
                        stem=q_data["stem"],
                        type=q_data.get("type", "single"),
                        external_id=ext,
                        options=q_data.get("options", []),
                        meta_data=q_data.get("meta_data") or {},
                        difficulty=q_data.get("difficulty", "medium"),
                        category=q_data.get("category"),
                        explanation=q_data.get("explanation"),
                        question_number=q_data.get("question_number") or q_data.get("number"),
                        tags=q_data.get("tags", []),
                        score=q_data.get("score", 1.0),
                    )
                    self._upsert_or_create(bank_id, item, owner_user_id, result)
                except Exception as exc:
                    result.failed_count += 1
                    result.errors.append(error_from_exception(
                        exc, row=i + 1, external_id=q_data.get("external_id"),
                    ))

        return finalize_import_result(result, start, total_rows=len(questions_data))

    def _process_csv_rows(
        self,
        bank_id: str,
        rows: list,
        owner_user_id: int,
        external_id_prefix: str,
        result: IntegrationImportResult,
    ) -> None:
        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                item, skip_reason = parse_csv_row(row, row_num, external_id_prefix)
                if skip_reason:
                    result.skipped_count += 1
                    continue
                self._upsert_or_create(bank_id, item, owner_user_id, result)
            except ValueError as exc:
                result.failed_count += 1
                result.errors.append(make_error(
                    ErrorCode.IMPORT_ROW_ERROR, str(exc), row=row_num,
                    external_id=build_external_id_safe(row, external_id_prefix),
                    suggestion="检查该行选项列与答案列是否匹配",
                ))
            except Exception as exc:
                result.failed_count += 1
                result.errors.append(error_from_exception(
                    exc, row=row_num, external_id=build_external_id_safe(row, external_id_prefix),
                ))

    def _import_csv_text(
        self,
        bank_id: str,
        text: str,
        owner_user_id: int,
        external_id_prefix: str = "import",
        source_file: str = "csv",
    ) -> IntegrationImportResult:
        import time
        start = time.time()
        if not text or not text.strip():
            raise_integration_error(
                400, ErrorCode.IMPORT_EMPTY_FILE, "CSV 文件内容为空",
                suggestion="请确认 CSV 包含表头和至少一行题目数据",
            )

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise_integration_error(
                400, ErrorCode.IMPORT_CSV_INVALID, "CSV 缺少表头行",
                suggestion="第一行应包含：题干,A,B,C,D,E,答案,题型 等列名",
            )

        rows = list(reader)
        result = IntegrationImportResult(
            success=False, bank_id=bank_id, imported_count=0, source_files=[source_file],
        )

        with self._bulk_import_mode(bank_id):
            self._process_csv_rows(bank_id, rows, owner_user_id, external_id_prefix, result)

        return finalize_import_result(result, start, total_rows=len(rows))

    async def import_csv_to_bank(
        self, bank_id: str, file: UploadFile, owner_user_id: int,
        external_id_prefix: str = "import",
    ) -> IntegrationImportResult:
        content = await file.read()
        text = content.decode("utf-8-sig")
        filename = file.filename or "upload.csv"
        result = self._import_csv_text(
            bank_id, text, owner_user_id, external_id_prefix, source_file=filename,
        )
        return result

    async def import_zip_to_bank(
        self, bank_id: str, file: UploadFile, owner_user_id: int,
        external_id_prefix: str = "import",
    ) -> IntegrationImportResult:
        import os
        import tempfile
        import time
        import zipfile

        start = time.time()
        content = await file.read()
        if not content:
            raise_integration_error(
                400, ErrorCode.IMPORT_EMPTY_FILE, "ZIP 文件为空",
                suggestion="请上传包含 CSV 或 questions.json 的有效 ZIP 压缩包",
            )

        merged = IntegrationImportResult(
            success=False, bank_id=bank_id, imported_count=0, source_files=[],
        )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "upload.zip")
                with open(zip_path, "wb") as f:
                    f.write(content)

                extract_dir = os.path.join(temp_dir, "extracted")
                try:
                    with zipfile.ZipFile(zip_path, "r") as zipf:
                        if not zipf.namelist():
                            raise_integration_error(
                                400, ErrorCode.IMPORT_ZIP_EMPTY, "ZIP 压缩包内没有文件",
                                suggestion="压缩包应至少包含一个 .csv 或 questions.json",
                            )
                        zipf.extractall(extract_dir)
                except zipfile.BadZipFile as exc:
                    raise_integration_error(
                        400, ErrorCode.IMPORT_ZIP_INVALID, f"ZIP 文件损坏或格式无效：{exc}",
                        suggestion="请确认上传的是标准 ZIP 格式文件",
                    )

                questions_json_path = None
                csv_paths: List[str] = []
                for root, _, files in os.walk(extract_dir):
                    for name in files:
                        path = os.path.join(root, name)
                        if name == "questions.json":
                            questions_json_path = path
                        elif name.lower().endswith(".csv"):
                            csv_paths.append(path)

                if not questions_json_path and not csv_paths:
                    raise_integration_error(
                        400, ErrorCode.IMPORT_ZIP_EMPTY,
                        "ZIP 中未找到 questions.json 或 CSV 文件",
                        suggestion="支持：questions.json，或含 题干/A/B/C/答案 列的 CSV",
                    )

                total_rows = 0
                with self._bulk_import_mode(bank_id):
                    if questions_json_path:
                        merged.source_files.append(os.path.basename(questions_json_path))
                        with open(questions_json_path, encoding="utf-8") as f:
                            data = json.load(f)
                        questions_data = data if isinstance(data, list) else data.get("questions", [])
                        total_rows += len(questions_data)
                        for i, q_data in enumerate(questions_data):
                            try:
                                ext = q_data.get("external_id") or q_data.get("id")
                                if ext and external_id_prefix:
                                    ext = f"{external_id_prefix}-{ext}"
                                item = IntegrationQuestionCreate(
                                    stem=q_data["stem"],
                                    type=q_data.get("type", "single"),
                                    external_id=ext,
                                    options=q_data.get("options", []),
                                    meta_data=q_data.get("meta_data") or {},
                                    difficulty=q_data.get("difficulty", "medium"),
                                    category=q_data.get("category"),
                                    explanation=q_data.get("explanation"),
                                    question_number=q_data.get("question_number") or q_data.get("number"),
                                    tags=q_data.get("tags", []),
                                    score=q_data.get("score", 1.0),
                                )
                                self._upsert_or_create(bank_id, item, owner_user_id, merged)
                            except Exception as exc:
                                merged.failed_count += 1
                                merged.errors.append(error_from_exception(exc, row=i + 1))

                    for csv_path in sorted(csv_paths):
                        fname = os.path.basename(csv_path)
                        merged.source_files.append(fname)
                        with open(csv_path, encoding="utf-8-sig") as f:
                            text = f.read()
                        reader = csv.DictReader(io.StringIO(text))
                        csv_rows = list(reader)
                        total_rows += len(csv_rows)
                        csv_partial = IntegrationImportResult(
                            success=False, bank_id=bank_id, imported_count=0, source_files=[fname],
                        )
                        self._process_csv_rows(
                            bank_id, csv_rows, owner_user_id, external_id_prefix, csv_partial,
                        )
                        merged.imported_count += csv_partial.imported_count
                        merged.created_count += csv_partial.created_count
                        merged.updated_count += csv_partial.updated_count
                        merged.skipped_count += csv_partial.skipped_count
                        merged.failed_count += csv_partial.failed_count
                        merged.errors.extend(csv_partial.errors)

        except HTTPException:
            raise

        return finalize_import_result(merged, start, total_rows=total_rows)
