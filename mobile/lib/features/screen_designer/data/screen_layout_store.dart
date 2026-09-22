import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../domain/screen_layout.dart';

const _keyPrefix = 'screen_designer.layout.';

/// Persists one [ScreenLayout] per group name on the device (MVP scope: not
/// yet namespaced by backend, so two different backends with a
/// same-named group share a design — acceptable for a single-backend-at-a-time
/// workflow, revisit once multiple saved connections exist).
class ScreenLayoutStore {
  const ScreenLayoutStore();

  Future<ScreenLayout?> load(String groupName) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_keyPrefix$groupName');
    if (raw == null) return null;
    return ScreenLayout.fromJson(jsonDecode(raw) as Map<String, Object?>);
  }

  Future<void> save(ScreenLayout layout) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_keyPrefix${layout.groupName}', jsonEncode(layout.toJson()));
  }
}
