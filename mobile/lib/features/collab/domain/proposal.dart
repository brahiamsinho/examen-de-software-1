/// One change inside an AI draft, with whether the server could apply it
/// (`ProposalOut.changes`). The server checked each one against the diagram.
class ProposalChange {
  const ProposalChange({required this.ok, required this.message});

  final bool ok;
  final String message;

  factory ProposalChange.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('change is not an object');
    final message = json['message'];
    if (message is! String) throw const FormatException('change without a message');
    return ProposalChange(ok: json['ok'] == true, message: message);
  }
}

/// A draft the AI left on the board: nothing in it touches the diagram until a
/// person approves it (issue #15). `pending` is the only state that can still
/// be decided; `stale` means the diagram moved on after it was made.
class Proposal {
  const Proposal({
    required this.id,
    required this.status,
    required this.prompt,
    required this.requestedBy,
    required this.changes,
    required this.createdAt,
  });

  final String id;
  final String status;
  final String prompt;
  final String requestedBy;
  final List<ProposalChange> changes;
  final DateTime createdAt; // UTC

  bool get isPending => status == 'pending';

  /// Approving applies every change, and the server refuses the whole draft if
  /// one of them cannot be applied, so the app does not offer it.
  bool get canApprove => isPending && changes.isNotEmpty && changes.every((c) => c.ok);

  factory Proposal.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('proposal is not an object');
    final id = json['id'];
    final status = json['status'];
    final prompt = json['prompt'];
    final requestedBy = json['requested_by'];
    final created = json['created_at'];
    final changes = json['changes'];
    if (id is! String ||
        status is! String ||
        prompt is! String ||
        requestedBy is! String ||
        created is! String ||
        changes is! List) {
      throw const FormatException('proposal is missing a field');
    }
    return Proposal(
      id: id,
      status: status,
      prompt: prompt,
      requestedBy: requestedBy,
      changes: [for (final change in changes) ProposalChange.fromJson(change)],
      createdAt: DateTime.parse(created).toUtc(),
    );
  }
}
