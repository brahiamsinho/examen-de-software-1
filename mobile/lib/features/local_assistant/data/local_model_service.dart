import 'package:flutter_gemma/flutter_gemma.dart';
import 'package:flutter_gemma_litertlm/flutter_gemma_litertlm.dart';

/// Wraps flutter_gemma's install/download + active-model lookup for the
/// local_assistant feature (on-device AI, step 1 of 3: prove the pipeline
/// works end to end — function-calling wiring and an offline OpenAPI cache
/// are later steps).
///
/// flutter_gemma's core package ships NO inference engine on its own (it is
/// a federated plugin): [ensureEngineRegistered] registers the LiteRT-LM
/// engine (from the separate `flutter_gemma_litertlm` package) that actually
/// runs a `.litertlm` file. Every method here calls it first, so callers
/// never have to remember to.
class LocalModelService {
  const LocalModelService();

  /// The exact `.litertlm` file flutter_gemma's own README quick-start
  /// example downloads for Gemma3-1B-IT — the multi-prefill-seq, q4 build
  /// that runs on every platform (desktop + mobile), confirmed against the
  /// real file listing at https://huggingface.co/litert-community/Gemma3-1B-IT.
  static const modelFileName = 'Gemma3-1B-IT_multi-prefill-seq_q4_ekv4096.litertlm';

  /// Built from [modelFileName] (never duplicated as a literal) so the two
  /// can never drift apart. Uses `/resolve/main/`, not `/blob/main/` — the
  /// raw-file path Hugging Face requires for a direct download.
  static const modelDownloadUrl =
      'https://huggingface.co/litert-community/Gemma3-1B-IT/resolve/main/$modelFileName';

  static bool _engineRegistered = false;

  /// Registers the LiteRT-LM engine. Idempotent (safe to call before every
  /// operation) — `FlutterGemma.initialize` is otherwise required exactly
  /// once at app startup, which this app has no single entry point for
  /// (features load their own dependencies lazily), so each operation below
  /// ensures it itself instead.
  Future<void> ensureEngineRegistered() async {
    if (_engineRegistered) return;
    await FlutterGemma.initialize(inferenceEngines: const [LiteRtLmEngine()]);
    _engineRegistered = true;
  }

  /// Whether Gemma3-1B-IT is already installed on this device — so
  /// re-opening the download screen doesn't force a redownload.
  Future<bool> isModelInstalled() async {
    await ensureEngineRegistered();
    return FlutterGemma.isModelInstalled(modelFileName);
  }

  /// Downloads and installs Gemma3-1B-IT, authenticated with the user's own
  /// Hugging Face [token]. [onProgress] receives 0-100. Idempotent: if the
  /// model is already installed, flutter_gemma skips the download and just
  /// (re)activates it as the active inference model.
  ///
  /// Throws [DownloadException] (401/403/404/429/5xx/network — see
  /// `DownloadError.toUserMessage()`) or another [Exception] on failure.
  Future<void> install({required String token, required void Function(int progress) onProgress}) async {
    await ensureEngineRegistered();
    await FlutterGemma.installModel(modelType: ModelType.gemmaIt, fileType: ModelFileType.litertlm)
        .fromNetwork(modelDownloadUrl, token: token)
        .withProgress(onProgress)
        .install();
  }
}
