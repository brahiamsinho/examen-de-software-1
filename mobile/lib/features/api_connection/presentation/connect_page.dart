import 'package:flutter/material.dart';

import 'connect_controller.dart';
import 'discovery_page.dart';

/// The app's entry screen (spec: Connection Flow and Feedback): a URL field,
/// a "Connect" button, and status feedback driven entirely by
/// [ConnectController.state]. `initialUrl` optionally pre-fills the field
/// from the build-time `GENERATED_API_URL` define (spec: Configuration).
class ConnectPage extends StatefulWidget {
  const ConnectPage({super.key, required this.controller, this.initialUrl = ''});

  final ConnectController controller;
  final String initialUrl;

  @override
  State<ConnectPage> createState() => _ConnectPageState();
}

class _ConnectPageState extends State<ConnectPage> {
  late final _urlController = TextEditingController(text: widget.initialUrl);

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onControllerChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onControllerChanged);
    _urlController.dispose();
    super.dispose();
  }

  void _onControllerChanged() {
    setState(() {});
    final state = widget.controller.state;
    if (state is ConnectSuccess) {
      // Reset back to idle once the user returns from discovery, so a
      // revisited connect screen never shows a stale success/failure.
      Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => DiscoveryPage(discovery: state.discovery))).then((_) {
        widget.controller.reset();
      });
    }
  }

  void _submit() {
    widget.controller.connect(_urlController.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = widget.controller.state;
    final loading = state is ConnectLoading;
    final failure = state is ConnectFailed ? state.failure : null;

    return Scaffold(
      appBar: AppBar(title: const Text('Connect to generated API')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(labelText: 'Public URL or OpenAPI URL'),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            FilledButton(onPressed: loading ? null : _submit, child: const Text('Connect')),
            if (loading) ...[const SizedBox(height: 16), const Center(child: CircularProgressIndicator())],
            if (failure != null) ...[
              const SizedBox(height: 16),
              Text(failure.message, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ],
        ),
      ),
    );
  }
}
