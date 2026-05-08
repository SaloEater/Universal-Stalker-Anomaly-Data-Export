#!/usr/bin/env python3
"""Extract item icon sprites from STALKER Anomaly icon atlases — MO2 plugin + standalone."""

from __future__ import annotations

import csv
import inspect
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import mobase
    from PyQt5.QtCore import QCoreApplication, QRect
    from PyQt5.QtGui import QIcon, QImage, QImageReader
    from PyQt5.QtWidgets import QMessageBox
    _MO2_AVAILABLE = True
except ImportError:
    _MO2_AVAILABLE = False


def _this_module_file() -> str:
    return ""


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
    return Path(inspect.getfile(_this_module_file)).resolve().parent


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


def extract_icons_qt(
    organizer: "mobase.IOrganizer",
    textures_dir: Path,
    specs: List[ItemIconSpec],
    output_dir: Path,
    cell_size: int,
) -> Tuple[int, int, List[str]]:
    """Extract icons using QImage — no external dependencies, used by the MO2 plugin."""
    extracted = 0
    failed = 0
    warnings: List[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    supported = [fmt.data().decode() for fmt in QImageReader.supportedImageFormats()]
    if "dds" not in supported:
        warnings.append(f"[DIAG] DDS not supported by Qt. Supported formats: {supported}")

    by_texture: Dict[str, List[ItemIconSpec]] = {}
    for spec in specs:
        by_texture.setdefault(spec.texture, []).append(spec)

    for texture, texture_specs in sorted(by_texture.items()):
        real = _find_atlas(organizer, texture)
        atlas_path = real if real else textures_dir / Path(texture.replace("\\", "/")).with_suffix(".dds")
        reader = QImageReader(str(atlas_path))
        atlas = reader.read()
        if atlas.isNull():
            atlas = _load_dds_fallback(atlas_path) or QImage()
        if atlas.isNull():
            err = reader.errorString()
            dds_fmt = _dds_format(atlas_path)
            for spec in texture_specs:
                failed += 1
                warnings.append(f"Failed {spec.section_name} ({atlas_path}) [{dds_fmt}]: {err}")
            continue

        atlas_size = (atlas.width(), atlas.height())
        for spec in texture_specs:
            out_path = output_dir / f"{spec.section_name}.png"
            try:
                left, top, right, bottom = to_pixel_rect(spec, cell_size)
                validate_rect((left, top, right, bottom), atlas_size, spec.section_name, str(atlas_path))
                icon = atlas.copy(QRect(left, top, right - left, bottom - top))
                if not icon.save(str(out_path), "PNG"):
                    raise RuntimeError(f"QImage.save failed for {out_path}")
                extracted += 1
            except Exception as exc:
                failed += 1
                warnings.append(str(exc))

    return extracted, failed, warnings


def extract_icons_pil(
    textures_dir: Path,
    specs: List[ItemIconSpec],
    output_dir: Path,
    cell_size: int,
) -> Tuple[int, int, List[str]]:
    """Extract icons using Pillow — used for standalone execution."""
    extracted = 0
    failed = 0
    warnings: List[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    by_texture: Dict[str, List[ItemIconSpec]] = {}
    for spec in specs:
        by_texture.setdefault(spec.texture, []).append(spec)

    for texture, texture_specs in sorted(by_texture.items()):
        atlas_path = textures_dir / Path(texture.replace("\\", "/")).with_suffix(".dds")
        if not atlas_path.exists():
            for spec in texture_specs:
                failed += 1
                warnings.append(f"Atlas not found for {spec.section_name}: {atlas_path.absolute()}")
            continue

        with Image.open(atlas_path) as atlas:
            atlas_img = atlas.convert("RGBA")
            atlas_size = atlas_img.size

            for spec in texture_specs:
                out_path = output_dir / f"{spec.section_name}.png"
                try:
                    rect = to_pixel_rect(spec, cell_size)
                    validate_rect(rect, atlas_size, spec.section_name, str(atlas_path))
                    atlas_img.crop(rect).save(out_path, format="PNG")
                    extracted += 1
                except Exception as exc:
                    failed += 1
                    warnings.append(str(exc))

    return extracted, failed, warnings


if _MO2_AVAILABLE:
    def _find_atlas(organizer: mobase.IOrganizer, texture: str) -> Optional[Path]:
        rel = Path(texture.replace("\\", "/")).with_suffix(".dds")
        subdir = "/".join(rel.parts[:-1])
        for base in ("textures", "gamedata/textures"):
            search_path = f"{base}/{subdir}" if subdir else base
            results = organizer.findFiles(search_path, rel.name)
            if results:
                return Path(results[0])
        return None

    def _dds_format(path: Path) -> str:
        try:
            with path.open("rb") as f:
                if f.read(4) != b"DDS ":
                    return "not-DDS"
                hdr = f.read(124)
                pf_flags = struct.unpack_from("<I", hdr, 76)[0]
                fourcc   = struct.unpack_from("4s", hdr, 80)[0]
                if pf_flags & 0x4:
                    if fourcc == b"DX10":
                        dxgi = struct.unpack_from("<I", f.read(4), 0)[0]
                        return f"DX10/DXGI={dxgi}"
                    return fourcc.decode("ascii", errors="replace")
                rgb_bits = struct.unpack_from("<I", hdr, 84)[0]
                return f"uncompressed-{rgb_bits}bpp"
        except Exception as e:
            return f"read-error({e})"

    # Maps DXGI format numbers (from DX10 header) to legacy FourCC equivalents
    _DXGI_TO_FOURCC = {
        **{v: b"DXT1" for v in (70, 71, 72)},   # BC1 typeless/unorm/srgb
        **{v: b"DXT3" for v in (73, 74, 75)},   # BC2 typeless/unorm/srgb
        **{v: b"DXT5" for v in (76, 77, 78)},   # BC3 typeless/unorm/srgb
    }

    def _load_dds_fallback(path: Path) -> Optional["QImage"]:
        """Pure-Python DXT1/DXT3/DXT5 decoder — fallback when QImageReader can't handle the DDS variant."""
        try:
            with path.open("rb") as f:
                if f.read(4) != b"DDS ":
                    return None
                hdr = f.read(124)
                height   = struct.unpack_from("<I", hdr,  8)[0]
                width    = struct.unpack_from("<I", hdr, 12)[0]
                pf_flags = struct.unpack_from("<I", hdr, 76)[0]
                fourcc   = struct.unpack_from("4s", hdr, 80)[0]

                if not (pf_flags & 0x4):
                    return None

                if fourcc == b"DX10":
                    dx10_hdr = f.read(20)
                    dxgi_fmt = struct.unpack_from("<I", dx10_hdr, 0)[0]
                    fourcc = _DXGI_TO_FOURCC.get(dxgi_fmt)
                    if fourcc is None:
                        return None
                elif fourcc not in (b"DXT1", b"DXT3", b"DXT5"):
                    return None

                data = f.read()

            bw = (width  + 3) // 4
            bh = (height + 3) // 4
            pixels = bytearray(width * height * 4)
            block_size = 8 if fourcc == b"DXT1" else 16
            offset = 0

            def c565(v):
                return ((v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)

            for by in range(bh):
                for bx in range(bw):
                    blk = data[offset: offset + block_size]
                    offset += block_size

                    alpha = [255] * 16
                    color_off = 0

                    if fourcc == b"DXT5":
                        a0, a1 = blk[0], blk[1]
                        bits48 = int.from_bytes(blk[2:8], "little")
                        if a0 > a1:
                            apal = [a0, a1,
                                    (6*a0+a1)//7, (5*a0+2*a1)//7,
                                    (4*a0+3*a1)//7, (3*a0+4*a1)//7,
                                    (2*a0+5*a1)//7, (a0+6*a1)//7]
                        else:
                            apal = [a0, a1,
                                    (4*a0+a1)//5, (3*a0+2*a1)//5,
                                    (2*a0+3*a1)//5, (a0+4*a1)//5,
                                    0, 255]
                        alpha = [apal[(bits48 >> (i * 3)) & 7] for i in range(16)]
                        color_off = 8
                    elif fourcc == b"DXT3":
                        bits64 = int.from_bytes(blk[0:8], "little")
                        alpha = [((bits64 >> (i * 4)) & 0xF) * 17 for i in range(16)]
                        color_off = 8

                    c0, c1 = struct.unpack_from("<HH", blk, color_off)
                    cbits  = struct.unpack_from("<I",  blk, color_off + 4)[0]
                    r0, g0, b0 = c565(c0)
                    r1, g1, b1 = c565(c1)

                    if c0 > c1 or fourcc != b"DXT1":
                        pal4 = [(r0,g0,b0),(r1,g1,b1),
                                ((2*r0+r1)//3,(2*g0+g1)//3,(2*b0+b1)//3),
                                ((r0+2*r1)//3,(g0+2*g1)//3,(b0+2*b1)//3)]
                    else:
                        pal4 = [(r0,g0,b0),(r1,g1,b1),
                                ((r0+r1)//2,(g0+g1)//2,(b0+b1)//2),(0,0,0)]
                        alpha = [0 if ((cbits >> (i*2)) & 3) == 3 else alpha[i] for i in range(16)]

                    for i in range(16):
                        px = bx * 4 + (i % 4)
                        py = by * 4 + (i // 4)
                        if px >= width or py >= height:
                            continue
                        r, g, b = pal4[(cbits >> (i * 2)) & 3]
                        pos = (py * width + px) * 4
                        pixels[pos]   = r
                        pixels[pos+1] = g
                        pixels[pos+2] = b
                        pixels[pos+3] = alpha[i]

            return QImage(bytes(pixels), width, height, width * 4, QImage.Format_RGBA8888)
        except Exception:
            return None

    class IconExtractorPlugin(mobase.IPluginTool):

        def __init__(self):
            super().__init__()
            self._organizer: Optional[mobase.IOrganizer] = None
            self._parent = None

        def init(self, organizer: mobase.IOrganizer) -> bool:
            self._organizer = organizer
            return True

        def name(self) -> str:
            return "StalkerAnomalyIconExtractor"

        def author(self) -> str:
            return "SaloEater"

        def description(self) -> str:
            return "Extracts weapon and outfit icons from STALKER Anomaly texture atlases."

        def version(self) -> mobase.VersionInfo:
            return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

        def isActive(self) -> bool:
            return True

        def settings(self) -> List[mobase.PluginSetting]:
            return []

        def displayName(self) -> str:
            return "Extract Weapon && Outfit Icons"

        def tooltip(self) -> str:
            return "Extracts weapon and outfit icons from STALKER Anomaly texture atlases."

        def icon(self) -> QIcon:
            return QIcon()

        def setParentWidget(self, widget) -> None:
            self._parent = widget

        def display(self) -> None:
            game_dir = Path(self._organizer.managedGame().gameDirectory().absolutePath())
            plugin_dir = Path(inspect.getfile(_this_module_file)).resolve().parent
            repo_root = plugin_dir.parent
            csv_path = repo_root / "data" / "export_item_icons.csv"
            textures_dir = game_dir / "gamedata" / "textures"
            output_dir = repo_root / "scripts" / "img-data" / "icons"

            mo2_dir = Path(sys.executable).parent
            QCoreApplication.addLibraryPath(str(mo2_dir / "plugins"))
            QCoreApplication.addLibraryPath(str(mo2_dir))

            if not csv_path.exists():
                QMessageBox.critical(self._parent, "Error", f"CSV not found:\n{csv_path}")
                return

            specs = read_icon_specs_from_csv(csv_path)
            if not specs:
                QMessageBox.critical(self._parent, "Error", "No icon specs found in CSV.")
                return

            extracted, failed, warnings = extract_icons_qt(
                self._organizer, textures_dir, specs, output_dir, DEFAULT_CELL_SIZE
            )

            log_path = Path(self._organizer.basePath()) / "logs" / "icon_extractor.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as lf:
                lf.write(f"CSV:          {csv_path}\n")
                lf.write(f"Textures dir: {textures_dir}\n")
                lf.write(f"Output dir:   {output_dir}\n")
                lf.write(f"Extracted: {extracted}  Failed: {failed}  Total: {len(specs)}\n")

                for diag_dir in ["", "gamedata", "textures", "textures/ui", "gamedata/textures", "gamedata/textures/ui"]:
                    results = self._organizer.findFiles(diag_dir, lambda f: True)
                    lf.write(f"\nfindFiles({diag_dir!r}) → {len(results)} results:\n")
                    for r in results:
                        lf.write(f"  {r}\n")

                if warnings:
                    lf.write(f"\nWarnings ({len(warnings)}):\n")
                    for w in warnings:
                        lf.write(f"  {w}\n")

            msg = (
                f"Extracted: {extracted}\n"
                f"Failed:    {failed}\n"
                f"Total:     {len(specs)}\n\n"
                f"Output:\n{output_dir}\n\n"
                f"Log:\n{log_path}"
            )
            if warnings:
                msg += f"\n\nWarnings ({len(warnings)}):\n" + "\n".join(warnings[:20])
                if len(warnings) > 20:
                    msg += f"\n... and {len(warnings) - 20} more (see log)"

            QMessageBox.information(self._parent, "Done", msg)

    def createPlugin() -> mobase.IPluginTool:
        return IconExtractorPlugin()


def main() -> int:
    if not _PIL_AVAILABLE:
        print("[ERROR] Pillow not installed. Run: pip install Pillow", file=sys.stderr)
        return 1

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

    extracted, failed, warnings = extract_icons_pil(textures_dir, specs, output_dir, DEFAULT_CELL_SIZE)

    log_path = output_dir / "extract.log"
    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"CSV:          {csv_path}\n")
        lf.write(f"Textures dir: {textures_dir}\n")
        lf.write(f"Output dir:   {output_dir}\n")
        lf.write(f"Extracted: {extracted}  Failed: {failed}  Total: {len(specs)}\n")
        if warnings:
            lf.write(f"\nWarnings ({len(warnings)}):\n")
            for w in warnings:
                lf.write(f"  {w}\n")

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    print(f"Extracted: {extracted}")
    print(f"Failed:    {failed}")
    print(f"Total:     {len(specs)}")
    print(f"Log:       {log_path}")

    return 0


