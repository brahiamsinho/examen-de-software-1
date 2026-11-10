import 'package:flutter/material.dart';

import '../../../core/config/app_config.dart';
import '../data/auth_repository.dart';
import '../data/token_storage.dart';
import 'collab_gate.dart';
import 'session_controller.dart';

/// Route target for the collaborative features (issue #19). It owns the
/// [SessionController] so it survives rebuilds while the route is open; the
/// session itself survives launches through [TokenStorage].
class CollabEntry extends StatefulWidget {
  const CollabEntry({super.key, this.storage = const SecureTokenStorage()});

  final TokenStorage storage;

  @override
  State<CollabEntry> createState() => _CollabEntryState();
}

class _CollabEntryState extends State<CollabEntry> {
  late final SessionController _controller = SessionController(
    repository: AuthRepository(storage: widget.storage),
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CollabGate(
      controller: _controller,
      initialServerUrl: AppConfig.apiBaseUrl,
      initialEmail: AppConfig.demoEmail,
      initialPassword: AppConfig.demoPassword,
    );
  }
}
