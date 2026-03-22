# Background

These scripts were originally created to populate a [Google Sheets database](https://docs.google.com/spreadsheets/d/1OWE25Go9kSao5-IDOS4ZWkBtLfyEF_hPLJz7QQR2lqY/edit?usp=sharing) of GAMMA item data. They now power the [Stalker Anomaly GAMMA DB](https://stalker-gamma-db.pages.dev) web app ([source](https://github.com/simonwdev/stalker-anomaly-gamma-db)).

# Data Export Instructions

## Overview

`universal_anomaly_data_export.script` is a Lua script that runs inside the game engine to export item data as CSV files. It is accessed via the in-game debug launcher UI. All commands are prefixed with `[USADE]`.

All output files are written to the game's `bin/` folder (e.g. `Gamma/Overwrite/bin/`).

## Setup

1. Copy `universal_anomaly_data_export.script` into your game's `gamedata/scripts/` folder.
2. Launch the game and load a save.
3. Open the debug launcher UI (F7) to access the export commands.

## Export steps

1. Run **Export all** and wait for all `[END]` messages in the console (outfits, weapons, and melee are async - wait for all three)
2. Switch the game to the desired language in settings
3. Use **Toggle translation language filename** to select the matching output filename (e.g. `en_us` or `ru_ru`)
4. Run **Export translations** - this reads the existing exported CSVs and translates all keys found in them
5. Repeat steps 2-4 for each additional language

No need to restart the game between languages. No need to re-run the data exports - the translation step picks up keys from the existing CSV files.

## Output structure

- Each export produces a CSV file in `bin/` with the first column being the item's section ID and the remaining columns being stats
- Headers are translation keys (e.g. `pda_encyclopedia_name`) rather than translated text, so the CSVs are language-independent
- Item names and descriptions are also stored as translation keys (e.g. `st_wpn_ak74`) and resolved via the translation files
- Translation CSVs (`en_us.csv`, `ru_ru.csv`) map every key to its translated value in that language
- Some exports produce multiple files split by type (e.g. `export_weapons_pistol.csv`, `export_outfits_outfit_heavy.csv`)