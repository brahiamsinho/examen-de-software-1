import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart' show DownloadException, DownloadErrorMessage;

import '../data/local_assistant_token_store.dart';
import '../data/local_model_service.dart';
import 'local_assistant_chat_page.dart';

/// Lets the user provide their own Hugging Face access token and download
/// Gemma3-1B-IT on-device (on-device AI feature, step 1 of 3 — proving the
/// local-LLM pipeline works end to end; function-calling wiring and an
/// offline OpenAPI cache are later steps). Mirrors [ConnectPage]'s
/// form/loading-state conventions.
class LocalAssistantSettingsPage extends StatefulWidget {
  const LocalAssistantSettingsPage({
    super.key,
    this.tokenStore = const LocalAssistantTokenStore(),
    this.modelService = const LocalModelService(),
  });

  final LocalAssistantTokenStore tokenStore;
  final LocalModelService modelService;

  @override
  State<LocalAssistantSettingsPage> createState() => _LocalAssistantSettingsPageState();
}

class _LocalAssistantSettingsPageState extends State<LocalAssistantSettingsPage> {
  final _tokenController = TextEditingController();

  bool _checkingStatus = true;
  bool _installed = false;
  bool _downloading = false;
  int _progress = 0;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadInitialState();
  }

  Future<void> _loadInitialState() async {
    final savedToken = await widget.tokenStore.load();
    final installed = await widget.modelService.isModelInstalled();
    if (!mounted) return;
    setState(() {
      if (savedToken != null) _tokenController.text = savedToken;
      _installed = installed;
      _checkingStatus = false;
    });
  }

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _download() async {
    final token = _tokenController.text.trim();
    if (token.isEmpty) {
      setState(() => _errorMessage = 'Enter your Hugging Face access token first.');
      return;
    }

    setState(() {
      _downloading = true;
      _progress = 0;
      _errorMessage = null;
    });

    await widget.tokenStore.save(token);

    try {
      await widget.modelService.install(
        token: token,
        onProgress: (progress) {
          if (!mounted) return;
          setState(() => _progress = progress);
        },
      );
      if (!mounted) return;
      setState(() {
        _downloading = false;
        _installed = true;
      });
    } on DownloadException catch (e) {
      if (!mounted) return;
      setState(() {
        _downloading = false;
        _errorMessage = e.error.toUserMessage();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _downloading = false;
        _errorMessage = 'Could not download the model: $e';
      });
    }
  }

  void _openChat() {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LocalAssistantChatPage()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('On-device assistant')),
      body: _checkingStatus
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Runs Gemma3-1B-IT fully on this device — nothing is sent to a '
                    'server. You need a free Hugging Face account, and you must '
                    'accept the license on huggingface.co/litert-community/Gemma3-1B-IT '
                    'before the download below will work.',
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _tokenController,
                    obscureText: true,
                    enabled: !_downloading,
                    decoration: const InputDecoration(labelText: 'Hugging Face access token'),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _downloading ? null : _download,
                    child: Text(_installed ? 'Re-download model' : 'Download model'),
                  ),
                  if (_downloading) ...[
                    const SizedBox(height: 16),
                    LinearProgressIndicator(value: _progress / 100),
                    const SizedBox(height: 8),
                    Text('$_progress%'),
                  ],
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 16),
                    Text(_errorMessage!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                  if (_installed && !_downloading) ...[
                    const SizedBox(height: 16),
                    OutlinedButton(onPressed: _openChat, child: const Text('Open test chat')),
                  ],
                ],
              ),
            ),
    );
  }
}
