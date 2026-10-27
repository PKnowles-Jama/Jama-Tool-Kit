"""Actual ZIP containers for formats excluded by Jama's attachment allowlist."""
import io
import zipfile
from .core import local_file


def pack(data, name):
    local_file('.', name)
    buffer = io.BytesIO()
    # Fixed metadata makes resumed uploads byte-for-byte deterministic.
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(info, data, compresslevel=9)
    return buffer.getvalue()


def unpack(data, name, limit, expected_bytes=None):
    local_file('.', name)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != name:
            raise ValueError('Expected exactly the named artifact in its ZIP container')
        info = entries[0]
        if info.flag_bits & 1 or not 0 < info.file_size <= limit:
            raise ValueError('ZIP content is encrypted or exceeds its expansion budget')
        if expected_bytes is not None and info.file_size != expected_bytes:
            raise ValueError('ZIP uncompressed length differs from manifest')
        return archive.read(info)
