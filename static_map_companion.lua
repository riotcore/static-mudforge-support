-- Public STATIC / Stillwake MudForge companion.
-- Read-only GMCP diagnostics. Never touches map topology or player data.
plugin = {
    id = "stillwake-map-companion",
    name = "Stillwake Map Companion",
    version = "1.0.0",
    author = "STATIC",
    description = "Read-only Stillwake GMCP terrain diagnostics for MudForge"
}

local last_room = false

local function value_or(value, fallback)
    if value == nil or value == false or value == "" then
        return fallback
    end
    return tostring(value)
end

local function current_room()
    local value = getGMCPData("Room.Info")
    if type(value) == "table" then
        return value
    end
    if type(last_room) == "table" then
        return last_room
    end
    return false
end

local function diagnostics()
    print("Stillwake Map Companion v" .. plugin.version .. " (read-only)")
    if type(utilprint) == "function" then
        utilprint("[Stillwake] Map companion active. See plugin output for GMCP details.")
    end
    local room = current_room()
    if type(room) ~= "table" then
        print("No GMCP Room.Info received yet. Check connection and GMCP settings.")
        return
    end
    local vnum = value_or(room.num or room.vnum, "?")
    local title = value_or(room.name, "?")
    local terrain = value_or(room.terrain or room.environment, "?")
    local zone = value_or(room.zone or room.area, "?")
    local plane = value_or(room.map_plane, "?")
    print("Room " .. vnum .. ": " .. title)
    print("GMCP zone " .. zone .. " | map_plane " .. plane)
    print("Authoritative terrain " .. terrain .. " | source "
          .. value_or(room.terrain_source, "?"))
    print("If MudForge displays a different saved terrain, export the map,")
    print("run the bundled terrain-only repair, then import the copy.")
    print("This plugin never edits room records or sends MUD commands.")
end

registerCommand("swmap", function(_args)
    diagnostics()
end, "Show Stillwake GMCP terrain without editing the map")

onGMCPUpdate("Room.Info", function(data)
    last_room = type(data) == "table" and data or false
end)

function init()
    print("Stillwake Map Companion v" .. plugin.version
        .. " loaded. Type /swmap for GMCP diagnostics.")
    if type(utilprint) == "function" then
        utilprint("[Stillwake] Map companion loaded. Type /swmap.")
    end
end

function onConnect()
    last_room = false
end

function onDisconnect()
    last_room = false
end

function cleanup()
    -- No state is stored, and no map database is opened or modified.
end
