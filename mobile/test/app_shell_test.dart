import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    // The secure storage is a native plugin: without a phone it never answers.
    // Answer "nothing stored" so the login screen can appear.
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  testWidgets('the home shows both entry buttons, the collaborative one with a visible label', (tester) async {
    await tester.pumpWidget(const ModeliaApp());
    await tester.pumpAndSettle();

    expect(find.text('Colaborar en Modelia'), findsOneWidget);
    expect(find.byTooltip('On-device assistant'), findsOneWidget);
    expect(find.text('Connect to generated API'), findsOneWidget);
  });

  testWidgets('inside the collaborative pages the buttons are gone, so they cannot cover the screen', (tester) async {
    await tester.pumpWidget(const ModeliaApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Colaborar en Modelia'));
    await tester.pumpAndSettle();

    expect(find.text('Iniciar sesión'), findsWidgets); // the Modelia login is open
    expect(find.text('Colaborar en Modelia'), findsNothing);
    expect(find.byTooltip('On-device assistant'), findsNothing);
  });

  testWidgets('going back to the home brings the buttons back, and the generated-backend screen is intact', (tester) async {
    await tester.pumpWidget(const ModeliaApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Colaborar en Modelia'));
    await tester.pumpAndSettle();

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('Colaborar en Modelia'), findsOneWidget);
    expect(find.byTooltip('On-device assistant'), findsOneWidget);
    expect(find.text('Connect'), findsOneWidget);
  });

  testWidgets('opening the collaborative area twice in a row never stacks two copies', (tester) async {
    await tester.pumpWidget(const ModeliaApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Colaborar en Modelia'));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Colaborar en Modelia'));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('Connect to generated API'), findsOneWidget);
    expect(find.text('Colaborar en Modelia'), findsOneWidget);
  });
}
