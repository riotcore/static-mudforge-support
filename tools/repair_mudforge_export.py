#!/usr/bin/env python3
"""Repair Stillwake terrain inside a *copy* of a MudForge Map Data JSON export.

This tool does not talk to the game, import a map, or touch a map database.
No non-terrain field is changed. The user must inspect/import the new file.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "stillwake-terrain-v1.json"
EXPECTED_TERRAIN = {
    "promenade": 49, "city": 33, "dock": 3, "ferry": 3,
    "marina": 3, "beach": 14, "boardwalk": 11,
}


def load_manifest() -> dict[int, str]:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parsed: dict[int, str] = {}
    counts: dict[str, int] = {}
    for key, ids in document["terrainByType"].items():
        assert key in EXPECTED_TERRAIN, ("unknown terrain", key)
        for number in ids:
            assert isinstance(number, int) and not isinstance(number, bool)
            assert 10000 <= number <= 10853
            assert number not in parsed, ("duplicate room", number)
            parsed[number] = key
            counts[key] = counts.get(key, 0) + 1
    assert counts == EXPECTED_TERRAIN, ("incorrect terrain counts", counts)
    assert len(parsed) == 116
    return parsed


def room_id(room: dict) -> int | None:
    value = room.get("num", room.get("vnum"))
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    return None


def is_stillwake_room(room: dict) -> bool:
    """Only touch known world/area names; a matching VNUM alone is not enough."""
    for field in ("zone", "area", "map_plane", "map_area"):
        value = room.get(field)
        if isinstance(value, str) and "stillwake" in value.lower():
            return True
    return False


def repair(document: dict, terrain: dict[int, str]) -> tuple[dict, dict]:
    if not isinstance(document, dict) or not isinstance(document.get("rooms"), list):
        raise ValueError("Not a supported MudForge Map Data export (missing rooms array)")
    fixed = copy.deepcopy(document)
    seen: set[int] = set()
    matched = changed = unchanged = 0
    foreign = []
    edited = []

    for room in fixed["rooms"]:
        if not isinstance(room, dict):
            raise ValueError("Invalid room record in Map Data export")
        vid = room_id(room)
        if vid is None:
            continue
        if vid in seen:
            raise ValueError(f"Duplicate room VNUM in export: {vid}")
        seen.add(vid)
        target = terrain.get(vid)
        if target is None:
            continue
        if not is_stillwake_room(room):
            foreign.append(vid)
            continue
        matched += 1
        if "terrain" not in room or not isinstance(room["terrain"], str):
            raise ValueError(f"Mapped Stillwake room {vid} lacks a string terrain field")
        if room["terrain"] == target:
            unchanged += 1
        else:
            edited.append([vid, room["terrain"], target])
            room["terrain"] = target
            changed += 1

    if not matched:
        raise ValueError(
            "No confirmed Stillwake rooms found. Export the correct MudForge "
            "map database; no output created."
        )

    # This is an essential integrity check, not an estimate: every value
    # EXCEPT selected room.terrain is exactly the original Python JSON value.
    expected = copy.deepcopy(document)
    original_by_vnum = {room_id(r): r for r in expected["rooms"]}
    for room in fixed["rooms"]:
        vid = room_id(room)
        if vid in terrain and vid in original_by_vnum and is_stillwake_room(room):
            original_by_vnum[vid]["terrain"] = room["terrain"]
    if fixed != expected:
        raise AssertionError("Integrity failure: a non-terrain map field changed")

    report = {
        "total_exported_rooms": len(fixed["rooms"]),
        "known_nonroad_rooms": len(terrain),
        "mapped_stillwake_rooms_matched": matched,
        "terrain_values_changed": changed,
        "already_correct": unchanged,
        "unmapped_known_rooms": len(terrain) - matched,
        "matching_vnums_in_other_worlds_skipped": foreign,
        "changes": edited,
        "all_coordinates_exits_names_settings_notes_preserved": True,
    }
    return fixed, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Original MudForge Map Data export .json")
    parser.add_argument("--output", type=Path, help="Output path (must not exist)")
    parser.add_argument("--dry-run", action="store_true", help="Report proposed changes, do not write")
    args = parser.parse_args(argv)
    path = args.export.expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".json":
        parser.error("export must be an existing .json file")
    try:
        original = path.read_bytes()
        doc = json.loads(original)
        updated, report = repair(doc, load_manifest())
    except (ValueError, AssertionError, KeyError, TypeError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 2
    print("=== STILLWAKE TERRAIN-ONLY MAP REPAIR ===")
    print(f"Input: {path}")
    print(f"Input SHA-256: {hashlib.sha256(original).hexdigest()}")
    print(json.dumps({k: v for k, v in report.items() if k != "changes"}, indent=2))
    for vid, previous, new in report["changes"][:15]:
        print(f"  {vid}: {previous} -> {new}")
    if len(report["changes"]) > 15:
        print(f"  ... and {len(report['changes']) - 15} more terrain values")
    if args.dry_run:
        print("DRY RUN: nothing written.")
        return 0
    out = args.output or path.with_name(path.stem + "-STILLWAKE-TERRAIN-FIXED.json")
    out = out.expanduser().resolve()
    if out == path:
        print("STOP: output must not overwrite original export", file=sys.stderr)
        return 2
    data = (json.dumps(updated, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        # Exclusive create: no accidental overwrite, even after a race.
        with out.open("xb") as handle:
            handle.write(data)
    except OSError as error:
        print(f"STOP: cannot safely create output: {error}", file=sys.stderr)
        return 2
    print(f"Created: {out}")
    print(f"Output SHA-256: {hashlib.sha256(data).hexdigest()}")
    print("Original export remains unchanged. Inspect the output before importing it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
