import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';

/// Minimal text chat proving the on-device pipeline (install → load → infer)
/// works end to end on a real device (on-device AI feature, step 1 of 3).
/// No chat history persistence and no function calling — those come in
/// later steps. Assumes the model is already installed (reached only from
/// [LocalAssistantSettingsPage] once [LocalModelService.isModelInstalled]
/// is true).
class LocalAssistantChatPage extends StatefulWidget {
  const LocalAssistantChatPage({super.key});

  @override
  State<LocalAssistantChatPage> createState() => _LocalAssistantChatPageState();
}

class _LocalAssistantChatPageState extends State<LocalAssistantChatPage> {
  final _inputController = TextEditingController();

  InferenceModel? _model;
  InferenceChat? _chat;
  String _answer = '';
  bool _loadingModel = true;
  bool _generating = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadModel();
  }

  Future<void> _loadModel() async {
    try {
      final model = await FlutterGemma.getActiveModel(preferredBackend: PreferredBackend.gpu);
      final chat = await model.createChat();
      if (!mounted) return;
      setState(() {
        _model = model;
        _chat = chat;
        _loadingModel = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Could not load the model: $e';
        _loadingModel = false;
      });
    }
  }

  @override
  void dispose() {
    _inputController.dispose();
    _model?.close();
    super.dispose();
  }

  Future<void> _send() async {
    final chat = _chat;
    final text = _inputController.text.trim();
    if (chat == null || text.isEmpty || _generating) return;

    setState(() {
      _generating = true;
      _answer = '';
      _errorMessage = null;
    });
    _inputController.clear();

    try {
      await chat.addQueryChunk(Message.text(text: text, isUser: true));
      await for (final response in chat.generateChatResponseAsync()) {
        if (response is TextResponse) {
          if (!mounted) return;
          setState(() => _answer += response.token);
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = 'Generation failed: $e');
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Test chat (on-device)')),
      body: _loadingModel
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_errorMessage != null) ...[
                    Text(_errorMessage!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    const SizedBox(height: 8),
                  ],
                  Expanded(child: SingleChildScrollView(child: Text(_answer))),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _inputController,
                    enabled: !_generating,
                    decoration: const InputDecoration(labelText: 'Ask something'),
                    onSubmitted: (_) => _send(),
                  ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: _generating ? null : _send,
                    child: Text(_generating ? 'Generating…' : 'Send'),
                  ),
                ],
              ),
            ),
    );
  }
}
