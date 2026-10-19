# WipEout Fusion — Arcade Race Settings (PCSX2 patch)

A PCSX2 patch for **WipEout Fusion** (PAL and NTSC-U) that gives single-player **Arcade** its own race
set-up screen. Pick the number of laps, fill the grid with up to 16 ships, set shields, make the CPU ships
stronger than yours, and decide what happens to destroyed opponents: they drop out, respawn, or stay on the
track as wrecks.

The same files also contain optional extras: skipping the intro movies, and a fix for the 3D **FINAL LAP**
text on older PCSX2 versions.

*Краткая инструкция на русском — [README.ru.md](README.ru.md).*

## What you get

After you choose your ship in **Arcade**, a **race set-up** screen opens before track selection:

| Setting | What it does |
|---|---|
| number of laps | 1–10 laps |
| shield energy player | your shield, 5–100 % |
| shield energy cpu ships | CPU shield, 5–100 % |
| computer ships | slider 0–10 → **6 to 16 ships** on the grid (full grid at max) |
| upgrade level | CPU upgrade level and race class (1–4). Preset to your ship's level each time the screen opens; all four levels are available, so the CPU can be stronger than you. Your own ship keeps the upgrades you bought |
| pit lane | on / off |
| respawn player | you respawn after being destroyed instead of dropping out |
| catch-up | off / low / high rubber band |
| destroyed cpu ships | **out** — as in the original game · **respawn** — they come back and race on · **wreck** — they come back as dead hulks that sit on the track: no steering, no weapons, but solid |

Press ✕ to accept and go on to track selection, △ to go back to ship selection.
All other modes (League, Time Trial, Challenges, Zone, two-player) are unchanged.

## Supported versions

| Release | Serial | CRC | Patch file |
|---|---|---|---|
| PAL (Europe) | SCES-50005 | 90DB90F1 | `patches/90DB90F1.pnach` |
| NTSC-U (USA) | SLUS-20462 | 4C2D1E6D | `patches/4C2D1E6D.pnach` |

Both were tested in **PCSX2 2.8**. The NTSC-U patch also works together with PCSX2's built-in *Widescreen 16:9*
and *No-Interlacing* patches for that release. Other emulators, real hardware and other releases have not been
tested, so the patch is not guaranteed to work there.

## Installation

1. Download the release archive and take the `.pnach` file for your release (see the table above).
2. Put it into the PCSX2 **patches** folder. In PCSX2 2.x it is `Documents\PCSX2\patches` by default
   (*Settings → Folders* shows the exact path).
   - If a file with the same name is already there, append the sections from this file to it instead of
     replacing it.
3. Start PCSX2, right-click the game in the list → **Properties → Patches**, and tick
   **Arcade race settings**. The other entries are optional and independent.
4. **Restart the game** after enabling or disabling the patch. The new screen is set up when the game
   boots, so toggling the patch mid-game is not enough.

## Optional extras

- **Skip intro movies** — skips the two logo movies when the game boots. The movie that plays in the menu when
  you leave the game idle is kept.
- **FINAL LAP fix: 1 echo layer instead of 5** — older PCSX2 versions slow down while the 3D race messages
  (FINAL LAP, lap times, records) are on screen: the game draws every letter pixel as a translucent cube,
  five echo layers deep. This draws one layer; the text still animates. **Not needed with PCSX2 2.8**, where
  these messages run at full speed with both Vulkan and Direct3D 12.
- **FINAL LAP fix: no FINAL LAP text** — removes that message completely. The announcer still says it.

## Notes and known limitations

- The race settings are stored in the same place as the two-player race settings, so changing them in Arcade
  also changes them in two-player mode and the other way round. They are saved with your profile like the
  original two-player settings.
- **destroyed cpu ships** is not saved: it starts at **out** every time the game boots.
- The new labels (*respawn player*, *destroyed cpu ships*, *out / respawn / wreck*, *race set-up*,
  *shield energy player*) are in English whatever the game language is.
- Ship models follow the race class: with a higher **upgrade level** every ship, yours included, uses the
  model of that class. Your ship's handling still comes from your own upgrades.
- In Arcade the two-player screen's *shield energy player 2* value follows the CPU shield value.
- The attract-mode demo races in the menu are built from the same settings (number of ships, laps and so on).

## For modders

`tools/arcade_mod.py` generates the PAL patch: `python arcade_mod.py pnach` prints it, and with the PINE
interface enabled in PCSX2 `python arcade_mod.py live` can poke parts of it into a running game. The comments
in the script explain every hook. Code caves live in the unused EE RAM range `0x000C0000–0x000FFFFF`.
The NTSC-U patch is the same code relocated to that build: every hook and data address was found by matching
the surrounding code, and the original instructions at each hook were checked to be identical.

This mod is a by-product of **ReFusion**, a reverse-engineering project for WipEout Fusion.

## License

MIT, see [LICENSE](LICENSE). The patch contains no game data. You need your own copy of the game.
