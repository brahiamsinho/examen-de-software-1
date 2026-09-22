import 'package:shared_preferences/shared_preferences.dart';

const _hfTokenKey = 'local_assistant_hf_token';

/// Persists the user's own Hugging Face access token on-device, so the
/// on-device model download (local_assistant feature) doesn't ask for it on
/// every app launch. Mirrors [ScreenLayoutStore]'s shared_preferences
/// pattern. The token value is never logged or printed anywhere.
class LocalAssistantTokenStore {
  const LocalAssistantTokenStore();

  Future<String?> load() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_hfTokenKey);
  }

  Future<void> save(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_hfTokenKey, token);
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_hfTokenKey);
  }
}
