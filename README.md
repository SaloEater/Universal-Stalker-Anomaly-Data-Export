Now power the [Stalker Anomaly GAMMA DB](https://stalker-gamma-db.pages.dev) web app ([source](https://github.com/simonwdev/stalker-anomaly-gamma-db)).

# Data Export Instructions

## Overview

All output files are written to the game's `bin/` folder.
If you are using MO2, they would be in the `MO2/overwrite/bin` folder.

## Setup

1. Install the mod
2. Launch the game and load a save.
3. Open the debug launcher UI (F7) to access the export commands.

## Export steps

1. Switch the game to the desired language in settings
2. Run **Export all** and wait for all `[END]` messages in the console (outfits, weapons, and melee are async - wait for all three)
3. Run **Export translations** - this reads the existing exported CSVs and translates all keys found in them
4. Repeat steps 1-3 for each additional language

## Output structure

- Each export produces a CSV file with the first column being the item's section ID and the remaining columns being stats
- Headers are translation keys (e.g. `pda_encyclopedia_name`) rather than translated text, so the CSVs are language-independent
- Item names and descriptions are also stored as translation keys (e.g. `st_wpn_ak74`) and resolved via the translation files
- Translation CSVs (`en_us.csv`, `ru_ru.csv`) map every key to its translated value in that language
- Some exports produce multiple files split by type (e.g. `export_weapons_pistol.csv`, `export_outfits_outfit_heavy.csv`)

## Weapon and outfit icon extraction script

To generate icons, add a new executable to your MO2 that points at `scripts\extract-weapon-and-outfit-icons.bat`