/// A member's role in an organization. It mirrors the backend's `my_role`,
/// which is also what decides who may write: the server enforces it, the app
/// only uses it to avoid offering what would be refused.
enum MemberRole {
  owner('Propietario', true),
  editor('Editor', true),
  viewer('Lector', false);

  const MemberRole(this.label, this.canWrite);

  final String label;
  final bool canWrite;

  /// An unknown value is read-only: failing closed means a new backend role
  /// can never make the app offer a write the person may not have.
  static MemberRole fromWire(Object? value) => switch (value) {
    'OWNER' => MemberRole.owner,
    'EDITOR' => MemberRole.editor,
    _ => MemberRole.viewer,
  };
}

class Organization {
  const Organization({required this.id, required this.name, required this.slug, required this.role});

  final String id;
  final String name;
  final String slug;
  final MemberRole role;

  factory Organization.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('organization is not an object');
    final id = json['id'];
    final name = json['name'];
    final slug = json['slug'];
    if (id is! String || name is! String || slug is! String || slug.isEmpty) {
      throw const FormatException('organization is missing a field');
    }
    return Organization(id: id, name: name, slug: slug, role: MemberRole.fromWire(json['my_role']));
  }
}

/// One diagram in an organization's list (`DocumentSummaryOut`).
class DocumentSummary {
  const DocumentSummary({required this.id, required this.name, required this.revision, required this.updatedAt});

  final String id;
  final String name;
  final int revision;
  final DateTime updatedAt; // UTC

  String get displayName => name.trim().isEmpty ? 'Sin título' : name;

  factory DocumentSummary.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('document is not an object');
    final id = json['id'];
    final name = json['name'];
    final revision = json['revision'];
    final updated = json['updated_at'];
    if (id is! String || name is! String || revision is! int || updated is! String) {
      throw const FormatException('document is missing a field');
    }
    return DocumentSummary(id: id, name: name, revision: revision, updatedAt: DateTime.parse(updated).toUtc());
  }
}
