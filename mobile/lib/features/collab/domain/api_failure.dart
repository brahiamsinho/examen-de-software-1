/// Why a call to the Modelia API failed, reduced to what a screen needs to
/// explain it (issue #19, S4: "estado claro"). The kind drives the message
/// and whether a retry button makes sense; it never carries a stack trace.
enum ApiFailureKind {
  /// No connection or the server could not be reached.
  offline,

  /// The server took too long to answer.
  timeout,

  /// 401: bad credentials or an invalid/expired token.
  unauthorized,

  /// 403: the user's role does not allow this (e.g. a VIEWER writing).
  forbidden,

  /// 404: unknown, or belonging to another organization.
  notFound,

  /// 409: the thing changed under the user (e.g. a stale proposal).
  conflict,

  /// 400/422: the request was rejected as invalid.
  validation,

  /// 5xx (or 429): the server had a problem.
  server,

  /// Anything else, including an answer that is not the expected JSON.
  unexpected,
}

class ApiFailure implements Exception {
  const ApiFailure(this.kind, {this.statusCode, this.message, this.code});

  final ApiFailureKind kind;
  final int? statusCode;

  /// The backend's `detail`, when it sent one. Not always user-friendly.
  final String? message;

  /// The backend's machine-readable `code` (e.g. `invalid_token`).
  final String? code;

  /// Whether trying again could plausibly work, so the screen can offer it.
  bool get canRetry =>
      kind == ApiFailureKind.offline || kind == ApiFailureKind.timeout || kind == ApiFailureKind.server;

  /// Neutral Spanish text for the screen.
  String get userMessage {
    switch (kind) {
      case ApiFailureKind.offline:
        return 'Sin conexión con el servidor. Revisa tu internet e intenta de nuevo.';
      case ApiFailureKind.timeout:
        return 'El servidor tardó demasiado en responder. Intenta de nuevo.';
      case ApiFailureKind.unauthorized:
        return 'Tu sesión venció. Inicia sesión de nuevo.';
      case ApiFailureKind.forbidden:
        return 'Tu rol no permite hacer esto.';
      case ApiFailureKind.notFound:
        return 'No se encontró lo que buscas.';
      case ApiFailureKind.conflict:
        // The backend's detail is English; the screen speaks Spanish.
        return 'El cambio ya no es válido. Actualiza e intenta de nuevo.';
      case ApiFailureKind.validation:
        return message ?? 'Revisa los datos e intenta de nuevo.';
      case ApiFailureKind.server:
        return 'El servidor tuvo un problema. Intenta de nuevo en un momento.';
      case ApiFailureKind.unexpected:
        return 'Ocurrió un error inesperado.';
    }
  }

  @override
  String toString() => 'ApiFailure($kind, status: $statusCode, code: $code)';
}
