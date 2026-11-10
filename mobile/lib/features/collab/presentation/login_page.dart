import 'package:flutter/material.dart';

import '../data/server_url_store.dart';
import 'session_controller.dart';

/// Signs the phone in to Modelia (issue #19). The server address is a field
/// because a real phone reaches the backend by its network address, not by the
/// emulator's `10.0.2.2`.
class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.controller,
    required this.initialServerUrl,
    this.initialEmail = '',
    this.initialPassword = '',
    this.serverUrlStore = const ServerUrlStore(),
  });

  final SessionController controller;
  final String initialServerUrl;
  // Prefilled only when the build provides them (see `AppConfig`): empty otherwise.
  final String initialEmail;
  final String initialPassword;
  final ServerUrlStore serverUrlStore;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  late final TextEditingController _server = TextEditingController(text: widget.initialServerUrl);
  late final TextEditingController _email = TextEditingController(text: widget.initialEmail);
  late final TextEditingController _password = TextEditingController(text: widget.initialPassword);
  bool _serverTouched = false;

  @override
  void initState() {
    super.initState();
    _loadSavedServer();
  }

  // The remembered address wins over the build-time default, unless the person
  // already started typing a different one.
  Future<void> _loadSavedServer() async {
    final saved = await widget.serverUrlStore.load();
    if (!mounted || _serverTouched || saved == null || saved.isEmpty) return;
    _server.text = saved;
  }

  @override
  void dispose() {
    _server.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    await widget.controller.signIn(baseUrl: _server.text, email: _email.text, password: _password.text);
    if (widget.controller.session != null) {
      await widget.serverUrlStore.save(_server.text.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.controller,
      builder: (context, _) {
        final busy = widget.controller.busy;
        final error = widget.controller.errorMessage;
        return Scaffold(
          appBar: AppBar(title: const Text('Modelia')),
          body: SafeArea(
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text('Inicia sesión', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 4),
                const Text('Participa en los diagramas de tu organización desde el celular.'),
                const SizedBox(height: 24),
                TextField(
                  controller: _server,
                  enabled: !busy,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  onChanged: (_) => _serverTouched = true,
                  decoration: const InputDecoration(
                    labelText: 'Servidor',
                    helperText: 'En un celular real usa la dirección de red del servidor.',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _email,
                  enabled: !busy,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  autofillHints: const [AutofillHints.email],
                  decoration: const InputDecoration(labelText: 'Correo electrónico'),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _password,
                  enabled: !busy,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  onSubmitted: (_) => _submit(),
                  decoration: const InputDecoration(labelText: 'Contraseña'),
                ),
                if (error != null) ...[
                  const SizedBox(height: 16),
                  Semantics(
                    liveRegion: true,
                    child: Text(error, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: busy ? null : _submit,
                  child: busy
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Iniciar sesión'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
