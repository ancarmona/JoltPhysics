# Surfbird's branch of Jolt Physics

This is the `surfbird` branch of `ancarmona/JoltPhysics`, a fork of `jrouwe/JoltPhysics`. Surfbird (a custom VR engine)
compiles Jolt in its own build: clang 20, C++23, no C++ standard library (`-nostdinc`), no exceptions, no RTTI. The
standard library names Jolt uses come from a small subset that NativeCoreLibrary implements (its std shim,
`Source/Core/Std/Include` in Surfbird). This choice is decision D33 of the Birdwatcher project (route B).

## Base

- Upstream commit: `57d9e2a4` (2026-11-06, "Fixed a race condition in JobSystemWithBarrier (#2206)"). Jolt 5.6.1.

## Patches to Jolt's sources

One, on ARM only (one commit):

| File | Change | Reason |
|---|---|---|
| `Jolt/Math/Vec3.inl`, `Vec4.inl`, `DVec3.inl` | `sFusedMultiplyAdd` on NEON: `vfmaq_f32` / `vfmaq_f64` instead of `vmlaq_f32` / `vmlaq_f64` | `vmlaq` is a multiply then an add; clang fuses it only with FP contraction on, which Surfbird's build turns off (`-ffp-contract=off`). Jolt's CMake turns contraction on for ARM instead, but contraction then also fuses every other `a * b + c` of the source, Surfbird's own code included, and the results differ from x86. `vfmaq` fuses only here, like `_mm_fmadd_ps` on x86. Without it, `TestDifferenceOfProducts` fails on ARM |

Otherwise Jolt compiles unchanged. These parts make that possible, and none of them is in this repository:

| Need | Where it is met |
|---|---|
| The `std` names and standard headers that Jolt uses (84 names, see `std_symbols.txt`) | NativeCoreLibrary `Std/Include` (the std shim) and `Std/Std.cpp` |
| `__debugbreak` (`JPH_BREAKPOINT` on Windows), which clang declares only for MSVC targets. Surfbird targets `x86_64-pc-windows-gnu` | Surfbird `Source/Surfbird/Jolt/JoltConfig.h` |
| `__MINGW32__` is undefined, because there is no MinGW runtime | Surfbird `Source/Surfbird/Jolt/Module.json` (`-U__MINGW32__ -U__MINGW64__`) |
| Static destructors are left out (no `atexit`) | `-fno-c++-static-destructors` on Jolt's sources |
| Function-local statics (`__cxa_guard_*`) | the std shim's `Std.cpp` |
| Configuration: `JPH_DOUBLE_PRECISION`, `JPH_ENABLE_ASSERTS` in Checked builds only, cross-platform determinism off | `JoltConfig.h`, force-included in every source that includes Jolt |

Some parts of Jolt are not compiled: `Compute/`, `Renderer/`, `Physics/Hair/`, `Shaders/`, ObjectStream (except
`SerializableObject.cpp`), `JobSystemThreadPool`, `JobSystemWithBarrier`, `Semaphore` and `Profiler.cpp`. Surfbird has
its own job system adapter on its Core job system.

This branch adds files only, all of them in `Surfbird/`:

- `PATCHES.md` (this file).
- `check_std_symbols.py`.
- `std_symbols.txt`, the baseline for `check_std_symbols.py`.

## Taking a new upstream version

1. `git fetch upstream && git merge upstream/master` on `surfbird`. Only the patch above changes upstream files: resolve it if
   upstream changed those lines.
2. Run `python Surfbird/check_std_symbols.py --shim <Surfbird>/Source/Core/Std/Include`. If it reports a new `std::` name
   or header, add it to the shim (in NativeCoreLibrary), then run the script again with `--update`.
3. Check `Jolt/Jolt.cmake` for new or removed source files and for new optional modules. Update the `exclude` list in
   Surfbird's `Source/Surfbird/Jolt/Module.json` and `EXCLUDE` in the script, so that the two stay the same.
4. Build Surfbird (`python Tools/winbuild.py`). Then run `SurfbirdPhysicsTests` (Checked and Unchecked) and
   `Tools/Tests/test_physics.py`.

If a source patch ever becomes necessary, keep it small, add it here (file, reason, upstream issue), and make each patch its
own commit, so that a merge shows it.
