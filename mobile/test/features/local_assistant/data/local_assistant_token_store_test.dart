import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/local_assistant/data/local_assistant_token_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('LocalAssistantTokenStore', () {
    test('nothing saved yet loads null', () async {
      const store = LocalAssistantTokenStore();

      expect(await store.load(), isNull);
    });

    test('save then load returns the same token', () async {
      const store = LocalAssistantTokenStore();

      await store.save('hf_example_token');

      expect(await store.load(), 'hf_example_token');
    });

    test('saving twice overwrites the previous token', () async {
      const store = LocalAssistantTokenStore();
      await store.save('hf_old_token');

      await store.save('hf_new_token');

      expect(await store.load(), 'hf_new_token');
    });

    test('clear removes the saved token', () async {
      const store = LocalAssistantTokenStore();
      await store.save('hf_example_token');

      await store.clear();

      expect(await store.load(), isNull);
    });
  });
}
