class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.author,
    required this.isAi,
    required this.content,
    required this.createdAt,
  });

  /// A MongoDB ObjectId: 24 lowercase hex characters, which sort in creation order.
  final String id;
  final String author;
  final bool isAi;
  final String content;
  final DateTime createdAt; // UTC

  factory ChatMessage.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('message is not an object');
    final id = json['id'];
    final author = json['author'];
    final content = json['content'];
    final created = json['created_at'];
    if (id is! String || author is! String || content is! String || created is! String) {
      throw const FormatException('message is missing a field');
    }
    return ChatMessage(
      id: id,
      author: author,
      isAi: json['is_ai'] == true,
      content: content,
      createdAt: DateTime.parse(created).toUtc(),
    );
  }
}

/// The server's answer to posting a chat message (`ChatPostOut`).
class ChatSendResult {
  const ChatSendResult({required this.message, this.reply, this.aiError, this.hasProposal = false});

  final ChatMessage message;

  /// The AI's answer, when the message mentioned it and it answered.
  final ChatMessage? reply;

  /// Set when the message asked the AI but it could not answer.
  final String? aiError;

  /// The AI left a draft on the board that someone has to approve or reject.
  final bool hasProposal;

  factory ChatSendResult.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw const FormatException('answer is not an object');
    final reply = json['reply'];
    return ChatSendResult(
      message: ChatMessage.fromJson(json['message']),
      reply: reply == null ? null : ChatMessage.fromJson(reply),
      aiError: json['ai_error'] is String ? json['ai_error'] as String : null,
      hasProposal: json['proposal'] != null,
    );
  }
}
