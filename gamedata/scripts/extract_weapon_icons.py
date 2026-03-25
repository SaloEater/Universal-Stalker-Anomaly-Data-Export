#!/usr/bin/env python3
"""Extract weapon icon sprites from the STALKER Anomaly equipment atlas."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, TextIO, Tuple

from PIL import Image


EXAMPLE_WEAPONS_DIR = Path(r"C:\Anomaly\tools\_unpacked\configs\items\weapons")
EXAMPLE_ATLAS_PATH = Path(r"C:\Anomaly\tools\_unpacked\configs\ui\ui_icon_equipment.dds")
DEFAULT_CELL_SIZE = 50


@dataclass
class WeaponIconSpec:
    file_path: Path
    output_name: str
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_output_dir() -> Path:
    return project_root() / "img-data" / "weapons"


def print_banner(output: TextIO = sys.stdout) -> None:
    print("=" * 72, file=output)
    print(" STALKER Anomaly Weapon Icon Extractor", file=output)
    print("=" * 72, file=output)
    print("This tool reads inv_grid_* coordinates from all w_*.ltx files", file=output)
    print("and crops matching icons from ui_icon_equipment.dds into PNG files.", file=output)
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
    *,
    input_func: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> tuple[Path, Path]:
    print_banner(output)
    weapons_dir = prompt_for_required_path(
        "Enter the full path to the folder that contains weapon LTX files (w_*.ltx).",
        example_path=EXAMPLE_WEAPONS_DIR,
        expected_kind="dir",
        input_func=input_func,
        output=output,
    )
    atlas_path = prompt_for_required_path(
        "Enter the full path to ui_icon_equipment.dds.",
        example_path=EXAMPLE_ATLAS_PATH,
        expected_kind="file",
        input_func=input_func,
        output=output,
    )
    return weapons_dir, atlas_path


def parse_int(value: str, key: str, file_path: Path) -> int:
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{file_path}: invalid integer for {key}: {value!r}") from exc


def parse_ltx(file_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}

    with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith(";") or line.startswith("//"):
                continue

            if ";" in line:
                line = line.split(";", 1)[0].strip()
            if "//" in line:
                line = line.split("//", 1)[0].strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                values[key] = value

    return values


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


def read_weapon_icon_spec(file_path: Path) -> WeaponIconSpec | None:
    values = parse_ltx(file_path)
    required = ("inv_grid_x", "inv_grid_y", "inv_grid_width", "inv_grid_height")

    missing = [key for key in required if key not in values]
    if missing:
        return None

    preferred_output_name = values.get("inv_name") or values.get("inv_name_short") or file_path.stem

    return WeaponIconSpec(
        file_path=file_path,
        output_name=sanitize_filename(preferred_output_name, file_path.stem),
        grid_x=parse_int(values["inv_grid_x"], "inv_grid_x", file_path),
        grid_y=parse_int(values["inv_grid_y"], "inv_grid_y", file_path),
        grid_w=parse_int(values["inv_grid_width"], "inv_grid_width", file_path),
        grid_h=parse_int(values["inv_grid_height"], "inv_grid_height", file_path),
    )


def discover_weapon_files(weapons_dir: Path) -> List[Path]:
    return sorted(weapons_dir.rglob("w_*.ltx"), key=lambda path: path.name.lower())


def to_pixel_rect(spec: WeaponIconSpec, cell_size: int) -> Tuple[int, int, int, int]:
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
    specs: Iterable[WeaponIconSpec],
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
        description="Interactively extract weapon icons from ui_icon_equipment.dds using inv_grid values from w_*.ltx files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir(),
        help=f"Output directory for extracted PNG files (default: {default_output_dir()})",
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
        weapons_dir, atlas_path = prompt_user_configuration()
    except KeyboardInterrupt:
        print("\n[INFO] Cancelled by user.", file=sys.stderr)
        return 130

    print(f"Output directory: {args.output_dir}")
    print(f"Cell size:        {args.cell_size}px")
    print()

    weapon_files = discover_weapon_files(weapons_dir)
    if not weapon_files:
        print(f"[ERROR] No w_*.ltx files found in: {weapons_dir}", file=sys.stderr)
        return 1

    specs: List[WeaponIconSpec] = []
    skipped = 0

    for file_path in weapon_files:
        try:
            spec = read_weapon_icon_spec(file_path)
            if spec is None:
                skipped += 1
                print(f"[WARN] Missing inv_grid_* in {file_path}", file=sys.stderr)
                continue
            specs.append(spec)
        except ValueError as exc:
            skipped += 1
            print(f"[WARN] {exc}", file=sys.stderr)

    extracted, failed = extract_icons(atlas_path, specs, args.output_dir, args.cell_size)

    print(f"Found weapon files: {len(weapon_files)}")
    print(f"Valid icon specs:   {len(specs)}")
    print(f"Extracted icons:    {extracted}")
    print(f"Skipped files:      {skipped}")
    print(f"Failed extracts:    {failed}")
    print(f"Output folder:      {args.output_dir}")

    return 0 if extracted > 0 and failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

