import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/screen_designer/data/pending_action_store.dart';
import 'package:mobile/features/screen_designer/data/pending_action_sync_service.dart';
import 'package:mobile/features/screen_designer/data/screen_action_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

PendingActionEntry _entry({
  String entryId = 'e1',
  PendingActionKind kind = PendingActionKind.create,
  String? recordId,
}) => PendingActionEntry(
  entryId: entryId,
  kind: kind,
  deploymentBase: Uri.parse('http://h/gen/abc/'),
  collectionPath: '/api/class-as',
  recordId: recordId,
  body: const {'edad': '20'},
  groupName: 'class-a-controller',
  layoutName: 'My screen',
  queuedAt: DateTime.utc(2024, 1, 1),
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('PendingActionSyncService', () {
    test('syncNow replays a queued create and removes it on success', () async {
      const store = PendingActionStore();
      await store.add(_entry());
      final client = ScreenActionClient(
        httpClient: MockClient((_) async => http.Response('', 201)),
        timeout: const Duration(seconds: 1),
      );
      final service = PendingActionSyncService(actionClient: client, store: store);

      await service.syncNow();

      expect(await store.load(), isEmpty);
      expect(service.pendingCount.value, 0);
    });

    test('a failed replay stays queued and does not block later entries', () async {
      const store = PendingActionStore();
      await store.add(_entry(entryId: 'e1'));
      await store.add(_entry(entryId: 'e2'));
      var call = 0;
      final client = ScreenActionClient(
        httpClient: MockClient((_) async {
          call++;
          if (call == 1) return http.Response('nope', 500);
          return http.Response('', 201);
        }),
        timeout: const Duration(seconds: 1),
      );
      final service = PendingActionSyncService(actionClient: client, store: store);

      await service.syncNow();

      final remaining = await store.load();
      expect(remaining.map((e) => e.entryId), ['e1']);
      expect(service.pendingCount.value, 1);
    });

    test('replays update and delete entries against their record id', () async {
      const store = PendingActionStore();
      await store.add(_entry(kind: PendingActionKind.delete, recordId: '7'));
      late Uri seenUrl;
      late String seenMethod;
      final client = ScreenActionClient(
        httpClient: MockClient((request) async {
          seenUrl = request.url;
          seenMethod = request.method;
          return http.Response('', 204);
        }),
        timeout: const Duration(seconds: 1),
      );
      final service = PendingActionSyncService(actionClient: client, store: store);

      await service.syncNow();

      expect(seenMethod, 'DELETE');
      expect(seenUrl.toString(), 'http://h/gen/abc/api/class-as/7');
      expect(await store.load(), isEmpty);
    });

    test('refreshPendingCount reflects what is currently queued', () async {
      const store = PendingActionStore();
      await store.add(_entry(entryId: 'e1'));
      await store.add(_entry(entryId: 'e2'));
      final client = ScreenActionClient(httpClient: MockClient((_) async => http.Response('', 201)));
      final service = PendingActionSyncService(actionClient: client, store: store);

      await service.refreshPendingCount();

      expect(service.pendingCount.value, 2);
    });

    test('a connectivity-restored event triggers an automatic sync', () async {
      const store = PendingActionStore();
      await store.add(_entry());
      final client = ScreenActionClient(
        httpClient: MockClient((_) async => http.Response('', 201)),
        timeout: const Duration(seconds: 1),
      );
      final controller = StreamController<List<ConnectivityResult>>();
      final service = PendingActionSyncService(
        actionClient: client,
        store: store,
        connectivityStream: controller.stream,
      );
      service.startListening();

      controller.add([ConnectivityResult.wifi]);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(await store.load(), isEmpty);

      service.stopListening();
      await controller.close();
    });

    test('a connectivity event that is still "none" does not trigger a sync', () async {
      const store = PendingActionStore();
      await store.add(_entry());
      var called = false;
      final client = ScreenActionClient(
        httpClient: MockClient((_) async {
          called = true;
          return http.Response('', 201);
        }),
        timeout: const Duration(seconds: 1),
      );
      final controller = StreamController<List<ConnectivityResult>>();
      final service = PendingActionSyncService(
        actionClient: client,
        store: store,
        connectivityStream: controller.stream,
      );
      service.startListening();

      controller.add([ConnectivityResult.none]);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(called, isFalse);
      expect(await store.load(), hasLength(1));

      service.stopListening();
      await controller.close();
    });

    test('stopListening stops reacting to further connectivity events', () async {
      const store = PendingActionStore();
      await store.add(_entry());
      var calls = 0;
      final client = ScreenActionClient(
        httpClient: MockClient((_) async {
          calls++;
          return http.Response('', 201);
        }),
        timeout: const Duration(seconds: 1),
      );
      final controller = StreamController<List<ConnectivityResult>>();
      final service = PendingActionSyncService(
        actionClient: client,
        store: store,
        connectivityStream: controller.stream,
      );
      service.startListening();
      service.stopListening();

      controller.add([ConnectivityResult.wifi]);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(calls, 0);

      await controller.close();
    });
  });
}
