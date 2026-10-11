# Release rules requested by the owner

- Bug fixes retain the public version and filenames. Increase the internal build identifier so installed launchers still detect and offer the fix.
- New features increase the public minor version (1.2 -> 1.3). A release that combines a new feature and fixes uses the new feature version.
- Keep release.json, Core.Brand, State.version, AssemblyVersion/FileVersion/InformationalVersion, Core.ReleaseBuild, current build/test/package filenames and both user manuals consistent. Build identifiers must increase for every published replacement.
- Do not silently overwrite a published build/tag. Use a new vVERSION-bBUILD tag and set that release as latest after its assets are complete.
- Use the owner's KoreanAirline/KoreanAIR-AC8-ModPack repository for the update feed. Never publish account credentials, private email addresses, personal filesystem paths, game executables, or unrelated workspace files.
- Update installation preserves the user's selected modules, all user settings, UI language, other mods and suspended/disabled state. Do not uninstall first. Do not update while the game is running.
- READMEs are current English/Korean user manuals based on the owner's supplied text. Integrate current features naturally; do not add development history, obsolete Thai mod references or exaggerated feature descriptions.
- Verify the updater and settings preservation before publishing. Keep outputs limited to the current distribution ZIP and source/validation ZIP; installer and update.json are release assets generated from the same verified build.
