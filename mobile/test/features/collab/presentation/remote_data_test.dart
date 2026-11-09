import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/collab/domain/api_failure.dart';
import 'package:mobile/features/collab/presentation/widgets/remote_data.dart';

Widget _host(RemoteData<List<String>> child) => MaterialApp(home: Scaffold(body: child));

RemoteData<List<String>> _data(Future<List<String>> Function() load, {String empty = 'Nada por aquí.'}) {
  return RemoteData<List<String>>(
    load: load,
    isEmpty: (items) => items.isEmpty,
    emptyMessage: empty,
    builder: (context, items) => ListView(children: [for (final i in items) ListTile(title: Text(i))]),
  );
}

void main() {
  testWidgets('shows a spinner while loading, then the data', (tester) async {
    final completer = Completer<List<String>>();
    await tester.pumpWidget(_host(_data(() => completer.future)));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    completer.complete(['uno', 'dos']);
    await tester.pumpAndSettle();

    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.text('uno'), findsOneWidget);
    expect(find.text('dos'), findsOneWidget);
  });

  testWidgets('shows the empty message when there is nothing', (tester) async {
    await tester.pumpWidget(_host(_data(() async => [], empty: 'Todavía no hay diagramas.')));
    await tester.pumpAndSettle();

    expect(find.text('Todavía no hay diagramas.'), findsOneWidget);
  });

  testWidgets('a failure shows its explanation and a retry that works', (tester) async {
    var calls = 0;
    await tester.pumpWidget(_host(_data(() async {
      calls++;
      if (calls == 1) throw const ApiFailure(ApiFailureKind.offline);
      return ['listo'];
    })));
    await tester.pumpAndSettle();

    expect(find.textContaining('Sin conexión'), findsOneWidget);
    expect(find.text('listo'), findsNothing);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(find.text('listo'), findsOneWidget);
    expect(find.text('Reintentar'), findsNothing);
    expect(calls, 2);
  });

  testWidgets('a failure that cannot be fixed by retrying still offers to try again', (tester) async {
    await tester.pumpWidget(_host(_data(() async => throw const ApiFailure(ApiFailureKind.notFound))));
    await tester.pumpAndSettle();

    expect(find.text('No se encontró lo que buscas.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });

  testWidgets('an unexpected exception is explained and never crashes the screen', (tester) async {
    await tester.pumpWidget(_host(_data(() async => throw StateError('boom'))));
    await tester.pumpAndSettle();

    expect(find.text('Ocurrió un error inesperado.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pull to refresh reloads and shows the new data', (tester) async {
    var calls = 0;
    await tester.pumpWidget(_host(_data(() async => ['v${++calls}'])));
    await tester.pumpAndSettle();
    expect(find.text('v1'), findsOneWidget);

    await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();

    expect(find.text('v2'), findsOneWidget);
  });

  testWidgets('the empty state can also be pulled to refresh', (tester) async {
    var calls = 0;
    await tester.pumpWidget(_host(_data(() async => ++calls == 1 ? <String>[] : ['ya hay'])));
    await tester.pumpAndSettle();

    await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();

    expect(find.text('ya hay'), findsOneWidget);
  });

  testWidgets('leaving the screen while loading does not throw', (tester) async {
    final completer = Completer<List<String>>();
    await tester.pumpWidget(_host(_data(() => completer.future)));

    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: SizedBox())));
    completer.complete(['tarde']);
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });
}
