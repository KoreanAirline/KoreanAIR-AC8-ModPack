# KoreanAIR AC8 Mod Pack

An offline mod pack for **ACE COMBAT 8** with a Windows installer and bilingual launcher.

- **Korean campaign subtitles** based on the English dialogue.
- **Mouse flight controls**, configurable free look, flight helper HUD and crosshairs.
- **Screen and camera options** for flight FOV, three-display span and third-person camera distance/height.
- **Subtitle position**, module management and updates that preserve saved settings.

## Download and instructions

[Download the latest release](https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/latest).
Run the installer from the release and follow the [English manual](README_ENG.txt) or [한국어 사용 안내](README_KOR.txt).

The modules are intended for offline play. Use the launcher's **Disable pack for standard play** option before launching standard or online play through Steam. The supported game build and installation details are described in the manuals.

## Source and build

This repository contains the launcher, installer and shared updater source, release metadata, synthetic tests and legal notices. See [BUILDING.md](BUILDING.md) for build instructions.

The matching release's `KoreanAIR_AC8_ModPack_1.2_Sources.zip` includes the native runtime source, campaign loader source, translation source and redistributable `Payload.zip` needed for a full installer rebuild. Game executables are not included.

Independently written KoreanAIR code uses the [MIT license](LICENSE). Third-party components retain their notices in [licenses](licenses).
