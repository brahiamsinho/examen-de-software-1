import 'package:flutter/material.dart';

import '../domain/api_failure.dart';
import '../domain/chat.dart';
import '../domain/organization.dart';
import 'format.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

/// The diagram's group chat (issue #19, S3). The AI answers only when a
/// message mentions `@IA`; if it wants to change the diagram it leaves a draft
/// that has to be approved in the proposals tab, never a direct change.
class ChatTab extends StatefulWidget {
  const ChatTab({super.key, required this.controller, required this.organization, required this.document});

  final SessionController controller;
  final Organization organization;
  final DocumentSummary document;

  @override
  State<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<ChatTab> {
  final _remote = GlobalKey<RemoteDataState<List<ChatMessage>>>();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _sending = false;
  String? _notice;
  String? _error;

  bool get _canSend => !_sending && _input.text.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    _input.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() {
      _sending = true;
      _error = null;
      _notice = null;
    });
    try {
      final result = await widget.controller.run(
        (repository) => repository.sendChat(widget.organization.slug, widget.document.id, text),
      );
      if (!mounted) return;
      _input.clear();
      setState(() {
        _notice = result.aiError != null
            ? 'La IA no pudo responder. Menciónala de nuevo para reintentar.'
            : result.hasProposal
            ? 'La IA dejó un borrador. Revísalo en la pestaña Propuestas.'
            : null;
      });
      await _remote.currentState?.refresh();
    } on ApiFailure catch (failure) {
      if (!mounted) return;
      setState(() {
        // Offline or timed out: the message may have arrived. It is kept in
        // the field and NOT resent automatically, so it is never posted twice.
        _error = failure.kind == ApiFailureKind.offline || failure.kind == ApiFailureKind.timeout
            ? 'Sin conexión estable: no sabemos si tu mensaje llegó. '
                  'Actualiza el chat para comprobarlo antes de reenviarlo.'
            : failure.userMessage;
      });
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      children: [
        Expanded(
          child: RemoteData<List<ChatMessage>>(
            key: _remote,
            load: () => widget.controller.run(
              (repository) => repository.listChat(widget.organization.slug, widget.document.id),
            ),
            isEmpty: (messages) => messages.isEmpty,
            emptyMessage: 'Todavía no hay mensajes. Escribe el primero.',
            builder: (context, messages) {
              // Newest at the bottom, like any chat.
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
              });
              return ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.all(12),
                itemCount: messages.length,
                itemBuilder: (context, index) => _MessageTile(message: messages[index]),
              );
            },
          ),
        ),
        if (_notice != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Semantics(liveRegion: true, child: Text(_notice!)),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Semantics(liveRegion: true, child: Text(_error!, style: TextStyle(color: scheme.error))),
          ),
        if (widget.organization.role.canWrite)
          _Composer(controller: _input, enabled: !_sending, canSend: _canSend, sending: _sending, onSend: _send)
        else
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Eres lector: puedes ver el chat, pero no escribir.'),
          ),
      ],
    );
  }
}

class _MessageTile extends StatelessWidget {
  const _MessageTile({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: message.isAi ? scheme.secondaryContainer : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (message.isAi) ...[const Icon(Icons.smart_toy_outlined, size: 16), const SizedBox(width: 4)],
                Text(message.author, style: Theme.of(context).textTheme.labelLarge),
                const Spacer(),
                Text(formatDateTime(message.createdAt), style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 4),
            Text(message.content),
          ],
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.enabled,
    required this.canSend,
    required this.sending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool canSend;
  final bool sending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 4, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: enabled,
                minLines: 1,
                maxLines: 4,
                maxLength: 2000,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(
                  hintText: 'Escribe al equipo…',
                  helperText: 'Menciona @IA para que responda.',
                  counterText: '',
                ),
              ),
            ),
            IconButton(
              tooltip: 'Enviar',
              onPressed: canSend ? onSend : null,
              icon: sending
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }
}
