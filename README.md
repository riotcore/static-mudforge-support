# Stillwake Map Companion for MudForge

This is a **standalone, public-repository-ready client package**, not the
private STATIC 2.0 game source. It contains no room descriptions, game code,
player saves, credentials, account data, or map export. Only a tiny read-only
MudForge Lua plugin, a terrain color pack, and an offline terrain fix tool.

## What it does

- **Stillwake Map Companion 1.0.0** shows GMCP `Room.Info` terrain and map
  identity when you type `/swmap` in the MudForge terminal. It makes *zero*
  map API calls and does not send any game commands. Look for a load message
  after installation; if `/swmap` is silent, the plugin isn't loaded.
- **Terrain colors** define `dock`, `ferry`, `marina`, `promenade`, `beach`,
  `boardwalk` and other allowed STATIC map terrain keys.
- **Optional export repair** corrects terrain only for previously mapped
  Stillwake tiles using **a copy of MudForge's full Map Data export**. It
  preserves room IDs, names, coordinates, exits, notes and settings. It is
  safer than `updateMapRoom(id, {terrain=...})`, which some client versions
  implement as a record replacement, not a partial patch.

**No rewalking, zone deletion, new VNUMs or server copyover is needed.**

## Troubleshoot: repository validated but plugin is missing

**Validating/adding a repository is not the same as installing a plugin.**
A green "Found 1 plugin" response establishes that the catalog is readable,
but does not prove that Stillwake Map Companion is enabled in the current
MudForge client. In the plugin manager, switch to its **browse/available**
plugins view (rather than only installed plugins), clear search/category
filters, and locate **Stillwake Map Companion** under the STATIC / Stillwake
source. Install and enable it. The command `/swmap` must print the version
and diagnostics. If the MUD replies `Unknown command`, the client did not
intercept `/swmap`; do not ask the MUD server to be updated.

If the repository still does not appear in your client, skip the repository
browser entirely and import `static_map_companion.lua` from this package
via MudForge's local-plugin import/editor. Do not import the terrain JSON as
a Lua plugin; import it separately in the map's terrain color settings.
The CLI output is a read-only diagnostic, not an automatic map repair.
Never reset the map to troubleshoot a missing plugin.

## Install the plugin now (download ZIP, no GitHub required)

1. Extract the ZIP. In MudForge, go to **Settings -> Plugins** and use the
   local plugin import/editor to install **`static_map_companion.lua`**.
   Enable it. It is independent of the older STATIC support plugin.
2. It should announce `Stillwake Map Companion v1.0.0 loaded`. Enter
   `/swmap` in MudForge's client terminal. It displays the current GMCP
   terrain. It does **not** itself rewrite saved map tiles.
3. Import `stillwake_terrain_pack.json` from the map's **Terrain Colors**
   settings. An unknown custom terrain may otherwise use a default color.

If using the old STATIC Support Pack v0.3.1, **do not run `/static terrain`**
with this release. That historical command used a terrain-only `updateMapRoom`
call; public integration experience suggests some MudForge builds replace
whole room records, so we cannot certify it safe for a mapped city.

## Repair old terrain labels without remapping

1. In MudForge, select the correct Stillwake map database. In the **Map**
   panel's `...` menu, select **Export Map Data**. Keep that downloaded export.
   Do not choose a layout/settings export instead.
2. From a terminal with Python 3, run:

   ```bash
   python3 tools/repair_mudforge_export.py '/path/to/map-data-export.json' --dry-run
   python3 tools/repair_mudforge_export.py '/path/to/map-data-export.json'
   ```

3. The tool creates `map-data-export-STILLWAKE-TERRAIN-FIXED.json` beside the
   original, leaving your export untouched. Inspect its report first: it
   should find existing Stillwake rooms and confirm no non-terrain field
   changed. It will not create any room that wasn't mapped already.
4. Back in MudForge's map panel, use **Import Map Data** on the *new* file,
   then restart MudForge if the map view is stale. This imports a complete
   copy of your map, not a new map generated from geometry. Preserve the
   original export until you have inspected your existing map successfully.

The 116 non-road room identifiers are in `stillwake-terrain-v1.json`.
Only existing rooms in a map export whose `zone`/`area` identifies Stillwake
are patched. The 738 proper `road` rooms remain roads.

## Publish as a **separate public GitHub repository**

Intended repository: `riotcore/static-mudforge-support` (separate from the
private `riotcore/Static2.0`). **A local ZIP is not a live GitHub repository.**

1. Create a new, **public**, empty GitHub repository named
   `static-mudforge-support` under `riotcore` (do **not** initialize it with
   a README, since one is included here).
2. Upload the contents of this extracted folder, preserving the `dist/`,
   `github.com/`, and `tools/` folders, or use the optional
   `publish_to_github.sh` after authenticating GitHub CLI (`gh auth login`).
3. After upload, in MudForge **Settings -> Plugins -> Add Repository**, enter:

   ```text
   https://raw.githubusercontent.com/riotcore/static-mudforge-support/main/github.com/plugins.json
   ```

   The literal `github.com` path segment accommodates MudForge's current
   repository URL validator while preserving raw GitHub CORS delivery.
4. Install **Stillwake Map Companion** from the repository. The catalog's
   download URL, SHA-256 and size are already generated for this repository.

If you use a **different** GitHub owner or repository name, update both
`plugins.json` files' `downloadUrl` and `homepage` fields, then recompute the
catalog for the same package. Never publicly upload a live map export or
anything from the private game checkout.

## Contents

- `dist/stillwake-map-companion.json` - plugin package used by the catalog
- `github.com/plugins.json` - MudForge Add Repository entry point
- `plugins.json` - plain catalog mirror
- `static_map_companion.lua` - manual plugin install
- `stillwake_terrain_pack.json` - custom terrain colors
- `stillwake-terrain-v1.json` - 116 public non-road VNUM-to-terrain entries
- `tools/repair_mudforge_export.py` - optional offline, terrain-only map repair
- `tools/test_terrain_repair.py` - repeatable integrity tests
- `publish_to_github.sh` - optional GitHub CLI publisher
- `LICENSE` - MIT license for these stand-alone client helpers

## Safety

No login or GitHub token is stored in this package. The Lua plugin never
opens a database or calls `updateMapRoom`, `addMapRoom`, or `setMapExit`.
The Python repair tool edits only the `terrain` fields of already-existing
Stillwake rooms inside a **new exported JSON file**. Other JSON fields are
compared deeply for exact equality before the new file is created.
