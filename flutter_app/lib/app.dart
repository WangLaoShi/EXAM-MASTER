/// 根 Widget：主题 + Provider + 路由
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/constants/app_constants.dart';
import 'core/di/app_dependencies.dart';
import 'routes/app_router.dart';

class ExamMasterApp extends StatelessWidget {
  const ExamMasterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: buildAppProviders(),
      child: MaterialApp(
        title: 'EXAM MASTER',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(AppConstants.primaryColorValue),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 0,
          ),
        ),
        initialRoute: AppRoutes.splash,
        routes: appRoutes,
        onGenerateRoute: onGenerateRoute,
      ),
    );
  }
}
