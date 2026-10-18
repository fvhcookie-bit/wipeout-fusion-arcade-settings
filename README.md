# WipEout Fusion — Arcade Race Settings (PCSX2 patch)

A PCSX2 patch for **WipEout Fusion (PAL, SCES-50005)** that gives single-player **Arcade** its own race
set-up screen. Pick the number of laps, fill the grid with up to 16 ships, set shields, make the CPU ships
stronger than yours, and decide what happens to destroyed opponents: they drop out, respawn, or stay on the
track as wrecks.

The same file also contains an optional fix for the slowdown PCSX2 has on the 3D **FINAL LAP** text.

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

## Requirements

- **PCSX2 2.x** (tested with 2.8). Other emulators and real hardware are not supported.
- **PAL** WipEout Fusion, serial **SCES-50005**, CRC **90DB90F1**. The NTSC versions are different
  builds and will not work.

## Installation

1. Download `patches/90DB90F1.pnach` (or the release archive).
2. Put it into the PCSX2 **patches** folder. In PCSX2 2.x it is `Documents\PCSX2\patches` by default
   (*Settings → Folders* shows the exact path).
   - If you already have a `90DB90F1.pnach` there, append the sections from this file to it instead of
     replacing it.
3. Start PCSX2, right-click the game in the list → **Properties → Patches**, and tick
   **Arcade race settings**. The three **FINAL LAP fix** entries are optional and independent.
4. **Restart the game** after enabling or disabling the patch. The new screen is set up when the game
   boots, so toggling the patch mid-game is not enough.

## Notes and known limitations

- The race settings are stored in the same place as the two-player race settings, so changing them in Arcade
  also changes them in two-player mode and the other way round. They are saved with your profile like the
  original two-player settings.
- **destroyed cpu ships** is not saved: it starts at **out** every time the game boots.
- The new labels (*respawn player*, *destroyed cpu ships*, *out / respawn / wreck*, *race set-up*,
  *shield energy player*) are in English whatever the game language is.
- Ship models follow the race class: with a higher **upgrade level** every ship, yours included, uses the
  model of that class. Your ship's handling still comes from your own upgrades.
- Wrecks never move, so you will lap them. The game's usual rule then takes a ship that is a full lap behind
  out of the race, and the opponent counter goes down. The wreck stays on the track and is still solid.
- In Arcade the two-player screen's *shield energy player 2* value follows the CPU shield value.

## FINAL LAP fix

PCSX2 slows down when the 3D race messages (FINAL LAP, lap times, records) are on screen. The game draws every
letter pixel as a separate translucent cube, five echo layers deep.

- **1 echo layer instead of 5**: recommended, removes the slowdown. The text still animates; only the trail
  is gone.
- **brightest layer alpha 192 → 128**: optional experiment that helps some renderers; messages get dimmer.
- **no FINAL LAP text**: removes that message completely. The announcer still says it.

## For modders

`tools/arcade_mod.py` generates the patch. `python arcade_mod.py pnach` prints it, and with the PINE
interface enabled in PCSX2 `python arcade_mod.py live` can poke parts of it into a running game. The comments
in the script explain every hook. Code caves live in the unused EE RAM range `0x000C0000–0x000FFFFF`.

This mod is a by-product of **ReFusion**, a reverse-engineering project for WipEout Fusion.

## License

MIT, see [LICENSE](LICENSE). The patch contains no game data. You need your own copy of the game.
