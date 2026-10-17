# KoreanAIR AC8 Mod Pack

An offline mod pack for **ACE COMBAT 8** with a Windows installer and bilingual launcher.

- **Korean campaign subtitles** based on the English dialogue.
- **Mouse flight controls**, configurable free look, smooth click-to-toggle zoom toward mouse aim, flight helper HUD and crosshairs.
- **Screen and camera options** for flight FOV, single ultrawide displays, three-display span and third-person camera distance/height. A monitor diagram lets you choose the three game displays independently of the Windows main display.
- **Frame generation** through the game's bundled NVIDIA feature, with On/Off and original-settings restoration. Restart the game after saving.
- **Subtitle position**, module management and updates that preserve saved settings.
- **Bug-report export** from the launcher, with optional short input recording.

## Download and instructions

[Download the latest release](https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/latest).
Extract the complete main ZIP, keeping `Payload.zip` beside the installer, and follow the [English manual](README_ENG.txt) or [한국어 사용 안내](README_KOR.txt). The standalone installer downloads its matching verified payload when needed.

The modules are intended for offline play. Use the launcher's **Disable pack for standard play** option before launching standard or online play through Steam. The supported game build and installation details are described in the manuals.

## Monitor selection and other mods

For three-display span, choose three equal-resolution displays aligned side by side in Windows. Extra displays and different refresh rates are allowed. Single ultrawide displays use the camera options with three-display span off.

Setup can merge the inspected AC8HOTAS 0.2.0 shared runtime while keeping HOTAS folders and bindings. Leave **Mouse flight off** when HOTAS or AnalogYaw is enabled; simultaneous flight controllers are not supported. Combined in-game HOTAS operation has not been verified. See the manuals for installation details.

## Bug reports

In **Support**, optionally start input recording, reproduce the issue for up to two minutes, close the game, then create a report. Send the generated `BugReport_*.txt` from `<game folder>/KoreanAIR_AC8_ModPack/Reports` with the mission, aircraft, game control mode and a short video if possible. If the game folder is not writable, the launcher uses `%LocalAppData%/KoreanAIR_AC8_ModPack/Reports` and opens the file location. Reports stay on the PC until you share them.

Stationary-target weaving reported on another PC is still under investigation; this release preserves the existing flight controller.

## 한국어 안내

모니터 배치 그림에서 게임에 쓸 왼쪽·가운데·오른쪽 화면을 선택할 수 있습니다. 선택한 세 화면은 같은 해상도로 좌우가 이어져 있어야 하며, Windows 주 모니터가 가운데일 필요는 없습니다. 추가 화면이나 서로 다른 주사율을 사용할 수 있습니다.

AC8HOTAS 0.2.0과 함께 설치할 때는 **마우스 조종을 끄세요**. 확인된 공용 런타임을 통합하면서 HOTAS 폴더와 바인딩을 보존합니다. 두 조종 기능의 동시 사용은 지원하지 않으며, 실제 게임 병용은 아직 검증하지 못했습니다.

버그가 발생하면 **문제 보고**에서 입력 기록을 시작해 최대 2분 재현한 후 게임을 종료하고 보고서를 만드세요. 생성된 `BugReport_*.txt`와 미션·기체·게임 조작 방식, 가능하면 짧은 영상을 보내 주세요. 보고서는 직접 공유하기 전까지 PC에만 저장됩니다.

## Source and build

This repository contains the launcher, installer and shared updater source, release metadata, synthetic tests and legal notices. See [BUILDING.md](BUILDING.md) for build instructions.

The matching release's `KoreanAIR_AC8_ModPack_2.3_Sources.zip` includes the native runtime source, campaign loader source, translation source and redistributable `Payload.zip` needed for a full installer rebuild. Game executables are not included.

Independently written KoreanAIR code uses the [MIT license](LICENSE). Third-party components retain their notices in [licenses](licenses).
