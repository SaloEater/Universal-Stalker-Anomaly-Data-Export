#!/usr/bin/env python3
"""Extract item icon sprites from STALKER Anomaly icon atlases."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image


DEFAULT_CELL_SIZE = 1
EXAMPLE_CSV_PATH = Path("data/export_item_icons.csv")
EXAMPLE_TEXTURES_DIR = Path("gamedata/textures")


@dataclass
class ItemIconSpec:
    section_name: str
    texture: str
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int


def project_root() -> Path:
    return Path(__file__).resolve().parent


def default_output_dir() -> Path:
    return project_root() / "img-data" / "icons"




def read_icon_specs_from_csv(csv_path: Path) -> List[ItemIconSpec]:
    specs: List[ItemIconSpec] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                texture = row["texture"].strip()
                if not texture:
                    continue
                spec = ItemIconSpec(
                    section_name=row["id"],
                    texture=texture,
                    grid_x=int(float(row["x"])),
                    grid_y=int(float(row["y"])),
                    grid_w=int(float(row["width"])),
                    grid_h=int(float(row["height"])),
                )
                specs.append(spec)
            except (KeyError, ValueError) as exc:
                print(f"[WARN] Skipping row {row.get('id', '?')}: {exc}", file=sys.stderr)
    return specs


def to_pixel_rect(spec: ItemIconSpec, cell_size: int) -> Tuple[int, int, int, int]:
    left = spec.grid_x * cell_size
    top = spec.grid_y * cell_size
    width = spec.grid_w * cell_size
    height = spec.grid_h * cell_size

    if width <= 0 or height <= 0:
        raise ValueError(
            f"{spec.section_name}: icon size must be positive, "
            f"got {spec.grid_w}x{spec.grid_h} grid cells"
        )

    return left, top, left + width, top + height


def validate_rect(
    rect: Tuple[int, int, int, int],
    atlas_size: Tuple[int, int],
    section_name: str,
    path: str,
) -> None:
    left, top, right, bottom = rect
    atlas_w, atlas_h = atlas_size

    if left < 0 or top < 0 or right > atlas_w or bottom > atlas_h:
        raise ValueError(
            f"{section_name}: icon rect {rect} outside atlas bounds {(atlas_w, atlas_h)} for atlas {path}"
        )


def extract_icons(
    textures_dir: Path,
    specs: List[ItemIconSpec],
    output_dir: Path,
    cell_size: int,
) -> Tuple[int, int]:
    extracted = 0
    failed = 0
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group by texture to open each atlas only once
    by_texture: Dict[str, List[ItemIconSpec]] = {}
    for spec in specs:
        by_texture.setdefault(spec.texture, []).append(spec)

    for texture, texture_specs in sorted(by_texture.items()):
        atlas_path = textures_dir / Path(texture.replace("\\", "/")).with_suffix(".dds")
        if not atlas_path.exists():
            for spec in texture_specs:
                failed += 1
                print(
                    f"[WARN] Atlas not found for {spec.section_name}: {atlas_path}",
                    file=sys.stderr,
                )
            continue

        with Image.open(atlas_path) as atlas:
            atlas_img = atlas.convert("RGBA")
            atlas_size = atlas_img.size

            for spec in texture_specs:
                out_path = output_dir / f"{spec.section_name}.png"
                try:
                    rect = to_pixel_rect(spec, cell_size)
                    validate_rect(rect, atlas_size, spec.section_name, atlas_path)
                    icon = atlas_img.crop(rect)
                    icon.save(out_path, format="PNG")
                    extracted += 1
                except Exception as exc:
                    failed += 1
                    print(f"[WARN] {exc}", file=sys.stderr)

    return extracted, failed


def main() -> int:
    csv_path = EXAMPLE_CSV_PATH
    textures_dir = EXAMPLE_TEXTURES_DIR
    output_dir = default_output_dir()

    print(f"CSV:          {csv_path}")
    print(f"Textures dir: {textures_dir}")
    print(f"Output dir:   {output_dir}")
    print(f"Cell size:    {DEFAULT_CELL_SIZE}px")
    print()

    specs = read_icon_specs_from_csv(csv_path)
    if not specs:
        print("[ERROR] No icon specs found in CSV.", file=sys.stderr)
        return 1

    print(f"Loaded {len(specs)} icon specs.")
    print()

    extracted, failed = extract_icons(textures_dir, specs, output_dir, DEFAULT_CELL_SIZE)

    print(f"Extracted: {extracted}")
    print(f"Failed:    {failed}")
    print(f"Total:     {len(specs)}")

    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        code = 1
    input("\nPress Enter to exit...")
    raise SystemExit(code)
