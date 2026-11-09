import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/auth_repository.dart';
import 'package:mobile/features/collab/data/token_storage.dart';
import 'package:mobile/features/collab/presentation/session_controller.dart';

class _MemoryStorage implements TokenStorage {
  String? value;

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String value) async => this.value = value;

  @override
  Future<void> clear() async => value = null;
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

  SessionController controller(MockClient mock) => SessionController(
    repository: AuthRepository(storage: storage, httpClient: mock),
    httpClient: mock,
  );

  test('starts restoring and becomes signed out when nothing is stored', () async {
    final c = controller(MockClient((r) async => _json({})));
    expect(c.status, SessionStatus.restoring);

    await c.restore();

    expect(c.status, SessionStatus.signedOut);
    expect(c.session, isNull);
  });

  test('signing in moves to signed in and exposes the user', () async {
    final c = controller(MockClient((r) async => _json(_loginBody)));
    await c.restore();

    await c.signIn(baseUrl: 'https://modelia.test', email: 'ana@acme.test', password: 'secret');

    expect(c.status, SessionStatus.signedIn);
    expect(c.session?.user.displayName, 'Ana');
    expect(c.errorMessage, isNull);
    expect(c.busy, isFalse);
  });

  test('a stored session restores straight into signed in', () async {
    await controller(MockClient((r) async => _json(_loginBody)))
        .signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

    final again = controller(MockClient((r) async => _json({})));
    await again.restore();

    expect(again.status, SessionStatus.signedIn);
  });

  test('empty fields are explained and never reach the network', () async {
    var calls = 0;
    final c = controller(MockClient((r) async {
      calls++;
      return _json(_loginBody);
    }));
    await c.restore();

    await c.signIn(baseUrl: '', email: 'a@b.c', password: 'x');
    expect(c.errorMessage, 'Escribe la dirección del servidor.');
    await c.signIn(baseUrl: 'https://modelia.test', email: '  ', password: 'x');
    expect(c.errorMessage, 'Escribe tu correo electrónico.');
    await c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: '');
    expect(c.errorMessage, 'Escribe tu contraseña.');

    expect(calls, 0);
    expect(c.status, SessionStatus.signedOut);
  });

  test('wrong credentials say so in neutral Spanish and stay signed out', () async {
    final c = controller(MockClient(
      (r) async => _json({'detail': 'Invalid email or password.', 'code': 'invalid_credentials'}, 401),
    ));
    await c.restore();

    await c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'bad');

    expect(c.errorMessage, 'Correo o contraseña incorrectos.');
    expect(c.status, SessionStatus.signedOut);
    expect(c.busy, isFalse);
  });

  test('being offline is explained and can be retried', () async {
    final c = controller(MockClient((r) async => throw http.ClientException('down')));
    await c.restore();

    await c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

    expect(c.errorMessage, contains('Sin conexión'));
    expect(c.status, SessionStatus.signedOut);
  });

  test('busy is true while the login is in flight', () async {
    final c = controller(MockClient((r) async => _json(_loginBody)));
    await c.restore();

    final future = c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');
    expect(c.busy, isTrue);
    await future;

    expect(c.busy, isFalse);
  });

  test('signing out forgets the session even without a connection', () async {
    final c = controller(MockClient((r) async {
      if (r.url.path.endsWith('revoke')) throw http.ClientException('offline');
      return _json(_loginBody);
    }));
    await c.restore();
    await c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');

    await c.signOut();

    expect(c.status, SessionStatus.signedOut);
    expect(c.session, isNull);
    expect(storage.value, isNull);
  });

  test('a token the server rejects ends the session with an explanation, once', () async {
    final c = controller(MockClient((r) async {
      if (r.url.path.endsWith('mobile-token')) return _json(_loginBody);
      return _json({'detail': 'Invalid or expired token.', 'code': 'invalid_token'}, 401);
    }));
    await c.restore();
    await c.signIn(baseUrl: 'https://modelia.test', email: 'a@b.c', password: 'x');
    var notifications = 0;
    c.addListener(() => notifications++);

    final api = c.api!; // two in-flight calls can both get the 401
    await expectLater(api.getJson('/api/orgs'), throwsA(anything));
    await expectLater(api.getJson('/api/orgs'), throwsA(anything));

    expect(c.status, SessionStatus.signedOut);
    expect(c.errorMessage, 'Tu sesión venció. Inicia sesión de nuevo.');
    expect(c.session, isNull);
    expect(storage.value, isNull);
    expect(notifications, 1);
  });
}
