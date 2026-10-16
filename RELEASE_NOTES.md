# War Thunder-Style Mouse Controls, Ultrawide & Triple-Monitor Support, and More!

**⚠️ Important Note:** This mod reads game data to perform calculations, so it only works in single-player mode.

## Features

Here's what this mod offers:

1. **War Thunder-style keyboard and mouse controls** (Check out the YouTube demo video to see how it works!)
2. **Ultrawide and triple-monitor support** (See screenshots)
3. **Improved Japanese-to-Korean subtitles** (For Korean players, fixing awkward or unnatural translations)
4. **Frame Generation support** (This was previously possible by manually editing the game's .ini files, but now you can enable it directly through the mod launcher.)
5. **Adjustable subtitle position** (Personally, I find subtitles at the top of the screen a bit hard to read, so I've added an option to move them to the bottom.)
6. **Configurable keyboard and mouse shortcuts**, including mouse side buttons.

## War Thunder-Style Mouse Controls

I made this mod mainly for players who prefer using a keyboard and mouse.

I took inspiration from War Thunder, which is well known for its mouse-friendly flight controls, and tried to bring a similar control scheme to this game.

**You no longer have to manually manage pitch, yaw, and roll with your mouse just to get your aircraft to follow the circle on the screen.**

Instead, your aircraft will automatically follow your mouse aim, just like in War Thunder.

Of course, you can still manually control your roll using **A and D**, which allows you to pull off more advanced maneuvers.

You can also **right-click to zoom in**, just like in War Thunder.

## Ultrawide & Triple-Monitor Support

For those of you running a triple-monitor setup (three 16:9 monitors), I've added support for using all three screens **without needing NVIDIA Surround**.

You can simply enable and configure it through the mod launcher.

Single ultrawide displays, including 21:9 and 32:9, are also supported using the actual game viewport ratio. Enable **Screen & camera settings**, leave **Span across three monitors** unchecked, and select the display's native resolution in borderless/fullscreen mode. No NVIDIA Surround is required. Prerecorded videos keep their original aspect ratio.

This works not only during campaign gameplay but also in **real-time rendered cutscenes**.

As a result, you can actually see parts of the game world that would normally be outside the visible area on a standard 16:9 display.

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

### 워 썬더 방식 마우스 조작

이 모드는 주로 키보드와 마우스로 플레이하는 분들을 위해 만들었습니다.

마우스로 편하게 비행할 수 있는 워 썬더에서 영감을 받아, 이 게임에서도 비슷한 방식으로 조작할 수 있도록 했습니다.

**이제 화면의 원을 따라 기체를 움직이기 위해 마우스로 피치·요·롤을 일일이 조절할 필요가 없습니다.**

워 썬더처럼 마우스로 가리키는 방향을 기체가 자동으로 따라갑니다.

물론 **A와 D 키로 롤을 수동 조작**할 수 있어, 더 다양한 기동도 가능합니다.

워 썬더처럼 **마우스 오른쪽 버튼으로 확대**할 수도 있습니다.

### 울트라와이드·트리플 모니터 지원

16:9 모니터 3대를 사용하는 트리플 모니터 환경에서 **NVIDIA Surround 없이도 세 화면을 모두 사용할 수 있도록** 지원합니다.

모드 런처에서 기능을 켜고 설정하면 됩니다.

21:9와 32:9를 포함한 단일 울트라와이드 모니터도 실제 게임 화면 비율에 맞춰 지원합니다. **화면·카메라 설정을 켜고**, **모니터 3대 확장은 끈 상태로**, 테두리 없는 창 모드 또는 전체 화면 모드에서 **모니터의 기본 해상도**를 선택하세요. NVIDIA Surround는 필요하지 않습니다. 사전 제작 영상은 원래 화면 비율을 유지합니다.

캠페인 플레이뿐 아니라 **실시간으로 렌더링되는 컷신**에도 적용됩니다.

따라서 일반적인 16:9 화면에서는 보이는 영역 밖에 있던 게임 속 장면도 볼 수 있습니다.

### 버그 제보 및 의견

최근 개인 일정이 바빠 모든 기능을 충분히 테스트하지는 못했습니다.

아직 버그가 있을 수 있으니, 문제가 생기면 **댓글로 알려 주세요!**

모드에 관심을 가져 주셔서 감사합니다. 즐겁게 플레이하시길 바랍니다!

---

## Bug fixes — 2.2 (build 2026101608)

- Reduced repeated controller validation and unnecessary native head-look release calls during flight and cinematic transitions. Current ownership is still checked every frame.
- Fixed a valid native input mode that could leave mouse-flight camera and aim-marker initialization incomplete.
- Kept mouse guidance during interactive campaign focus shots, while respecting native input locks and the game's animated close-up/slow-motion lens.
- Added Korean translation selection to the Subtitles tab. English subtitles, mouse flight and screen options remain independent; other selected modules are retained.

**Updating:** Close the game and run `KoreanAIR_AC8_ModPack_2.2_Setup.exe` over the existing installation, or use the launcher's update notice. Saved settings and selected modules are preserved. Uninstalling first is unnecessary. Setup downloads its matching verified files when needed; for offline installation, keep `Payload.zip` beside Setup.

Multi-second transition stalls remain under investigation. This build reduces verified redundant mod work; it does not claim to eliminate all game/driver stalls or increase measured FPS. Graphics quality, DLSS and frame-generation settings are preserved.

### 한국어 버그 수정 — 2.2 (빌드 2026101608)

- 비행·시네마틱 전환에서 컨트롤러 중복 검사와 불필요한 자유 시점 해제 호출을 줄였습니다. 현재 카메라·입력 소유권은 매 프레임 확인합니다.
- 유효한 일부 게임 입력 모드에서 마우스 조종 카메라와 조준원 초기화가 끝나지 않을 수 있는 문제를 수정했습니다.
- 조종 가능한 캠페인 집중 장면에서 마우스 조종을 유지하고, 게임의 입력 잠금과 클로즈업·슬로모션 확대를 존중하도록 보완했습니다.
- 자막 탭에 한국어 번역 선택을 추가했습니다. 영어 자막 사용 여부와 마우스 조종·화면 기능은 독립적이며 다른 기능 선택은 유지합니다.

**기존 사용자 설치:** 게임을 종료하고 Setup을 기존 게임 폴더에 설치하거나 런처의 업데이트 알림을 이용하세요. 먼저 삭제할 필요 없이 기존 설정과 선택한 기능을 유지합니다. Setup만 실행해도 필요한 파일을 검증하여 내려받습니다. 오프라인 설치는 ZIP 전체를 풀고 `Payload.zip`을 Setup 옆에 두세요.

전환 때 수 초간 끊기는 현상의 원인은 계속 조사 중입니다. 이번 빌드는 확인된 모드 중복 작업을 줄였으며, 모든 게임·드라이버 정지 해소나 실측 FPS 향상을 보장하지 않습니다. 그래픽 품질·DLSS·프레임 생성 설정은 유지합니다.
