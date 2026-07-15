import 'package:exam_master_app/core/constants/api_constants.dart';
import 'package:exam_master_app/core/constants/app_constants.dart';
import 'package:exam_master_app/routes/app_router.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('API 与路由常量已配置', () {
    expect(ApiConstants.apiBaseUrl, isNotEmpty);
    expect(AppConstants.appName, 'EXAM MASTER');
    expect(AppRoutes.home, '/home');
  });
}
