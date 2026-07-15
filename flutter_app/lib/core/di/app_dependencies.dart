/// 应用级依赖装配（手动 DI，无 get_it）
///
/// 在 [ExamMasterApp] 根部创建一次，经 Provider 向下注入：
/// DioClient → *Api → *Repository → *Provider
///
/// 注意：部分 Screen（收藏/错题/统计）仍自行 `DioClient()`，与全局实例分离，
/// Token 依赖 ApiInterceptor 读 SharedPreferences，功能可用但架构不一致。
library;

import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';

import '../network/dio_client.dart';
import '../storage/local_storage.dart';
import '../../data/datasources/remote/auth_api.dart';
import '../../data/datasources/remote/favorites_api.dart';
import '../../data/datasources/remote/practice_api.dart';
import '../../data/datasources/remote/question_bank_api.dart';
import '../../data/repositories/auth_repository.dart';
import '../../data/repositories/favorites_repository.dart';
import '../../data/repositories/practice_repository.dart';
import '../../data/repositories/question_bank_repository.dart';
import '../../presentation/providers/auth_provider.dart';
import '../../presentation/providers/practice_provider.dart';
import '../../presentation/providers/question_bank_provider.dart';

/// 根 Widget 所需的 Provider 列表
List<SingleChildWidget> buildAppProviders() {
  final dioClient = DioClient();
  final localStorage = LocalStorage();

  final authRepository = AuthRepository(
    authApi: AuthApi(dioClient),
    localStorage: localStorage,
  );
  final questionBankRepository = QuestionBankRepository(
    api: QuestionBankApi(dioClient),
  );
  final practiceRepository = PracticeRepository(
    api: PracticeApi(dioClient),
  );
  final favoritesRepository = FavoritesRepository(
    api: FavoritesApi(dioClient),
  );

  return [
    ChangeNotifierProvider(
      create: (_) => AuthProvider(authRepository: authRepository),
    ),
    ChangeNotifierProvider(
      create: (_) => QuestionBankProvider(repository: questionBankRepository),
    ),
    ChangeNotifierProxyProvider<AuthProvider, PracticeProvider>(
      create: (context) => PracticeProvider(
        repository: practiceRepository,
        questionBankRepository: questionBankRepository,
        favoritesRepository: favoritesRepository,
        getUserId: () => context.read<AuthProvider>().currentUser?.id,
      ),
      update: (context, authProvider, previous) => PracticeProvider(
        repository: practiceRepository,
        questionBankRepository: questionBankRepository,
        favoritesRepository: favoritesRepository,
        getUserId: () => authProvider.currentUser?.id,
      ),
    ),
  ];
}
