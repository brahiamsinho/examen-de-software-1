import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/api_connection/domain/connection_failure.dart';
import 'package:mobile/features/api_connection/domain/openapi_url.dart';

void main() {
  group('normalizeOpenApiUrl', () {
    const valid = <String, String>{
      'https://demo.example.com/gen/abc/':
          'https://demo.example.com/gen/abc/v3/api-docs',
      'https://demo.example.com': 'https://demo.example.com/v3/api-docs',
      '  http://192.168.1.5:8090/gen/abc  ':
          'http://192.168.1.5:8090/gen/abc/v3/api-docs',
      'http://localhost:8080/v3/api-docs': 'http://localhost:8080/v3/api-docs',
      'http://localhost:8080/v3/api-docs/':
          'http://localhost:8080/v3/api-docs',
      'http://h/gen/abc/swagger-ui/index.html?x=1#frag':
          'http://h/gen/abc/v3/api-docs',
      'http://h/gen/abc/swagger-ui.html': 'http://h/gen/abc/v3/api-docs',
      'HTTPS://Demo.Example.com/gen/abc':
          'https://demo.example.com/gen/abc/v3/api-docs',
      'https://demo.example.com/gen/abc?token=1#top':
          'https://demo.example.com/gen/abc/v3/api-docs',
    };

    valid.forEach((input, expected) {
      test('normalizes "$input"', () {
        expect(normalizeOpenApiUrl(input).toString(), expected);
      });
    });

    const invalid = <String>[
      '',
      '   ',
      'not a url',
      'ftp://host/path',
      'demo.example.com/gen/abc',
      'localhost:8080/x',
      'http://',
      'https:///path',
    ];

    for (final input in invalid) {
      test('rejects "$input" as an invalid URL', () {
        expect(
          () => normalizeOpenApiUrl(input),
          throwsA(
            isA<ConnectionFailure>().having(
              (f) => f.kind,
              'kind',
              ConnectionFailureKind.invalidUrl,
            ),
          ),
        );
      });
    }
  });
}
