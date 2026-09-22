import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/api_connection/data/openapi_parser.dart';
import 'package:mobile/features/api_connection/domain/connection_failure.dart';

Map<String, Object?> _doc({
  String openapi = '3.1.0',
  Object? paths,
  Object? info = const {'title': 'Demo API', 'version': '1.2.3'},
  Object? components,
}) => {
  'openapi': openapi,
  'info': ?info,
  'paths': ?paths,
  'components': ?components,
};

Matcher _invalidOpenApi() => throwsA(
  isA<ConnectionFailure>().having(
    (f) => f.kind,
    'kind',
    ConnectionFailureKind.invalidOpenApi,
  ),
);

void main() {
  group('parseOpenApi', () {
    test('groups tagged endpoints and keeps document order', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/api/class-as': {
              'get': {
                'tags': ['class-a-controller'],
                'summary': 'List',
              },
              'post': {
                'tags': ['class-a-controller'],
              },
            },
            '/api/class-as/{id}': {
              'parameters': <Object?>[],
              'get': {
                'tags': ['class-a-controller'],
              },
              'put': {
                'tags': ['class-a-controller'],
              },
              'delete': {
                'tags': ['class-a-controller'],
              },
            },
          },
        ),
      );

      expect(result.title, 'Demo API');
      expect(result.version, '1.2.3');
      expect(result.openApiVersion, '3.1.0');
      expect(result.groups, hasLength(1));
      expect(result.groups.single.name, 'class-a-controller');
      expect(result.endpointCount, 5);
      expect(
        result.groups.single.endpoints.map((e) => '${e.method} ${e.path}'),
        [
          'GET /api/class-as',
          'POST /api/class-as',
          'GET /api/class-as/{id}',
          'PUT /api/class-as/{id}',
          'DELETE /api/class-as/{id}',
        ],
      );
      expect(result.groups.single.endpoints.first.summary, 'List');
    });

    test('accepts OpenAPI 3.0.x', () {
      expect(
        parseOpenApi(_doc(openapi: '3.0.3', paths: <String, Object?>{})).groups,
        isEmpty,
      );
    });

    test('groups untagged endpoints by the segment after /api/', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/api/orders': {'get': <String, Object?>{}},
            '/api/orders/{id}': {'delete': <String, Object?>{}},
          },
        ),
      );

      expect(result.groups.single.name, 'orders');
      expect(result.groups.single.endpoints, hasLength(2));
    });

    test('groups untagged endpoints without /api/ by first segment', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/health': {'get': <String, Object?>{}},
            '/': {'get': <String, Object?>{}},
          },
        ),
      );

      expect(result.groups.map((g) => g.name), ['health', 'untagged']);
    });

    test('resolves a group\'s attribute names from its POST request body schema', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/api/class-as': {
              'post': {
                'tags': ['class-a-controller'],
                'requestBody': {
                  'content': {
                    'application/json': {
                      'schema': {r'$ref': '#/components/schemas/ClassARequestDto'},
                    },
                  },
                },
              },
            },
          },
          components: {
            'schemas': {
              'ClassARequestDto': {
                'properties': {'edad': {}, 'name': {}},
              },
            },
          },
        ),
      );

      expect(result.groups.single.attributeNames, ['edad', 'name']);
    });

    test('a group with no POST, or an unresolvable schema, has no attribute names', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/api/class-as': {
              'get': {
                'tags': ['class-a-controller'],
              },
            },
            '/api/orders': {
              'post': {
                'tags': ['orders'],
                'requestBody': {
                  'content': {
                    'application/json': {
                      'schema': {r'$ref': '#/components/schemas/Missing'},
                    },
                  },
                },
              },
            },
          },
        ),
      );

      expect(result.groups.map((g) => g.attributeNames), [[], []]);
    });

    test('sorts groups by name', () {
      final result = parseOpenApi(
        _doc(
          paths: {
            '/b': {
              'get': {
                'tags': ['zeta'],
              },
            },
            '/a': {
              'get': {
                'tags': ['alpha'],
              },
            },
          },
        ),
      );

      expect(result.groups.map((g) => g.name), ['alpha', 'zeta']);
    });

    test('uses defaults when info is missing', () {
      final result = parseOpenApi(
        _doc(info: null, paths: <String, Object?>{}),
      );

      expect(result.title, 'Untitled API');
      expect(result.version, '');
    });

    test('rejects a Swagger 2 document', () {
      expect(
        () => parseOpenApi({'swagger': '2.0', 'paths': <String, Object?>{}}),
        _invalidOpenApi(),
      );
    });

    test('rejects an unsupported openapi version', () {
      expect(
        () => parseOpenApi(_doc(openapi: '4.0.0', paths: <String, Object?>{})),
        _invalidOpenApi(),
      );
    });

    test('rejects a document without paths', () {
      expect(() => parseOpenApi(_doc()), _invalidOpenApi());
    });

    test('rejects paths that are not an object', () {
      expect(() => parseOpenApi(_doc(paths: <Object?>[])), _invalidOpenApi());
    });

    test('rejects a JSON value that is not an object', () {
      expect(() => parseOpenApi(<Object?>[1, 2]), _invalidOpenApi());
      expect(() => parseOpenApi(null), _invalidOpenApi());
    });
  });
}
