import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

const _key = 'screen_designer_pending_actions';

/// The mutation a queued [PendingActionEntry] will replay — mirrors
/// [ScreenAction] minus `list`, since a read has no "pending" semantics and
/// is never queued.
enum PendingActionKind { create, update, delete }

/// One `create`/`update`/`delete` that failed because the request never
/// reached the server (see `ScreenActionFailure.isUnreachable`), queued for
/// an automatic or manual retry later. Carries everything needed to replay
/// the exact same request through [ScreenActionClient], plus a bit of
/// display context for a future "pending mutations" UI list.
class PendingActionEntry {
  const PendingActionEntry({
    required this.entryId,
    required this.kind,
    required this.deploymentBase,
    required this.collectionPath,
    this.recordId,
    this.body,
    required this.groupName,
    required this.layoutName,
    required this.queuedAt,
  });

  /// Identifies this queued entry so it can be removed again after a
  /// successful replay, without depending on list position.
  final String entryId;
  final PendingActionKind kind;
  final Uri deploymentBase;
  final String collectionPath;

  /// The record id an `update`/`delete` targets. Always null for `create`.
  final String? recordId;

  /// The request body a `create`/`update` sends. Always null for `delete`.
  final Map<String, Object?>? body;

  /// The connected class this mutation belongs to — display context only.
  final String groupName;

  /// The screen this mutation was triggered from — display context only.
  final String layoutName;
  final DateTime queuedAt;

  Map<String, Object?> toJson() => {
    'entryId': entryId,
    'kind': kind.name,
    'deploymentBase': deploymentBase.toString(),
    'collectionPath': collectionPath,
    'recordId': recordId,
    'body': body,
    'groupName': groupName,
    'layoutName': layoutName,
    'queuedAt': queuedAt.toIso8601String(),
  };

  factory PendingActionEntry.fromJson(Map<String, Object?> json) => PendingActionEntry(
    entryId: json['entryId'] as String,
    kind: PendingActionKind.values.byName(json['kind'] as String),
    deploymentBase: Uri.parse(json['deploymentBase'] as String),
    collectionPath: json['collectionPath'] as String,
    recordId: json['recordId'] as String?,
    body: (json['body'] as Map<String, Object?>?)?.cast<String, Object?>(),
    groupName: json['groupName'] as String? ?? '',
    layoutName: json['layoutName'] as String? ?? '',
    queuedAt: DateTime.parse(json['queuedAt'] as String),
  );
}

/// Persists the queue of offline `create`/`update`/`delete` mutations
/// (screen_designer's runtime buttons) as JSON in shared_preferences.
/// Mirrors [ScreenLayoutStore]/`LocalAssistantTokenStore`'s exact pattern —
/// a handful of pending mutations doesn't warrant a local database.
class PendingActionStore {
  const PendingActionStore();

  Future<List<PendingActionEntry>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return const [];
    final decoded = jsonDecode(raw) as List<Object?>;
    return [for (final item in decoded) PendingActionEntry.fromJson(item as Map<String, Object?>)];
  }

  Future<void> add(PendingActionEntry entry) async {
    final entries = await load();
    await _save([...entries, entry]);
  }

  Future<void> remove(PendingActionEntry entry) async {
    final entries = await load();
    await _save(entries.where((e) => e.entryId != entry.entryId).toList());
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  Future<void> _save(List<PendingActionEntry> entries) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode([for (final entry in entries) entry.toJson()]));
  }
}
