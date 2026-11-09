/// One line of the diagram's session log (`LogEntryOut`): what happened and
/// who did it, people and the AI alike.
class LogEntry {
  const LogEntry({
    required this.id,
    required this.kind,
    required this.author,
    required this.isAi,
    required this.summary,
    required this.createdAt,
  });

  final int id;
  final String kind;
  final String author;
  final bool isAi;
  final String summary;
  final DateTime createdAt; // UTC

  /// A readable label. A kind a newer backend adds is shown as "Otro" instead
  /// of breaking the screen.
  String get kindLabel => switch (kind) {
    'change' => 'Cambio',
    'version.restored' => 'Versión restaurada',
    'diagram.replaced' => 'Diagrama reemplazado',
    'proposal.created' => 'Propuesta de la IA',
    'proposal.approved' => 'Aprobada',
    'proposal.rejected' => 'Rechazada',
    'chat.message' => 'Mensaje',
    _ => 'Otro',
  };

  factory LogEntry.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('log entry is not an object');
    final id = json['id'];
    final kind = json['kind'];
    final author = json['author'];
    final summary = json['summary'];
    final created = json['created_at'];
    if (id is! int || kind is! String || author is! String || summary is! String || created is! String) {
      throw const FormatException('log entry is missing a field');
    }
    return LogEntry(
      id: id,
      kind: kind,
      author: author,
      isAi: json['is_ai'] == true,
      summary: summary,
      createdAt: DateTime.parse(created).toUtc(),
    );
  }
}
