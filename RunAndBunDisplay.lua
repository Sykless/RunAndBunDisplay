-- Credits for most of memory reading logic : https://drive.google.com/drive/folders/1M-PdZrACBkGPpceTanCq_ltbGNT24lR8

local lastTime = os.clock()

local terminator = 0xFF
local monNameLength = 10
local speciesNameLength = 11
local playerNameLength = 10
local boxMonSize = 80
local partyMonSize = 100
local partyloc = 0x2023a98 --gPlayerParty
local partyCount = 0x2023a95 --gPlayerPartyCount
local storageLoc = 0x2028848 -- gPokemonStorage
local speciesNameTable = 0x3185c8

local defeatedTrainersStart = 0X020262DD
local defeatedTrainersEnd = 0x020263ED
local pickedStarterAddress = 0x02026442 -- 0 Turtwig / 1 Chimchar / 2 Piplup

function slowCurve(n)
    return math.floor((5*(n^3))/4)
end
function fastCurve(n)
    return math.floor((4*(n^3))/5)
end
function medfastCurve(n)
    return n^3
end
function medslowCurve(n)
    return math.floor((6 * (n)^3) / 5) - (15 * (n)^2) + (100 * n) - 140
end
function erraticCurve(n)
    if (n<=50) then
        return math.floor(((100 - n)*n^3)/50)
    end
    if (n<=68) then
        return math.floor(((150 - n)*n^3)/100)
    end
    if (n<=98) then
        return math.floor(math.floor((1911 - 10 * n) / 3) * n^3 / 500)
    end
    return math.floor((160 - n) * n^3 / 100)
end
function flutuatingCurve(n)
	if (n<15) then
	  return math.floor((math.floor((n + 1) / 3) + 24) * n^3 / 50)
	end
	if (n<=36) then
		return math.floor((n + 14) * n^3 / 50)
	end
	return math.floor((math.floor(n / 2) + 32) * n^3 / 50)
end

function calcLevel(exp, species)
	level = 1
	while (exp>=expRequired(species,level+1)) do
		level=level+1
	end
	return level
end

function expRequired(species,level)
	expCurve = curve[species]
	if (expCurve == 0) then return medfastCurve(level) end
	if (expCurve == 1) then return erraticCurve(level) end
	if (expCurve == 2) then return flutuatingCurve(level) end
	if (expCurve == 3) then return medslowCurve(level) end
	if (expCurve == 4) then return fastCurve(level) end
	if (expCurve == 5) then return slowCurve(level) end
end

function readBoxMon(address)
	local mon = {}
	mon.personality = emu:read32(address + 0)
	mon.otId = emu:read32(address + 4)
	mon.nickname = emu:readRange(address + 8, monNameLength)
	mon.language = emu:read8(address + 18)
	local flags = emu:read8(address + 19)
	mon.isBadEgg = flags & 1
	mon.hasSpecies = (flags >> 1) & 1
	mon.isEgg = (flags >> 2) & 1
	mon.otName = emu:readRange(address + 20, playerNameLength)
	mon.markings = emu:read8(address + 27)

	local key = mon.otId ~ mon.personality
	local substructSelector = {
		[ 0] = {0, 1, 2, 3},
		[ 1] = {0, 1, 3, 2},
		[ 2] = {0, 2, 1, 3},
		[ 3] = {0, 3, 1, 2},
		[ 4] = {0, 2, 3, 1},
		[ 5] = {0, 3, 2, 1},
		[ 6] = {1, 0, 2, 3},
		[ 7] = {1, 0, 3, 2},
		[ 8] = {2, 0, 1, 3},
		[ 9] = {3, 0, 1, 2},
		[10] = {2, 0, 3, 1},
		[11] = {3, 0, 2, 1},
		[12] = {1, 2, 0, 3},
		[13] = {1, 3, 0, 2},
		[14] = {2, 1, 0, 3},
		[15] = {3, 1, 0, 2},
		[16] = {2, 3, 0, 1},
		[17] = {3, 2, 0, 1},
		[18] = {1, 2, 3, 0},
		[19] = {1, 3, 2, 0},
		[20] = {2, 1, 3, 0},
		[21] = {3, 1, 2, 0},
		[22] = {2, 3, 1, 0},
		[23] = {3, 2, 1, 0},
	}

	local pSel = substructSelector[mon.personality % 24]
	local ss0 = {}
	local ss1 = {}
	local ss2 = {}
	local ss3 = {}

	for i = 0, 2 do
		ss0[i] = emu:read32(address + 32 + pSel[1] * 12 + i * 4) ~ key
		ss1[i] = emu:read32(address + 32 + pSel[2] * 12 + i * 4) ~ key
		ss2[i] = emu:read32(address + 32 + pSel[3] * 12 + i * 4) ~ key
		ss3[i] = emu:read32(address + 32 + pSel[4] * 12 + i * 4) ~ key
	end

	mon.species = ss0[0] & 0xFFFF
	mon.heldItem = ss0[0] >> 16
	mon.experience = ss0[1]
	mon.ppBonuses = ss0[2] & 0xFF
	mon.friendship = (ss0[2] >> 8) & 0xFF
	mon.hiddenNature = (ss0[2] >> 16) & 0x1F

	mon.moves = {
		ss1[0] & 0xFFFF,
		ss1[0] >> 16,
		ss1[1] & 0xFFFF,
		ss1[1] >> 16
	}
	mon.pp = {
		ss1[2] & 0xFF,
		(ss1[2] >> 8) & 0xFF,
		(ss1[2] >> 16) & 0xFF,
		ss1[2] >> 24
	}

	mon.hpEV = ss2[0] & 0xFF
	mon.attackEV = (ss2[0] >> 8) & 0xFF
	mon.defenseEV = (ss2[0] >> 16) & 0xFF
	mon.speedEV = ss2[0] >> 24
	mon.spAttackEV = ss2[1] & 0xFF
	mon.spDefenseEV = (ss2[1] >> 8) & 0xFF
	mon.cool = (ss2[1] >> 16) & 0xFF
	mon.beauty = ss2[1] >> 24
	mon.cute = ss2[2] & 0xFF
	mon.smart = (ss2[2] >> 8) & 0xFF
	mon.tough = (ss2[2] >> 16) & 0xFF
	mon.sheen = ss2[2] >> 24

	mon.pokerus = ss3[0] & 0xFF
	mon.metLocation = (ss3[0] >> 8) & 0xFF
	flags = ss3[0] >> 16
	mon.metLevel = flags & 0x7F
	mon.metGame = (flags >> 7) & 0xF
	mon.pokeball = (flags >> 11) & 0xF
	mon.otGender = (flags >> 15) & 0x1
	flags = ss3[1]
	mon.hpIV = (flags >> 1) & 0x1F
	mon.attackIV = (flags >> 6) & 0x1F
	mon.defenseIV = (flags >> 11) & 0x1F
	mon.speedIV = (flags >> 16) & 0x1F
	mon.spAttackIV = (flags >> 21) & 0x1F
	mon.spDefenseIV = (flags >> 26) & 0x1F
	-- Bit 30 is another "isEgg" bit
	flags = ss3[2]
	mon.coolRibbon = flags & 7
	mon.beautyRibbon = (flags >> 3) & 7
	mon.cuteRibbon = (flags >> 6) & 7
	mon.smartRibbon = (flags >> 9) & 7
	mon.toughRibbon = (flags >> 12) & 7
	mon.championRibbon = (flags >> 15) & 1
	mon.winningRibbon = (flags >> 16) & 1
	mon.victoryRibbon = (flags >> 17) & 1
	mon.artistRibbon = (flags >> 18) & 1
	mon.effortRibbon = (flags >> 19) & 1
	mon.marineRibbon = (flags >> 20) & 1
	mon.landRibbon = (flags >> 21) & 1
	mon.skyRibbon = (flags >> 22) & 1
	mon.countryRibbon = (flags >> 23) & 1
	mon.nationalRibbon = (flags >> 24) & 1
	mon.earthRibbon = (flags >> 25) & 1
	mon.worldRibbon = (flags >> 26) & 1
	mon.altAbility = (flags >> 29) & 3
	return mon
end

function readPartyMon(address)
	local mon = readBoxMon(address)
	mon.status = emu:read32(address + 80)
	mon.level = emu:read8(address + 84)
	mon.mail = emu:read32(address + 85)
	mon.hp = emu:read16(address + 86)
	mon.maxHP = emu:read16(address + 88)
	mon.attack = emu:read16(address + 90)
	mon.defense = emu:read16(address + 92)
	mon.speed = emu:read16(address + 94)
	mon.spAttack = emu:read16(address + 96)
	mon.spDefense = emu:read16(address + 98)
	return mon
end

function getParty()
	local party = {}
	local monStart = partyloc
	for i = 1, emu:read8(partyCount) do
		party[i] = readPartyMon(monStart)
		monStart = monStart + partyMonSize
	end
	return party
end

function startScript()
	if not displayBuffer then
		displayBuffer = console:createBuffer("Run&Bun Display")
		displayBuffer:setSize(200,1000)
		displayBuffer:print("Run&Bun Display en cours d'exécution...\n")
	end
end

-- Main loop, triggered each frame
function updateBuffer()
    local now = os.clock()

	-- Execute script logic every second
    if now - lastTime >= 1 then
        local lastTime = now
        local address = storageLoc + 4
		local i = 0

		local emptyBox = false
		local alivePokemon = true

        local partyPokemon = "PARTY"
        local boxPokemon = "BOX"
        local deadPokemon = "DEAD"
		local defeatedTrainers = "TRAINERS"
		local pickedStarter = "STARTER|" .. emu:read16(pickedStarterAddress)

		-- Retrieve party Pokémon
        for _, mon in ipairs(getParty()) do
            if (mon.species ~= 0) then
                partyPokemon = partyPokemon .. "|" .. mon.species .. "-" .. mon.level .. "-" .. mon.heldItem
            end
        end

		-- Retrieve PC Pokémon (box + dead)
		while i < 420 do
            if alivePokemon then
				boxPokemon = boxPokemon .. "|"
			elseif i >= 390 then
				deadPokemon = deadPokemon .. "|"
			end

			-- If no Pokémon was found in the box, stop parsing alive Pokémon
			if (i % 30 == 0) then
				if emptyBox then
					if alivePokemon then
						alivePokemon = false
						boxPokemon = string.sub(boxPokemon, 1, #boxPokemon - 31) -- Remove last 30 empty Pokémon
					end
				else
					emptyBox = true
				end
			end

			-- Only read valid data
			if (emu:read32(address) ~=0) then
				mon = readBoxMon(address)

				-- Pokémon found : add it to data file
				if (mon.species ~= 0) then
					emptyBox = false
					
					if (alivePokemon) then
						boxPokemon = boxPokemon .. mon.species .. "-" .. calcLevel(mon.experience, mon.species) .. "-" .. mon.heldItem
					else
						deadPokemon = deadPokemon .. mon.species .. "-0-" .. mon.heldItem -- No need to calc level for dead Pokémon
					end
				end
			end

            address = address + 80
            i = i + 1
        end

		-- Retrieve booleans indicating if trainers have been defeated
		for trainerAddress = defeatedTrainersStart, defeatedTrainersEnd do
			defeatedTrainers = defeatedTrainers .. "|" .. emu:read8(trainerAddress)
		end

		-- Retrieve pokemonData.txt path from env variable defined by Python script
		local dataFilePath = os.getenv("RUNANDBUNREADER_CONFFILE")

		-- Write data in pokemonData.txt
		if dataFilePath then
			local f = io.open(dataFilePath, "w")

			if f then
				f:write(partyPokemon .. "\n" .. boxPokemon .. "\n" .. deadPokemon .. "\n" .. defeatedTrainers .. "\n" .. pickedStarter)
				f:close()
			else
				displayBuffer:print("Cannot write pokemon data\n")
			end
		else
			displayBuffer:print('Cannot find current folder, run "Run&Bun Reader.exe" and restart mGBA\n')
		end
    end
end

callbacks:add("frame", updateBuffer)
callbacks:add("start", startScript)
callbacks:add("reset", startScript)

if emu then
	startScript()
end

curve = {3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,3,3,3,3,3,3,4,4,0,0,4,4,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,5,5,3,3,3,3,3,3,3
		,3,3,3,3,3,5,5,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,3,3,3,0,0,0,0,0,0,0,5,5,0,0,0,0,0,0,0,5,5,4,0,0,0,0,0,0,5,5,0,0,0,0,0,5,5,5,5,5,0,0,0,0
		,0,0,0,0,0,0,5,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,3,0,0,0,0,4,4,4,4,0,5,5,0,4,4,4,4,0,0,3,3,3,3,4,4,0,3,3,3,3,4,3,3,0,0,0,0,0,3,0,4,0,0,0,0
		,0,0,3,0,4,4,0,0,3,5,3,0,0,0,0,5,5,4,0,0,4,5,5,5,5,0,0,0,0,5,4,0,0,0,0,0,5,4,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,3,3,3,3
		,3,3,3,3,0,0,5,5,5,0,0,2,2,5,5,5,1,1,1,3,3,3,2,2,4,0,4,4,3,4,5,5,5,0,0,5,5,0,0,1,2,3,2,2,5,5,2,2,0,0,0,4,4,4,3,3,3,3,3,1,1,1,2,4,4,0,0,2,2
		,0,0,1,1,1,1,1,1,0,3,4,4,4,4,5,4,3,0,0,0,3,3,3,1,1,1,5,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,3,3,3,0,0,3,3,3,3,3,3,3,1,1,1,1
		,0,0,0,3,3,0,0,0,0,0,0,0,4,2,2,0,0,4,3,4,4,4,0,0,0,0,0,0,4,3,0,5,5,5,5,3,3,5,5,5,5,0,0,5,1,1,5,5,5,3,0,0,5,0,0,0,4,0,0,0,3,5,0,5,0,4,0,0,5
		,5,5,5,5,5,5,5,5,5,5,5,3,5,5,3,3,3,3,3,3,3,3,3,0,0,3,3,3,0,0,0,0,0,0,0,0,4,4,3,3,3,0,0,3,3,3,0,0,0,0,4,3,3,3,3,3,3,0,0,3,3,3,3,3,3,0,0,0,0
		,0,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,3,4,4,3,3,3,3,3,3,0,0,5,5,5,0,0,0,0,0,0,0,0,0,4,0,0,0,0,3,3,3,5,5,5,0,0,3,3,3,5,5,5,0,0,0,0,0,0
		,3,3,0,0,0,0,0,0,5,5,5,5,0,0,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,0,0,3,3,3,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
		,0,0,0,0,5,5,0,0,0,0,0,0,0,0,0,5,5,5,5,4,0,0,0,0,0,0,0,0,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0
		,0,0,0,0,3,3,3,4,5,5,0,0,0,0,4,5,5,0,5,0,0,0,0,0,0,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,0,0,3,3,3,0,0
		,0,4,4,0,0,0,0,0,0,4,4,3,3,3,1,1,1,0,0,0,5,5,3,3,0,0,3,3,0,0,5,5,5,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,5,5,4,0,0,0,5,5,5,5,0,5,5,5,5,5,5,5,5,5,5
		,5,5,5,5,5,0,0,0,3,0,5,3,3,3,3,0,3,3,0,3,0,5,5,5,5,5,3,0,0,5,5,5,3,3,3,5,3,4,5,0,5,5,0,1,4,3,0,5,5,5,5,0,5,3,5,5,4,5,5,5,5,0,0,0,0,0,0,0,0
		,0,0,0,3,3,3,0,0,5,0,0,0,0,0,0,0,0,0,5,5,5,0,4,0,0,3,3,0,0,5,5,0,0,3,0,3,3,0,3,3,5,5,5,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
		,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,5,0,0,0,0,0,0,0,0,0,0,0,0,5,5,5,3,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,0,0,3,3,0,0,0,0,0,0,5,5
		,5,5,5,5,5,5,5,5,5,5,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,5,5,5,5,0,0
		,0,0,0,0,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,5,5,0,0,3,0,0,0,0,0,0,0,0,0,0,5,4,0,5,5,5,5,5,5,5,5}