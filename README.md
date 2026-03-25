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

Use `gamedata/scripts/extract_weapon_icons.py` to crop weapon and armor icon images from `ui_icon_equipment.dds` using `inv_grid_*` values from all `w_*.ltx` (weapons) and `o_*.ltx` (outfits) files.

By default it writes PNG files to:
- `img-data/weapons` for weapons
- `img-data/outfits` for armor/outfits

Output filenames are taken from the item config in this order:
- `inv_name`
- `inv_name_short`
- the section name (for outfits with multiple definitions per file) or `.ltx` filename as a final fallback

Install Python dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the script:

```powershell
python .\gamedata\scripts\extract_weapon_icons.py
```

The script then opens an interactive console flow:
1. Prompts you to choose extraction mode:
   - **(1) Weapons only** - extracts from `w_*.ltx` files only
   - **(2) Outfits only** - extracts from `o_*.ltx` files only  
   - **(3) Both weapons and outfits** - extracts both types

2. Asks you to enter paths for:
   - the folder containing weapon LTX files (if mode includes weapons)
   - the folder containing outfit LTX files (if mode includes outfits)
   - the full path to `ui_icon_equipment.dds`

3. Validates all input paths before proceeding

Example paths you can paste when prompted:
- Weapons: `C:\Anomaly\tools\_unpacked\configs\items\weapons`
- Outfits: `C:\Anomaly\tools\_unpacked\configs\items\outfits`
- Atlas: `C:\Anomaly\tools\_unpacked\configs\ui\ui_icon_equipment.dds`

Optional arguments for output customization:

```powershell
python .\gamedata\scripts\extract_weapon_icons.py `
  --weapons-output-dir ".\img-data\weapons" `
  --outfits-output-dir ".\img-data\outfits" `
  --cell-size 50
```

### How it works

- **Weapons** (`w_*.ltx`): Each file contains one weapon definition with `inv_grid_x`, `inv_grid_y`, `inv_grid_width`, `inv_grid_height`
- **Outfits** (`o_*.ltx`): Each file can contain **multiple** armor/outfit definitions in separate sections `[section_name]`, each with its own inventory grid coordinates
- Both use the same `ui_icon_equipment.dds` atlas file with different grid positions
- Filenames with special characters are sanitized for Windows compatibility

