# Diagnostic source snapshot: 2.3 b2026101902

This snapshot belongs to the installation-diagnostic prerelease, not the stable update channel. The owner authorized sharing it with an installation reporter. The reporter's underlying Windows restriction and installation success have not been confirmed; no personal gameplay test of this build is claimed.

The installer adds bounded create/write/rename preflight checks and failure diagnostics. It does not change user ACLs, security software, gameplay control calculations, graphics settings or rendering logic. The native source differs from stable b2026101901 only in its build identity; the supplied native binary and payload use b2026101902.

Use this archive's Payload.zip when rebuilding this snapshot. It is the exact verified redistributable payload associated with b2026101902 and contains the installable mod binaries. No game executable, individual test executable/DLL, private capture or nested historical source ZIP is included. Launcher/installer rebuilds may have different hashes because compilation is not guaranteed deterministic; the build metadata must remain consistent.

Run `python build_pack.py --payload-zip Payload.zip` on Windows with the documented compiler. See BUILDING.md. Native builds require the Visual Studio tools and included vendor source/dependencies. Owner-specific validation that requires a game executable or private capture is not fully reproducible from public materials.

Current installation tests are in tests/install_access_1902. The source-scope test reads a separate stable b2026101901 Sources.zip; download that release asset and place it at tests/install_access_1902/baseline_1901_sources.zip before running that comparison. Historical baseline ZIPs are intentionally not nested in this archive. Tests that require the owner-supplied HOTAS distribution need that separately obtained package.

Only fresh b2026101902 validation is included under validation/. Historical release approvals and old aggregate VALIDATION.json were removed. The new VALIDATION.json states the diagnostic scope and limits. Original validation source/binary hashes identify the private tested files; some public source or report text is anonymized, so its byte hash can differ. PUBLIC_SOURCE_SHA256.json hashes the public archive entries (excluding itself); PUBLIC_REPOSITORY_SHA256.json hashes the public Git snapshot entries (excluding itself). The original-local/public-critical source map appears in validation/public_source_map.json.

No stable promotion or automatic-update change is authorized by the preparation of this diagnostic snapshot. The stable b2026101901 release assets remain separate. A future stable replacement needs the owner's release instruction and a new internal build.
