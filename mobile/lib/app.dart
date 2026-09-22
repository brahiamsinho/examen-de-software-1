import 'package:flutter/material.dart';

import 'core/config/app_config.dart';
import 'features/api_connection/data/openapi_client.dart';
import 'features/api_connection/presentation/connect_controller.dart';
import 'features/api_connection/presentation/connect_page.dart';

/// App root. `client` is injectable so tests (and, later, other entry
/// points) never depend on a real `http.Client` (design.md
/// `ModeliaApp({OpenApiClient? client})`).
class ModeliaApp extends StatelessWidget {
  // `client` is the public parameter name tests rely on; `this._client`
  // would rename it to the private `_client` and break every
  // `ModeliaApp(client: ...)` call.
  // ignore: prefer_initializing_formals
  const ModeliaApp({super.key, OpenApiClient? client}) : _client = client;

  final OpenApiClient? _client;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Modelia',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo)),
      home: ConnectPage(
        controller: ConnectController(client: _client ?? OpenApiClient()),
        initialUrl: AppConfig.generatedApiUrl,
      ),
    );
  }
}
