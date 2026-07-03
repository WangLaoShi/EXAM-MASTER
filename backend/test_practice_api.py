"""
Test script for Practice API endpoints
测试脚本 - 验证练习 API 与各练习模式
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"

PRACTICE_MODES = [
    ("sequential", "顺序练习"),
    ("random", "随机练习"),
    ("wrong_only", "错题专练"),
    ("favorite_only", "收藏专练"),
    ("unpracticed", "未做题"),
]


def login():
    """登录获取 token"""
    print("\n=== 1. 测试登录 ===")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "admin", "password": "admin123"},
        timeout=30,
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✓ 登录成功，获取到 token")
        return token
    print(f"✗ 登录失败: {response.text}")
    return None


def get_question_banks(token):
    """获取题库列表"""
    print("\n=== 2. 测试获取题库列表 ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/qbank/banks/", headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        banks = response.json()
        print(f"✓ 成功获取题库列表，共 {len(banks)} 个题库")
        if banks:
            print(f"  第一个题库: {banks[0].get('name')} (ID: {banks[0].get('id')})")
            return banks[0].get("id")
        return None
    print(f"✗ 获取题库失败: {response.text}")
    return None


def preview_practice_modes(token, bank_id):
    """预览各练习模式可用题量"""
    print("\n=== 3. 测试练习模式预览 ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/practice/modes/preview",
        headers=headers,
        params={"bank_id": bank_id},
        timeout=30,
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"✗ 模式预览失败: {response.text}")
        return None
    preview = response.json()
    print("✓ 模式预览成功")
    for mode, label in PRACTICE_MODES:
        count = preview.get(mode, 0)
        print(f"  {label} ({mode}): {count} 题")
    return preview


def create_practice_session(token, bank_id, mode, resume_if_exists=False):
    """创建练习会话"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {"bank_id": bank_id, "mode": mode}
    response = requests.post(
        f"{BASE_URL}/practice/sessions",
        headers=headers,
        json=data,
        params={"resume_if_exists": resume_if_exists},
        timeout=30,
    )
    return response


def test_all_practice_modes(token, bank_id, preview):
    """逐个测试五种练习模式"""
    print("\n=== 4. 测试各练习模式创建会话 ===")
    created = []
    for mode, label in PRACTICE_MODES:
        count = (preview or {}).get(mode, 0)
        print(f"\n--- {label} ({mode}) ---")
        response = create_practice_session(token, bank_id, mode, resume_if_exists=False)
        print(f"Status: {response.status_code}")
        if count == 0:
            if response.status_code == 404:
                print(f"✓ 预期无题可用: {response.json().get('detail')}")
            else:
                print(f"✗ 预期 404，实际: {response.text}")
            continue
        if response.status_code != 200:
            print(f"✗ 创建失败: {response.text}")
            continue
        session = response.json()
        print("✓ 创建成功")
        print(f"  会话ID: {session.get('id')}")
        print(f"  题目总数: {session.get('total_questions')} (预览 {count})")
        if session.get("total_questions") != count:
            print("✗ 题量与预览不一致")
        else:
            print("✓ 题量与预览一致")
        created.append(session.get("id"))
    return created


def get_current_question(token, session_id):
    """获取当前题目"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/practice/sessions/{session_id}/current",
        headers=headers,
        timeout=30,
    )
    if response.status_code != 200:
        print(f"✗ 获取题目失败: {response.text}")
        return None
    return response.json()


def submit_answer(token, session_id, question_id):
    """提交答案"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "question_id": question_id,
        "user_answer": {"answer": "A"},
        "time_spent": 30,
    }
    response = requests.post(
        f"{BASE_URL}/practice/sessions/{session_id}/submit",
        headers=headers,
        json=data,
        timeout=30,
    )
    return response.status_code == 200


def smoke_flow_with_sequential(token, session_id):
    """对顺序练习会话做完整答题冒烟"""
    print("\n=== 5. 顺序练习完整流程冒烟 ===")
    question = get_current_question(token, session_id)
    if not question:
        print("✗ 无法获取当前题目")
        return False
    print(f"✓ 当前题目: {question.get('current_index')}/{question.get('total_questions')}")
    if not submit_answer(token, session_id, question.get("id")):
        print("✗ 提交答案失败")
        return False
    print("✓ 提交答案成功")
    return True


def main():
    """主测试流程"""
    print("=" * 60)
    print("开始测试 Practice API（含全部练习模式）")
    print("=" * 60)

    token = login()
    if not token:
        print("\n✗ 测试终止: 无法获取 token")
        return

    bank_id = get_question_banks(token)
    if not bank_id:
        print("\n✗ 测试终止: 无法获取题库 ID")
        return

    preview = preview_practice_modes(token, bank_id)
    session_ids = test_all_practice_modes(token, bank_id, preview)

    sequential_session = None
    if preview and preview.get("sequential", 0) > 0:
        response = create_practice_session(token, bank_id, "sequential", resume_if_exists=False)
        if response.status_code == 200:
            sequential_session = response.json().get("id")

    if sequential_session and not smoke_flow_with_sequential(token, sequential_session):
        print("\n✗ 顺序练习流程冒烟失败")
        return

    print("\n" + "=" * 60)
    print(f"✓ 练习模式测试完成（成功创建 {len(session_ids)} 个模式会话）")
    print("=" * 60)


if __name__ == "__main__":
    main()
