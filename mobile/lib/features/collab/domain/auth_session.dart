/// The signed-in person, as the backend describes them (`UserOut`).
class CollabUser {
  const CollabUser({required this.id, required this.email, required this.fullName});

  final String id;
  final String email;
  final String fullName;

  /// What to show as the person's name: the full name, else the email.
  String get displayName => fullName.trim().isEmpty ? email : fullName;

  factory CollabUser.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('user is not an object');
    final id = json['id'];
    final email = json['email'];
    if (id is! String || email is! String) throw const FormatException('user without id or email');
    return CollabUser(id: id, email: email, fullName: (json['full_name'] as String?) ?? '');
  }

  Map<String, Object?> toJson() => {'id': id, 'email': email, 'full_name': fullName};
}

/// One signed-in device: the bearer token, when it expires, who owns it and
/// which Modelia server it belongs to (issue #19, S2/S6).
class AuthSession {
  const AuthSession({
    required this.token,
    required this.expiresAt,
    required this.user,
    required this.baseUrl,
  });

  final String token;
  final DateTime expiresAt; // always UTC
  final CollabUser user;
  final String baseUrl;

  bool isExpired(DateTime now) => !expiresAt.isAfter(now.toUtc());

  factory AuthSession.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('session is not an object');
    final token = json['token'];
    final expires = json['expires_at'];
    final baseUrl = json['base_url'];
    if (token is! String || token.isEmpty || expires is! String || baseUrl is! String) {
      throw const FormatException('session is missing a field');
    }
    return AuthSession(
      token: token,
      expiresAt: DateTime.parse(expires).toUtc(),
      user: CollabUser.fromJson(json['user']),
      baseUrl: baseUrl,
    );
  }

  Map<String, Object?> toJson() => {
    'token': token,
    'expires_at': expiresAt.toIso8601String(),
    'base_url': baseUrl,
    'user': user.toJson(),
  };
}
