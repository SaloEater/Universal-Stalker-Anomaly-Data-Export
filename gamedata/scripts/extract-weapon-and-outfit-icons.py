#!/usr/bin/env python3
"""Extract item icon sprites from the STALKER Anomaly equipment atlas."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, TextIO, Tuple

from PIL import Image


EXAMPLE_WEAPONS_DIR = Path(r"C:\Anomaly\tools\_unpacked\configs\items\weapons")
EXAMPLE_OUTFITS_DIR = Path(r"C:\Anomaly\tools\_unpacked\configs\items\outfits")
EXAMPLE_ATLAS_PATH = Path(r"C:\Anomaly\tools\_unpacked\configs\ui\ui_icon_equipment.dds")
DEFAULT_CELL_SIZE = 50


@dataclass
class ItemIconSpec:
    file_path: Path
    section_name: str
    item_type: str
    output_name: str
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_output_dir() -> Path:
    return project_root() / "img-data" / "weapons"


def default_outfits_output_dir() -> Path:
    return project_root() / "img-data" / "outfits"


def print_banner(output: TextIO = sys.stdout) -> None:
    print("=" * 72, file=output)
    print(" STALKER Anomaly Item Icon Extractor", file=output)
    print("=" * 72, file=output)
    print("This tool reads inv_grid_* coordinates from w_*.ltx (weapons) and", file=output)
    print("o_*.ltx (outfits) files and crops icons from ui_icon_equipment.dds.", file=output)
    print(file=output)


def prompt_extraction_mode(
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> str:
    """Prompt user to choose extraction mode: weapons, outfits, or both."""
    print_banner(output)
    print("Choose what to extract:", file=output)
    print("  (1) Weapons only", file=output)
    print("  (2) Outfits only", file=output)
    print("  (3) Both weapons and outfits", file=output)
    print(file=output)

    while True:
        choice = input_func("Enter your choice (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            return {"1": "weapons", "2": "outfits", "3": "both"}[choice]
        print(f"[ERROR] Invalid choice. Please enter 1, 2, or 3.", file=output)
        print(file=output)


def validate_required_path(raw_value: str, *, expected_kind: str) -> tuple[Path | None, str | None]:
    value = raw_value.strip().strip('"')
    if not value:
        return None, "Input cannot be empty. Please enter a valid path."

    path = Path(value)
    if not path.exists():
        return None, f"Path does not exist: {path}"

    if expected_kind == "dir" and not path.is_dir():
        return None, f"Expected a folder path, but got a file: {path}"

    if expected_kind == "file" and not path.is_file():
        return None, f"Expected a file path, but got a folder: {path}"

    if expected_kind == "file" and path.suffix.lower() != ".dds":
        return None, f"Expected a .dds file, but got: {path.name}"

    return path, None


def prompt_for_required_path(
    prompt_label: str,
    *,
    example_path: Path,
    expected_kind: str,
    input_func: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> Path:
    while True:
        print(prompt_label, file=output)
        print(f"Example: {example_path}", file=output)
        raw_value = input_func("> ")
        path, error = validate_required_path(raw_value, expected_kind=expected_kind)

        if error:
            print(f"[ERROR] {error}", file=output)
            print(file=output)
            continue

        assert path is not None
        print(f"[OK] Using: {path}", file=output)
        print(file=output)
        return path


def prompt_user_configuration(
    mode: str,
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> tuple[Path | None, Path | None, Path]:
    """Prompt for weapons dir, outfits dir, and atlas folder path based on mode.
    
    Returns: (weapons_dir, outfits_dir, atlas_path)
    Only weapons_dir/outfits_dir relevant to the mode will be non-None.
    Automatically appends ui_icon_equipment.dds to the atlas folder path.
    """
    weapons_dir = None
    outfits_dir = None

    if mode in ("weapons", "both"):
        weapons_dir = prompt_for_required_path(
            "Enter the full path to the folder that contains weapon LTX files (w_*.ltx).",
            example_path=EXAMPLE_WEAPONS_DIR,
            expected_kind="dir",
            input_func=input_func,
            output=output,
        )

    if mode in ("outfits", "both"):
        outfits_dir = prompt_for_required_path(
            "Enter the full path to the folder that contains outfit LTX files (o_*.ltx).",
            example_path=EXAMPLE_OUTFITS_DIR,
            expected_kind="dir",
            input_func=input_func,
            output=output,
        )

    atlas_dir = prompt_for_required_path(
        "Enter the full path to the folder containing ui_icon_equipment.dds.",
        example_path=EXAMPLE_ATLAS_PATH.parent,
        expected_kind="dir",
        input_func=input_func,
        output=output,
    )
    atlas_path = atlas_dir / "ui_icon_equipment.dds"
    if not atlas_path.exists():
        print(f"[ERROR] ui_icon_equipment.dds not found at: {atlas_path}", file=sys.stderr)
        raise FileNotFoundError(f"ui_icon_equipment.dds not found in: {atlas_dir}")
    return weapons_dir, outfits_dir, atlas_path


def parse_int(value: str, key: str, file_path: Path) -> int:
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{file_path}: invalid integer for {key}: {value!r}") from exc


def parse_ltx(file_path: Path) -> Dict[str, Dict[str, str]]:
    """Parse LTX file and return dict of sections, each containing key-value pairs."""
    sections: Dict[str, Dict[str, str]] = {}
    current_section: str | None = None

    with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("//"):
                continue

            if ";" in line:
                line = line.split(";", 1)[0].strip()
            if "//" in line:
                line = line.split("//", 1)[0].strip()
            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                if current_section not in sections:
                    sections[current_section] = {}
                continue

            if "=" not in line or current_section is None:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                sections[current_section][key] = value

    return sections


def sanitize_filename(value: str, fallback: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    sanitized = "".join("_" if char in invalid_chars else char for char in value.strip())
    sanitized = sanitized.rstrip(" .")

    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    if not sanitized or sanitized.upper() in reserved_names:
        sanitized = fallback.strip().rstrip(" .")

    if not sanitized:
        sanitized = "weapon_icon"

    return sanitized


def read_icon_specs_from_file(file_path: Path, item_type: str) -> List[ItemIconSpec | None]:
    """Read all icon specs from a single LTX file (which may have multiple sections)."""
    sections = parse_ltx(file_path)
    specs: List[ItemIconSpec | None] = []
    required = ("inv_grid_x", "inv_grid_y", "inv_grid_width", "inv_grid_height")

    for section_name, values in sections.items():
        missing = [key for key in required if key not in values]
        if missing:
            continue

        preferred_output_name = values.get("inv_name") or values.get("inv_name_short") or section_name

        spec = ItemIconSpec(
            file_path=file_path,
            section_name=section_name,
            item_type=item_type,
            output_name=sanitize_filename(preferred_output_name, section_name),
            grid_x=parse_int(values["inv_grid_x"], "inv_grid_x", file_path),
            grid_y=parse_int(values["inv_grid_y"], "inv_grid_y", file_path),
            grid_w=parse_int(values["inv_grid_width"], "inv_grid_width", file_path),
            grid_h=parse_int(values["inv_grid_height"], "inv_grid_height", file_path),
        )
        specs.append(spec)

    return specs


def discover_weapon_files(weapons_dir: Path) -> List[Path]:
    return sorted(weapons_dir.rglob("w_*.ltx"), key=lambda path: path.name.lower())


def discover_outfit_files(outfits_dir: Path) -> List[Path]:
    return sorted(outfits_dir.rglob("o_*.ltx"), key=lambda path: path.name.lower())


def to_pixel_rect(spec: ItemIconSpec, cell_size: int) -> Tuple[int, int, int, int]:
    left = spec.grid_x * cell_size
    top = spec.grid_y * cell_size
    width = spec.grid_w * cell_size
    height = spec.grid_h * cell_size

    if width <= 0 or height <= 0:
        raise ValueError(
            f"{spec.file_path}: icon size must be positive, got {spec.grid_w}x{spec.grid_h} grid cells"
        )

    return left, top, left + width, top + height


def validate_rect(rect: Tuple[int, int, int, int], atlas_size: Tuple[int, int], file_path: Path) -> None:
    left, top, right, bottom = rect
    atlas_w, atlas_h = atlas_size

    if left < 0 or top < 0 or right > atlas_w or bottom > atlas_h:
        raise ValueError(
            f"{file_path}: icon rect {rect} outside atlas bounds {(atlas_w, atlas_h)}"
        )


def extract_icons(
    atlas_path: Path,
    specs: Iterable[ItemIconSpec],
    output_dir: Path,
    cell_size: int,
) -> Tuple[int, int]:
    extracted = 0
    failed = 0
    used_output_names: Dict[str, int] = {}

    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(atlas_path) as atlas:
        atlas = atlas.convert("RGBA")
        atlas_size = atlas.size

        for spec in specs:
            suffix = used_output_names.get(spec.output_name, 0)
            used_output_names[spec.output_name] = suffix + 1

            output_stem = spec.output_name if suffix == 0 else f"{spec.output_name}_{suffix + 1}"
            output_name = f"{output_stem}.png"
            out_path = output_dir / output_name

            try:
                rect = to_pixel_rect(spec, cell_size)
                validate_rect(rect, atlas_size, spec.file_path)
                icon = atlas.crop(rect)
                icon.save(out_path, format="PNG")
                extracted += 1
            except Exception as exc:  # pragma: no cover - defensive logging path
                failed += 1
                print(f"[WARN] {exc}", file=sys.stderr)

    return extracted, failed


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interactively extract item icons from ui_icon_equipment.dds using inv_grid values from w_*.ltx and o_*.ltx files."
    )
    parser.add_argument(
        "--weapons-output-dir",
        type=Path,
        default=default_output_dir(),
        help=f"Output directory for extracted weapon PNG files (default: {default_output_dir()})",
    )
    parser.add_argument(
        "--outfits-output-dir",
        type=Path,
        default=default_outfits_output_dir(),
        help=f"Output directory for extracted outfit PNG files (default: {default_outfits_output_dir()})",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=DEFAULT_CELL_SIZE,
        help=f"Icon grid cell size in pixels (default: {DEFAULT_CELL_SIZE})",
    )
    return parser


def main() -> int:
    parser = build_cli()
    args = parser.parse_args()

    try:
        mode = prompt_extraction_mode()
        weapons_dir, outfits_dir, atlas_path = prompt_user_configuration(mode)
    except KeyboardInterrupt:
        print("\n[INFO] Cancelled by user.", file=sys.stderr)
        return 130

    print(f"Extraction mode:      {mode}")
    print(f"Cell size:            {args.cell_size}px")
    if mode in ("weapons", "both"):
        print(f"Weapons output:       {args.weapons_output_dir}")
    if mode in ("outfits", "both"):
        print(f"Outfits output:       {args.outfits_output_dir}")
    print()

    all_specs: List[ItemIconSpec] = []
    total_skipped = 0

    if mode in ("weapons", "both"):
        if weapons_dir is None:
            print(f"[ERROR] Weapons directory not provided.", file=sys.stderr)
            return 1

        weapon_files = discover_weapon_files(weapons_dir)
        if not weapon_files:
            print(f"[ERROR] No w_*.ltx files found in: {weapons_dir}", file=sys.stderr)
            return 1

        print(f"Processing weapons from: {weapons_dir}")
        for file_path in weapon_files:
            try:
                specs = read_icon_specs_from_file(file_path, item_type="weapon")
                if not specs:
                    total_skipped += 1
                    print(f"[WARN] Missing inv_grid_* in {file_path}", file=sys.stderr)
                    continue
                all_specs.extend(specs)
            except ValueError as exc:
                total_skipped += 1
                print(f"[WARN] {exc}", file=sys.stderr)

        print(f"Found {len(weapon_files)} weapon files, {len(all_specs)} icon specs")
        print()

    if mode in ("outfits", "both"):
        if outfits_dir is None:
            print(f"[ERROR] Outfits directory not provided.", file=sys.stderr)
            return 1

        outfit_files = discover_outfit_files(outfits_dir)
        if not outfit_files:
            print(f"[ERROR] No o_*.ltx files found in: {outfits_dir}", file=sys.stderr)
            return 1

        print(f"Processing outfits from: {outfits_dir}")
        outfit_specs: List[ItemIconSpec] = []
        for file_path in outfit_files:
            try:
                specs = read_icon_specs_from_file(file_path, item_type="outfit")
                if not specs:
                    total_skipped += 1
                    print(f"[WARN] Missing inv_grid_* in {file_path}", file=sys.stderr)
                    continue
                outfit_specs.extend(specs)
            except ValueError as exc:
                total_skipped += 1
                print(f"[WARN] {exc}", file=sys.stderr)

        print(f"Found {len(outfit_files)} outfit files, {len(outfit_specs)} icon specs")
        all_specs.extend(outfit_specs)
        print()

    if not all_specs:
        print(f"[ERROR] No icon specs found to extract.", file=sys.stderr)
        return 1

    if mode in ("weapons", "both"):
        weapon_specs = [spec for spec in all_specs if spec.item_type == "weapon"]
        extracted_w, failed_w = extract_icons(atlas_path, weapon_specs, args.weapons_output_dir, args.cell_size)
        print(f"Weapons: extracted {extracted_w}, failed {failed_w}")

    if mode in ("outfits", "both"):
        outfit_specs = [spec for spec in all_specs if spec.item_type == "outfit"]
        extracted_o, failed_o = extract_icons(atlas_path, outfit_specs, args.outfits_output_dir, args.cell_size)
        print(f"Outfits: extracted {extracted_o}, failed {failed_o}")

    print()
    print(f"Total icon specs:   {len(all_specs)}")
    print(f"Skipped files:      {total_skipped}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

