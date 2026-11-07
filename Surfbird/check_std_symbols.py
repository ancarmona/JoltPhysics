#!/usr/bin/env python3
"""Checks that the part of Jolt that Surfbird compiles uses no std:: name and no standard header beyond the recorded ones.

Surfbird builds Jolt without a C++ standard library, on its own subset of it (NativeCoreLibrary's std shim,
Source/Core/Std/Include in Surfbird). After an upstream update, run this before building:

    python Surfbird/check_std_symbols.py                       compare with Surfbird/std_symbols.txt (exit 1 on a new name)
    python Surfbird/check_std_symbols.py --shim <Include dir>  also check that every standard header Jolt includes is in the shim
                                                               (or is one of clang's own: the intrinsics, float.h, ...)
    python Surfbird/check_std_symbols.py --update              write the baseline again (after the shim has the new names)

The files are Surfbird's build of Jolt (Source/Surfbird/Jolt/Module.json "sources"): Jolt/**/*.cpp and every header and
.inl, without the optional modules below. Keep EXCLUDE the same as that Module.json's "exclude".
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOLT = ROOT / "Jolt"
BASELINE = Path(__file__).resolve().parent / "std_symbols.txt"
# Optional modules Surfbird leaves out (Module.json "exclude"), and their headers
EXCLUDE = ["Compute/**", "Renderer/**", "Physics/Hair/**", "Shaders/**", "ObjectStream/ObjectStream*", "ObjectStream/TypeDeclarations*",
           "Core/JobSystemThreadPool.*", "Core/JobSystemWithBarrier.*", "Core/Semaphore.*", "Core/Profiler.cpp", "Core/StreamWrapper.h"]
# Headers clang itself gives (its resource folder), not the standard library's
COMPILER_HEADERS = {"immintrin.h", "x86intrin.h", "intrin.h", "arm_neon.h", "arm64_neon.h", "riscv_vector.h", "larchintrin.h",
                    "float.h", "limits.h", "stdarg.h", "stddef.h", "stdint.h"}


def strip_code(text):
    """Comments and string literals blanked: a std:: in a comment is no use of the library."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r'"(?:\.|[^"\\n])*"', '""', text)


def files():
    excluded = {path for pattern in EXCLUDE for path in JOLT.glob(pattern)}
    return sorted(path for pattern in ("**/*.cpp", "**/*.h", "**/*.inl") for path in JOLT.glob(pattern) if path not in excluded)


def scan():
    """{std name: files} and {standard header: files}; preprocessor branches are not followed, so every branch counts."""
    names, headers = {}, {}
    for path in files():
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_text(encoding="utf-8", errors="replace")
        code = strip_code(raw)
        for match in re.finditer(r"\bstd::(\w+)", code):
            names.setdefault(match.group(1), set()).add(relative)
        if re.search(r"\busing\s+namespace\s+std\b", code):
            names.setdefault("<using namespace std>", set()).add(relative)
        for match in re.finditer(r"^\s*#\s*include\s*<([^>]+)>", raw, flags=re.M):
            if not match.group(1).startswith("Jolt/"):
                headers.setdefault(match.group(1), set()).add(relative)
    return names, headers


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="write the baseline from the current sources")
    parser.add_argument("--shim", type=Path, help="the std shim's include folder, to check the headers against")
    arguments = parser.parse_args()

    names, headers = scan()
    if arguments.update:
        lines = ["# std:: names used by the part of Jolt Surfbird compiles (Surfbird/check_std_symbols.py --update)"]
        lines += [f"std::{name}" for name in sorted(names)]
        lines += [f"<{header}>" for header in sorted(headers)]
        BASELINE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{BASELINE.name}: {len(names)} names, {len(headers)} headers")
        return 0

    known = set(BASELINE.read_text(encoding="utf-8").split()) if BASELINE.exists() else set()
    failed = False
    for name in sorted(names):
        if f"std::{name}" not in known:
            failed = True
            print(f"new: std::{name} in {', '.join(sorted(names[name]))}")
    for header in sorted(headers):
        if f"<{header}>" not in known:
            failed = True
            print(f"new: #include <{header}> in {', '.join(sorted(headers[header]))}")
    if arguments.shim:
        for header in sorted(headers):
            if header not in COMPILER_HEADERS and not (arguments.shim / header).exists():
                # Platform headers behind #if (the Windows SDK, Apple, POSIX) that Surfbird's targets never reach are listed too
                print(f"not in the shim: <{header}> ({', '.join(sorted(headers[header]))})")
    print(f"{len(files())} files, {len(names)} std names, {len(headers)} headers: {'NEW ONES' if failed else 'as recorded'}")
    return 1 if failed else 0


sys.exit(main())
