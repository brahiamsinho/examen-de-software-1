// Named parameters cannot start with an underscore, so they cannot be
// initializing formals for the private fields.
// ignore_for_file: prefer_initializing_formals

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../data/auth_repository.dart';
import '../data/modelia_api_client.dart';
import '../domain/api_failure.dart';
import '../domain/auth_session.dart';

enum SessionStatus { restoring, signedOut, signedIn }

/// Holds who is signed in and hands out the authenticated API client (issue
/// #19). One `ChangeNotifier`, like `ConnectController`; no state library.
class SessionController extends ChangeNotifier {
  SessionController({required AuthRepository repository, http.Client? httpClient})
    : _repository = repository,
      _httpClient = httpClient;

  final AuthRepository _repository;
  final http.Client? _httpClient;

  SessionStatus _status = SessionStatus.restoring;
  AuthSession? _session;
  ModeliaApiClient? _api;
  bool _busy = false;
  String? _errorMessage;

  SessionStatus get status => _status;
  AuthSession? get session => _session;
  bool get busy => _busy;

  /// Why the last sign-in failed or why the session ended; shown on the login
  /// screen. Cleared when a new sign-in starts.
  String? get errorMessage => _errorMessage;

  /// The client for the signed-in session, or `null` when signed out. A 401
  /// `invalid_token` through it ends the session.
  ModeliaApiClient? get api => _api;

  Future<void> restore() async {
    final stored = await _repository.restore();
    if (stored == null) {
      _status = SessionStatus.signedOut;
    } else {
      _adopt(stored);
    }
    notifyListeners();
  }

  Future<void> signIn({required String baseUrl, required String email, required String password}) async {
    final problem = _validate(baseUrl, email, password);
    if (problem != null) {
      _errorMessage = problem;
      notifyListeners();
      return;
    }
    _busy = true;
    _errorMessage = null;
    notifyListeners();
    try {
      _adopt(await _repository.signIn(baseUrl: baseUrl, email: email, password: password));
    } on ApiFailure catch (failure) {
      _errorMessage = failure.kind == ApiFailureKind.unauthorized
          ? 'Correo o contraseña incorrectos.'
          : failure.userMessage;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    final current = _session;
    if (current != null) await _repository.signOut(current);
    _clear();
    notifyListeners();
  }

  String? _validate(String baseUrl, String email, String password) {
    if (baseUrl.trim().isEmpty) return 'Escribe la dirección del servidor.';
    if (email.trim().isEmpty) return 'Escribe tu correo electrónico.';
    if (password.isEmpty) return 'Escribe tu contraseña.';
    return null;
  }

  void _adopt(AuthSession session) {
    _session = session;
    _status = SessionStatus.signedIn;
    _api = ModeliaApiClient(
      baseUrl: session.baseUrl,
      tokenProvider: () => _session?.token,
      httpClient: _httpClient,
      onUnauthorized: _expire,
    );
  }

  void _clear() {
    _session = null;
    _api = null;
    _status = SessionStatus.signedOut;
  }

  // The server no longer accepts the token. Guarded so two calls that were in
  // flight together end the session once.
  void _expire() {
    if (_session == null) return;
    _clear();
    _errorMessage = 'Tu sesión venció. Inicia sesión de nuevo.';
    _repository.forget();
    notifyListeners();
  }
}
