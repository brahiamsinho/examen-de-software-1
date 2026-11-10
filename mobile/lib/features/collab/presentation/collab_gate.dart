import 'package:flutter/material.dart';

import 'collab_home_page.dart';
import 'login_page.dart';
import 'session_controller.dart';

/// Entry point of the collaborative features (issue #19): restores the saved
/// session, then shows the login form or the signed-in home.
class CollabGate extends StatefulWidget {
  const CollabGate({
    super.key,
    required this.controller,
    required this.initialServerUrl,
    this.initialEmail = '',
    this.initialPassword = '',
  });

  final SessionController controller;
  final String initialServerUrl;
  final String initialEmail;
  final String initialPassword;

  @override
  State<CollabGate> createState() => _CollabGateState();
}

class _CollabGateState extends State<CollabGate> {
  ModalRoute<dynamic>? _route;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_closePagesWhenSignedOut);
    if (widget.controller.status == SessionStatus.restoring) widget.controller.restore();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _route = ModalRoute.of(context);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_closePagesWhenSignedOut);
    super.dispose();
  }

  // Pages pushed from the home sit above this route, so swapping the gate's
  // body is not enough: when the session ends (logout, or the server rejects
  // the token) they must be closed, or the person would keep reading data
  // behind a login screen.
  void _closePagesWhenSignedOut() {
    final route = _route;
    if (!mounted || route == null || widget.controller.status != SessionStatus.signedOut) return;
    Navigator.of(context).popUntil((candidate) => candidate == route);
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
            return LoginPage(
              controller: widget.controller,
              initialServerUrl: widget.initialServerUrl,
              initialEmail: widget.initialEmail,
              initialPassword: widget.initialPassword,
            );
          case SessionStatus.signedIn:
            return CollabHomePage(controller: widget.controller);
        }
      },
    );
  }
}
