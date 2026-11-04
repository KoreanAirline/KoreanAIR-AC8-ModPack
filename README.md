# War Thunder-Style Mouse Controls, Ultrawide & Triple-Monitor Support, and More!

**⚠️ Important Note:** This mod reads game data to perform calculations, so it only works in single-player mode.

**Installation: [한국어 설치·설정 안내](INSTALL_KOR.md) · [English installation guide](INSTALL_ENG.md)**

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

**Using ACE8 Mod Launcher too?** Follow the [step-by-step installation guide](INSTALL_ENG.md). Install its loader, switch it to **Modded**, then install this pack with **KoreanAIR Setup**. Setup installs the components where the external manager finds them automatically. **Do not use Add mods/Add folder with this pack's EXE, Payload.zip or installation folder.**

The external list shows **AC8MouseAim** for controls, screen/camera and subtitle placement, and **KoreanAIRCampaign** for optional Korean translation. These are components of one installation. Save settings in **KoreanAIR**, then launch using either **ACE8 Mod Launcher → Modded → Play modded** or **KoreanAIR → Play → Play with selected mods**. Both use the saved settings. The [guide](INSTALL_ENG.md#triple-monitor-setup) covers triple-monitor setup, load order and updating.

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

**ACE8 Mod Launcher도 함께 쓰나요?** [처음부터 따라 하는 설치·설정 안내](INSTALL_KOR.md)를 확인하세요. 외부 로더 설치 → **Modded** 전환 → **우리 Setup 설치** 순서입니다. Setup이 설치한 구성요소는 외부 런처가 자동으로 목록에 표시합니다. **우리 EXE·Payload.zip·설치 폴더를 Add mods/Add folder에 넣지 마세요.**

외부 목록의 **AC8MouseAim**은 조종·화면·카메라·자막 위치 기능이고, **KoreanAIRCampaign**은 선택형 한국어 번역 파일입니다. 하나의 Setup이 설치하는 구성요소이며 설정은 **KoreanAIR 런처**에서 저장합니다. 게임은 **ACE8 Mod Launcher → Modded → Play modded** 또는 **KoreanAIR → 플레이 → 선택한 모드로 게임 실행** 중 원하는 방식으로 시작하세요. 두 경로 모두 저장한 설정을 사용합니다. [상세 안내](INSTALL_KOR.md#트리플-모니터-설정)에 트리플 모니터 설정, 각 설정 위치, 로드 순서와 업데이트 방법을 정리했습니다.

확인된 AC8HOTAS 0.2.0 묶음을 함께 사용할 때는 **마우스 조종을 끄세요**. HOTAS 폴더와 바인딩을 보존하면서 공용 런타임을 통합합니다. 실제 게임 병용은 아직 검증하지 못했습니다.

**문제 보고**에서 선택적으로 입력 기록을 시작하고 최대 2분 재현한 뒤 게임을 종료해 보고서를 만드세요. `<게임 폴더>/KoreanAIR_AC8_ModPack/Reports`의 `BugReport_*.txt`와 미션·기체·게임 조작 방식을 보내 주세요. 저장할 수 없는 폴더라면 `%LocalAppData%/KoreanAIR_AC8_ModPack/Reports`를 사용하며, 런처에서 저장 위치를 열어 줍니다. 보고서는 자동 전송하지 않습니다.

### 버그 제보 및 의견

최근 개인 일정이 바빠 모든 기능을 충분히 테스트하지는 못했습니다.

아직 버그가 있을 수 있으니, 문제가 생기면 **댓글로 알려 주세요!**

모드에 관심을 가져 주셔서 감사합니다. 즐겁게 플레이하시길 바랍니다!

---

## Changes — 3.0 (build 2026110403)

- ACE8 Mod Launcher's Modded Play now starts this pack's mouse-flight and display runtime with the settings saved in KoreanAIR.
- Triple-monitor selection, crosshair and camera settings apply through either supported launcher. Existing controls and settings are retained.
- Expanded the English/Korean installation guide with automatic component detection, settings locations and load-order instructions.

### 변경 내용 — 3.0 (빌드 2026110403)

- ACE8 Mod Launcher의 Modded 실행에서도 KoreanAIR에 저장한 마우스 조종·화면 설정이 적용됩니다.
- 두 런처 모두 저장한 모니터 선택·조준선·카메라 설정을 사용하며 기존 조종 설정을 유지합니다.
- 자동 인식되는 구성요소, 설정 위치와 로드 순서를 한국어·영어 설치 안내에 정리했습니다.

## Previous changes — 2.4 (build 2026110402)

- Fixed mouse-flight response compensation falling back to slower tracking on aircraft with a fast neutral response.
- The launcher checks for duplicate bindings between Accelerate, Decelerate and the game's Accelerate + Decelerate action. It explains how to remove the conflict without changing saved keys.
- Existing control, camera, subtitle and display settings are retained.

### 변경 내용 — 2.4 (빌드 2026110402)

- 복원 응답이 빠른 기체에서 조종 응답 보정이 해제돼 추적이 느려지는 문제를 수정했습니다.
- 게임의 가속·감속 키와 ‘가속 + 감속’ 키가 중복되면 런처에서 해제 방법을 안내합니다. 저장된 키는 자동으로 바꾸지 않습니다.
- 기존 조종·카메라·자막·화면 설정을 유지합니다.

## Previous changes — 2.4 (build 2026110401)

- Module changes now run the verified installed Setup directly, removing the temporary executable copy. Verified install files are cached and reused. Missing files for an unpublished build show instructions to use the complete ZIP instead of a generic 404. This does not claim Defender's classification is resolved.

- Korean campaign translation is OFF for a new installation. Enable it explicitly in Setup or the launcher's Subtitles tab. Subtitle positioning starts at the game's original layout. Updates retain previously saved choices.

- Replaced the obsolete shipped subtitle table with a reviewed dialogue dictionary. If enabled, Setup generates a full current CP_G table overlay whose only changed values are reviewed dialogue. Menu strings, indices and control glyphs are preserved byte-for-byte. This still mounts a complete table; per-lookup dialogue replacement and automatic merging of other mods' CP_G changes are not implemented.
- Pre-launch checks remove the previous generated overlay when stock data is unsupported. The game then uses original subtitles, with a notice; no stale table is mounted. Changed or ambiguous source lines also keep their current text.
- Preserves existing input, camera, subtitle-position and other-mod settings. No per-frame text searching was added. Launch from KoreanAIR to run the subtitle checks; the external mod manager remains usable for installing aircraft and restoring its Modded files.
- FALKEN 1.0.3's Aircraft Set crash also reproduced with this pack's native runtime absent and its campaign translation archive disabled. The underlying game/external-mod cause remains unresolved. This release does not certify FALKEN compatibility or claim that crash is fixed.
- Defender reported Trojan:Win32/Bearfoos.A!ml for the previous local build 2026110302. That classification has not been cleared by Microsoft analysis. Source review and a manually configured exclusion do not establish that it was a false positive; no clearance is claimed for this release.

### 변경 내용 — 2.4 (빌드 2026110401)

- 기능 변경 시 검증된 설치 Setup을 직접 실행하도록 임시 EXE 복사를 제거했습니다. 확인된 설치 파일을 로컬 캐시에 보관해 재사용하며, 미공개 빌드의 온라인 파일이 없으면 404 대신 전체 ZIP 사용 방법을 안내합니다. 이 변경으로 Defender 탐지 판정이 해소됐다고 주장하지는 않습니다.

- 신규 설치의 캠페인 한국어 번역은 기본 OFF입니다. Setup 또는 런처 자막 탭에서 직접 켠 경우만 적용합니다. 자막 위치도 게임 기본 배치로 시작하며, 업데이트 시 기존에 저장한 선택은 유지합니다.

- 예전 자막 표를 배포하던 방식을 제거했습니다. 켠 경우 현재 게임의 전체 CP_G 표에 확인된 대사 값만 반영한 파일을 생성하며, 메뉴·인덱스·제어 글리프는 바이트 단위로 보존합니다. 적용 파일은 여전히 전체 표이며, 대사 조회 단계 교체와 다른 모드의 CP_G 변경 자동 병합은 구현하지 않았습니다.
- 실행 전 원본 검사를 통과하지 못하면 이전 번역 파일을 제외하고 안내한 뒤 원본 자막을 사용합니다. 원문이 달라지거나 대응이 불명확한 대사도 원문을 유지합니다.
- 조종·카메라·자막 위치·다른 모드 설정을 유지합니다. 플레이 중 반복 검색은 추가하지 않았습니다. 자막 검사를 위해 게임은 KoreanAIR 런처에서 실행하고, 외부 모드 관리자는 기체 설치와 Modded 파일 복원에 사용하세요.
- FALKEN 1.0.3의 기체 세트 크래시는 우리 네이티브 런타임이 로드되지 않고 번역 파일도 꺼진 상태에서도 재현됐습니다. 게임·외부 모드 중 정확한 원인은 아직 확정하지 못했으며, FALKEN 호환성이나 해당 크래시 해결을 보증하지 않습니다.
- 이전 로컬 빌드 2026110302에 Defender의 Trojan:Win32/Bearfoos.A!ml 탐지가 있었습니다. Microsoft 분석으로 해소되지 않았으며 소스 검사나 수동 예외 설정만으로 오진이 확인된 것은 아닙니다. 이번 배포에 대한 보안 판정 해소도 주장하지 않습니다.

## Previous changes — 2.4 (build 2026110301)

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
