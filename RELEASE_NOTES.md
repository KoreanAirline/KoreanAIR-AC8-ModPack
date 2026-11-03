# War Thunder-Style Mouse Controls, Ultrawide & Triple-Monitor Support, and More!

**⚠️ Important Note:** This mod reads game data to perform calculations, so it only works in single-player mode.

## Features

Here's what this mod offers:

1. **War Thunder-style keyboard and mouse controls** (Check out the YouTube demo video to see how it works!)
2. **Ultrawide and triple-monitor support** (See screenshots)
3. **Improved Korean campaign subtitles** (For Korean players, fixing awkward or unnatural translations)
4. **Frame Generation support** (This was previously possible by manually editing the game's .ini files, but now you can enable it directly through the mod launcher.)
5. **Adjustable subtitle position** (Personally, I find subtitles at the top of the screen a bit hard to read, so I've added an option to move them to the bottom.)
6. **Configurable keyboard and mouse shortcuts**, including mouse side buttons.
7. **Bug-report export** from the launcher, with optional short input recording.
8. **Shared-loader compatibility** for the inspected ACE8 Mod Loader / IoStoreLoaderMod 1.3.1.
9. **Version/build transition and update notes** in the launcher.

## War Thunder-Style Mouse Controls

I made this mod mainly for players who prefer using a keyboard and mouse.

I took inspiration from War Thunder, which is well known for its mouse-friendly flight controls, and tried to bring a similar control scheme to this game.

**You no longer have to manually manage pitch, yaw, and roll with your mouse just to get your aircraft to follow the circle on the screen.**

Instead, your aircraft will automatically follow your mouse aim, just like in War Thunder.

Of course, you can still manually control your roll using **A and D**, which allows you to pull off more advanced maneuvers.

You can also **right-click to zoom in**, just like in War Thunder.

## Ultrawide & Triple-Monitor Support

For those of you running a triple-monitor setup (three 16:9 monitors), I've added support for using all three screens **without needing NVIDIA Surround**.

You can simply enable and configure it through the mod launcher. The monitor diagram lets you choose the left, centre and right game displays independently of the Windows main display. Extra monitors and different refresh rates are allowed. Manual selection can span the bounding rectangle of the selected three, including unequal sizes, gaps or vertical offsets. This option is on by default; turn it off to require an aligned equal-resolution row. The launcher shows the selected physical area and gaps. It does not rearrange Windows displays, and a bounding rectangle can include unused desktop space.

Single ultrawide displays, including 21:9 and 32:9, are also supported using the actual game viewport ratio. Enable **Screen & camera settings**, leave **Span across three monitors** unchecked, and select the display's native resolution in borderless/fullscreen mode. No NVIDIA Surround is required. Prerecorded videos keep their original aspect ratio.

This works not only during campaign gameplay but also in **real-time rendered cutscenes**.

As a result, you can actually see parts of the game world that would normally be outside the visible area on a standard 16:9 display.

## Installation and bug reports

Run Setup over the existing installation after closing the game. Your settings and module selection are retained. The standalone Setup downloads its matching payload when needed; extracting the complete ZIP also allows installation with `Payload.zip` beside Setup.

For the shared-loader path, download [ACE8 Mod Loader 1.3.1 from its author](https://www.nexusmods.com/acecombat8wingsoftheve/mods/64) separately and follow its installation guide. Enable its IoStoreLoaderMod, close the game, then run this pack's Setup. The recognized loader owns archive loading; this pack removes only its own previous campaign hook and keeps external mod folders, shared runtime settings and load-order entries. Third-party loader files are not bundled. Unknown replacement DLLs are preserved and reported. FALKEN Add On 1.0.3 passed package/import/structure checks; combined in-game flight is not verified, and arbitrary mods are not guaranteed compatible.

When using the inspected AC8HOTAS 0.2.0 bundle, keep **Mouse flight off**. Setup can merge the known shared runtime while retaining HOTAS folders and bindings. Actual combined in-game operation has not been verified.

In **Support**, start optional input recording, reproduce the issue for up to two minutes, close the game and create a report. Send `BugReport_*.txt` from `<game folder>/KoreanAIR_AC8_ModPack/Reports`, plus the mission, aircraft and game control mode. The launcher opens the report location and uses `%LocalAppData%/KoreanAIR_AC8_ModPack/Reports` if necessary. Nothing is uploaded automatically.

## Bug Reports & Feedback

Unfortunately, I've been pretty busy lately, so I haven't had enough time to thoroughly test everything.

There might still be some bugs, so if you run into any issues, **please let me know in the comments!**

Thanks for checking out my mod, and I hope you enjoy it!

---

## 한국어 안내

### 워 썬더 방식 마우스 조작, 울트라와이드·트리플 모니터 지원 등

**⚠️ 중요 안내:** 이 모드는 게임 데이터를 읽어 계산하므로 **싱글플레이에서만 사용할 수 있습니다.**

### 주요 기능

이 모드에서 제공하는 기능은 다음과 같습니다.

1. **워 썬더 방식 키보드·마우스 조작** (YouTube 시연 영상에서 작동 방식을 확인해 보세요!)
2. **울트라와이드·트리플 모니터 지원** (스크린샷 참고)
3. **한국어 자막 개선** (어색하거나 부자연스러운 한국어 자막을 다듬었습니다.)
4. **프레임 생성 지원** (기존에는 게임의 .ini 파일을 직접 수정해야 했지만, 이제 모드 런처에서 바로 켤 수 있습니다.)
5. **자막 위치 조절** (화면 위쪽 자막이 읽기 불편해, 아래쪽으로 옮기는 옵션을 추가했습니다.)
6. **키보드·마우스 단축키 변경** (마우스 사이드 버튼도 지정할 수 있습니다.)
7. **문제 보고 파일 만들기** (필요할 때 짧은 입력 기록을 함께 남길 수 있습니다.)
8. **공용 로더 병용** (확인된 ACE8 Mod Loader / IoStoreLoaderMod 1.3.1을 지원합니다.)
9. **런처의 버전·빌드 변경 표시와 업데이트 내역**

### 워 썬더 방식 마우스 조작

이 모드는 주로 키보드와 마우스로 플레이하는 분들을 위해 만들었습니다.

마우스로 편하게 비행할 수 있는 워 썬더에서 영감을 받아, 이 게임에서도 비슷한 방식으로 조작할 수 있도록 했습니다.

**이제 화면의 원을 따라 기체를 움직이기 위해 마우스로 피치·요·롤을 일일이 조절할 필요가 없습니다.**

워 썬더처럼 마우스로 가리키는 방향을 기체가 자동으로 따라갑니다.

물론 **A와 D 키로 롤을 수동 조작**할 수 있어, 더 다양한 기동도 가능합니다.

워 썬더처럼 **마우스 오른쪽 버튼으로 확대**할 수도 있습니다.

### 울트라와이드·트리플 모니터 지원

16:9 모니터 3대를 사용하는 트리플 모니터 환경에서 **NVIDIA Surround 없이도 세 화면을 모두 사용할 수 있도록** 지원합니다.

모드 런처에서 기능을 켜고 설정하면 됩니다. 모니터 배치 그림에서 Windows 주 모니터와 별개로 게임에 사용할 왼쪽·가운데·오른쪽 화면을 선택할 수 있습니다. 추가 화면과 서로 다른 주사율도 사용할 수 있습니다. 직접 선택의 전체 영역 사용 옵션은 기본으로 켜져 있어, 크기·높이가 다르거나 사이에 틈이 있어도 선택한 3대를 감싸는 직사각형으로 확장합니다. 이 옵션을 끄면 같은 해상도로 좌우가 이어진 배치만 허용합니다. 실제 영역과 틈을 런처에 표시하며 Windows 배치를 바꾸지는 않습니다. 직사각형에는 사용하지 않는 바탕화면 영역도 포함될 수 있습니다.

21:9와 32:9를 포함한 단일 울트라와이드 모니터도 실제 게임 화면 비율에 맞춰 지원합니다. **화면·카메라 설정을 켜고**, **모니터 3대 확장은 끈 상태로**, 테두리 없는 창 모드 또는 전체 화면 모드에서 **모니터의 기본 해상도**를 선택하세요. NVIDIA Surround는 필요하지 않습니다. 사전 제작 영상은 원래 화면 비율을 유지합니다.

캠페인 플레이뿐 아니라 **실시간으로 렌더링되는 컷신**에도 적용됩니다.

따라서 일반적인 16:9 화면에서는 보이는 영역 밖에 있던 게임 속 장면도 볼 수 있습니다.

### 설치 및 문제 보고

게임을 종료하고 기존 폴더에 Setup을 실행하면 설정과 기능 선택을 유지한 채 업데이트합니다. 먼저 제거할 필요가 없습니다. Setup만 실행해도 필요한 파일을 내려받으며, 전체 ZIP을 받았다면 압축을 모두 풀고 `Payload.zip` 옆의 Setup을 실행하면 됩니다.

공용 로더를 사용하려면 [제작자의 ACE8 Mod Loader 1.3.1](https://www.nexusmods.com/acecombat8wingsoftheve/mods/64)을 별도로 받아 설치 안내를 따르세요. IoStoreLoaderMod를 활성화하고 게임을 종료한 뒤 이 모드팩의 Setup을 실행하면, 확인된 로더 하나로 아카이브를 읽습니다. 이 모드팩의 기존 캠페인 훅만 제거하며 외부 모드 폴더·공용 런타임 설정·로드 순서를 보존합니다. 외부 로더 파일은 포함하지 않으며 확인되지 않은 DLL은 덮어쓰지 않고 안내합니다. FALKEN Add On 1.0.3은 패키지·DLL 의존성·구조를 확인했지만 실제 병용 비행은 검증하지 못했고, 임의의 모드까지 모두 호환된다는 뜻은 아닙니다.

확인된 AC8HOTAS 0.2.0 묶음을 함께 사용할 때는 **마우스 조종을 끄세요**. HOTAS 폴더와 바인딩을 보존하면서 공용 런타임을 통합합니다. 실제 게임 병용은 아직 검증하지 못했습니다.

**문제 보고**에서 선택적으로 입력 기록을 시작하고 최대 2분 재현한 뒤 게임을 종료해 보고서를 만드세요. `<게임 폴더>/KoreanAIR_AC8_ModPack/Reports`의 `BugReport_*.txt`와 미션·기체·게임 조작 방식을 보내 주세요. 저장할 수 없는 폴더라면 `%LocalAppData%/KoreanAIR_AC8_ModPack/Reports`를 사용하며, 런처에서 저장 위치를 열어 줍니다. 보고서는 자동 전송하지 않습니다.

### 버그 제보 및 의견

최근 개인 일정이 바빠 모든 기능을 충분히 테스트하지는 못했습니다.

아직 버그가 있을 수 있으니, 문제가 생기면 **댓글로 알려 주세요!**

모드에 관심을 가져 주셔서 감사합니다. 즐겁게 플레이하시길 바랍니다!

---

## Changes — 2.4 (build 2026110301)

- Updated the inspected executable identity and guarded campaign-loader addresses for the game update: timestamp `6AD2D0A7`, image size `215A2000`. Other game builds receive a warning rather than a version-only block; exact native code guards still apply, so changed features may remain inactive.
- Added one recognized archive-loader owner when IoStoreLoaderMod 1.3.1 is installed. The Korean campaign archive uses that loader, avoiding two hooks on the same game constructor. External runtime files, mod folders and load order are retained during update, disable and uninstall.
- The updater shows the installed-to-new version/build and provides English/Korean change notes. Settings, selected modules and disabled state are preserved.
- Manual triple-display selection uses only the chosen displays. Its default bounding-area option allows uneven layouts; the launcher shows exact bounds, gaps and offsets. Extra displays do not need to be disconnected. The individual five-display report's PC-specific cause remains unconfirmed.
- Packaging now rejects a campaign-loader DLL if its source, executable-guard proof, approved archive or offline verification no longer matches the recorded build.

The inspected external loader is a separate download. Static compatibility checks and isolated installation tests do not certify every mission or third-party aircraft; FALKEN combined in-game flight remains unverified. Graphics quality, DLSS Quality and saved frame-generation preference are preserved.

### 변경 내용 — 2.4 (빌드 2026110301)

- 게임 업데이트에 맞춰 확인한 실행 파일 정보와 검증된 캠페인 로더 주소를 갱신했습니다. 타임스탬프는 `6AD2D0A7`, 이미지 크기는 `215A2000`입니다. 다른 빌드에는 경고를 표시하며 버전만으로 차단하지 않습니다. 실제 코드 검사는 유지하므로 변경된 기능은 비활성화될 수 있습니다.
- IoStoreLoaderMod 1.3.1을 확인하면 로더 하나가 한국어 캠페인 아카이브도 읽게 했습니다. 같은 게임 생성자에 두 훅이 겹치지 않으며, 업데이트·끄기·제거 시 외부 런타임·모드 폴더·로드 순서를 보존합니다.
- 현재 버전·빌드에서 새 버전·빌드로의 변경 표시와 한국어·영어 업데이트 내역을 추가했습니다. 설정, 선택한 기능과 모드가 꺼진 상태도 유지합니다.
- 모니터 직접 선택은 지정한 3대만 사용합니다. 기본으로 켜진 전체 영역 사용 옵션으로 고르지 않은 배치도 허용하며, 실제 좌표·틈·높이 차이를 표시합니다. 추가 화면을 끌 필요가 없습니다. 개별 5대 모니터 제보의 PC별 정확한 원인은 아직 확정하지 못했습니다.
- 캠페인 로더의 소스·실행 파일 검증 정보·승인된 아카이브·오프라인 검사 결과가 빌드 기록과 달라지면 패키징을 거부합니다.

확인한 외부 로더는 별도 다운로드가 필요합니다. 파일·구조 검사와 격리된 설치 시험이 모든 미션과 외부 기체의 실제 작동을 보증하지는 않으며, FALKEN 병용 비행은 아직 검증하지 못했습니다. 그래픽 품질·DLSS 품질·저장한 프레임 생성 선택은 유지합니다.
