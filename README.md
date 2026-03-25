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

## Weapon icon extraction script

Use `gamedata/scripts/extract_weapon_icons.py` to crop weapon icon images from `ui_icon_equipment.dds` using `inv_grid_*` values from all `w_*.ltx` files.

By default it writes PNG files to `img-data/weapons` in this repository.

Output filenames are taken from the weapon config in this order:
- `inv_name`
- `inv_name_short`
- the `.ltx` filename as a final fallback

Install Python dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the script:

```powershell
python .\gamedata\scripts\extract_weapon_icons.py
```

The script then opens an interactive console flow and asks you to enter:
- the full path to the folder containing `w_*.ltx` files
- the full path to `ui_icon_equipment.dds`

It validates empty input, missing paths, wrong file/folder types, and non-`.dds` atlas files before continuing.

Example values you can paste when prompted:
- `C:\Anomaly\tools\_unpacked\configs\items\weapons`
- `C:\Anomaly\tools\_unpacked\configs\ui\ui_icon_equipment.dds`

Optional arguments for output customization:

```powershell
python .\gamedata\scripts\extract_weapon_icons.py `
  --output-dir ".\img-data\weapons" `
  --cell-size 50
```
