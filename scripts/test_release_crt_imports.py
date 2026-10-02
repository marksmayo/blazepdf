"""Verify the Windows release executables do not require runtime CRT DLLs.

Reads PE import descriptors using only Python's standard library. This checks
the produced artifacts rather than merely checking a build configuration flag.
"""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def imported_dlls(path):
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe:pe + 4] == b"PE\0\0", path
    sections = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    assert magic in (0x10B, 0x20B), magic
    directories = optional + (112 if magic == 0x20B else 96)
    import_rva = struct.unpack_from("<I", data, directories + 8)[0]
    assert import_rva, "missing import table"
    section_table = optional + optional_size

    def offset(rva):
        for index in range(sections):
            section = section_table + 40 * index
            virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", data, section + 8)
            if address <= rva < address + max(virtual_size, raw_size):
                result = raw_offset + rva - address
                assert 0 <= result < len(data), rva
                return result
        raise AssertionError(f"unmapped RVA {rva}")

    descriptor = offset(import_rva)
    dlls = []
    for index in range(1024):
        fields = struct.unpack_from("<IIIII", data, descriptor + index * 20)
        if not any(fields):
            return dlls
        name = offset(fields[3])
        end = data.index(b"\0", name)
        dlls.append(data[name:end].decode("ascii").lower())
    raise AssertionError("unterminated import table")


def main():
    paths = [Path(value) for value in sys.argv[1:]] or [
        ROOT / "target/release/blazepdf.exe",
        ROOT / "target/release/blazepdf-window.exe",
    ]
    for path in paths:
        dlls = imported_dlls(path)
        assert "kernel32.dll" in dlls, (path, dlls)
        crt = [name for name in dlls if "vcruntime" in name or "api-ms-win-crt" in name or name.startswith("msvcr")]
        print(f"{path.name}: CRT imports {crt}")
        assert not crt, (path, crt)


if __name__ == "__main__":
    main()
