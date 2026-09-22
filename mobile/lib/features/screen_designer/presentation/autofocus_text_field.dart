import 'package:flutter/material.dart';

/// A dialog's entrance transition can race a same-frame `autofocus`
/// request on some devices, leaving the field focused but never actually
/// raising the soft keyboard (observed on a real Android device: the "Add
/// field"/id-prompt dialogs opened with the cursor placed but no keyboard).
/// Asking again once the transition has settled is the reliable fix; kept
/// as its own widget since `showDialog`'s `builder` has no state of its own
/// to hang a `FocusNode`/timer on.
class AutofocusTextField extends StatefulWidget {
  const AutofocusTextField({super.key, required this.controller, required this.label});

  final TextEditingController controller;
  final String label;

  @override
  State<AutofocusTextField> createState() => _AutofocusTextFieldState();
}

class _AutofocusTextFieldState extends State<AutofocusTextField> {
  final _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 200), () {
        if (mounted) _focusNode.requestFocus();
      });
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: widget.controller,
      focusNode: _focusNode,
      decoration: InputDecoration(labelText: widget.label),
      autofocus: true,
    );
  }
}
