KoreanAIR_AC8_ModPack_2.4
English user guide — build 2026110301

INSTALL AND PLAY

1. Start ACE COMBAT 8 normally through Steam at least once, then close the game.
2. Extract the complete ZIP, keeping Payload.zip beside the installer, then run
   KoreanAIR_AC8_ModPack_2.4_Setup.exe. Select the game folder containing
   start_protected_game.exe, then choose the modules and click Install / Update.
3. Open KoreanAIR_AC8_ModPack_2.4.exe in the game folder. Keep Steam open and
   choose Play with selected mods.

The standalone installer downloads the matching verified mod files when needed.

Close the game before installing, removing or changing modules. A writable Steam
library does not need administrator rights; a protected folder may require running
Setup as administrator. The inspected executable has timestamp 0x6AD2D0A7 and
image size 0x215A2000. A different game build receives an unverified-version
warning. Its version alone does not prevent installation or launch; native
features still require matching code guards and may stay inactive after updates.

If your installed launcher does not have an update banner, run the latest installer
once without uninstalling. Your settings are preserved.

An installed, enabled ACE8 Mod Loader / IoStoreLoaderMod 1.3.1 with the recognized
shared UE4SS files can load the Korean campaign archive as well. Setup uses that
one loader and removes only this pack's previous campaign hook. See OTHER MODS
below. An unknown dinput8.dll or runtime is preserved and reported; Setup does
not overwrite it to force compatibility. If only the campaign loader conflicts,
you may install without Korean campaign translation while keeping Mouse flight
and Screen options with a recognized runtime.

UPDATES

The launcher checks for updates every time you open it. An available update appears
in a prominent banner at the top. Close the game, then choose Update now. The launcher
downloads and verifies the update, applies it and restarts. A newer bug-fix build can
keep the same displayed version number; these updates also appear in the banner.
The banner shows the installed version/build and the offered version/build.
After updating, the installed banner retains the previous-to-current transition.
Choose What's changed to read the matching English or Korean update notes.

Updates preserve your selected modules, saved INI settings, controls and keybindings,
HUD and crosshair settings, aim zoom, FOV and camera settings, frame generation
selection, subtitle position
and interface language. If the pack is disabled for standard play, it stays
disabled after updating.
While offline or if an update check or download fails, you can still use the launcher
to play with your installed mods.

MODULES

- Korean campaign subtitles: improves campaign subtitles using the English source.
  Online dialogue remains unchanged. In Subtitles, select Korean campaign
  translation and Apply translation selection to add/remove it through Setup.
  Mouse flight and screen features also work without Korean translation.
- Mouse flight controls: mouse steering, Alt free look, toggle zoom toward mouse
  aim and the flight helper HUD.
- Screen & camera: flight FOV, automatic ultrawide correction or a window spanning
  three displays, plus chase camera distance/height when Mouse flight is installed.

ADJUSTING VALUES

Numeric settings have a slider and a matching numeric entry field. Drag the slider
for quick changes, or focus it and use the Left/Right arrow keys. Click the numeric
field to type a precise value, or use its Up/Down arrows. Both controls show the
same setting. Values stay within the range displayed by the controls.
Fine adjustments use steps of 0.001 for sensitivity, 0.01× for aim zoom and
0.1 degree for FOV.
Camera distance and height use steps of 1.
Use the tab's Save button to store your changes.

MOUSE FLIGHT (Controls)

The mouse steering circle updates independently of game frames, using the current
refresh rate of the displays covered by the game window. Unchanged glyph images
are reused. Aircraft direction follows the game's actual state updates. Camera
compensation is blended between updates without delaying mouse input or the
aircraft's steering target.

Adjust Mouse steering sensitivity and Free look sensitivity separately.
Hold the free-look key during flight to look around. The aircraft keeps following
your last mouse steering target; free-look mouse movement does not change it.
Pitch, roll or yaw input during free look cancels pursuit for the rest of that
hold. The steering circle follows the aircraft nose until you release the
free-look key; mouse steering then resumes from that direction.
Save changes, then focus the game; sensitivity, aim zoom and mod
shortcut settings reload automatically in about 0.5 seconds. F10 is an optional manual
reload shortcut; it is not required to apply saved changes.

Aim zoom is on by default. During ordinary flight, click the right mouse button to
point the camera toward the mouse steering target and magnify the view; click again
to return to the normal flight camera. Both transitions take 140 ms and are smooth.
Releasing the button keeps zoom active. Zoom does not select a locked target.
Enable aim zoom on Controls turns the feature on/off.
Adjust Aim zoom magnification with the slider or numeric field from 1× to 8×,
in 0.01× steps; the default is 2×. Change Aim zoom (toggle) to a keyboard key or a
right, middle or side mouse button. Hold Alt while zoomed to look around at the
same magnification. Releasing Alt smoothly returns the camera toward mouse aim
while keeping zoom active. Click the zoom button again at any time, including
during Alt free look, to return to normal magnification. Menus and cinematic
cameras cancel zoom; click again after normal flight resumes.
Mouse flight is required; zoom also works when Screen & camera settings are off.
It does not replace target-view, free-look or cinematic camera behavior. If the
same button also triggers a game action, change that binding in the game's controls
menu. Save controls & keys applies zoom changes automatically without pressing F10.

Use the game's view-switch control for first-person, cockpit and third-person
views. First-person and cockpit retain their native camera position and roll.
Chase distance and height affect third-person view only.

A short press and release of the game's target-selection button chooses the
visible native target candidate nearest the center of the mouse steering circle.
A target does not have to be inside the circle. Offscreen/behind-camera targets
are excluded; the game's own candidate list still determines eligible targets.
Holding the button for 0.35 seconds or longer retains the game's target-view
behavior.
When the player aircraft uses a target-focus or impact camera, the game retains
its camera while mouse steering continues. Scripted camera actors and interactive
head-look scenes retain their own input.

Cobra, Kulbit and other native special maneuvers retain the game's aircraft and
activation requirements. During the game's special-maneuver rotation, ordinary
mouse pursuit yields to native maneuver controls. Held keyboard axes retain their
native input, and mouse elevator follows the game's maneuver input behavior.
Ordinary mouse pursuit resumes when that rotation ends. During normal flight,
keyboard pitch and lateral mouse steering can be used together. Holding both
throttle and brake for a tight turn does not disable mouse pursuit.

INTERACTIVE SCENE MOUSE LOOK

In supported interactive cinematic scenes that allow head/camera movement, move
the mouse to look around instead of using the original 7/8/9/0 controls. No ALT
press is needed. This uses Free look sensitivity from Controls, just like ALT
look during flight. Stopping the mouse retains the selected look direction.
Original keyboard look remains available and the game's
scene-specific angle limits remain in effect. Mouse movement in these scenes
does not change the flight steering target.

Default mod shortcuts (change them on Controls):
- F7: show/hide the flight helper HUD.
- F8: enable/disable mouse steering.
- F9: recenter mouse steering.
- F10: reload saved control settings.
- Alt (hold): free look.
- Right mouse button (click): toggle aim zoom, 2× by default; click again to return.

Choose keys from the list or use Press key to capture one. All six mod actions
accept Mouse 4 / Mouse 5 (side buttons); aim zoom also accepts right and middle
mouse buttons. Each of the six mod actions needs
a different key. WASD/QE, Escape, Enter, Tab and Windows keys are reserved.
Avoid conflicts with the game's other bindings.
Set the game's own flight and target-selection keys in its controls menu.

CROSSHAIRS (Crosshairs)

Mouse flight provides two anti-aliased markers: the mouse steering target and the
aircraft's nose direction. The mouse steering target is always a circle, updated
from new mouse input at the refresh rate of the displays covered by the game window. Choose
its size and color separately from the aircraft direction marker. Only the aircraft
direction marker has selectable styles: Circle, Cross + dot, X, Cross and Ring +
cross. Line thickness, optional
thin outline and opacity apply to both. Colors accept six-digit RGB values such
as FFFFFF or #00FF80; the color picker is also available.
These are illustrative aiming symbols,
not a simulation of a particular aircraft's weapon sight. The nose marker shows
heading, not bullet lead or the game's weapon aiming solution.

Save crosshair changes during play, then focus the game. They reload automatically
in about 0.5 seconds without restarting. The HUD shortcut hides/shows both markers.

SCREEN AND CAMERA (Screen & camera)

Enable screen & camera settings to apply this tab's camera options and automatic
aspect correction in supported rendered scenes. FOV uses a 16:9 reference and
affects flight only. Prerecorded videos retain their original view.
Chase camera distance and height require the Mouse flight module and affect
third-person view only.

For a single 21:9 or 32:9 ultrawide display, enable screen & camera settings and
leave Span across three monitors unchecked. Select the display's native resolution
in the game's borderless or fullscreen mode. Three monitors are not required;
correction follows the actual game render viewport.

Automatic detection uses three adjacent equal-resolution displays, including the
Windows main display. Different refresh rates and additional displays are allowed.
Use manual selection to choose the game left, centre and right displays, even when
the Windows main display is elsewhere. The diagram shows the actual desktop layout;
it does not rearrange Windows displays. With five displays, only the three chosen
game displays determine the manual span; the other two displays' resolution or
refresh rate does not disqualify that selection.

Include gaps and different screen sizes is on by default in manual selection.
It spans one rectangle
covering your selected displays, allowing different sizes, gaps and vertical
offsets. The launcher shows the physical pixel bounds and any gaps/overlaps.
That rectangle may include desktop space between displays or outside their edges;
an irregular Windows arrangement cannot become a continuous physical screen.
Turn this option off to require three equal-resolution displays touching side by
side with aligned top/bottom edges. If needed, arrange them in Windows and refresh
detection. Send a Support report if the selected area is incorrect. The individual
five-display reporter's original PC-specific cause has not been confirmed.
For Surround or a single ultrawide surface, leave triple span off and choose its
native wide resolution in the game.

Save screen & camera, then focus the game to apply changes.

Supported rendered hangar aircraft/weapon selection, sortie and departure scenes,
real-time cinematics, T target-view and interactive head-look scenes adapt to the
actual game render viewport on an ultrawide display or triple span. The mod extends
the horizontal view while preserving native camera motion and animated zoom; the
flight FOV slider does not replace the cinematic lens. This requires a positively
identified active camera and a confirmed render viewport. Unrecognized cameras,
prerecorded videos and separately drawn black-bar overlays are unchanged.

FRAME GENERATION (Frame generation)

The saved override protects its settings file while managed by the launcher.
Restore original setting returns the original contents and file attributes.

Close the game, select On or Off on the Frame generation tab, then click Save
frame generation. Your selection applies on the next game launch. Restart the
game after each change; settings cannot be changed while the game is running.
If the pack is disabled, choose Resume mod pack before saving.

The initial setting inherits your existing game preference; updates preserve
your saved choice. Restore original setting removes this mod's override and uses
the game's original setting. Saving On may not activate frame generation if the
game, graphics card or driver does not support it. A saved selection alone does
not verify actual activation or a frame-rate improvement.

Use the game's graphics menu for ordinary DLSS, graphics quality, frame limits,
VSync and other graphics options. This launcher tab controls frame generation
on/off only.

SUBTITLE POSITION (Subtitles)

Choose Original position to keep the game's dialogue subtitle placement, or Bottom
of screen to lower supported flight radio dialogue and cinematic dialogue subtitles.
Click Save subtitle position, then focus the game. Saved changes apply automatically
while playing. The choice is available when any module is installed and is separate
from the Korean campaign subtitle translation. Titles, credits and other HUD
elements keep their original placement.

GAME SETTINGS

Use the game's own menus for graphics quality, ordinary DLSS, frame rate, VSync and other
game options. The launcher provides only settings specific to this mod pack.

STANDARD / ONLINE PLAY

The mod launcher uses the game's offline Null-client configuration. Modules are
for offline play. Before standard or online play, close the game, choose Disable
pack for standard play on the Play tab, then start the game normally in Steam.
This parks this pack's loaders and subtitle archive outside the active game paths.
In recognized shared-loader mode, it parks this pack's entry script and subtitle
archive while retaining the external loader and runtime needed by other mods.
Check other installed mods yourself before online play. Resume mod pack enables
this pack again for offline play.

CHANGE MODULES, UNINSTALL AND BACKUPS

Open Installation and choose Change installed modules to reopen the installer.
Use Uninstall there, or select no modules and click Install / Update, to remove the
pack. Only files tracked by this pack are removed/restored; saves and unrelated
files are preserved. If a tracked program file was changed externally, removal
stops and preserves it instead of deleting it.

Recoverable migration/original-file backups are stored outside the game folder:
%LocalAppData%\KoreanAIR_AC8_ModPack\Backups

OTHER MODS / ACE8 MOD LOADER

Download ACE8 Mod Loader 1.3.1 separately from its author and follow its installation
instructions: https://www.nexusmods.com/acecombat8wingsoftheve/mods/64
The third-party loader is not included in this pack. Once its IoStoreLoaderMod is
installed and enabled, close the game and run this pack's Setup over your existing
installation. Setup recognizes only the inspected loader and shared runtime files.
In this mode there is one archive-loading owner: IoStoreLoaderMod loads the Korean
campaign PAK and this pack omits its own campaign constructor hook. Existing mod
folders, runtime settings and load-order entries are preserved.

Keep KoreanAIRCampaign enabled in IoStoreLoaderMod's loadorder.txt if you use the
translation. An explicit disabled entry is reported rather than silently changed.
Updating or removing this pack does not remove that external loader, its runtime
or its other mod folders. Changes to unknown shared DLLs are reported for review;
they are not treated as compatible merely because their filenames match.

Use this pack's launcher for its offline mod play. Do not use two launchers to
repeatedly move or replace the same shared files. A third-party manager's Unmodded
mode may move the whole UE4SS tree; restore that manager's modded files before
resuming this pack. Disabling this pack alone does not disable external mods.

FALKEN Add On 1.0.3 was checked for package files, imports and loader structure.
It needs IoStoreLoaderMod for its new assets. Combined in-game FALKEN flight has
not been verified. This compatibility path is limited to the recognized files;
arbitrary aircraft, camera or flight-controller mods are not guaranteed compatible.


AC8HOTAS / ANALOGUE YAW

Use HOTAS controls with Mouse flight OFF; Screen & camera and subtitles can remain
installed. The installer recognises the inspected AC8HOTAS0.2.0 runtime bundle and
can use this pack's shared UE4SS while retaining HOTAS mod folders and bindings.
Close the game and rerun Setup with Mouse flight unchecked after a shared-runtime
replacement error. Do not overwrite the shared runtime with the HOTAS bundle again.
Unknown replacement files are preserved. Actual combined in-game HOTAS operation
has not been verified. To use this pack's mouse steering, disable AC8HOTAS and
AC8AnalogYaw in UE4SS first; do not enable both flight controllers together.

BUG REPORTS (Support)

For mouse steering issues, select Start input recording just before reproducing
the problem. The next active flight records up to two minutes at4Hz, then stops;
start the game within ten minutes if it is closed. This recording is off in normal
play and does not enable the large binary controller trace.
After reproducing the issue, close the game and select Create bug report. The
launcher opens the generated text file's folder:
<game folder>\KoreanAIR_AC8_ModPack\Reports\BugReport_*.txt
Send that text with the mission, camera mode, approximate issue time and actions.
If the game folder is not writable, Reports is stored under
%LocalAppData%\KoreanAIR_AC8_ModPack instead; the launcher opens that folder.
A short video helps with steering/display issues. The file contains selected
settings, monitor layout, file verification and bounded recent logs; private paths
are redacted. Review it before sharing. Nothing is uploaded automatically.
