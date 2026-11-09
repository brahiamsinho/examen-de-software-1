import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/auth_repository.dart';
import 'package:mobile/features/collab/data/token_storage.dart';
import 'package:mobile/features/collab/domain/api_failure.dart';

class _MemoryStorage implements TokenStorage {
  String? value;
  int clears = 0;

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String value) async => this.value = value;

  @override
  Future<void> clear() async {
    value = null;
    clears++;
  }
}

class _ThrowingStorage implements TokenStorage {
  @override
  Future<String?> read() async => throw StateError('keystore unavailable');

  @override
  Future<void> write(String value) async => throw StateError('keystore unavailable');

  @override
  Future<void> clear() async => throw StateError('keystore unavailable');
}

const _loginBody = {
  'token': 'raw-token',
  'expires_at': '2099-01-01T00:00:00Z',
  'user': {'id': 'u1', 'email': 'ana@acme.test', 'full_name': 'Ana', 'is_verified': false},
};

http.Response _json(Object body, [int status = 200]) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

void main() {
  late _MemoryStorage storage;

  setUp(() => storage = _MemoryStorage());

  AuthRepository repo(MockClient mock) => AuthRepository(storage: storage, httpClient: mock);

  group('signIn', () {
    test('posts the credentials and the device name, stores the session and returns it', () async {
      late http.Request seen;
      final repository = repo(MockClient((r) async {
        seen = r;
        return _json(_loginBody);
      }));

      final session = await repository.signIn(
        baseUrl: 'https://modelia.test',
        email: ' ana@acme.test ',
        password: 'secret-pass',
      );

      expect(seen.url.toString(), 'https://modelia.test/api/auth/mobile-token');
      expect(seen.method, 'POST');
      final sent = jsonDecode(seen.body) as Map<String, dynamic>;
      expect(sent['email'], 'ana@acme.test');
      expect(sent['password'], 'secret-pass');
      expect(sent['device_name'], isNotEmpty);
      expect(session.token, 'raw-token');
      expect(session.user.fullName, 'Ana');
      expect(session.expiresAt.isUtc, isTrue);
      expect(session.baseUrl, 'https://modelia.test');
      expect(storage.value, isNotNull);
    });

    test('the token is stored once as one opaque string, never in plain extra places', () async {
      final repository = repo(MockClient((r) async => _json(_loginBody)));

      await repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

      expect(storage.value, contains('raw-token'));
      expect(storage.clears, 0);
    });

    test('bad credentials surface the backend message and store nothing', () async {
      final repository = repo(MockClient(
        (r) async => _json({'detail': 'Invalid email or password.', 'code': 'invalid_credentials'}, 401),
      ));

      await expectLater(
        repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'bad'),
        throwsA(isA<ApiFailure>().having((e) => e.message, 'message', 'Invalid email or password.')),
      );
      expect(storage.value, isNull);
    });

    test('a login response without a token is unexpected, not a crash', () async {
      final repository = repo(MockClient((r) async => _json({'user': {}})));

      await expectLater(
        repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x'),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.unexpected)),
      );
      expect(storage.value, isNull);
    });

    test('an empty server URL is rejected before any request', () async {
      var calls = 0;
      final repository = repo(MockClient((r) async {
        calls++;
        return _json(_loginBody);
      }));

      await expectLater(
        repository.signIn(baseUrl: '  ', email: 'a@b.c', password: 'x'),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.validation)),
      );
      expect(calls, 0);
    });
  });

  group('restore', () {
    test('returns the stored session while it has not expired', () async {
      final repository = repo(MockClient((r) async => _json(_loginBody)));
      await repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

      final restored = await repo(MockClient((r) async => _json({}))).restore();

      expect(restored?.token, 'raw-token');
      expect(restored?.user.email, 'ana@acme.test');
    });

    test('nothing stored restores nothing', () async {
      expect(await repo(MockClient((r) async => _json({}))).restore(), isNull);
    });

    test('an expired session is dropped from storage', () async {
      storage.value = jsonEncode({
        'token': 't',
        'expires_at': '2000-01-01T00:00:00Z',
        'base_url': 'https://modelia.test',
        'user': {'id': 'u', 'email': 'a@b.c', 'full_name': ''},
      });

      expect(await repo(MockClient((r) async => _json({}))).restore(), isNull);
      expect(storage.value, isNull);
    });

    test('a storage that cannot be read restores nothing instead of hanging the app', () async {
      final repository = AuthRepository(storage: _ThrowingStorage(), httpClient: MockClient((r) async => _json({})));

      expect(await repository.restore(), isNull);
    });

    test('a corrupted stored value is dropped instead of crashing', () async {
      storage.value = '{not json';

      expect(await repo(MockClient((r) async => _json({}))).restore(), isNull);
      expect(storage.value, isNull);
    });
  });

  group('signOut', () {
    test('revokes the token on the server and clears the device', () async {
      final seen = <http.Request>[];
      final repository = repo(MockClient((r) async {
        seen.add(r);
        return r.url.path.endsWith('mobile-token') ? _json(_loginBody) : http.Response('', 204);
      }));
      final session = await repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

      await repository.signOut(session);

      expect(seen.last.url.path, '/api/auth/mobile-token/revoke');
      expect(seen.last.headers['Authorization'], 'Bearer raw-token');
      expect(storage.value, isNull);
    });

    test('still clears the device when the phone is offline', () async {
      final repository = repo(MockClient((r) async {
        if (r.url.path.endsWith('revoke')) throw http.ClientException('offline');
        return _json(_loginBody);
      }));
      final session = await repository.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

      await repository.signOut(session);

      expect(storage.value, isNull);
    });
  });
}
