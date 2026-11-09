// Named parameters cannot start with an underscore, so they cannot be
// initializing formals for the private fields.
// ignore_for_file: prefer_initializing_formals

import 'dart:convert';

import 'package:flutter/foundation.dart' show defaultTargetPlatform;
import 'package:http/http.dart' as http;

import '../domain/api_failure.dart';
import '../domain/auth_session.dart';
import 'modelia_api_client.dart';
import 'token_storage.dart';

/// Signs the phone in with a Modelia bearer token (issue #19, S2/S6): the
/// session cookie plus CSRF flow of the web does not fit a native app.
class AuthRepository {
  AuthRepository({required TokenStorage storage, http.Client? httpClient})
    : _storage = storage,
      _httpClient = httpClient;

  final TokenStorage _storage;
  final http.Client? _httpClient;

  /// Logs in and stores the session. Throws [ApiFailure] (bad credentials are
  /// `unauthorized`); nothing is stored on failure.
  Future<AuthSession> signIn({required String baseUrl, required String email, required String password}) async {
    final server = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    if (server.isEmpty) throw const ApiFailure(ApiFailureKind.validation);

    final client = ModeliaApiClient(baseUrl: server, tokenProvider: () => null, httpClient: _httpClient);
    final body = await client.postJson('/api/auth/mobile-token', {
      'email': email.trim(),
      'password': password,
      'device_name': 'Modelia mobile (${defaultTargetPlatform.name})',
    });

    final AuthSession session;
    try {
      session = AuthSession.fromJson({
        if (body is Map<String, dynamic>) ...body,
        'base_url': server,
      });
    } on FormatException {
      throw const ApiFailure(ApiFailureKind.unexpected);
    }
    await _storage.write(jsonEncode(session.toJson()));
    return session;
  }

  /// The stored session if it is still valid; an expired or corrupted one is
  /// dropped so the next launch starts clean.
  Future<AuthSession?> restore() async {
    final String? raw;
    try {
      raw = await _storage.read();
    } catch (_) {
      // A keystore that cannot be read (corrupted, restored from a backup on
      // another device...) must not leave the app on a spinner: treat it as
      // "not signed in" and let the person log in again.
      return null;
    }
    if (raw == null) return null;
    try {
      final session = AuthSession.fromJson(jsonDecode(raw));
      if (!session.isExpired(DateTime.now())) return session;
    } on FormatException {
      // fall through to clear
    }
    await _clearQuietly();
    return null;
  }

  /// Drops the stored session without telling the server (it already said the
  /// token is invalid).
  Future<void> forget() => _clearQuietly();

  // Forgetting must never throw: it runs on sign-out and on token expiry.
  Future<void> _clearQuietly() async {
    try {
      await _storage.clear();
    } catch (_) {
      // Nothing more can be done about an unusable keystore.
    }
  }

  /// Revokes this device's token on the server (best effort) and ALWAYS
  /// clears it locally, so signing out works offline too.
  Future<void> signOut(AuthSession session) async {
    try {
      final client = ModeliaApiClient(
        baseUrl: session.baseUrl,
        tokenProvider: () => session.token,
        httpClient: _httpClient,
      );
      await client.postJson('/api/auth/mobile-token/revoke', null);
    } on ApiFailure {
      // The token still expires on its own; the device forgets it now.
    } finally {
      await _clearQuietly();
    }
  }
}
