import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../domain/screen_layout.dart';

const _indexKey = 'screen_designer.index';
const _layoutKeyPrefix = 'screen_designer.layout.';

/// Persists any number of named [ScreenLayout]s on the device — a screen is
/// no longer scoped to one class, so it needs its own name to be found
/// again. An index (the list of known names) lives alongside each layout so
/// the designer's "open a screen" list can be built without loading every
/// layout's full content.
class ScreenLayoutStore {
  const ScreenLayoutStore();

  Future<List<String>> listNames() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(_indexKey) ?? const [];
  }

  Future<ScreenLayout?> load(String name) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_layoutKeyPrefix$name');
    if (raw == null) return null;
    return ScreenLayout.fromJson(jsonDecode(raw) as Map<String, Object?>);
  }

  Future<void> save(ScreenLayout layout) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_layoutKeyPrefix${layout.name}', jsonEncode(layout.toJson()));
    final names = prefs.getStringList(_indexKey) ?? const [];
    if (!names.contains(layout.name)) {
      await prefs.setStringList(_indexKey, [...names, layout.name]);
    }
  }

  Future<void> delete(String name) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_layoutKeyPrefix$name');
    final names = prefs.getStringList(_indexKey) ?? const [];
    await prefs.setStringList(_indexKey, names.where((n) => n != name).toList());
  }
}
