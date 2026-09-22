import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import 'pending_action_store.dart';
import 'screen_action_client.dart';

/// Replays queued offline mutations (see [PendingActionStore]) through the
/// SAME [ScreenActionClient] used for a live attempt, either on demand
/// (`syncNow`, e.g. a manual "sync now" tap) or automatically when
/// `connectivity_plus` reports connectivity restored.
///
/// `connectivity_plus` only reports interface-level state, never real
/// reachability — it is used purely as a HINT to retry. The actual HTTP
/// call remains the ground truth: a retry can still fail and the entry
/// stays queued.
class PendingActionSyncService {
  PendingActionSyncService({
    required this.actionClient,
    required this.store,
    Stream<List<ConnectivityResult>>? connectivityStream,
  }) : _connectivityStream = connectivityStream ?? Connectivity().onConnectivityChanged;

  final ScreenActionClient actionClient;
  final PendingActionStore store;
  final Stream<List<ConnectivityResult>> _connectivityStream;
  StreamSubscription<List<ConnectivityResult>>? _subscription;

  /// How many mutations are currently queued — a plain `ValueNotifier`,
  /// matching this codebase's `setState`-only state management (no external
  /// state package is in use).
  final ValueNotifier<int> pendingCount = ValueNotifier<int>(0);

  Future<void> refreshPendingCount() async {
    pendingCount.value = (await store.load()).length;
  }

  /// Starts reacting to connectivity-restored hints. Safe to call more than
  /// once — only the first call subscribes.
  void startListening() {
    _subscription ??= _connectivityStream.listen(
      (results) {
        if (results.any((result) => result != ConnectivityResult.none)) {
          syncNow();
        }
      },
      // A platform without connectivity_plus wired up (or a plugin failure)
      // must never crash the page — it just means no automatic retry hint,
      // manual "sync now" still works.
      onError: (Object _) {},
    );
    refreshPendingCount();
  }

  void stopListening() {
    _subscription?.cancel();
    _subscription = null;
  }

  /// Replays every queued entry, in order, through the same client methods
  /// a live button press would use. Each attempt is independent: a failure
  /// leaves that entry queued and moves on to the next one rather than
  /// stopping the batch (no rollback — mirrors how this project's
  /// multi-command voice feature already handles partial failure). An entry
  /// that fails to replay is never re-queued as a new entry — it is already
  /// in the store.
  Future<void> syncNow() async {
    final entries = await store.load();
    for (final entry in entries) {
      final result = await _replay(entry);
      if (result is ScreenActionSuccess) {
        await store.remove(entry);
      }
    }
    await refreshPendingCount();
  }

  Future<ScreenActionResult> _replay(PendingActionEntry entry) => switch (entry.kind) {
    PendingActionKind.create => actionClient.create(entry.deploymentBase, entry.collectionPath, entry.body ?? const {}),
    PendingActionKind.update => actionClient.update(
      entry.deploymentBase,
      entry.collectionPath,
      entry.recordId!,
      entry.body ?? const {},
    ),
    PendingActionKind.delete => actionClient.delete(entry.deploymentBase, entry.collectionPath, entry.recordId!),
  };
}
