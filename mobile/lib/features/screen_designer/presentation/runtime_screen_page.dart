import 'package:flutter/material.dart';

import '../../api_connection/domain/api_discovery.dart';
import '../data/pending_action_store.dart';
import '../data/pending_action_sync_service.dart';
import '../data/screen_action_client.dart';
import '../domain/screen_layout.dart';
import '../domain/screen_widget_config.dart';
import 'autofocus_text_field.dart';

/// Runs a saved [ScreenLayout] for real: renders each placed widget at its
/// designed position and wires each Button to its OWN class's (`groupName`)
/// actual collection endpoint — a screen may mix widgets from several
/// classes, so every Button/Field resolves independently rather than
/// assuming one shared class (spec MVP — update/delete additionally ask for
/// a record id, since there is no data grid yet to pick one from). Field
/// widgets are plain `TextField`s the user types into; their current text
/// feeds only the create/update calls of buttons bound to the SAME class.
class RuntimeScreenPage extends StatefulWidget {
  const RuntimeScreenPage({
    super.key,
    required this.layout,
    required this.groups,
    required this.deploymentBase,
    this.actionClient,
    this.pendingActionStore,
    this.pendingActionSyncService,
  });

  final ScreenLayout layout;
  final List<EndpointGroup> groups;
  final Uri deploymentBase;
  final ScreenActionClient? actionClient;
  final PendingActionStore? pendingActionStore;
  final PendingActionSyncService? pendingActionSyncService;

  @override
  State<RuntimeScreenPage> createState() => _RuntimeScreenPageState();
}

class _RuntimeScreenPageState extends State<RuntimeScreenPage> {
  late final ScreenActionClient _client = widget.actionClient ?? ScreenActionClient();
  late final PendingActionStore _pendingActionStore = widget.pendingActionStore ?? const PendingActionStore();
  late final PendingActionSyncService _pendingActionSyncService =
      widget.pendingActionSyncService ??
      PendingActionSyncService(actionClient: _client, store: _pendingActionStore);
  final Map<String, TextEditingController> _controllers = {};
  String? _resultText;
  bool _busy = false;
  int _pendingEntrySeq = 0;

  TextEditingController _controllerFor(String fieldName) =>
      _controllers.putIfAbsent(fieldName, () => TextEditingController());

  @override
  void initState() {
    super.initState();
    _pendingActionSyncService.startListening();
  }

  @override
  void dispose() {
    _pendingActionSyncService.stopListening();
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  /// The path a `POST` for `groupName` lands on, per this project's Spring
  /// generator convention: the collection path, with `/{id}` appended for a
  /// specific record (design.md `screen_designer` MVP note).
  String? _collectionPathFor(String groupName) {
    final endpoints = widget.groups.where((g) => g.name == groupName).firstOrNull?.endpoints ?? const [];
    for (final endpoint in endpoints) {
      if (endpoint.method == 'POST') return endpoint.path;
    }
    for (final endpoint in endpoints) {
      if (endpoint.method == 'GET' && !endpoint.path.contains('{')) return endpoint.path;
    }
    return null;
  }

  /// Only the Field widgets bound to the SAME class as the button that is
  /// running — a screen mixing several classes must never leak one class's
  /// typed values into another's request body.
  Map<String, Object?> _fieldValuesFor(String groupName) => {
    for (final placed in widget.layout.widgets)
      if (placed is FieldWidgetConfig && placed.groupName == groupName)
        placed.fieldName: _controllerFor('${placed.groupName}.${placed.fieldName}').text,
  };

  Future<String?> _promptId(String verb) => showDialog<String>(
    context: context,
    builder: (dialogContext) {
      final controller = TextEditingController();
      return AlertDialog(
        title: Text('$verb — record id'),
        content: AutofocusTextField(controller: controller, label: 'id'),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(dialogContext).pop(controller.text), child: Text(verb)),
        ],
      );
    },
  );

  Future<void> _run(ButtonWidgetConfig button) async {
    final path = _collectionPathFor(button.groupName);
    if (path == null) {
      setState(() => _resultText = '${button.groupName} has no collection endpoint to call.');
      return;
    }

    setState(() => _busy = true);
    ScreenActionResult result;
    String? recordId;
    Map<String, Object?>? requestBody;
    switch (button.action) {
      case ScreenAction.list:
        result = await _client.list(widget.deploymentBase, path);
      case ScreenAction.create:
        requestBody = _fieldValuesFor(button.groupName);
        result = await _client.create(widget.deploymentBase, path, requestBody);
      case ScreenAction.update:
        final id = await _promptId('Update');
        if (id == null || id.trim().isEmpty) {
          setState(() => _busy = false);
          return;
        }
        recordId = id.trim();
        requestBody = _fieldValuesFor(button.groupName);
        result = await _client.update(widget.deploymentBase, path, recordId, requestBody);
      case ScreenAction.delete:
        final id = await _promptId('Delete');
        if (id == null || id.trim().isEmpty) {
          setState(() => _busy = false);
          return;
        }
        recordId = id.trim();
        result = await _client.delete(widget.deploymentBase, path, recordId);
    }

    if (!mounted) return;

    // Only create/update/delete ever get queued — a read has no "pending"
    // semantics — and only when the request never actually left the device.
    // Anything else (timeout, 4xx/5xx, bad response) is surfaced exactly as
    // before and is NEVER auto-queued: the generated backend has no
    // idempotency key, so blindly retrying those risks duplicate records.
    if (button.action != ScreenAction.list && result is ScreenActionFailure && result.isUnreachable) {
      await _queue(button, path, recordId, requestBody);
      if (!mounted) return;
      setState(() {
        _busy = false;
        _resultText = 'No connection — queued, will sync automatically.';
      });
      return;
    }

    setState(() {
      _busy = false;
      _resultText = switch (result) {
        ScreenActionSuccess(:final data) => data == null ? 'Done.' : data.toString(),
        ScreenActionFailure(:final message) => message,
      };
    });
  }

  Future<void> _queue(
    ButtonWidgetConfig button,
    String collectionPath,
    String? recordId,
    Map<String, Object?>? requestBody,
  ) async {
    final kind = switch (button.action) {
      ScreenAction.create => PendingActionKind.create,
      ScreenAction.update => PendingActionKind.update,
      ScreenAction.delete => PendingActionKind.delete,
      ScreenAction.list => throw StateError('list is never queued'),
    };
    await _pendingActionStore.add(
      PendingActionEntry(
        entryId: '${DateTime.now().microsecondsSinceEpoch}-${_pendingEntrySeq++}',
        kind: kind,
        deploymentBase: widget.deploymentBase,
        collectionPath: collectionPath,
        recordId: recordId,
        body: requestBody,
        groupName: button.groupName,
        layoutName: widget.layout.name,
        queuedAt: DateTime.now(),
      ),
    );
    await _pendingActionSyncService.refreshPendingCount();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.layout.name),
        actions: [
          ValueListenableBuilder<int>(
            valueListenable: _pendingActionSyncService.pendingCount,
            builder: (context, count, _) {
              if (count == 0) return const SizedBox.shrink();
              return Center(
                child: TextButton.icon(
                  onPressed: _pendingActionSyncService.syncNow,
                  icon: const Icon(Icons.sync),
                  label: Text('$count pending'),
                ),
              );
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          for (final config in widget.layout.widgets)
            Positioned(left: config.x, top: config.y, child: _runtimeWidgetFor(config)),
          if (_resultText != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                padding: const EdgeInsets.all(12),
                constraints: const BoxConstraints(maxHeight: 200),
                child: SingleChildScrollView(child: Text(_resultText!)),
              ),
            ),
          if (_busy) const Positioned(top: 8, right: 8, child: CircularProgressIndicator()),
        ],
      ),
    );
  }

  Widget _runtimeWidgetFor(ScreenWidgetConfig config) {
    return switch (config) {
      LabelWidgetConfig(:final text) => Text(text, style: Theme.of(context).textTheme.titleMedium),
      FieldWidgetConfig(:final groupName, :final fieldName) => SizedBox(
        width: 160,
        child: TextField(
          controller: _controllerFor('$groupName.$fieldName'),
          decoration: InputDecoration(labelText: fieldName),
        ),
      ),
      ButtonWidgetConfig() => FilledButton(
        onPressed: _busy ? null : () => _run(config),
        child: Text(config.action.name),
      ),
    };
  }
}
