import 'package:flutter/foundation.dart';

import '../data/openapi_client.dart';
import '../domain/api_discovery.dart';
import '../domain/connection_failure.dart';
import '../domain/openapi_url.dart';

/// One of idle, loading, success or failed — a fresh instance replaces the
/// whole state on every transition (design.md `presentation/connect_controller.dart`).
sealed class ConnectState {
  const ConnectState();
}

class ConnectIdle extends ConnectState {
  const ConnectIdle();
}

class ConnectLoading extends ConnectState {
  const ConnectLoading();
}

class ConnectSuccess extends ConnectState {
  const ConnectSuccess({required this.discovery, required this.openApiUri});

  final ApiDiscovery discovery;
  final Uri openApiUri;
}

class ConnectFailed extends ConnectState {
  const ConnectFailed(this.failure);

  final ConnectionFailure failure;
}

/// Drives the connect screen (spec: Connection Flow and Feedback). Validates
/// the URL before ever touching the network (D2), ignores a second
/// submission while one is in flight, and ignores a response that arrives
/// after [reset] (D6's stale-request guard) so a late reply from an earlier,
/// abandoned attempt can never override newer state.
class ConnectController extends ChangeNotifier {
  // `client` is the public parameter name tests rely on; `this._client`
  // would rename it to the private `_client` and break every
  // `ConnectController(client: ...)` call.
  // ignore: prefer_initializing_formals
  ConnectController({required OpenApiClient client}) : _client = client;

  final OpenApiClient _client;
  ConnectState _state = const ConnectIdle();
  int _requestId = 0;

  ConnectState get state => _state;

  Future<void> connect(String input) async {
    if (_state is ConnectLoading) return;

    final requestId = ++_requestId;

    final Uri uri;
    try {
      uri = normalizeOpenApiUrl(input);
    } on ConnectionFailure catch (failure) {
      _state = ConnectFailed(failure);
      notifyListeners();
      return;
    }

    _state = const ConnectLoading();
    notifyListeners();

    try {
      final discovery = await _client.fetch(uri);
      if (requestId != _requestId) return; // superseded by reset() or a newer connect()
      _state = ConnectSuccess(discovery: discovery, openApiUri: uri);
    } on ConnectionFailure catch (failure) {
      if (requestId != _requestId) return;
      _state = ConnectFailed(failure);
    }
    notifyListeners();
  }

  void reset() {
    _requestId++; // orphans any request still in flight
    _state = const ConnectIdle();
    notifyListeners();
  }
}
