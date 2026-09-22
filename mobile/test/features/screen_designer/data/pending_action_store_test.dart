import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/screen_designer/data/pending_action_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

PendingActionEntry _entry({
  String entryId = 'e1',
  PendingActionKind kind = PendingActionKind.create,
  String? recordId,
}) => PendingActionEntry(
  entryId: entryId,
  kind: kind,
  deploymentBase: Uri.parse('https://demo.example.com/gen/abc/'),
  collectionPath: '/api/class-as',
  recordId: recordId,
  body: const {'edad': '20'},
  groupName: 'class-a-controller',
  layoutName: 'My screen',
  queuedAt: DateTime.utc(2024, 1, 1, 12),
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('PendingActionStore', () {
    test('nothing queued yet loads an empty list', () async {
      const store = PendingActionStore();

      expect(await store.load(), isEmpty);
    });

    test('add then load round-trips every field', () async {
      const store = PendingActionStore();
      final entry = _entry(kind: PendingActionKind.update, recordId: '7');

      await store.add(entry);
      final loaded = await store.load();

      expect(loaded, hasLength(1));
      final loadedEntry = loaded.single;
      expect(loadedEntry.entryId, 'e1');
      expect(loadedEntry.kind, PendingActionKind.update);
      expect(loadedEntry.deploymentBase, Uri.parse('https://demo.example.com/gen/abc/'));
      expect(loadedEntry.collectionPath, '/api/class-as');
      expect(loadedEntry.recordId, '7');
      expect(loadedEntry.body, {'edad': '20'});
      expect(loadedEntry.groupName, 'class-a-controller');
      expect(loadedEntry.layoutName, 'My screen');
      expect(loadedEntry.queuedAt, DateTime.utc(2024, 1, 1, 12));
    });

    test('a create entry with no record id round-trips a null recordId', () async {
      const store = PendingActionStore();
      await store.add(_entry());

      final loaded = await store.load();

      expect(loaded.single.recordId, isNull);
    });

    test('add appends without disturbing earlier entries', () async {
      const store = PendingActionStore();
      await store.add(_entry(entryId: 'e1'));
      await store.add(_entry(entryId: 'e2'));

      final loaded = await store.load();

      expect(loaded.map((e) => e.entryId), ['e1', 'e2']);
    });

    test('remove drops only the matching entry', () async {
      const store = PendingActionStore();
      await store.add(_entry(entryId: 'e1'));
      await store.add(_entry(entryId: 'e2'));

      await store.remove(_entry(entryId: 'e1'));

      final loaded = await store.load();
      expect(loaded.map((e) => e.entryId), ['e2']);
    });

    test('clear empties the queue', () async {
      const store = PendingActionStore();
      await store.add(_entry(entryId: 'e1'));
      await store.add(_entry(entryId: 'e2'));

      await store.clear();

      expect(await store.load(), isEmpty);
    });
  });
}
