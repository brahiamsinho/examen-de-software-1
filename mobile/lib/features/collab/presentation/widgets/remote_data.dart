import 'package:flutter/material.dart';

import '../../domain/api_failure.dart';

/// Loads something from the server and shows the state a person needs to
/// understand (issue #19, S4): a spinner, the data, an empty message, or the
/// failure with a retry. Pull down to refresh.
///
/// One component for every collaborative screen, so each of them explains
/// "loading / offline / error / retry" the same way instead of reinventing it.
class RemoteData<T> extends StatefulWidget {
  const RemoteData({
    super.key,
    required this.load,
    required this.builder,
    this.isEmpty,
    this.emptyMessage = 'No hay nada para mostrar.',
  });

  final Future<T> Function() load;

  /// Must return a scrollable (a `ListView`): it is what the pull-to-refresh
  /// gesture attaches to.
  final Widget Function(BuildContext context, T data) builder;
  final bool Function(T data)? isEmpty;
  final String emptyMessage;

  @override
  State<RemoteData<T>> createState() => RemoteDataState<T>();
}

class RemoteDataState<T> extends State<RemoteData<T>> {
  bool _loading = true;
  T? _data;
  bool _hasData = false;
  ApiFailure? _failure;

  @override
  void initState() {
    super.initState();
    reload();
  }

  /// Loads again showing the spinner (first load and "Reintentar").
  Future<void> reload() async {
    setState(() {
      _loading = true;
      _failure = null;
    });
    await _fetch(keepOldDataOnFailure: false);
  }

  Future<void> _refresh() => _fetch(keepOldDataOnFailure: true);

  Future<void> _fetch({required bool keepOldDataOnFailure}) async {
    try {
      final data = await widget.load();
      if (!mounted) return;
      setState(() {
        _data = data;
        _hasData = true;
        _failure = null;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      final failure = error is ApiFailure ? error : const ApiFailure(ApiFailureKind.unexpected);
      if (keepOldDataOnFailure && _hasData) {
        // A failed refresh must not wipe what the person is reading. An ended
        // session is the exception: the login screen explains it, and the
        // session controller already closed this page.
        if (failure.kind != ApiFailureKind.unauthorized) {
          ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(failure.userMessage)));
        }
        return;
      }
      setState(() {
        _failure = failure;
        _hasData = false;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final failure = _failure;
    if (failure != null) return _FailureView(failure: failure, onRetry: reload);

    final data = _data as T;
    final empty = widget.isEmpty?.call(data) ?? false;
    return ScrollConfiguration(
      behavior: const _AlwaysScrollable(),
      child: RefreshIndicator(
        onRefresh: _refresh,
        child: empty
            ? ListView(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(32),
                    child: Center(child: Text(widget.emptyMessage, textAlign: TextAlign.center)),
                  ),
                ],
              )
            : widget.builder(context, data),
      ),
    );
  }
}

// Short lists must still be pullable, or "refresh" would not work on them.
class _AlwaysScrollable extends MaterialScrollBehavior {
  const _AlwaysScrollable();

  @override
  ScrollPhysics getScrollPhysics(BuildContext context) =>
      const AlwaysScrollableScrollPhysics(parent: ClampingScrollPhysics());
}

class _FailureView extends StatelessWidget {
  const _FailureView({required this.failure, required this.onRetry});

  final ApiFailure failure;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final offline = failure.kind == ApiFailureKind.offline || failure.kind == ApiFailureKind.timeout;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(offline ? Icons.cloud_off_outlined : Icons.error_outline, size: 40),
            const SizedBox(height: 12),
            Semantics(liveRegion: true, child: Text(failure.userMessage, textAlign: TextAlign.center)),
            const SizedBox(height: 16),
            FilledButton.tonal(onPressed: onRetry, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }
}
