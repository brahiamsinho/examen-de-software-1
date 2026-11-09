import 'package:flutter/material.dart';

import '../domain/api_failure.dart';
import '../domain/organization.dart';
import '../domain/proposal.dart';
import 'format.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

enum _Decision { approve, reject }

/// The drafts the AI left on the board, to approve or reject from the phone
/// (issue #19, S1). Only an OWNER or EDITOR decides; a VIEWER just reads.
/// Approving changes the shared diagram, so it asks first; a decision is never
/// retried automatically.
class ProposalsTab extends StatefulWidget {
  const ProposalsTab({super.key, required this.controller, required this.organization, required this.document});

  final SessionController controller;
  final Organization organization;
  final DocumentSummary document;

  @override
  State<ProposalsTab> createState() => _ProposalsTabState();
}

class _ProposalsTabState extends State<ProposalsTab> {
  final _remote = GlobalKey<RemoteDataState<List<Proposal>>>();
  String? _busyId;
  String? _error;

  Future<List<Proposal>> _load() => widget.controller.run((repository) async {
    final proposals = await repository.listProposals(widget.organization.slug, widget.document.id);
    return proposals.where((proposal) => proposal.isPending).toList();
  });

  Future<void> _decide(Proposal proposal, _Decision decision) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _ConfirmDialog(decision: decision, changeCount: proposal.changes.length),
    );
    if (confirmed != true || !mounted) return;

    setState(() {
      _busyId = proposal.id;
      _error = null;
    });
    try {
      await widget.controller.run(
        (repository) => decision == _Decision.approve
            ? repository.approveProposal(widget.organization.slug, widget.document.id, proposal.id)
            : repository.rejectProposal(widget.organization.slug, widget.document.id, proposal.id),
      );
      if (!mounted) return;
      final count = proposal.changes.length;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            decision == _Decision.approve
                ? 'Propuesta aprobada: se ${count == 1 ? 'aplicó 1 cambio' : 'aplicaron $count cambios'}.'
                : 'Propuesta rechazada.',
          ),
        ),
      );
      await _remote.currentState?.refresh();
    } on ApiFailure catch (failure) {
      if (!mounted) return;
      setState(() => _error = _explain(failure));
      // After a conflict the list on screen is out of date: show the truth.
      if (failure.kind == ApiFailureKind.conflict) await _remote.currentState?.refresh();
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  String _explain(ApiFailure failure) {
    switch (failure.kind) {
      case ApiFailureKind.conflict:
        return 'La propuesta ya no es válida: el diagrama cambió o alguien ya decidió. Se actualizó la lista.';
      case ApiFailureKind.offline:
      case ApiFailureKind.timeout:
        // The decision may have reached the server. It is not repeated for the
        // person: refreshing shows whether it did.
        return 'Sin conexión estable: no sabemos si se aplicó tu decisión. '
            'Actualiza la lista para comprobarlo antes de repetirla.';
      default:
        return failure.userMessage;
    }
  }

  @override
  Widget build(BuildContext context) {
    final canDecide = widget.organization.role.canWrite;
    return Column(
      children: [
        Expanded(
          child: RemoteData<List<Proposal>>(
            key: _remote,
            load: _load,
            isEmpty: (proposals) => proposals.isEmpty,
            emptyMessage: 'No hay propuestas pendientes. Lo que proponga la IA aparecerá aquí.',
            builder: (context, proposals) => ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: proposals.length,
              itemBuilder: (context, index) {
                final proposal = proposals[index];
                return _ProposalCard(
                  proposal: proposal,
                  canDecide: canDecide,
                  busy: _busyId != null,
                  onApprove: () => _decide(proposal, _Decision.approve),
                  onReject: () => _decide(proposal, _Decision.reject),
                );
              },
            ),
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Semantics(
              liveRegion: true,
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          ),
        if (!canDecide)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Eres lector: puedes ver las propuestas, pero no decidirlas.'),
          ),
      ],
    );
  }
}

class _ProposalCard extends StatelessWidget {
  const _ProposalCard({
    required this.proposal,
    required this.canDecide,
    required this.busy,
    required this.onApprove,
    required this.onReject,
  });

  final Proposal proposal;
  final bool canDecide;
  final bool busy;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.smart_toy_outlined, size: 16),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    'Pedida por ${proposal.requestedBy} · ${formatDateTime(proposal.createdAt)}',
                    style: theme.textTheme.bodySmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(proposal.prompt, style: theme.textTheme.titleSmall),
            const SizedBox(height: 8),
            for (final change in proposal.changes)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      change.ok ? Icons.check_circle_outline : Icons.error_outline,
                      size: 16,
                      color: change.ok ? null : theme.colorScheme.error,
                    ),
                    const SizedBox(width: 6),
                    Expanded(child: Text(change.message)),
                  ],
                ),
              ),
            if (canDecide) ...[
              if (!proposal.canApprove)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text(
                    'Alguno de los cambios no se puede aplicar, así que solo puedes rechazar esta propuesta.',
                  ),
                ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(onPressed: busy ? null : onReject, child: const Text('Rechazar')),
                  if (proposal.canApprove) ...[
                    const SizedBox(width: 8),
                    FilledButton(onPressed: busy ? null : onApprove, child: const Text('Aprobar')),
                  ],
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ConfirmDialog extends StatelessWidget {
  const _ConfirmDialog({required this.decision, required this.changeCount});

  final _Decision decision;
  final int changeCount;

  @override
  Widget build(BuildContext context) {
    final approve = decision == _Decision.approve;
    return AlertDialog(
      title: Text(approve ? 'Aprobar propuesta' : 'Rechazar propuesta'),
      content: Text(
        approve
            ? 'Se aplicarán $changeCount ${changeCount == 1 ? 'cambio' : 'cambios'} al diagrama y '
                  'todo el equipo los verá.'
            : 'La propuesta se descartará y no se aplicará ningún cambio.',
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: Text(approve ? 'Aprobar' : 'Rechazar'),
        ),
      ],
    );
  }
}
