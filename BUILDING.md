# Building KoreanAIR AC8 Mod Pack

Build on 64-bit Windows with Python 3.9 or newer and the .NET Framework 4.x C# compiler. The build uses Windows Forms and the framework's built-in assemblies; no NuGet packages are required.

The public `src` files match the release source. The public build script accepts configurable paths and can compile the launcher without the runtime payload.

## Launcher

From this repository's root:

```powershell
python build_pack.py --launcher-only
```

The output is `build/KoreanAIR_AC8_ModPack_2.2.exe`. The compiler is resolved from the Windows directory. If necessary, pass `--csc <compiler-path>` or set the `CSC` environment variable.

## Installer with the release payload

Download `KoreanAIR_AC8_ModPack_2.2_Sources.zip` from the [matching release](https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases). Extract its `Payload.zip` into this repository's root, then run:

```powershell
python build_pack.py --payload-zip Payload.zip
```

This verifies the input payload file hashes, replaces the launcher and English/Korean manuals with the current build, updates their manifest hashes, and compiles `build/KoreanAIR_AC8_ModPack_2.2_Setup.exe`. Use the source archive belonging to the same public version and internal build recorded in `release.json`.

Keep the generated `Payload.zip` beside the installer. Setup embeds only its small manifest and payload descriptor; it verifies the separate ZIP before installing. Official standalone update installers can obtain their exact SHA-pinned payload from the matching GitHub release. Locally rebuilt packages should distribute both files together.

The release source archive also contains `runtime/`, `campaign-loader/` and `campaign-source/`. Native rebuilds require the Visual Studio 2022 C++ tools and the vendor dependencies included or pinned in that archive. Follow its `BUILDING.txt` and individual component build instructions. The Git repository focuses on the managed launcher/installer source; the release source archive carries the complete native and translation inputs.

The prepared-payload route in `build_pack.py` remains available when the required `runtime/` and `campaign-source/` files, campaign loader DLL and compatible redistributable runtime files are present locally:

```powershell
python build_pack.py --game-root <game-folder>
```

`AC8_GAME_ROOT` can supply the game folder instead. This route reads runtime files from the selected installation; it never packages a game executable. Build outputs and locally supplied payloads are ignored by Git.

## Synthetic checks

These checks create artificial game headers and small placeholder payloads. They do not launch the game or require a game installation:

```powershell
python tests/test_loader_compatibility.py
```

The runnable check verifies loader compatibility and preservation of unrelated mod files. Generated fixtures, executables and reports are ignored by Git. `tests/InstallerAudit.cs` supplies additional installer path and rollback checks for compilation with `src/PackCore.cs`. Full updater and runtime validation belongs to the matching release source archive.

Before publishing a release, follow [AGENTS.md](AGENTS.md): keep version/build metadata consistent, run the release validation and publish a new build tag for every replacement.
