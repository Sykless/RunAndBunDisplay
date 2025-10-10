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
local playerZoneAddress = 0X020368F0

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

function calcLevel(exp, species, isEgg)
	if (isEgg == 1) then
		return 1
	end

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

function getAbility(mon)
    current = ability[(mon.species*3)+1+mon.altAbility]
    if (current == "None") then
        current = ability[(mon.species*3)+1]
    end
    return current
end

function getNature(mon)
	if (mon.hiddenNature == 26) then
		return nature[(mon.personality % 25)+1]
	end
	return nature[mon.hiddenNature+1]
end

function toString(rawstring)
	local string = ""
	for _, char in ipairs({rawstring:byte(1, #rawstring)}) do
		if char == terminator then
			break
		end
		string = string..charmap[char]
	end
	return string
end

function readBoxMon(address)
	local mon = {}
	mon.personality = emu:read32(address + 0)
	mon.otId = emu:read32(address + 4)
	mon.nickname = toString(emu:readRange(address + 8, monNameLength))
	mon.language = emu:read8(address + 18)
	local flags = emu:read8(address + 19)
	mon.isBadEgg = flags & 1
	mon.hasSpecies = (flags >> 1) & 1
	mon.isEgg = (flags >> 2) & 1
	mon.otName = emu:readRange(address + 20, playerNameLength) -- need to use toString for actual value
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

function printFullData(mon)
	return string.format("%x", mon.personality) .. "¤"
		.. mon.species .. "¤"
		.. mon.nickname .. "¤"
		.. mon.metLocation .. "¤"
		.. calcLevel(mon.experience, mon.species, mon.isEgg) .. "¤"
		.. getAbility(mon) .. "¤"
		.. getNature(mon) .. "¤"
		.. mon.moves[1] .. "¤"
		.. mon.moves[2] .. "¤"
		.. mon.moves[3] .. "¤"
		.. mon.moves[4] .. "¤"
		.. mon.hpIV .. "¤"
		.. mon.attackIV .. "¤"
		.. mon.defenseIV .. "¤"
		.. mon.spAttackIV .. "¤"
		.. mon.spDefenseIV .. "¤"
		.. mon.speedIV
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
        lastTime = now

        local address = storageLoc + 4
		local i = 0

		local emptyBox = false
		local alivePokemon = true

        local partyPokemon = "PARTY"
        local boxPokemon = "BOX"
        local deadPokemon = "DEAD"
		local defeatedTrainers = "TRAINERS"
		local pickedStarter = "STARTER|" .. emu:read16(pickedStarterAddress)
		local teamFullData = "FULLDATA"

		-- Retrieve party Pokémon
        for _, mon in ipairs(getParty()) do
            if (mon.species ~= 0) then
                partyPokemon = partyPokemon .. "|" .. mon.species .. "¤" .. mon.level .. "¤" .. mon.heldItem
				teamFullData = teamFullData .. "|" .. printFullData(mon) .. "¤" .. "1"
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
						boxPokemon = boxPokemon .. mon.species .. "¤" .. calcLevel(mon.experience, mon.species, mon.isEgg) .. "¤" .. mon.heldItem
						teamFullData = teamFullData .. "|" .. printFullData(mon) .. "¤" .. "1"
					else
						deadPokemon = deadPokemon .. mon.species .. "¤0¤" .. mon.heldItem -- No need to calc level for dead Pokémon
						teamFullData = teamFullData .. "|" .. printFullData(mon) .. "¤" .. "0"
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
				f:write(partyPokemon .. "\n" .. boxPokemon .. "\n" .. deadPokemon .. "\n" .. defeatedTrainers .. "\n" .. pickedStarter .. "\n" .. teamFullData)
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

nature = {"Hardy","Lonely","Brave","Adamant","Naughty",
			"Bold","Docile","Relaxed","Impish","Lax",
			"Timid","Hasty","Serious","Jolly","Naive",
			"Modest","Mild","Quiet","Bashful","Rash",
			"Calm","Gentle","Sassy","Careful","Quirky"}

charmap = { [0]=
	" ", "À", "Á", "Â", "Ç", "È", "É", "Ê", "Ë", "Ì", "こ", "Î", "Ï", "Ò", "Ó", "Ô",
	"Œ", "Ù", "Ú", "Û", "Ñ", "ß", "à", "á", "ね", "ç", "è", "é", "ê", "ë", "ì", "ま",
	"î", "ï", "ò", "ó", "ô", "œ", "ù", "ú", "û", "ñ", "º", "ª", "�", "&", "+", "あ",
	"ぃ", "ぅ", "ぇ", "ぉ", "v", "=", "ょ", "が", "ぎ", "ぐ", "げ", "ご", "ざ", "じ", "ず", "ぜ",
	"ぞ", "だ", "ぢ", "づ", "で", "ど", "ば", "び", "ぶ", "べ", "ぼ", "ぱ", "ぴ", "ぷ", "ぺ", "ぽ",
	"っ", "¿", "¡", "P\u{200d}k", "M\u{200d}n", "P\u{200d}o", "K\u{200d}é", "�", "�", "�", "Í", "%", "(", ")", "セ", "ソ",
	"タ", "チ", "ツ", "テ", "ト", "ナ", "ニ", "ヌ", "â", "ノ", "ハ", "ヒ", "フ", "ヘ", "ホ", "í",
	"ミ", "ム", "メ", "モ", "ヤ", "ユ", "ヨ", "ラ", "リ", "⬆", "⬇", "⬅", "➡", "ヲ", "ン", "ァ",
	"ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ガ", "ギ", "グ", "ゲ", "ゴ", "ザ", "ジ", "ズ", "ゼ",
	"ゾ", "ダ", "ヂ", "ヅ", "デ", "ド", "バ", "ビ", "ブ", "ベ", "ボ", "パ", "ピ", "プ", "ペ", "ポ",
	"ッ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", ".", "-", "・",
	"…", "“", "”", "‘", "’", "♂", "♀", "$", ",", "×", "/", "A", "B", "C", "D", "E",
	"F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
	"V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
	"l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "▶",
	":", "Ä", "Ö", "Ü", "ä", "ö", "ü", "⬆", "⬇", "⬅", "�", "�", "�", "�", "�", ""
}

ability = {'None','None','None',
'Overgrow','None','Chlorophyll',
'Overgrow','None','Chlorophyll',
'Overgrow','None','Chlorophyll',
'Blaze','None','Solar Power',
'Blaze','None','Solar Power',
'Blaze','None','Solar Power',
'Torrent','None','Rain Dish',
'Torrent','None','Rain Dish',
'Torrent','None','Rain Dish',
'Shield Dust','Run Away','None',
'Shed Skin','None','None',
'Compound Eyes','None','Tinted Lens',
'Shield Dust','Run Away','Run Away',
'Shed Skin','None','None',
'Swarm','Sniper','Sniper',
'Keen Eye','None','None',
'Keen Eye','None','None',
'Keen Eye','None','None',
'Run Away','Guts','Hustle',
'Run Away','Guts','Hustle',
'Keen Eye','None','Sniper',
'Keen Eye','None','Sniper',
'Intimidate','None','Shed Skin',
'Intimidate','None','Shed Skin',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Sand Veil','None','Sand Rush',
'Sand Veil','None','Sand Rush',
'Poison Point','None','Hustle',
'Poison Point','None','Hustle',
'Poison Point','None','Sheer Force',
'Poison Point','None','Hustle',
'Poison Point','None','Hustle',
'Poison Point','None','Sheer Force',
'Friend Guard','Magic Guard','Friend Guard',
'Unaware','Magic Guard','Unaware',
'Flash Fire','None','Drought',
'Flash Fire','None','Drought',
'Cute Charm','Competitive','Friend Guard',
'Cute Charm','Competitive','Frisk',
'Inner Focus','None','Infiltrator',
'Inner Focus','None','Infiltrator',
'Chlorophyll','None','Run Away',
'Chlorophyll','None','Stench',
'Chlorophyll','None','Effect Spore',
'Effect Spore','None','Dry Skin',
'Effect Spore','None','Dry Skin',
'Compound Eyes','Tinted Lens','Run Away',
'Shield Dust','Tinted Lens','Wonder Skin',
'Arena Trap','None','Sand Force',
'Arena Trap','None','Sand Force',
'Pickup','Technician','Unnerve',
'Limber','Technician','Unnerve',
'Swift Swim','None','Cloud Nine',
'Swift Swim','None','Cloud Nine',
'Vital Spirit','Anger Point','Defiant',
'Vital Spirit','Anger Point','Defiant',
'Intimidate','None','Flash Fire',
'Intimidate','None','Flash Fire',
'Water Absorb','Damp','Swift Swim',
'Water Absorb','Damp','Swift Swim',
'Water Absorb','Damp','Swift Swim',
'Synchronize','Inner Focus','Magic Guard',
'Synchronize','Inner Focus','Magic Guard',
'Synchronize','Inner Focus','Magic Guard',
'Guts','No Guard','Steadfast',
'Guts','No Guard','Steadfast',
'Guts','No Guard','Steadfast',
'Chlorophyll','None','Gluttony',
'Chlorophyll','None','Gluttony',
'Chlorophyll','None','Gluttony',
'Clear Body','Liquid Ooze','Rain Dish',
'Clear Body','Liquid Ooze','Rain Dish',
'Rock Head','Sturdy','Sand Veil',
'Rock Head','Sturdy','Sand Veil',
'Rock Head','Sturdy','Sand Veil',
'Flame Body','None','Flash Fire',
'Flame Body','None','Flash Fire',
'Oblivious','Own Tempo','Regenerator',
'Oblivious','Own Tempo','Regenerator',
'Magnet Pull','Analytic','Sturdy',
'Magnet Pull','Analytic','Sturdy',
'Keen Eye','Inner Focus','Defiant',
'Run Away','Early Bird','Tangled Feet',
'Run Away','Early Bird','Tangled Feet',
'Thick Fat','Hydration','Ice Body',
'Thick Fat','Hydration','Ice Body',
'Poison Touch','Sticky Hold','Poison Touch',
'Poison Touch','Sticky Hold','Poison Touch',
'Shell Armor','None','Overcoat',
'Shell Armor','Skill Link','Overcoat',
'Levitate','None','None',
'Levitate','None','None',
'Cursed Body','None','Levitate',
'Rock Head','Weak Armor','Sturdy',
'Insomnia','None','Bad Dreams',
'Insomnia','None','Bad Dreams',
'Sheer Force','Shell Armor','Hyper Cutter',
'Sheer Force','Shell Armor','Hyper Cutter',
'Soundproof','Static','Galvanize',
'Soundproof','Static','Galvanize',
'Chlorophyll','None','Harvest',
'Chlorophyll','None','Harvest',
'Rock Head','Lightning Rod','Battle Armor',
'Rock Head','Lightning Rod','Battle Armor',
'Limber','Reckless','Unburden',
'Inner Focus','Iron Fist','No Guard',
'Own Tempo','Oblivious','Cloud Nine',
'Levitate','None','Stench',
'Levitate','None','Neutralizing Gas',
'Reckless','Rock Head','Lightning Rod',
'Reckless','Rock Head','Lightning Rod',
'Natural Cure','Serene Grace','Healer',
'Chlorophyll','Leaf Guard','Regenerator',
'Early Bird','Inner Focus','Scrappy',
'Swift Swim','Sniper','Damp',
'Poison Point','Sniper','Damp',
'Swift Swim','Water Veil','Lightning Rod',
'Swift Swim','Water Veil','Lightning Rod',
'Natural Cure','None','Analytic',
'Natural Cure','None','Analytic',
'Soundproof','Filter','Technician',
'Swarm','None','Technician',
'Oblivious','Forewarn','Dry Skin',
'Vital Spirit','None','Static',
'Flame Body','Vital Spirit','Flash Fire',
'Hyper Cutter','Mold Breaker','Moxie',
'Intimidate','None','Sheer Force',
'Swift Swim','None','Rattled',
'Intimidate','None','Moxie',
'Water Absorb','Shell Armor','Hydration',
'Limber','None','Imposter',
'Run Away','Adaptability','Anticipation',
'Water Absorb','Water Absorb','Hydration',
'Volt Absorb','Volt Absorb','Quick Feet',
'Flash Fire','Flash Fire','Guts',
'Trace','Analytic','Download',
'Swift Swim','Shell Armor','Weak Armor',
'Swift Swim','Shell Armor','Weak Armor',
'Swift Swim','Battle Armor','Weak Armor',
'Swift Swim','Battle Armor','Weak Armor',
'Rock Head','Unnerve','Pressure',
'Immunity','Thick Fat','Gluttony',
'Pressure','None','Snow Cloak',
'Pressure','None','Static',
'Pressure','None','Flame Body',
'Shed Skin','None','Marvel Scale',
'Shed Skin','None','Marvel Scale',
'Inner Focus','None','Multiscale',
'Pressure','None','Unnerve',
'Synchronize','None','None',
'Overgrow','None','Thick Fat',
'Overgrow','None','Thick Fat',
'Overgrow','None','Thick Fat',
'Blaze','None','Flash Fire',
'Blaze','None','Flash Fire',
'Blaze','None','Flash Fire',
'Torrent','None','Sheer Force',
'Torrent','None','Sheer Force',
'Torrent','None','Sheer Force',
'Run Away','Keen Eye','Frisk',
'Run Away','Keen Eye','Frisk',
'Insomnia','Keen Eye','Tinted Lens',
'Insomnia','Keen Eye','Tinted Lens',
'Rattled','Early Bird','Early Bird',
'Rattled','Early Bird','Iron Fist',
'Swarm','Insomnia','Sniper',
'Swarm','Insomnia','Sniper',
'Inner Focus','None','Infiltrator',
'Volt Absorb','None','Water Absorb',
'Volt Absorb','None','Water Absorb',
'Static','None','Lightning Rod',
'Friend Guard','Magic Guard','Friend Guard',
'Cute Charm','Competitive','Friend Guard',
'Super Luck','Serene Grace','Hustle',
'Super Luck','Serene Grace','Hustle',
'Synchronize','Early Bird','Magic Bounce',
'Synchronize','Early Bird','Magic Bounce',
'Static','None','None',
'Static','None','None',
'Static','None','None',
'Chlorophyll','None','Healer',
'Thick Fat','None','Huge Power',
'Thick Fat','None','Huge Power',
'Sturdy','Rock Head','Rock Head',
'Water Absorb','Damp','Drizzle',
'Chlorophyll','Leaf Guard','Infiltrator',
'Chlorophyll','Leaf Guard','Infiltrator',
'Chlorophyll','Leaf Guard','Infiltrator',
'Run Away','None','Skill Link',
'Chlorophyll','Solar Power','Early Bird',
'Chlorophyll','Solar Power','Early Bird',
'Compound Eyes','None','Speed Boost',
'Damp','Water Absorb','Unaware',
'Damp','Water Absorb','Unaware',
'Synchronize','Synchronize','Magic Bounce',
'Synchronize','Synchronize','Inner Focus',
'Insomnia','None','Prankster',
'Oblivious','Own Tempo','Regenerator',
'Levitate','None','None',
'Levitate','None','None',
'Shadow Tag','None','Telepathy',
'Inner Focus','Early Bird','Sap Sipper',
'Sturdy','None','Overcoat',
'Sturdy','None','Overcoat',
'Serene Grace','Run Away','Rattled',
'Hyper Cutter','None','Immunity',
'Rock Head','Sheer Force','Sturdy',
'Intimidate','None','Rattled',
'Intimidate','None','Quick Feet',
'Intimidate','None','Swift Swim',
'Swarm','None','Technician',
'Sturdy','Gluttony','Contrary',
'Swarm','Guts','Moxie',
'Inner Focus','Keen Eye','Pickpocket',
'Quick Feet','None','Honey Gather',
'Guts','Unnerve','Quick Feet',
'Magma Armor','Flame Body','Weak Armor',
'Magma Armor','Flame Body','Weak Armor',
'Oblivious','Thick Fat','Snow Cloak',
'Oblivious','Thick Fat','Snow Cloak',
'Hustle','Natural Cure','Regenerator',
'Hustle','None','Sniper',
'Suction Cups','None','Sniper',
'Vital Spirit','Hustle','Insomnia',
'Swift Swim','Water Absorb','Water Veil',
'Keen Eye','Sturdy','Weak Armor',
'Early Bird','Unnerve','Flash Fire',
'Early Bird','Unnerve','Flash Fire',
'Swift Swim','Sniper','Damp',
'Cute Charm','None','Sand Veil',
'Sturdy','Battle Armor','Sand Veil',
'Trace','Analytic','Download',
'Intimidate','None','Sap Sipper',
'Own Tempo','Technician','Moody',
'Guts','Steadfast','Vital Spirit',
'Intimidate','Technician','Steadfast',
'Oblivious','Forewarn','Hydration',
'Vital Spirit','None','Static',
'Flame Body','Vital Spirit','Flash Fire',
'Thick Fat','Scrappy','Sap Sipper',
'Natural Cure','Serene Grace','Healer',
'Pressure','None','Inner Focus',
'Pressure','None','Inner Focus',
'Pressure','None','Inner Focus',
'Guts','None','Sand Veil',
'Shed Skin','None','None',
'Unnerve','None','Sand Stream',
'Pressure','None','Multiscale',
'Pressure','None','Regenerator',
'Natural Cure','None','None',
'Overgrow','None','Unburden',
'Overgrow','None','Unburden',
'Overgrow','None','Unburden',
'Blaze','None','Speed Boost',
'Blaze','None','Speed Boost',
'Blaze','None','Speed Boost',
'Torrent','None','Damp',
'Torrent','None','Damp',
'Torrent','None','Damp',
'Run Away','None','Rattled',
'Intimidate','None','Moxie',
'Pickup','Gluttony','Quick Feet',
'Pickup','Gluttony','Quick Feet',
'Shield Dust','None','Run Away',
'Shed Skin','None','None',
'Swarm','None','Rivalry',
'Shed Skin','None','None',
'Shield Dust','None','Compound Eyes',
'Swift Swim','Rain Dish','Own Tempo',
'Swift Swim','Rain Dish','Own Tempo',
'Swift Swim','Rain Dish','Own Tempo',
'Chlorophyll','Early Bird','Pickpocket',
'Chlorophyll','Early Bird','Pickpocket',
'Chlorophyll','Early Bird','Pickpocket',
'Guts','None','Scrappy',
'Guts','None','Scrappy',
'Keen Eye','Hydration','Rain Dish',
'Keen Eye','Drizzle','Rain Dish',
'Synchronize','Trace','Telepathy',
'Synchronize','Trace','Telepathy',
'Synchronize','Trace','Telepathy',
'Swift Swim','None','Rain Dish',
'Intimidate','None','Unnerve',
'Effect Spore','Poison Heal','Quick Feet',
'Effect Spore','Poison Heal','Technician',
'Truant','None','None',
'Vital Spirit','None','None',
'Truant','None','None',
'Compound Eyes','None','Run Away',
'Speed Boost','None','Infiltrator',
'Wonder Guard','None','None',
'Soundproof','None','Rattled',
'Soundproof','None','Scrappy',
'Soundproof','None','Scrappy',
'Thick Fat','Guts','Sheer Force',
'Thick Fat','Guts','Sheer Force',
'Thick Fat','None','Huge Power',
'Sturdy','None','Sand Force',
'Normalize','None','None',
'Normalize','None','None',
'Keen Eye','Stall','Prankster',
'Hyper Cutter','Intimidate','Sheer Force',
'Heavy Metal','Rock Head','Sturdy',
'Heavy Metal','Rock Head','Sturdy',
'Heavy Metal','Rock Head','Sturdy',
'Pure Power','None','Inner Focus',
'Pure Power','None','Inner Focus',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Plus','None','Lightning Rod',
'Minus','None','Volt Absorb',
'Illuminate','Swarm','Prankster',
'Oblivious','Tinted Lens','Prankster',
'Natural Cure','Poison Point','Leaf Guard',
'Liquid Ooze','Sticky Hold','Gluttony',
'Liquid Ooze','Sticky Hold','Gluttony',
'Rough Skin','None','Speed Boost',
'Rough Skin','None','Speed Boost',
'Water Veil','Oblivious','Pressure',
'Water Veil','Oblivious','Pressure',
'Oblivious','Simple','Own Tempo',
'Magma Armor','Solid Rock','Own Tempo',
'Shell Armor','None','Drought',
'Thick Fat','Own Tempo','Gluttony',
'Thick Fat','Own Tempo','Gluttony',
'Own Tempo','Tangled Feet','Contrary',
'Arena Trap','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Sand Veil','None','Water Absorb',
'Sand Veil','None','Water Absorb',
'Natural Cure','None','Cloud Nine',
'Natural Cure','None','Cloud Nine',
'Immunity','None','Toxic Boost',
'Shed Skin','None','Infiltrator',
'Levitate','None','None',
'Levitate','None','None',
'Oblivious','Anticipation','Hydration',
'Oblivious','Anticipation','Hydration',
'Hyper Cutter','Shell Armor','Adaptability',
'Hyper Cutter','Shell Armor','Adaptability',
'Levitate','None','None',
'Levitate','None','None',
'Suction Cups','None','Storm Drain',
'Suction Cups','None','Storm Drain',
'Battle Armor','None','Swift Swim',
'Battle Armor','None','Swift Swim',
'Swift Swim','None','None',
'Marvel Scale','None','Competitive',
'Forecast','None','None',
'Protean','None','Color Change',
'Insomnia','None','Cursed Body',
'Insomnia','None','Cursed Body',
'Levitate','None','Frisk',
'Pressure','None','Frisk',
'Chlorophyll','Solar Power','Harvest',
'Levitate','None','None',
'Pressure','None','Super Luck',
'Shadow Tag','None','Telepathy',
'Inner Focus','None','Moody',
'Inner Focus','None','Moody',
'Thick Fat','Oblivious','Ice Body',
'Thick Fat','Oblivious','Ice Body',
'Thick Fat','Oblivious','Ice Body',
'Shell Armor','None','Rattled',
'Swift Swim','None','Water Veil',
'Swift Swim','None','Hydration',
'Swift Swim','Rock Head','Sturdy',
'Swift Swim','None','Hydration',
'Rock Head','None','Sheer Force',
'Rock Head','None','Overcoat',
'Intimidate','None','Moxie',
'Clear Body','None','None',
'Clear Body','None','None',
'Clear Body','None','None',
'Clear Body','None','Sturdy',
'Clear Body','None','Ice Body',
'Clear Body','None','Light Metal',
'Levitate','None','None',
'Levitate','None','None',
'Drizzle','None','None',
'Drought','None','None',
'Air Lock','None','None',
'Serene Grace','None','None',
'Pressure','None','None',
'Overgrow','Rock Head','Shell Armor',
'Overgrow','Rock Head','Shell Armor',
'Overgrow','Rock Head','Shell Armor',
'Blaze','Iron Fist','Vital Spirit',
'Blaze','Iron Fist','Vital Spirit',
'Blaze','Iron Fist','Vital Spirit',
'Torrent','Defiant','Clear Body',
'Torrent','Defiant','Clear Body',
'Torrent','Defiant','Clear Body',
'Keen Eye','None','Reckless',
'Intimidate','None','Reckless',
'Intimidate','None','Reckless',
'Simple','Unaware','Unaware',
'Simple','Unaware','Unaware',
'Shed Skin','None','Run Away',
'Swarm','None','Technician',
'Intimidate','None','Guts',
'Intimidate','None','Guts',
'Intimidate','None','Guts',
'Natural Cure','Poison Point','Leaf Guard',
'Natural Cure','Technician','Leaf Guard',
'Mold Breaker','None','Sheer Force',
'Mold Breaker','None','Sheer Force',
'Sturdy','None','Soundproof',
'Sturdy','None','Soundproof',
'Shed Skin','None','Overcoat',
'Anticipation','None','Overcoat',
'Swarm','None','Tinted Lens',
'Honey Gather','Honey Gather','Hustle',
'Unnerve','None','Pressure',
'Run Away','Pickup','Volt Absorb',
'Swift Swim','Water Veil','Swift Swim',
'Swift Swim','Water Veil','Swift Swim',
'Chlorophyll','None','None',
'Flower Gift','None','None',
'Sticky Hold','Sand Force','Storm Drain',
'Sticky Hold','Sand Force','Storm Drain',
'Technician','None','Skill Link',
'Aftermath','Unburden','Flare Boost',
'Aftermath','Unburden','Flare Boost',
'Cute Charm','Limber','Limber',
'Cute Charm','Limber','Limber',
'Levitate','None','None',
'Insomnia','None','Super Luck',
'Limber','Own Tempo','Keen Eye',
'Thick Fat','Own Tempo','Defiant',
'Levitate','None','None',
'Keen Eye','Aftermath','Stench',
'Keen Eye','Aftermath','Stench',
'Levitate','Heatproof','Heavy Metal',
'Levitate','Heatproof','Heavy Metal',
'Sturdy','Rock Head','Rock Head',
'Soundproof','Filter','Technician',
'Natural Cure','Serene Grace','Friend Guard',
'Keen Eye','Tangled Feet','Big Pecks',
'Pressure','None','Infiltrator',
'Rough Skin','None','Sand Veil',
'Rough Skin','None','Sand Veil',
'Rough Skin','None','Sand Veil',
'Pickup','Thick Fat','Gluttony',
'Steadfast','Inner Focus','Prankster',
'Steadfast','Inner Focus','Justified',
'Sand Stream','None','Sand Force',
'Sand Stream','None','Sand Force',
'Battle Armor','None','Sniper',
'Battle Armor','None','Sniper',
'Poison Touch','None','Dry Skin',
'Poison Touch','None','Dry Skin',
'Levitate','None','None',
'Swift Swim','Water Veil','Storm Drain',
'Swift Swim','Water Veil','Storm Drain',
'Swift Swim','Water Absorb','Water Veil',
'Soundproof','None','Snow Warning',
'Soundproof','None','Snow Warning',
'Inner Focus','Pressure','Pickpocket',
'Magnet Pull','Analytic','Sturdy',
'Own Tempo','Oblivious','Cloud Nine',
'Solid Rock','Rock Head','Lightning Rod',
'Chlorophyll','Leaf Guard','Regenerator',
'Vital Spirit','None','Motor Drive',
'Flame Body','Vital Spirit','Flash Fire',
'Super Luck','Serene Grace','Hustle',
'Tinted Lens','None','Speed Boost',
'Leaf Guard','Leaf Guard','Chlorophyll',
'Snow Cloak','Snow Cloak','Ice Body',
'Hyper Cutter','None','Poison Heal',
'Oblivious','Thick Fat','Snow Cloak',
'Adaptability','Analytic','Download',
'Inner Focus','None','Justified',
'Magnet Pull','None','Sand Force',
'Pressure','None','Frisk',
'Cursed Body','None','Snow Cloak',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Pressure','None','Telepathy',
'Pressure','None','Telepathy',
'Flash Fire','None','Flame Body',
'Slow Start','None','None',
'Pressure','None','Telepathy',
'Levitate','None','None',
'Hydration','None','None',
'Hydration','None','None',
'Bad Dreams','None','None',
'Natural Cure','None','None',
'Multitype','None','None',
'Victory Star','None','None',
'Overgrow','None','Contrary',
'Overgrow','None','Contrary',
'Overgrow','None','Contrary',
'Blaze','None','Thick Fat',
'Blaze','None','Thick Fat',
'Blaze','None','Reckless',
'Torrent','None','Shell Armor',
'Torrent','None','Shell Armor',
'Torrent','None','Shell Armor',
'Run Away','Keen Eye','Analytic',
'Illuminate','Keen Eye','Analytic',
'Vital Spirit','Run Away','Scrappy',
'Intimidate','Sand Rush','Scrappy',
'Intimidate','Sand Rush','Scrappy',
'Limber','Unburden','Prankster',
'Limber','Unburden','Prankster',
'Gluttony','None','Overgrow',
'Gluttony','None','Overgrow',
'Gluttony','None','Blaze',
'Gluttony','None','Blaze',
'Gluttony','None','Torrent',
'Gluttony','None','Torrent',
'Synchronize','None','Telepathy',
'Synchronize','None','Telepathy',
'Big Pecks','Super Luck','Rivalry',
'Big Pecks','Super Luck','Rivalry',
'Big Pecks','Super Luck','Rivalry',
'Lightning Rod','Motor Drive','Sap Sipper',
'Lightning Rod','Motor Drive','Sap Sipper',
'Weak Armor','Clear Body','Sturdy',
'Solid Rock','Clear Body','Sturdy',
'Solid Rock','Clear Body','Sand Stream',
'Unaware','Klutz','Simple',
'Unaware','Klutz','Simple',
'Sand Rush','Sand Force','Mold Breaker',
'Sand Rush','Sand Force','Mold Breaker',
'Healer','None','Regenerator',
'Guts','Sheer Force','Iron Fist',
'Guts','Sheer Force','Iron Fist',
'Guts','Sheer Force','Iron Fist',
'Swift Swim','Poison Touch','Water Absorb',
'Swift Swim','Poison Touch','Water Absorb',
'Swift Swim','Poison Touch','Water Absorb',
'Mold Breaker','Inner Focus','Guts',
'Mold Breaker','Inner Focus','Sturdy',
'Swarm','Chlorophyll','Overcoat',
'Leaf Guard','Chlorophyll','Overcoat',
'Swarm','Chlorophyll','Overcoat',
'Poison Point','None','Speed Boost',
'Poison Point','None','Speed Boost',
'Poison Point','None','Speed Boost',
'Prankster','Infiltrator','Chlorophyll',
'Prankster','Infiltrator','Chlorophyll',
'Chlorophyll','Own Tempo','Leaf Guard',
'Chlorophyll','None','Own Tempo',
'Reckless','Mold Breaker','Adaptability',
'Intimidate','None','Moxie',
'Intimidate','None','Moxie',
'Intimidate','None','Moxie',
'Hustle','None','Inner Focus',
'Sheer Force','None','Zen Mode',
'Chlorophyll','None','Storm Drain',
'Sturdy','Shell Armor','Weak Armor',
'Sturdy','Shell Armor','Weak Armor',
'Shed Skin','Moxie','Intimidate',
'Shed Skin','Moxie','Intimidate',
'Tinted Lens','Magic Guard','Magic Guard',
'Mummy','None','None',
'Mummy','None','None',
'Solid Rock','Swift Swim','Sturdy',
'Solid Rock','Swift Swim','Sturdy',
'Defeatist','None','None',
'Defeatist','None','None',
'Stench','Sticky Hold','Aftermath',
'Stench','Weak Armor','Aftermath',
'Illusion','None','None',
'Illusion','None','None',
'Cute Charm','Technician','Skill Link',
'Cute Charm','Technician','Skill Link',
'Frisk','Competitive','Shadow Tag',
'Frisk','Competitive','Shadow Tag',
'Frisk','Competitive','Shadow Tag',
'Overcoat','Magic Guard','Regenerator',
'Overcoat','Magic Guard','Regenerator',
'Overcoat','Magic Guard','Regenerator',
'Keen Eye','Big Pecks','Hydration',
'Keen Eye','Big Pecks','Hydration',
'Ice Body','Snow Cloak','Weak Armor',
'Ice Body','Snow Cloak','Weak Armor',
'Ice Body','Snow Warning','Weak Armor',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Static','None','Motor Drive',
'No Guard','Shed Skin','Shed Skin',
'Overcoat','Shell Armor','Shell Armor',
'Effect Spore','None','Regenerator',
'Effect Spore','None','Regenerator',
'Cursed Body','None','Water Absorb',
'Cursed Body','None','Water Absorb',
'Healer','Hydration','Regenerator',
'Compound Eyes','Unnerve','Swarm',
'Compound Eyes','Unnerve','Swarm',
'Anticipation','None','Iron Barbs',
'Anticipation','None','Iron Barbs',
'Plus','Minus','Clear Body',
'Plus','Minus','Clear Body',
'Plus','Minus','Clear Body',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Telepathy','Synchronize','Analytic',
'Telepathy','Synchronize','Analytic',
'Shadow Tag','Flame Body','Flash Fire',
'Shadow Tag','Flame Body','Flash Fire',
'Shadow Tag','Flame Body','Flash Fire',
'Rivalry','Mold Breaker','Unnerve',
'Rivalry','Mold Breaker','Unnerve',
'Rivalry','Mold Breaker','Unnerve',
'Snow Cloak','Slush Rush','Rattled',
'Snow Cloak','Slush Rush','Swift Swim',
'Levitate','None','None',
'Hydration','Shell Armor','Overcoat',
'Hydration','Sticky Hold','Unburden',
'Static','None','Sand Veil',
'Inner Focus','Regenerator','Reckless',
'Inner Focus','Regenerator','Reckless',
'Rough Skin','Sheer Force','Mold Breaker',
'Iron Fist','Klutz','No Guard',
'Iron Fist','Klutz','No Guard',
'Defiant','Inner Focus','Pressure',
'Defiant','Inner Focus','Pressure',
'Reckless','Sap Sipper','Soundproof',
'Keen Eye','Sheer Force','Hustle',
'Keen Eye','Sheer Force','Defiant',
'Big Pecks','Overcoat','Weak Armor',
'Big Pecks','Overcoat','Weak Armor',
'Gluttony','Flash Fire','White Smoke',
'Swarm','Hustle','Truant',
'Hustle','None','None',
'Hustle','None','None',
'Levitate','None','None',
'Swarm','None','Flame Body',
'Swarm','None','Flame Body',
'Justified','None','None',
'Justified','None','None',
'Justified','None','None',
'Prankster','None','Defiant',
'Prankster','None','Defiant',
'Turboblaze','None','None',
'Teravolt','None','None',
'Sand Force','None','Sheer Force',
'Pressure','None','None',
'Justified','None','None',
'Serene Grace','None','None',
'Download','None','None',
'Overgrow','None','Bulletproof',
'Overgrow','None','Bulletproof',
'Overgrow','None','Bulletproof',
'Blaze','None','Magic Guard',
'Blaze','None','Magic Guard',
'Blaze','None','Magic Guard',
'Torrent','None','Protean',
'Torrent','None','Protean',
'Torrent','None','Protean',
'Cheek Pouch','None','Huge Power',
'Cheek Pouch','None','Huge Power',
'Keen Eye','None','Gale Wings',
'Flame Body','None','Gale Wings',
'Flame Body','None','Gale Wings',
'Shield Dust','Compound Eyes','Friend Guard',
'Shed Skin','None','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Unnerve','None','None',
'Unnerve','None','None',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Sap Sipper','None','Grass Pelt',
'Sap Sipper','None','Grass Pelt',
'Iron Fist','Mold Breaker','Scrappy',
'Iron Fist','Mold Breaker','Scrappy',
'Fur Coat','None','None',
'Keen Eye','Infiltrator','Own Tempo',
'Keen Eye','Infiltrator','Prankster',
'No Guard','None','None',
'No Guard','None','None',
'Stance Change','None','None',
'Healer','None','Aroma Veil',
'Healer','None','Aroma Veil',
'Sweet Veil','None','Unburden',
'Sweet Veil','None','Unburden',
'Contrary','Suction Cups','Infiltrator',
'Contrary','Suction Cups','Infiltrator',
'Tough Claws','Sniper','Pickpocket',
'Tough Claws','Sniper','Pickpocket',
'Poison Point','None','Adaptability',
'Poison Point','None','Adaptability',
'Mega Launcher','None','None',
'Mega Launcher','None','None',
'Dry Skin','Sand Veil','Solar Power',
'Dry Skin','Sand Veil','Solar Power',
'Strong Jaw','None','Sturdy',
'Strong Jaw','None','Rock Head',
'Refrigerate','None','Snow Warning',
'Refrigerate','None','Snow Warning',
'Cute Charm','Cute Charm','Pixilate',
'Limber','Unburden','Mold Breaker',
'Cheek Pouch','Pickup','Plus',
'Clear Body','None','Sturdy',
'Gooey','Hydration','Sap Sipper',
'Gooey','Hydration','Sap Sipper',
'Gooey','Hydration','Sap Sipper',
'Prankster','None','Magician',
'Natural Cure','None','Harvest',
'Natural Cure','None','Harvest',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Own Tempo','Ice Body','Sturdy',
'Own Tempo','Ice Body','Sturdy',
'Frisk','Infiltrator','Telepathy',
'Frisk','Infiltrator','Telepathy',
'Fairy Aura','None','None',
'Dark Aura','None','None',
'Aura Break','None','None',
'Clear Body','None','None',
'Magician','None','None',
'Water Absorb','None','None',
'Overgrow','None','Long Reach',
'Overgrow','None','Long Reach',
'Overgrow','None','Long Reach',
'Blaze','None','Intimidate',
'Blaze','None','Intimidate',
'Blaze','None','Intimidate',
'Torrent','None','Liquid Voice',
'Torrent','None','Liquid Voice',
'Torrent','None','Liquid Voice',
'Keen Eye','Skill Link','Pickup',
'Keen Eye','Skill Link','Pickup',
'Keen Eye','Skill Link','Sheer Force',
'Stakeout','Strong Jaw','Adaptability',
'Stakeout','Strong Jaw','Adaptability',
'Swarm','None','None',
'Battery','None','None',
'Levitate','None','None',
'Hyper Cutter','Iron Fist','Anger Point',
'Hyper Cutter','Iron Fist','Anger Point',
'Dancer','None','None',
'Sweet Veil','Shield Dust','Honey Gather',
'Sweet Veil','Shield Dust','Honey Gather',
'Keen Eye','Vital Spirit','Steadfast',
'Sand Rush','None','Inner Focus',
'Schooling','None','None',
'Merciless','Limber','Regenerator',
'Merciless','Limber','Regenerator',
'Tangling Hair','Inner Focus','Stamina',
'Tangling Hair','Inner Focus','Stamina',
'Water Bubble','None','None',
'Water Bubble','None','None',
'Leaf Guard','None','Contrary',
'Leaf Guard','None','Contrary',
'Effect Spore','None','Rain Dish',
'Effect Spore','None','Rain Dish',
'Corrosion','None','None',
'Corrosion','None','None',
'Fluffy','None','None',
'Fluffy','None','None',
'Sweet Veil','Oblivious','Leaf Guard',
'Sweet Veil','Oblivious','Leaf Guard',
'Sweet Veil','Queenly Majesty','Leaf Guard',
'Triage','None','Natural Cure',
'Inner Focus','Telepathy','Symbiosis',
'Receiver','None','Defiant',
'Wimp Out','None','None',
'Emergency Exit','None','None',
'Water Compaction','None','Sand Veil',
'Water Compaction','None','Sand Veil',
'Innards Out','None','Unaware',
'Battle Armor','None','None',
'RKS System','None','None',
'Shields Down','None','None',
'Comatose','None','None',
'Shell Armor','None','None',
'Iron Barbs','None','Sturdy',
'Disguise','None','None',
'Dazzling','Strong Jaw','Strong Jaw',
'Berserk','Sap Sipper','Cloud Nine',
'Steelworker','None','None',
'Overcoat','Soundproof','Bulletproof',
'Overcoat','Soundproof','Bulletproof',
'Overcoat','Soundproof','Bulletproof',
'Electric Surge','None','Telepathy',
'Psychic Surge','None','Telepathy',
'Grassy Surge','None','Telepathy',
'Misty Surge','None','Telepathy',
'Unaware','None','None',
'Sturdy','None','None',
'Full Metal Body','None','None',
'Shadow Shield','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Prism Armor','None','None',
'Soul-Heart','None','None',
'Technician','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Beast Boost','None','None',
'Volt Absorb','None','None',
'Magnet Pull','None','None',
'Iron Fist','None','None',
'Overgrow','None','Grassy Surge',
'Overgrow','None','Grassy Surge',
'Overgrow','None','Grassy Surge',
'Blaze','None','Libero',
'Blaze','None','Libero',
'Blaze','None','Libero',
'Torrent','None','Sniper',
'Torrent','None','Sniper',
'Torrent','None','Sniper',
'Cheek Pouch','None','Gluttony',
'Cheek Pouch','None','Gluttony',
'Unnerve','None','Big Pecks',
'Unnerve','None','Big Pecks',
'Mirror Armor','None','Mirror Armor',
'Swarm','Compound Eyes','Telepathy',
'Swarm','Compound Eyes','Telepathy',
'Swarm','Compound Eyes','Telepathy',
'Run Away','Unburden','Stakeout',
'Run Away','Unburden','Stakeout',
'Cotton Down','None','Regenerator',
'Cotton Down','None','Regenerator',
'Fluffy','Run Away','Bulletproof',
'Fluffy','Steadfast','Bulletproof',
'Strong Jaw','Shell Armor','Swift Swim',
'Strong Jaw','Shell Armor','Swift Swim',
'Ball Fetch','None','Rattled',
'Strong Jaw','None','Competitive',
'Steam Engine','Heatproof','Flash Fire',
'Steam Engine','Flame Body','Flash Fire',
'Steam Engine','Flame Body','Flash Fire',
'Ripen','Gluttony','Bulletproof',
'Ripen','Gluttony','Hustle',
'Ripen','Gluttony','Thick Fat',
'Sand Spit','Shed Skin','Sand Veil',
'Sand Spit','Shed Skin','Sand Veil',
'Gulp Missile','None','None',
'Swift Swim','None','Propeller Tail',
'Swift Swim','None','Propeller Tail',
'Rattled','Static','Klutz',
'Punk Rock','None','Technician',
'Flame Body','White Smoke','Flash Fire',
'Flame Body','White Smoke','Flash Fire',
'Limber','None','Technician',
'Limber','None','Technician',
'Weak Armor','None','Cursed Body',
'Weak Armor','None','Cursed Body',
'Synchronize','None','Magic Bounce',
'Synchronize','None','Magic Bounce',
'Synchronize','None','Magic Bounce',
'Prankster','None','Pickpocket',
'Prankster','None','Pickpocket',
'Prankster','None','Pickpocket',
'Reckless','Guts','Defiant',
'Battle Armor','Tough Claws','Steely Spirit',
'Weak Armor','None','Perish Body',
'Inner Focus','None','Scrappy',
'Tangled Feet','Screen Cleaner','Ice Body',
'Wandering Spirit','None','None',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Battle Armor','None','Defiant',
'Lightning Rod','None','Electric Surge',
'Shield Dust','None','Ice Scales',
'Shield Dust','None','Ice Scales',
'Power Spot','None','None',
'Ice Face','None','None',
'Inner Focus','Synchronize','Psychic Surge',
'Hunger Switch','None','None',
'Sheer Force','Heavy Metal','Heavy Metal',
'Sheer Force','Heavy Metal','Heavy Metal',
'Volt Absorb','Hustle','Sand Rush',
'Volt Absorb','Static','Slush Rush',
'Water Absorb','Strong Jaw','Sand Rush',
'Water Absorb','Ice Body','Slush Rush',
'Light Metal','Heavy Metal','Stalwart',
'Clear Body','Infiltrator','Cursed Body',
'Clear Body','Infiltrator','Cursed Body',
'Clear Body','Infiltrator','Cursed Body',
'Intrepid Sword','None','None',
'Dauntless Shield','None','None',
'Pressure','None','None',
'Inner Focus','None','None',
'Unseen Fist','None','None',
'Leaf Guard','None','None',
'Transistor','None','None',
"Dragon's Maw",'None','None',
'Chilling Neigh','None','None',
'Grim Neigh','None','None',
'Unnerve','None','None',
'Intimidate','None','Sap Sipper',
'Swarm','Sheer Force','Steadfast',
'Guts','Unnerve','Bulletproof',
'Swift Swim','Mold Breaker','Adaptability',
'Inner Focus','None','Poison Touch',
'Intimidate','Poison Point','Swift Swim',
'Healer','None','Contrary',
'Thick Fat','Thick Fat','None',
'Tough Claws','Tough Claws','None',
'Drought','Drought','None',
'Mega Launcher','Mega Launcher','None',
'Adaptability','Adaptability','None',
'No Guard','No Guard','None',
'Trace','Trace','None',
'Shell Armor','Shell Armor','None',
'Shadow Tag','Shadow Tag','None',
'Parental Bond','Parental Bond','None',
'Aerilate','Aerilate','None',
'Mold Breaker','Mold Breaker','None',
'Tough Claws','Tough Claws','None',
'Steadfast','Steadfast','None',
'Insomnia','Insomnia','None',
'Mold Breaker','Mold Breaker','None',
'Sand Force','Sand Force','None',
'Technician','Technician','None',
'Skill Link','Skill Link','None',
'Solar Power','Solar Power','None',
'Sand Stream','Sand Stream','None',
'Lightning Rod','Lightning Rod','None',
'Speed Boost','Speed Boost','None',
'Swift Swim','Swift Swim','None',
'Pixilate','Pixilate','None',
'Magic Bounce','Magic Bounce','None',
'Huge Power','Huge Power','None',
'Filter','Filter','None',
'Pure Power','Pure Power','None',
'Intimidate','Intimidate','None',
'Strong Jaw','Strong Jaw','None',
'Sheer Force','Sheer Force','None',
'Pixilate','Pixilate','None',
'Prankster','Prankster','None',
'Magic Bounce','Magic Bounce','None',
'Refrigerate','Refrigerate','None',
'Aerilate','Aerilate','None',
'Tough Claws','Tough Claws','None',
'Levitate','Levitate','None',
'Levitate','Levitate','None',
'Scrappy','Scrappy','None',
'Sand Force','Sand Force','None',
'Adaptability','Adaptability','None',
'Snow Warning','Snow Warning','None',
'Inner Focus','Inner Focus','None',
'Healer','Healer','None',
'Magic Bounce','Magic Bounce','None',
'Delta Stream','Delta Stream','None',
'Primordial Sea','Primordial Sea','None',
'Desolate Land','Desolate Land','None',
'Gluttony','Hustle','Thick Fat',
'Gluttony','Hustle','Thick Fat',
'Surge Surfer','None','None',
'Slush Rush','None','Snow Cloak',
'Slush Rush','None','Snow Cloak',
'Snow Cloak','None','Snow Warning',
'Snow Cloak','None','Snow Warning',
'Sand Veil','Tangling Hair','Sand Force',
'Sand Veil','Tangling Hair','Sand Force',
'Pickup','Technician','Rattled',
'Fur Coat','Technician','Rattled',
'Magnet Pull','Rock Head','Galvanize',
'Magnet Pull','Rock Head','Galvanize',
'Magnet Pull','Rock Head','Galvanize',
'Poison Touch','Gluttony','Power of Alchemy',
'Poison Touch','Gluttony','Power of Alchemy',
'Harvest','None','None',
'Cursed Body','Lightning Rod','Rock Head',
'Run Away','Tough Claws','Unnerve',
'Run Away','Pastel Veil','Anticipation',
'Run Away','Pastel Veil','Anticipation',
'Gluttony','Own Tempo','Regenerator',
'Quick Draw','Own Tempo','Regenerator',
'Inner Focus','None','Scrappy',
'Levitate','Neutralizing Gas','Misty Surge',
'Vital Spirit','Screen Cleaner','Ice Body',
'Competitive','None','None',
'Defiant','None','None',
'Berserk','None','None',
'Curious Medicine','Own Tempo','Regenerator',
'Weak Armor','None','Cursed Body',
'Gluttony','None','Quick Feet',
'Gluttony','None','Quick Feet',
'Hustle','None','Inner Focus',
'Gorilla Tactics','None','Zen Mode',
'Wandering Spirit','None','None',
'Mimicry','None','None',
'Intimidate','Rock Head','Flash Fire',
'Intimidate','Rock Head','Flash Fire',
'Aftermath','Static','Soundproof',
'Aftermath','Static','Soundproof',
'Blaze','None','Flash Fire',
'Intimidate','Poison Point','Swift Swim',
'Inner Focus','None','Poison Touch',
'Torrent','None','Shell Armor',
'Chlorophyll','Own Tempo','Hustle',
'Illusion','None','None',
'Illusion','None','None',
'Keen Eye','Sheer Force','Defiant',
'Gooey','Shell Armor','Sap Sipper',
'Gooey','Shell Armor','Sap Sipper',
'Strong Jaw','Ice Body','Sturdy',
'Overgrow','None','Long Reach',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Static','None','Lightning Rod',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Forecast','None','None',
'Forecast','None','None',
'Forecast','None','None',
'Pressure','None','None',
'Pressure','None','None',
'Pressure','None','None',
'Shed Skin','None','Overcoat',
'Shed Skin','None','Overcoat',
'Anticipation','None','Overcoat',
'Anticipation','None','Overcoat',
'Flower Gift','None','None',
'Sticky Hold','Sand Force','Storm Drain',
'Sticky Hold','Sand Force','Storm Drain',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Levitate','None','None',
'Pressure','None','Telepathy',
'Pressure','None','Telepathy',
'Levitate','None','None',
'Serene Grace','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Multitype','None','None',
'Rock Head','Mold Breaker','Adaptability',
'Rattled','Adaptability','Mold Breaker',
'Sheer Force','None','Zen Mode',
'Gorilla Tactics','None','Zen Mode',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Chlorophyll','None','Serene Grace',
'Regenerator','None','None',
'Volt Absorb','None','None',
'Intimidate','None','None',
'Overcoat','None','None',
'Turboblaze','None','None',
'Teravolt','None','None',
'Justified','None','None',
'Serene Grace','None','None',
'Download','None','None',
'Download','None','None',
'Download','None','None',
'Download','None','None',
'Battle Bond','None','None',
'Battle Bond','None','None',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Shield Dust','Compound Eyes','Friend Guard',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Flower Veil','None','Symbiosis',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Fur Coat','None','None',
'Keen Eye','Infiltrator','Competitive',
'Stance Change','None','None',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Frisk','None','Insomnia',
'Fairy Aura','None','None',
'Aura Break','None','None',
'Power Construct','None','None',
'Power Construct','None','None',
'Power Construct','None','None',
'Magician','None','None',
'Dancer','None','None',
'Dancer','None','None',
'Dancer','None','None',
'Own Tempo','None','None',
'No Guard','None','Vital Spirit',
'Tough Claws','None','None',
'Schooling','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'RKS System','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Shields Down','None','None',
'Disguise','None','None',
'Prism Armor','None','None',
'Prism Armor','None','None',
'Neuroforce','None','None',
'Soul-Heart','None','None',
'Gulp Missile','None','None',
'Gulp Missile','None','None',
'Punk Rock','None','Technician',
'Weak Armor','None','Cursed Body',
'Weak Armor','None','Cursed Body',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Sweet Veil','None','Aroma Veil',
'Ice Face','None','None',
'Own Tempo','Synchronize','Psychic Surge',
'Hunger Switch','None','None',
'Intrepid Sword','None','None',
'Dauntless Shield','None','None',
'Pressure','None','None',
'Unseen Fist','None','None',
'Leaf Guard','None','None',
'As One (Glastrier)','None','None',
'As One (Spectrier)','None','None'}

local locations = {
    "Littleroot Town",
    "Oldale Town",
    "Dewford Town",
    "Lavaridge Town",
    "Fallarbor Town",
    "Verdanturf Town",
    "Pacifidlog Town",
    "Petalburg City",
    "Slateport City",
    "Mauville City",
    "Rustboro City",
    "Fortree City",
    "Lilycove City",
    "Mossdeep City",
    "Sootopolis City",
    "Ever Grande City",
    "Route 101",
    "Route 102",
    "Route 103",
    "Route 104",
    "Route 105",
    "Route 106",
    "Route 107",
    "Route 108",
    "Route 109",
    "Route 110",
    "Route 111",
    "Route 112",
    "Route 113",
    "Route 114",
    "Route 115",
    "Route 116",
    "Route 117",
    "Route 118",
    "Route 119",
    "Route 120",
    "Route 121",
    "Route 122",
    "Route 123",
    "Route 124",
    "Route 125",
    "Route 126",
    "Route 127",
    "Route 128",
    "Route 129",
    "Route 130",
    "Route 131",
    "Route 132",
    "Route 133",
    "Route 134",
    "Underwater (Route 124)",
    "Underwater (Route 126)",
    "Underwater (Route 127)",
    "Underwater (Route 128)",
    "Underwater (Sootopolis City)",
    "Granite Cave",
    "Mt. Chimney",
    "Safari Zone",
    "Battle Frontier",
    "Petalburg Woods",
    "Rusturf Tunnel",
    "Abandoned Ship",
    "New Mauville",
    "Meteor Falls",
    "Meteor Falls (unused)",
    "Mt. Pyre",
    "Hideout* (Magma HideoutR/Aqua HideoutS)",
    "Shoal Cave",
    "Seafloor Cavern",
    "Underwater (Seafloor Cavern)",
    "Victory Road",
    "Mirage Island",
    "Cave of Origin",
    "Southern Island",
    "Fiery Path",
    "Fiery Path (unused)",
    "Jagged Pass",
    "Jagged Pass (unused)",
    "Sealed Chamber",
    "Underwater (Route 134)",
    "Scorched Slab",
    "Island Cave",
    "Desert Ruins",
    "Ancient Tomb",
    "Inside of Truck",
    "Sky Pillar",
    "Secret Base",
    "Ferry",
    "Pallet Town",
    "Viridian City",
    "Pewter City",
    "Cerulean City",
    "Lavender Town",
    "Vermilion City",
    "Celadon City",
    "Fuchsia City",
    "Cinnabar Island",
    "Indigo Plateau",
    "Saffron City",
    "Route 4 (Pokémon Center)",
    "Route 10 (Pokémon Center)",
    "Route 1",
    "Route 2",
    "Route 3",
    "Route 4",
    "Route 5",
    "Route 6",
    "Route 7",
    "Route 8",
    "Route 9",
    "Route 10",
    "Route 11",
    "Route 12",
    "Route 13",
    "Route 14",
    "Route 15",
    "Route 16",
    "Route 17",
    "Route 18",
    "Route 19",
    "Route 20",
    "Route 21",
    "Route 22",
    "Route 23",
    "Route 24",
    "Route 25",
    "Viridian Forest",
    "Mt. Moon",
    "S.S. Anne",
    "Underground Path (Routes 5-6)",
    "Underground Path (Routes 7-8)",
    "Diglett's Cave",
    "Victory Road",
    "Rocket Hideout",
    "Silph Co.",
    "Pokémon Mansion",
    "Safari Zone",
    "Pokémon League",
    "Rock Tunnel",
    "Seafoam Islands",
    "Pokémon Tower",
    "Cerulean Cave",
    "Power Plant",
    "One Island",
    "Two Island",
    "Three Island",
    "Four Island",
    "Five Island",
    "Seven Island",
    "Six Island",
    "Kindle Road",
    "Treasure Beach",
    "Cape Brink",
    "Bond Bridge",
    "Three Isle Port",
    "Sevii Isle 6",
    "Sevii Isle 7",
    "Sevii Isle 8",
    "Sevii Isle 9",
    "Resort Gorgeous",
    "Water Labyrinth",
    "Five Isle Meadow",
    "Memorial Pillar",
    "Outcast Island",
    "Green Path",
    "Water Path",
    "Ruin Valley",
    "Trainer Tower (exterior)",
    "Canyon Entrance",
    "Sevault Canyon",
    "Tanoby Ruins",
    "Sevii Isle 22",
    "Sevii Isle 23",
    "Sevii Isle 24",
    "Navel Rock",
    "Mt. Ember",
    "Berry Forest",
    "Icefall Cave",
    "Rocket Warehouse",
    "Trainer Tower",
    "Dotted Hole",
    "Lost Cave",
    "Pattern Bush",
    "Altering Cave",
    "Tanoby Chambers",
    "Three Isle Path",
    "Tanoby Key",
    "Birth Island",
    "Monean Chamber",
    "Liptoo Chamber",
    "Weepth Chamber",
    "Dilford Chamber",
    "Scufib Chamber",
    "Rixy Chamber",
    "Viapois Chamber",
    "Ember Spa",
    "Special Area",
    "Aqua Hideout",
    "Magma Hideout",
    "Mirage Tower",
    "Birth Island",
    "Faraway Island",
    "Artisan Cave",
    "Marine Cave",
    "Underwater (Marine Cave)",
    "Terra Cave",
    "Underwater (Route 105)",
    "Underwater (Route 125)",
    "Underwater (Route 129)",
    "Desert Underpass",
    "Altering Cave",
    "Navel Rock",
    "Trainer Hill",
    "(gift egg)",
    "(in-game trade)",
    "(fateful encounter)"
}
