# Installation and settings

[Downloads](https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/latest) · [한국어](INSTALL_KOR.md)

## Which launcher does what?

**Save settings in KoreanAIR, then launch from KoreanAIR or ACE8 Mod Launcher in Modded mode.** The external launcher also installs the shared loader and manages other mods. Both launch paths read the same saved control, crosshair, display and camera settings in the game folder.

**Install this pack with its Setup.** Do not import its EXE, Payload.zip or installation folder through ACE8 Mod Launcher's Add mods/Add folder buttons. Setup puts the components in the game's mod folders; the external launcher reads those folders and lists them automatically.

| Listed component | Purpose | What to do |
| --- | --- | --- |
| `AC8MouseAim` — Script mods | Runs mouse flight, crosshair, screen/camera and subtitle-position features | Leave ON when using these features. Configure them in KoreanAIR. Despite its name, it also runs display features. |
| `KoreanAIRCampaign` — Load order | Optional Korean campaign translation archive | Created when translation is enabled in KoreanAIR's Subtitles tab. Leave ON while using translation. Its absence with translation OFF is normal. |

These are two components of one Setup installation. Mouse flight and display features work without Korean translation. Translation and subtitle position are separate settings.

## Installing this pack on its own

1. Close the game.
2. Open the [latest release](https://github.com/KoreanAirline/KoreanAIR-AC8-ModPack/releases/latest), expand **Assets** and download `KoreanAIR_AC8_ModPack_3.0_Setup.exe`. It downloads the required installation files.
3. For offline installation, download `KoreanAIR_AC8_ModPack_3.0.zip` from the same release, extract everything and run **the Setup EXE beside Payload.zip**. Do not extract Payload.zip. The Sources ZIP is not an installer.
4. Select the **ACE COMBAT 8 game folder** containing `start_protected_game.exe` and the `Game` folder. Do not select the inner Game or Win64 folder.
5. Choose your features and select **Install / Update**. Korean translation is OFF by default for new installations.
6. Open **`KoreanAIR_AC8_ModPack_3.0.exe` in the game folder**. Save your settings, then choose **Play → Play with selected mods**. Keep Steam running and signed in.

ACE8 Mod Launcher is optional when using only this pack.

## Installing alongside ACE8 Mod Launcher

Close the game before these steps.

1. Download **ACE8 Mod Loader 1.3.1 (Windows Version)** from [its author's page](https://www.nexusmods.com/acecombat8wingsoftheve/mods/64). The inspected bundle includes **ACE8 Mod Launcher 2.0.1**.
2. Extract the entire bundle to a tools folder. Keep these folders beside each other; do not move only the EXE into the game folder.

   ```text
   AC8 Mod Tools/
     ACE8 Mod Launcher 2.0.1/
       ACE8ModLauncher.exe
     War’s Mod Loader 1.3.1/
       Game/
   ```

3. Run `ACE8ModLauncher.exe`. If the game is not detected, use **Choose the game folder** and select **ACE COMBAT 8**.
4. Select **Play → Set up modding → Install**, or **Settings → Modding setup → Install**. Switch to **Modded** when installation finishes.
5. For another author's aircraft/skin mod, use **Mods → Add mods…** with that mod's ZIP, or **Add folder…** with its extracted folder. Follow that mod's own requirements too.
6. **Install KoreanAIR using the Setup procedure above.** If already installed, run Setup over the existing installation. Do not import this pack's EXE, distribution ZIP, Payload.zip or game folder into the external launcher.
7. Reopen the external mod list. It lists `AC8MouseAim` and, if translation is enabled, `KoreanAIRCampaign` from their installed locations. Check they are ON. No manual registration is needed.
8. **Open `KoreanAIR_AC8_ModPack_3.0.exe` in the game folder and save your settings.** Then use external **Modded → Play modded**, or KoreanAIR's **Play → Play with selected mods**. Both use the same saved settings.

Open KoreanAIR when you want to change settings. For daily play, external **Modded → Play modded** uses those saved settings and other enabled mods. **After a game update, Korean translation users should start once from KoreanAIR or update through Setup to check the current stock subtitles.** External Play does not run KoreanAIR's subtitle refresh or duplicate-key notice.

## Where are the settings?

| Setting | Location |
| --- | --- |
| Sensitivity, zoom, pack shortcuts | KoreanAIR → Controls |
| Crosshair shape, colour and size | KoreanAIR → Crosshair |
| Triple displays, ultrawide, FOV, camera distance/height | KoreanAIR → Screen & camera |
| Frame generation | KoreanAIR → Frame generation |
| Korean translation and subtitle position | KoreanAIR → Subtitles |
| Installed features | KoreanAIR → Installation → Change installed modules |
| Flight, weapons and throttle bindings | The game's key assignment menu |
| Other mods, ON/OFF and file priority | ACE8 Mod Launcher → Mods |

Use each tab's Save/Apply button. Close the game before changing installed modules or translation.

## Triple-monitor setup

You do not need another triple-monitor mod. **`AC8MouseAim` also runs display support.**

1. Use Windows **Extend** display mode.
2. Check that **Screen & camera** is installed under KoreanAIR → Installation.
3. Enable **Screen & camera settings** in KoreanAIR's **Screen & camera** tab.
4. Enable **Choose the game displays manually** and assign three different connected displays to Game left/center/right. Extra monitors can remain connected. Game center can differ from the Windows main display.
5. If sizes, heights or gaps differ, enable **Include gaps and different screen sizes**. Review the shown bounds and unused space. The launcher does not rearrange Windows displays.
6. Enable **Span across three monitors** and click **Save screen & camera** near the bottom.
7. Launch using external **Modded → Play modded** or **KoreanAIR → Play → Play with selected mods**. Both read the saved display selection and screen settings.

Three FHD screens typically span 5760×1080; three QHD screens span 7680×1440. The selected display area determines the actual size. NVIDIA Surround is not required. For a single 21:9/32:9 display or an existing Surround display exposed as one screen, leave **Span across three monitors OFF**, enable Screen & camera and select the display's native resolution in the game.

### Only the center screen works

- **Version 3.0 fixes the 2.4 issue where control/display features did not start through external Play.** Close the game and update with the latest Setup, then use external **Modded → Play modded**. Normal Steam launch and external Unmodded are not this pack's launch paths.
- If the external manager is **Unmodded**, close the game and restore **Modded**. Unmodded can move the entire mod tree out of the game.
- Check `AC8MouseAim` ON, **Screen & camera settings** ON, **Span across three monitors** ON and that settings were saved. If the span option is disabled, refresh monitor detection, select the three displays again and read the layout message.
- If it still fails, create a report in KoreanAIR's **Support** tab. Send `BugReport_*.txt` from `<game folder>/KoreanAIR_AC8_ModPack/Reports` and a screenshot of the display arrangement.

## Script mods and Load order

These are groups of installed files in the external manager. Seeing this pack's components there means they have already been found.

- **Script mods** change behaviour, such as controls and cameras. `AC8MouseAim` appears here. Its position in the list does not need changing.
- **Load order** contains game-file mods such as aircraft, skins and translation archives. **When two mods change the same file, the lower entry wins.** Mods touching different files do not need reordering just for this pack.
- Keep `KoreanAIRCampaign` ON when using translation. Other mods changing the same subtitle table are not automatically merged; choose the translation you want to use.
- With HOTAS/AnalogueYaw or another flight controller, disable KoreanAIR's **Mouse flight**. Screen/camera features can be used separately. Mods controlling the same inputs or camera require individual compatibility checks.

Shared-loader support means these mods use one loader. It does not certify every aircraft mod against the current game. FALKEN Add On 1.0.3 has reported Aircraft Set crashes and is not advertised as fixed.

## Updating an existing installation

Close the game. If using the external manager, restore **Modded** first. Then use KoreanAIR's update button or the new Setup with the same game folder. **Do not uninstall first.** Existing settings, module selection and other mod files are retained.

For online play: close game → disable KoreanAIR features → external Unmodded. To return to modded single-player: close game → external Modded → resume KoreanAIR features, then launch from either launcher.
