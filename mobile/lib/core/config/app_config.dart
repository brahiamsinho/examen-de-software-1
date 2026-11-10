import 'package:flutter/foundation.dart' show kDebugMode;

/// Central place for compile-time app configuration.
///
/// The backend API base URL is never hardcoded in the app. Instead it is
/// passed at build/run time via `--dart-define`, e.g.:
///
///   flutter run --dart-define=API_BASE_URL=http://localhost:8000
///
/// If no value is provided, it defaults to `http://10.0.2.2:8000`.
/// `10.0.2.2` is the special alias the Android emulator uses to reach
/// the host machine's `localhost` (the emulator runs in its own network
/// namespace, so `localhost` inside it would refer to the emulator
/// itself, not your development machine running Django).
class AppConfig {
  /// Demo account prefilled on the collaboration login so a presentation does not
  /// need typing. Debug builds only: a release build starts empty unless these are
  /// passed explicitly, e.g. `--dart-define=DEMO_EMAIL=... --dart-define=DEMO_PASSWORD=...`.
  /// These are the public seed accounts from the repo, never a real person's login.
  static const String demoEmail = String.fromEnvironment(
    'DEMO_EMAIL',
    defaultValue: kDebugMode ? 'owner@demo.com' : '',
  );
  static const String demoPassword = String.fromEnvironment(
    'DEMO_PASSWORD',
    defaultValue: kDebugMode ? 'DemoPass123!' : '',
  );

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  /// Optional URL of a generated backend to pre-fill on the connect screen,
  /// e.g. `flutter run --dart-define=GENERATED_API_URL=http://10.0.2.2:8090/gen/<id>`.
  /// Defaults to empty (spec: Configuration) — a fresh app never assumes a
  /// specific deployment.
  static const String generatedApiUrl = String.fromEnvironment('GENERATED_API_URL');
}
