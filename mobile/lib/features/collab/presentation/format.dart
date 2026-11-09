/// `8/11/2026 10:05`, in the phone's local time. Plain string work: the app
/// has no `intl` dependency and this is the only date format it needs.
String formatDateTime(DateTime utc) {
  final local = utc.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${local.day}/${local.month}/${local.year} ${two(local.hour)}:${two(local.minute)}';
}
