import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/auth_repository.dart';
import 'package:mobile/features/collab/data/token_storage.dart';
import 'package:mobile/features/collab/presentation/collab_gate.dart';
import 'package:mobile/features/collab/presentation/login_page.dart';
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

SessionController _controller(MockClient mock) =>
    SessionController(repository: AuthRepository(storage: _MemoryStorage(), httpClient: mock), httpClient: mock);

Future<void> _pump(WidgetTester tester, SessionController controller) async {
  await tester.pumpWidget(MaterialApp(home: CollabGate(controller: controller, initialServerUrl: 'http://10.0.2.2:8000')));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('a signed-out person sees the login form with the server prefilled', (tester) async {
    await _pump(tester, _controller(MockClient((r) async => _json(_loginBody))));

    expect(find.byType(LoginPage), findsOneWidget);
    expect(find.widgetWithText(TextField, 'http://10.0.2.2:8000'), findsOneWidget);
    expect(find.text('Correo electrónico'), findsOneWidget);
    expect(find.text('Contraseña'), findsOneWidget);
    expect(find.text('Iniciar sesión'), findsOneWidget);
  });

  testWidgets('the email and password start empty unless the build provides them', (tester) async {
    await _pump(tester, _controller(MockClient((r) async => _json(_loginBody))));

    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Correo electrónico')).controller!.text, isEmpty);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Contraseña')).controller!.text, isEmpty);
  });

  testWidgets('a build can prefill the email and password, and the password stays hidden', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: CollabGate(
        controller: _controller(MockClient((r) async => _json(_loginBody))),
        initialServerUrl: 'http://10.0.2.2:8000',
        initialEmail: 'owner@demo.com',
        initialPassword: 'DemoPass123!',
      ),
    ));
    await tester.pumpAndSettle();

    final email = tester.widget<TextField>(find.widgetWithText(TextField, 'Correo electrónico'));
    final password = tester.widget<TextField>(find.widgetWithText(TextField, 'Contraseña'));
    expect(email.controller!.text, 'owner@demo.com');
    expect(password.controller!.text, 'DemoPass123!');
    expect(password.obscureText, isTrue);
  });

  testWidgets('the password is hidden', (tester) async {
    await _pump(tester, _controller(MockClient((r) async => _json(_loginBody))));

    final field = tester.widget<TextField>(find.widgetWithText(TextField, 'Contraseña'));
    expect(field.obscureText, isTrue);
  });

  testWidgets('empty fields show the explanation and send nothing', (tester) async {
    var calls = 0;
    await _pump(tester, _controller(MockClient((r) async {
      calls++;
      return _json(_loginBody);
    })));

    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(find.text('Escribe tu correo electrónico.'), findsOneWidget);
    expect(calls, 0);
  });

  testWidgets('wrong credentials show a clear message and keep the form', (tester) async {
    await _pump(tester, _controller(MockClient((r) async => _json({'detail': 'x', 'code': 'invalid_credentials'}, 401))));

    await tester.enterText(find.widgetWithText(TextField, 'Correo electrónico'), 'ana@acme.test');
    await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'bad');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(find.text('Correo o contraseña incorrectos.'), findsOneWidget);
    expect(find.byType(LoginPage), findsOneWidget);
  });

  testWidgets('a good login lands on the signed-in home and signing out returns to the form', (tester) async {
    await _pump(tester, _controller(MockClient((r) async {
      if (r.url.path.endsWith('revoke')) return http.Response('', 204);
      return _json(_loginBody);
    })));

    await tester.enterText(find.widgetWithText(TextField, 'Correo electrónico'), 'ana@acme.test');
    await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'secret');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(find.byType(LoginPage), findsNothing);
    expect(find.textContaining('Ana'), findsWidgets);

    await tester.tap(find.byTooltip('Cerrar sesión'));
    await tester.pumpAndSettle();

    expect(find.byType(LoginPage), findsOneWidget);
  });

  testWidgets('the server address typed by the person is remembered', (tester) async {
    await _pump(tester, _controller(MockClient((r) async => _json(_loginBody))));

    await tester.enterText(find.widgetWithText(TextField, 'http://10.0.2.2:8000'), 'http://192.168.1.20:8000');
    await tester.enterText(find.widgetWithText(TextField, 'Correo electrónico'), 'ana@acme.test');
    await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'secret');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('collab_server_url'), 'http://192.168.1.20:8000');
  });
}
