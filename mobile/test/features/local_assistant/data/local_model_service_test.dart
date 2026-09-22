import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/local_assistant/data/local_model_service.dart';

// Only the pure, no-network/no-plugin logic is testable here: the download
// URL constant. Real install()/isModelInstalled() need a real device and a
// registered LiteRT-LM engine, so they are not unit-tested (see report).
void main() {
  group('LocalModelService', () {
    test('modelDownloadUrl points at the exact litertlm file under /resolve/main/', () {
      expect(
        LocalModelService.modelDownloadUrl,
        'https://huggingface.co/litert-community/Gemma3-1B-IT/resolve/main/'
        '${LocalModelService.modelFileName}',
      );
    });

    test('modelFileName is the multi-platform litertlm build, not a .task file', () {
      expect(LocalModelService.modelFileName, endsWith('.litertlm'));
    });
  });
}
