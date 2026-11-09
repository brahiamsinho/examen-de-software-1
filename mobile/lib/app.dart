import 'package:flutter/material.dart';

import 'core/config/app_config.dart';
import 'features/api_connection/data/openapi_client.dart';
import 'features/api_connection/presentation/connect_controller.dart';
import 'features/api_connection/presentation/connect_page.dart';
import 'features/collab/presentation/collab_entry.dart';
import 'features/local_assistant/presentation/local_assistant_settings_page.dart';

/// App root. `client` is injectable so tests (and, later, other entry
/// points) never depend on a real `http.Client` (design.md
/// `ModeliaApp({OpenApiClient? client})`).
class ModeliaApp extends StatefulWidget {
  // `client` is the public parameter name tests rely on; `this._client`
  // would rename it to the private `_client` and break every
  // `ModeliaApp(client: ...)` call.
  // ignore: prefer_initializing_formals
  const ModeliaApp({super.key, OpenApiClient? client}) : _client = client;

  final OpenApiClient? _client;

  @override
  State<ModeliaApp> createState() => _ModeliaAppState();
}

/// Counts the pages on the navigator's stack, so the shell can tell whether
/// the home screen is the one showing.
class _PageDepthObserver extends NavigatorObserver {
  final ValueNotifier<int> depth = ValueNotifier(0);

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) => depth.value++;

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) => depth.value--;

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) => depth.value--;
}

class _ModeliaAppState extends State<ModeliaApp> {
  // A GlobalKey (MaterialApp's own `navigatorKey`) is how a widget above the
  // Navigator — the `builder` below runs outside it — reaches Navigator
  // without a BuildContext under it. Used only to give the on-device
  // assistant and the collaborative area a reachable entry point without
  // touching api_connection's own screens/AppBar.
  static final _navigatorKey = GlobalKey<NavigatorState>();

  final _pages = _PageDepthObserver();

  @override
  void dispose() {
    _pages.depth.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      navigatorObservers: [_pages],
      title: 'Modelia',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo)),
      // Entry points to the on-device AI assistant (local_assistant feature)
      // and to the collaborative area (collab feature, issue #19). Added at
      // the app shell level, not inside any existing feature's page.
      //
      // They show ONLY on the home screen (one page on the stack). Because
      // this `builder` wraps the whole navigator, buttons here would float
      // over every page, including the collaborative chat, where they would
      // cover its send button.
      //
      // This `builder` runs OUTSIDE the Overlay/Navigator that MaterialApp
      // creates internally for `home`/routes, so anything here that needs an
      // Overlay ancestor (FloatingActionButton wraps itself in a Tooltip,
      // and Tooltip needs one) has none. Without this explicit Overlay, that
      // throws a widget-build exception on every single frame — confirmed
      // live via `flutter run`: "No Overlay widget found... RawTooltip
      // widgets require an Overlay widget ancestor" — which is what painted
      // the whole screen red (Flutter's per-frame build-error indicator).
      builder: (context, child) => Overlay(
        initialEntries: [
          OverlayEntry(
            builder: (context) => Stack(
              children: [
                ?child,
                ValueListenableBuilder<int>(
                  valueListenable: _pages.depth,
                  builder: (context, depth, _) => depth > 1
                      ? const SizedBox.shrink()
                      : Stack(
                          children: [
                            Positioned(
                              right: 16,
                              bottom: 72,
                              child: FloatingActionButton.extended(
                                heroTag: 'collab_entry',
                                tooltip: 'Colaborar en Modelia',
                                icon: const Icon(Icons.groups_outlined),
                                label: const Text('Colaborar en Modelia'),
                                onPressed: () => _navigatorKey.currentState?.push(
                                  MaterialPageRoute(builder: (_) => const CollabEntry()),
                                ),
                              ),
                            ),
                            Positioned(
                              right: 16,
                              bottom: 16,
                              child: FloatingActionButton.small(
                                heroTag: 'local_assistant_entry',
                                tooltip: 'On-device assistant',
                                onPressed: () => _navigatorKey.currentState?.push(
                                  MaterialPageRoute(builder: (_) => const LocalAssistantSettingsPage()),
                                ),
                                child: const Icon(Icons.smart_toy_outlined),
                              ),
                            ),
                          ],
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
      home: ConnectPage(
        controller: ConnectController(client: widget._client ?? OpenApiClient()),
        initialUrl: AppConfig.generatedApiUrl,
      ),
    );
  }
}
