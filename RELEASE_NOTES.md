# War Thunder-Style Mouse Controls, Triple-Monitor Support, and More!

**⚠️ Important Note:** This mod reads game data to perform calculations, so it only works in single-player mode.

## Features

Here's what this mod offers:

1. **War Thunder-style keyboard and mouse controls** (Check out the YouTube demo video to see how it works!)
2. **Triple-monitor support** (See screenshots)
3. **Improved Japanese-to-Korean subtitles** (For Korean players, fixing awkward or unnatural translations)
4. **Frame Generation support** (This was previously possible by manually editing the game's .ini files, but now you can enable it directly through the mod launcher.)
5. **Adjustable subtitle position** (Personally, I find subtitles at the top of the screen a bit hard to read, so I've added an option to move them to the bottom.)

## War Thunder-Style Mouse Controls

I made this mod mainly for players who prefer using a keyboard and mouse.

I took inspiration from War Thunder, which is well known for its mouse-friendly flight controls, and tried to bring a similar control scheme to this game.

**You no longer have to manually manage pitch, yaw, and roll with your mouse just to get your aircraft to follow the circle on the screen.**

Instead, your aircraft will automatically follow your mouse aim, just like in War Thunder.

Of course, you can still manually control your roll using **A and D**, which allows you to pull off more advanced maneuvers.

You can also **right-click to zoom in**, just like in War Thunder.

## Triple-Monitor Support

For those of you running a triple-monitor setup (three 16:9 monitors), I've added support for using all three screens **without needing NVIDIA Surround**.

You can simply enable and configure it through the mod launcher.

This works not only during campaign gameplay but also in **real-time rendered cutscenes**.

As a result, you can actually see parts of the game world that would normally be outside the visible area on a standard 16:9 display.

## Bug Reports & Feedback

Unfortunately, I've been pretty busy lately, so I haven't had enough time to thoroughly test everything.

There might still be some bugs, so if you run into any issues, **please let me know in the comments!**

Thanks for checking out my mod, and I hope you enjoy it!

---

## Bug fixes — 2.0 (build 2026101506)

- Corrected target selection to prioritize enemies nearest the visible mouse-aim circle.
- Corrected Alt free-look and manual-control handoff: Alt alone retains the existing flight goal; WASD/QE input while holding Alt switches the aim circle to the aircraft heading until Alt is released.
- Reduced aim-circle jitter while keeping mouse flight-goal input immediate.
- Extended widescreen handling to the active replay/debrief cameras.
- Fixed automatic recentering when using mouse head look in interactive scenes.
- Corrected independent mouse-input worker startup and removed redundant object searches, camera checks and status-text allocations.

Intermittent stalls around landing/takeoff were still observed during testing. Their cause remains unconfirmed; this update does not claim to fix them.
