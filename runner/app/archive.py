"""Safe zip intake: validate a project zip and repack it as an in-memory tar.

The tar is streamed straight into a Docker volume (`put_archive`), so nothing
from the request ever touches the runner's own filesystem and no host path is
involved. Rejected: oversize archives, too many entries, absolute paths, `..`
segments, backslashes, symlinks and zip bombs (declared unpacked size cap).
"""
import io
import posixpath
import stat
import tarfile
import zipfile


class InvalidArchiveError(ValueError):
    """The uploaded archive is not an acceptable project zip."""


def _clean_member(name: str) -> str:
    if "\\" in name or name.startswith("/") or "\x00" in name:
        raise InvalidArchiveError(f"unsafe path in archive: {name!r}")
    parts = name.split("/")
    if any(part in ("..",) for part in parts):
        raise InvalidArchiveError(f"path traversal in archive: {name!r}")
    return posixpath.normpath(name)


def zip_to_tar(
    data: bytes, *, max_zip_bytes: int, max_unpacked_bytes: int, max_files: int
) -> bytes:
    """Return a tar (uncompressed) with the zip's single top folder stripped."""
    if len(data) > max_zip_bytes:
        raise InvalidArchiveError("archive too large")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise InvalidArchiveError("not a valid zip") from exc

    entries = [info for info in archive.infolist() if not info.is_dir()]
    if not entries:
        raise InvalidArchiveError("archive has no files")
    if len(entries) > max_files:
        raise InvalidArchiveError("too many files in archive")
    if sum(info.file_size for info in entries) > max_unpacked_bytes:
        raise InvalidArchiveError("archive unpacks to too much data")

    names = [_clean_member(info.filename) for info in entries]
    top_folders = {name.split("/", 1)[0] for name in names}
    strip_top = len(top_folders) == 1 and all("/" in name for name in names)

    unpacked = 0
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for info, name in zip(entries, names):
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise InvalidArchiveError(f"symlink in archive: {info.filename!r}")
            target = name.split("/", 1)[1] if strip_top else name
            payload = archive.read(info)
            unpacked += len(payload)  # declared sizes can lie: count the real bytes too
            if unpacked > max_unpacked_bytes:
                raise InvalidArchiveError("archive unpacks to too much data")
            tar_info = tarfile.TarInfo(target)
            tar_info.size = len(payload)
            tar_info.mode = 0o644
            tar_info.mtime = 0
            tar.addfile(tar_info, io.BytesIO(payload))
    return buffer.getvalue()
