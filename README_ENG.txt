KoreanAIR_AC8_ModPack_1.3
English user guide

INSTALL AND PLAY

1. Start ACE COMBAT 8 normally through Steam at least once, then close the game.
2. Run KoreanAIR_AC8_ModPack_1.3_Setup.exe. Select the game folder containing
   start_protected_game.exe, then choose the modules and click Install / Update.
3. Open KoreanAIR_AC8_ModPack_1.3.exe in the game folder. Keep Steam open and
   choose Play with selected mods.

Close the game before installing, removing or changing modules. A writable Steam
library does not need administrator rights; a protected folder may require running
Setup as administrator. The supported executable has timestamp 0x6AA0E27D and
image size 0x2195A000. Installation/launch rejects unsupported game updates.

If your installed launcher does not have an update banner, run the latest installer
once without uninstalling. Your settings are preserved.

If another mod uses Game/Binaries/Win64/dinput8.dll, the installer warns you before
changing files. Choose Yes to install without Korean campaign subtitles; the
existing loader and other mod files are preserved, and your selected Mouse flight
and Screen options remain available. To add Korean campaign subtitles later,
remove the conflicting loader yourself, then use Change installed modules on
the launcher's Installation tab. Playing alongside other mods has not been verified.

UPDATES

The launcher checks for updates every time you open it. An available update appears
in a prominent banner at the top. Close the game, then choose Update now. The launcher
downloads and verifies the update, applies it and restarts. A newer bug-fix build can
keep the same displayed version number; these updates also appear in the banner.

Updates preserve your selected modules, saved INI settings, controls and keybindings,
HUD and crosshair settings, aim zoom, FOV and camera settings, subtitle position
and interface language. If the pack is disabled for standard play, it stays
disabled after updating.
While offline or if an update check or download fails, you can still use the launcher
to play with your installed mods.

MODULES

- Korean campaign subtitles: improves campaign subtitles using the English source.
  Online dialogue remains unchanged.
- Mouse flight controls: mouse steering, Alt free look, toggle zoom toward mouse
  aim and the flight helper HUD.
- Triple monitor span and FOV: single-display flight FOV or a window spanning
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

Adjust Mouse steering sensitivity and Free look sensitivity separately.
Hold the free-look key during flight to look around. WASD remains available for
direct control. Save changes, then focus the game; sensitivity, aim zoom and mod
shortcut settings reload automatically in about 0.5 seconds. F10 is an optional manual
reload shortcut; it is not required to apply saved changes.

Aim zoom is on by default. During ordinary flight, click the right mouse button to
point the camera toward the mouse steering target and magnify the view; click again
to return to the normal flight camera. Both transitions take 180 ms and are smooth.
Releasing the button keeps zoom active. Zoom does not select a locked target.
Enable aim zoom on Controls turns the feature on/off.
Adjust Aim zoom magnification with the slider or numeric field from 1× to 8×,
in 0.01× steps; the default is 2×. Change Aim zoom (toggle) to a keyboard key or a
right, middle or side mouse button. Free look, menus and cinematic cameras cancel
zoom; click again to zoom after normal flight resumes.
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
look during flight. Original keyboard look remains available and the game's
scene-specific angle limits remain in effect. Mouse movement in these scenes
does not change the flight steering target.

Default mod shortcuts (change them on Controls):
- F7: show/hide the flight helper HUD.
- F8: enable/disable mouse steering.
- F9: recenter mouse steering.
- F10: reload saved control settings.
- Alt (hold): free look.
- Right mouse button (click): toggle aim zoom, 2× by default; click again to return.

Choose keys from the list or use Press key to capture one. Aim zoom also accepts
the right, middle and side mouse buttons. Each of the six mod actions needs
a different key. WASD/QE, Escape, Enter, Tab and Windows keys are reserved.
Avoid conflicts with the game's other bindings.
Set the game's own flight and target-selection keys in its controls menu.

CROSSHAIRS (Crosshairs)

Mouse flight provides two anti-aliased markers: the mouse steering target and the
aircraft's nose direction. The mouse steering target is always a circle. Choose
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

Enable camera settings to apply this tab's camera options. FOV uses a 16:9 reference
and affects flight only. Menus and prerecorded videos retain their original view.
Chase camera distance and height require the Mouse flight module and affect
third-person view only.

Triple span requires three displays with equal pixel resolutions, arranged directly
left/main/right in Windows display settings. The middle display must be the main
display, and all three must align along the top with no gaps. NVIDIA Surround is
not required. If the layout is unsuitable, triple span is unavailable but
single-display FOV remains available. Save changes, then focus the game to see them.

When triple span is enabled, supported real-time rendered cinematics, T target-view
scenes and interactive head-look scenes also use the full span. The mod extends
the horizontal view while preserving native camera motion and animated zoom; the
flight FOV slider does not replace the cinematic lens. This requires a positively
identified active camera and a matching wide render viewport. Unrecognized
cameras, prerecorded videos and separately drawn black-bar overlays are unchanged.

SUBTITLE POSITION (Subtitles)

Choose Original position to keep the game's dialogue subtitle placement, or Bottom
of screen to lower supported flight radio dialogue and cinematic dialogue subtitles.
Click Save subtitle position, then focus the game. Saved changes apply automatically
while playing. The choice is available when any module is installed and is separate
from the Korean campaign subtitle translation. Titles, credits and other HUD
elements keep their original placement.

GAME SETTINGS

Use the game's own menus for graphics quality, DLSS, frame rate, VSync and other
game options. The launcher provides only settings specific to this mod pack.

STANDARD / ONLINE PLAY

The mod launcher uses the game's offline Null-client configuration. Modules are
for offline play. Before standard or online play, close the game, choose Disable
pack for standard play on the Play tab, then start the game normally in Steam.
This parks this pack's loaders and subtitle archive outside the active game paths.
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
