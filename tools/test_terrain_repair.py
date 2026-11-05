#!/usr/bin/env python3
"""Integrity and package contract tests for public MudForge-only files."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from repair_mudforge_export import load_manifest, repair

ROOT = Path(__file__).resolve().parents[1]


def sample_export():
    return {
        "rooms": [
            {"num": 10114, "name": "Working Fishing Dock", "zone": "Stillwake City",
             "terrain": "road", "x": 4, "y": 22, "z": 0,
             "exits": {"n": 10113, "s": 10115}, "lastVisited": 123456789,
             "timesVisited": 8, "userData": {"user.note": "Do not touch"}},
            {"num": 10432, "name": "Whalebone Walk and Spindle Avenue",
             "zone": "Stillwake City", "terrain": "road", "x": 17, "y": 26,
             "z": 0, "exits": {"n": 10423, "e": 10433, "s": 10468}},
            {"num": 10100, "zone": "Stillwake City", "terrain": "promenade",
             "exits": {}, "x": 0, "y": 0, "z": 0},
            {"num": 10001, "zone": "Stillwake City", "terrain": "road",
             "exits": {"s": 10000}, "x": 11, "y": 12, "z": 0},
            {"num": 3000, "zone": "Another World", "terrain": "forest"},
        ],
        "settings": {"terrainStyles": [{"name": "road", "color": "#111111"}],
                     "zoom": 1.1, "mapMode": "tiles"},
        "state": {"levels": {}, "currentLevel": 0, "currentRoom": None},
        "labels": [{"text": "Private label", "x": 4}],
        "extras": {"user_settings": {"secret-not-published": "preserved"}},
    }


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.terrain = load_manifest()

    def test_manifest(self):
        self.assertEqual(len(self.terrain), 116)
        self.assertEqual(self.terrain[10114], "dock")
        self.assertEqual(self.terrain[10272], "ferry")
        self.assertEqual(self.terrain[10616], "marina")
        self.assertEqual(self.terrain[10432], "promenade")

    def test_original_unchanged_and_only_terrain_modified(self):
        original = sample_export()
        before = copy.deepcopy(original)
        altered, report = repair(original, self.terrain)
        self.assertEqual(original, before)
        self.assertEqual(report["terrain_values_changed"], 2)
        self.assertEqual(report["already_correct"], 1)
        self.assertEqual(report["mapped_stillwake_rooms_matched"], 3)
        for old, new in zip(before["rooms"], altered["rooms"]):
            expected = copy.deepcopy(old)
            if old["num"] in self.terrain and old["zone"] == "Stillwake City":
                expected["terrain"] = self.terrain[old["num"]]
            self.assertEqual(expected, new)
        self.assertEqual(altered["settings"], original["settings"])
        self.assertEqual(altered["labels"], original["labels"])
        self.assertEqual(altered["state"], original["state"])
        self.assertEqual(altered["extras"], original["extras"])

    def test_other_game_vnum_untouched(self):
        document = {"rooms": [{"num": 10114, "zone": "Another Game", "terrain": "road"},
                              {"num": 10115, "zone": "Stillwake City", "terrain": "road"}]}
        fixed, report = repair(document, self.terrain)
        self.assertEqual(fixed["rooms"][0]["terrain"], "road")
        self.assertEqual(fixed["rooms"][1]["terrain"], "dock")
        self.assertEqual(report["matching_vnums_in_other_worlds_skipped"], [10114])

    def test_fails_closed_on_unknown_export(self):
        with self.assertRaisesRegex(ValueError, "Map Data export"):
            repair({"settings": {}}, self.terrain)
        with self.assertRaisesRegex(ValueError, "No confirmed Stillwake"):
            repair({"rooms": [{"num": 10114, "zone": "Another Game", "terrain": "road"}]}, self.terrain)

    def test_duplicate_room_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate room VNUM"):
            repair({"rooms": [
                {"num": 10432, "zone": "Stillwake City", "terrain": "road"},
                {"num": 10432, "zone": "Stillwake City", "terrain": "road"}]}, self.terrain)

    def test_full_city(self):
        rooms = []
        for vnum in range(10000, 10854):
            rooms.append({"num": vnum, "name": f"Room {vnum}",
                          "zone": "Stillwake City", "terrain": "road",
                          "x": vnum-10000, "y": 2, "z": 0,
                          "exits": {"e": vnum+1} if vnum < 10853 else {},
                          "userData": {"custom": vnum}})
        export = {"rooms": rooms, "settings": {"maxRooms": 10000}}
        altered, report = repair(export, self.terrain)
        self.assertEqual(report["terrain_values_changed"], 116)
        self.assertEqual(report["unmapped_known_rooms"], 0)
        self.assertEqual(len(altered["rooms"]), 854)
        self.assertEqual(sum(r["terrain"]=="road" for r in altered["rooms"]), 738)
        for old, new in zip(export["rooms"], altered["rooms"]):
            self.assertEqual(old["num"], new["num"])
            self.assertEqual(old["exits"], new["exits"])
            self.assertEqual((old["x"],old["y"],old["z"]),
                             (new["x"],new["y"],new["z"]))

    def test_cli_writes_new_file_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"map-data.json"
            source.write_text(json.dumps(sample_export()))
            original=source.read_bytes()
            script=ROOT/"tools/repair_mudforge_export.py"
            preview=subprocess.run([sys.executable,str(script),str(source),"--dry-run"],
                                   capture_output=True,text=True)
            self.assertEqual(preview.returncode,0,preview.stderr)
            self.assertEqual(len(list(Path(tmp).iterdir())),1)
            actual=subprocess.run([sys.executable,str(script),str(source)],capture_output=True,text=True)
            self.assertEqual(actual.returncode,0,actual.stderr)
            target=Path(tmp)/"map-data-STILLWAKE-TERRAIN-FIXED.json"
            self.assertTrue(target.is_file())
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(json.loads(target.read_text())["rooms"][0]["terrain"],"dock")
            second=subprocess.run([sys.executable,str(script),str(source)],capture_output=True,text=True)
            self.assertEqual(second.returncode,2)
            self.assertIn("cannot safely create", second.stderr)

    def test_package_catalog_consistency(self):
        pkg_bytes=(ROOT/"dist/stillwake-map-companion.json").read_bytes()
        pkg=json.loads(pkg_bytes)
        lua=(ROOT/"static_map_companion.lua").read_text()
        self.assertEqual(pkg["script"],lua)
        self.assertEqual(pkg["version"],"1.0.0")
        self.assertIn('registerCommand("swmap"',lua)
        self.assertIn('getGMCPData("Room.Info")',lua)
        for dangerous in ("updateMapRoom(","addMapRoom(","setMapExit(","send(","Send(","openDatabase("):
            self.assertNotIn(dangerous,lua)
        catalog_a=(ROOT/"plugins.json").read_bytes()
        catalog_b=(ROOT/"github.com/plugins.json").read_bytes()
        self.assertEqual(catalog_a,catalog_b)
        catalog=json.loads(catalog_a)
        self.assertEqual(len(catalog["plugins"]),1)
        entry=catalog["plugins"][0]
        self.assertEqual(entry["sha256"],hashlib.sha256(pkg_bytes).hexdigest())
        self.assertEqual(entry["size"],len(pkg_bytes))
        self.assertEqual(entry["version"],pkg["version"])
        self.assertIn("riotcore/static-mudforge-support/main",entry["downloadUrl"])
        self.assertNotIn("Static2.0/main",entry["downloadUrl"])
        color=json.loads((ROOT/"stillwake_terrain_pack.json").read_text())
        self.assertTrue({"dock","ferry","marina","promenade","beach","boardwalk"}.issubset(
            {r["name"] for r in color["terrainStyles"]}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
