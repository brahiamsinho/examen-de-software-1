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
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}
