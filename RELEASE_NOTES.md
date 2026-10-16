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

## Bug fixes — 2.2 (build 2026101605)

- Corrected widescreen output for supported real-time cinematics, briefing maps, replay and debrief views while retaining the native 3D proportions.
- Fixed horizontal stretching of death/retry menus, radio speaker names and `<< >>` frames on wide displays. Dialogue text and subtitle positioning are retained.
- Fixed mouse-aim marker visibility and camera/input handoff in supported campaign camera transitions, including focus/kill scenes.
- Improved aim-circle motion at different display refresh rates. Added mouse side-button bindings.
- Alt free look continues toward the existing aim point; manual flight input during Alt switches to manual control and resumes mouse aiming from the current nose direction on release.
- Added a bounded retry for a transient startup thread change that could prevent the mod, including screen expansion, from starting.

**Updating:** Close the game and run `KoreanAIR_AC8_ModPack_2.2_Setup.exe` over the existing installation, or use the launcher's update notice. Saved settings and selected modules are preserved; uninstalling first is unnecessary. The standalone installer downloads its matching payload from GitHub. For offline installation, extract the main ZIP and keep `Payload.zip` beside Setup.

### 한국어 버그 수정 — 2.2 (빌드 2026101605)

- 지원되는 실시간 시네마틱·브리핑 지도·리플레이·디브리프 화면의 와이드 출력을 수정했습니다. 3D 장면의 원래 비율은 유지합니다.
- 와이드 화면에서 사망·재시도 메뉴, 무전 화자 이름과 `<< >>` 칸이 가로로 늘어지는 문제를 수정했습니다. 대사 본문과 자막 위치 설정은 유지합니다.
- 집중·킬 장면을 포함한 지원되는 캠페인 카메라 전환에서 조준원 표시와 카메라·입력 연결을 수정했습니다.
- 모니터 주사율이 달라도 조준원이 부드럽게 움직이도록 개선하고, 마우스 사이드 버튼 바인딩을 추가했습니다.
- Alt 자유 시점에서는 기존 조준점을 계속 따라갑니다. Alt를 누른 채 수동 조종하면 수동 입력을 따르고, Alt를 놓으면 현재 기수 방향부터 마우스 조종을 재개합니다.
- 시작 시 일시적인 스레드 변경으로 모드와 화면 확장이 시작되지 않던 경우를 제한적으로 재시도하도록 보완했습니다.

**기존 사용자 설치:** 게임을 종료하고 `KoreanAIR_AC8_ModPack_2.2_Setup.exe`를 기존 게임 폴더에 설치하거나, 런처의 업데이트 알림을 이용하세요. 기존 설정과 선택한 기능은 유지되므로 먼저 삭제할 필요가 없습니다. Setup만 실행하면 해당 버전의 파일을 GitHub에서 받습니다. 인터넷 없이 설치하려면 배포 ZIP 전체를 풀고 `Payload.zip`을 Setup 옆에 두세요.
