import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Where the signed-in session is kept between launches. An interface so tests
/// never touch the platform keystore.
abstract class TokenStorage {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

/// Keeps the session in the platform's secure storage (Android Keystore /
/// iOS Keychain), not in `shared_preferences`, which is plain text. The value
/// is the bearer token, so it is never logged or printed.
class SecureTokenStorage implements TokenStorage {
  // ignore: prefer_initializing_formals
  const SecureTokenStorage({FlutterSecureStorage storage = const FlutterSecureStorage()}) : _storage = storage;

  static const _key = 'modelia_collab_session';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read() => _storage.read(key: _key);

  @override
  Future<void> write(String value) => _storage.write(key: _key, value: value);

  @override
  Future<void> clear() => _storage.delete(key: _key);
}
