import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/auth_repository.dart';
import 'package:mobile/features/collab/data/token_storage.dart';
import 'package:mobile/features/collab/presentation/collab_gate.dart';
import 'package:mobile/features/collab/presentation/session_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

Future<SessionController> _signedIn(WidgetTester tester, MockClient mock) async {
  final controller = SessionController(
    repository: AuthRepository(storage: _MemoryStorage(), httpClient: mock),
    httpClient: mock,
  );
  await tester.pumpWidget(MaterialApp(home: CollabGate(controller: controller, initialServerUrl: 'https://modelia.test')));
  await tester.pumpAndSettle();
  await tester.enterText(find.widgetWithText(TextField, 'Correo electrónico'), 'ana@acme.test');
  await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'secret');
  await tester.tap(find.text('Iniciar sesión'));
  await tester.pumpAndSettle();
  return controller;
}

http.Response _route(http.Request r, {Map<String, http.Response>? extra}) {
  final path = r.url.path;
  if (extra != null && extra.containsKey(path)) return extra[path]!;
  if (path == '/api/auth/mobile-token') return _json(_loginBody);
  if (path == '/api/orgs') {
    return _json([
      {'id': '1', 'name': 'Acme', 'slug': 'acme', 'plan': 'STARTER', 'my_role': 'OWNER'},
      {'id': '2', 'name': 'Beta', 'slug': 'beta', 'plan': 'STARTER', 'my_role': 'VIEWER'},
    ]);
  }
  if (path == '/api/orgs/acme/documents') {
    return _json([
      {'id': 'd1', 'name': 'Ventas', 'revision': 3, 'updated_at': '2026-11-08T10:00:00Z'},
      {'id': 'd2', 'name': 'Inventario', 'revision': 1, 'updated_at': '2026-11-07T10:00:00Z'},
    ]);
  }
  return _json({'detail': 'Not found'}, 404);
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('after login the person sees their organizations with their role', (tester) async {
    await _signedIn(tester, MockClient((r) async => _route(r)));

    expect(find.text('Acme'), findsOneWidget);
    expect(find.text('Beta'), findsOneWidget);
    expect(find.text('Propietario'), findsOneWidget);
    expect(find.text('Lector'), findsOneWidget);
    expect(find.textContaining('Ana'), findsWidgets);
  });

  testWidgets('opening an organization lists its diagrams', (tester) async {
    await _signedIn(tester, MockClient((r) async => _route(r)));

    await tester.tap(find.text('Acme'));
    await tester.pumpAndSettle();

    expect(find.text('Ventas'), findsOneWidget);
    expect(find.text('Inventario'), findsOneWidget);
    expect(find.textContaining('rev. 3'), findsOneWidget);
  });

  testWidgets('an organization without diagrams says so', (tester) async {
    await _signedIn(tester, MockClient((r) async => _route(r, extra: {'/api/orgs/acme/documents': _json([])})));

    await tester.tap(find.text('Acme'));
    await tester.pumpAndSettle();

    expect(find.text('Esta organización todavía no tiene diagramas.'), findsOneWidget);
  });

  testWidgets('a failing list shows the explanation and recovers on retry', (tester) async {
    var failing = true;
    await _signedIn(tester, MockClient((r) async {
      if (r.url.path == '/api/orgs' && failing) throw http.ClientException('offline');
      return _route(r);
    }));
    // GETs retry up to twice with real delays disabled only in unit tests, so
    // wait for the final failure to land.
    await tester.pumpAndSettle(const Duration(seconds: 5));

    expect(find.textContaining('Sin conexión'), findsOneWidget);

    failing = false;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle(const Duration(seconds: 5));

    expect(find.text('Acme'), findsOneWidget);
  });

  testWidgets('when the server rejects the token the person is sent back to the login with a message', (tester) async {
    var expired = false;
    await _signedIn(tester, MockClient((r) async {
      if (expired && r.url.path == '/api/orgs/acme/documents') {
        return _json({'detail': 'Invalid or expired token.', 'code': 'invalid_token'}, 401);
      }
      return _route(r);
    }));
    await tester.tap(find.text('Acme'));
    await tester.pumpAndSettle();
    expect(find.text('Ventas'), findsOneWidget);

    expired = true;
    await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();

    expect(find.text('Iniciar sesión'), findsWidgets);
    expect(find.text('Tu sesión venció. Inicia sesión de nuevo.'), findsOneWidget);
    expect(find.text('Ventas'), findsNothing);
  });
}
