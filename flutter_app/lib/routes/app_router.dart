/// 命名路由与带参数页面跳转
///
/// 固定路由见 [routes]；需传参的页面在 [onGenerateRoute] 中解析 arguments。
library;

import 'package:flutter/material.dart';

import '../data/models/practice_session_model.dart';
import '../presentation/screens/auth/change_password_screen.dart';
import '../presentation/screens/auth/login_screen.dart';
import '../presentation/screens/auth/register_screen.dart';
import '../presentation/screens/browse/browse_questions_screen.dart';
import '../presentation/screens/favorites/favorites_list_screen.dart';
import '../presentation/screens/home/main_screen.dart';
import '../presentation/screens/practice/practice_screen.dart';
import '../presentation/screens/question_bank/question_bank_detail_screen.dart';
import '../presentation/screens/settings/settings_screen.dart';
import '../presentation/screens/splash_screen.dart';
import '../presentation/screens/wrong_questions/wrong_questions_list_screen.dart';

abstract final class AppRoutes {
  static const splash = '/';
  static const login = '/login';
  static const register = '/register';
  static const home = '/home';
  static const settings = '/settings';
  static const changePassword = '/change-password';
  static const questionBankDetail = '/question-bank-detail';
  static const practice = '/practice';
  static const favorites = '/favorites';
  static const wrongQuestions = '/wrong-questions';
  static const browseQuestions = '/browse-questions';
}

Map<String, WidgetBuilder> get appRoutes => {
      AppRoutes.splash: (_) => const SplashScreen(),
      AppRoutes.login: (_) => const LoginScreen(),
      AppRoutes.register: (_) => const RegisterScreen(),
      AppRoutes.home: (_) => const MainScreen(),
      AppRoutes.settings: (_) => const SettingsScreen(),
      AppRoutes.changePassword: (_) => const ChangePasswordScreen(),
    };

Route<dynamic>? onGenerateRoute(RouteSettings settings) {
  switch (settings.name) {
    case AppRoutes.questionBankDetail:
      final bankId = settings.arguments as String;
      return MaterialPageRoute(
        builder: (_) => QuestionBankDetailScreen(bankId: bankId),
      );
    case AppRoutes.practice:
      final args = settings.arguments as Map<String, dynamic>;
      return MaterialPageRoute(
        builder: (_) => PracticeScreen(
          bankId: args['bankId'] as String,
          mode: args['mode'] as PracticeMode,
        ),
      );
    case AppRoutes.favorites:
      final args = settings.arguments as Map<String, dynamic>;
      return MaterialPageRoute(
        builder: (_) => FavoritesListScreen(bankId: args['bankId'] as String),
      );
    case AppRoutes.wrongQuestions:
      final args = settings.arguments as Map<String, dynamic>;
      return MaterialPageRoute(
        builder: (_) => WrongQuestionsListScreen(bankId: args['bankId'] as String),
      );
    case AppRoutes.browseQuestions:
      final args = settings.arguments as Map<String, dynamic>;
      return MaterialPageRoute(
        builder: (_) => BrowseQuestionsScreen(bankId: args['bankId'] as String),
      );
    default:
      return null;
  }
}
