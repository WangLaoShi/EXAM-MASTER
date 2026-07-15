/// EXAM MASTER 学员端入口
///
/// 架构概览见项目 [README.md](../README.md)。
/// 分层：core（网络/存储）→ data（API/Repository/Model）→ presentation（Provider/Screen）
library;

import 'package:flutter/material.dart';

import 'app.dart';
import 'core/constants/api_constants.dart';
import 'core/storage/local_storage.dart';
import 'core/utils/logger.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  AppLogger.info('Initializing LocalStorage...');
  await LocalStorage.init();
  AppLogger.info('LocalStorage initialized');

  AppLogger.info('API Base URL: ${ApiConstants.apiBaseUrl}');
  AppLogger.info(
    'Environment: ${ApiConstants.useProduction ? "Production" : "Development"}',
  );

  runApp(const ExamMasterApp());
}

/// 兼容旧测试/引用
typedef MyApp = ExamMasterApp;
