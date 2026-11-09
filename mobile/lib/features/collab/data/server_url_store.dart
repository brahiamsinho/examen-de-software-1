import 'package:shared_preferences/shared_preferences.dart';

const _serverUrlKey = 'collab_server_url';

/// Remembers the Modelia server address the person typed, so a real phone
/// (which cannot use the emulator's `10.0.2.2`) does not ask for it on every
/// launch. The address is not a secret.
class ServerUrlStore {
  const ServerUrlStore();

  Future<String?> load() async => (await SharedPreferences.getInstance()).getString(_serverUrlKey);

  Future<void> save(String url) async => (await SharedPreferences.getInstance()).setString(_serverUrlKey, url);
}
