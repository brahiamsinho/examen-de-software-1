import 'package:flutter/material.dart';

import 'collab_home_page.dart';
import 'login_page.dart';
import 'session_controller.dart';

/// Entry point of the collaborative features (issue #19): restores the saved
/// session, then shows the login form or the signed-in home.
class CollabGate extends StatefulWidget {
  const CollabGate({super.key, required this.controller, required this.initialServerUrl});

  final SessionController controller;
  final String initialServerUrl;

  @override
  State<CollabGate> createState() => _CollabGateState();
}

class _CollabGateState extends State<CollabGate> {
  @override
  void initState() {
    super.initState();
    if (widget.controller.status == SessionStatus.restoring) widget.controller.restore();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.controller,
      builder: (context, _) {
        switch (widget.controller.status) {
          case SessionStatus.restoring:
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          case SessionStatus.signedOut:
            return LoginPage(controller: widget.controller, initialServerUrl: widget.initialServerUrl);
          case SessionStatus.signedIn:
            return CollabHomePage(controller: widget.controller);
        }
      },
    );
  }
}
