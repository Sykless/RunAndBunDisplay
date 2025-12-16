import os
import sys
import json
import copy
import file
import time
import win32api
import requests
import subprocess
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from datetime import datetime

from data import LEVEL_CAPS, PETALBURG_GYM_SAMELEVELS, TRAINER_RIVAL, MOVE_NAMES, POKEMON_NAMES, STATS_NAMES, ABILITIES_DICO_FR, NATURES_DICO_FR, ZONE_NAMES, FULLDATA_ZONE, ZONE_ORDER
from trainer import TRAINERLIST, OPTIONALS_FIGHTS, ELITE_FOUR_DOUBLE_TEAMS
from file import TEMPOUTPUT_FOLDER, OUTPUT_FOLDER

LEVELUP_CLOCK = 0
BUFFER_UPLOAD_CLOCK = 0
BUFFER_UPLOAD_FREQUENCY = 60 # Every 60 seconds

GIFT_EGG = 253
FATEFUL_ENCOUNTER = 255

TRAINERS_START = 0X020262DD

POKEMON_FONT = "pokemon-gen-4-regular.ttf"
INPUT_FILE = "pokemonData.txt"
SPRITE_FOLDER = "sprites"
POKEMONSPRITE_FOLDER = SPRITE_FOLDER + "/pokemon"
ITEMSPRITE_FOLDER = SPRITE_FOLDER + "/items"
TRAINERSPRITE_FOLDER = SPRITE_FOLDER + "/trainers"
BACKGROUNDPRITE_FOLDER = SPRITE_FOLDER + "/background"
MISCSPRITE_FOLDER = SPRITE_FOLDER + "/misc"

DISPLAY_SPRITE_LEVELUP = "DISPLAY_SPRITE_LEVELUP"
DISPLAY_SPRITE_ITEMS = "DISPLAY_SPRITE_ITEMS"
DISPLAY_TRAINER_ITEMS = "DISPLAY_TRAINER_ITEMS"
DISPLAY_TRAINER_BACKGROUND = "DISPLAY_TRAINER_BACKGROUND"
DISPLAY_MULTIPLE_BOXES = "DISPLAY_MULTIPLE_BOXES"
BOX_DISPLAY_TIME = "BOX_DISPLAY_TIME"
OPTIONAL_ROUTE_123 = "OPTIONAL_ROUTE_123"
OPTIONAL_METEOR_FALLS = "OPTIONAL_METEOR_FALLS"
OPTIONAL_ROUTE_115 = "OPTIONAL_ROUTE_115"
ELITE_FOUR_SIDNEY_TEAM = "ELITE_FOUR_SIDNEY_TEAM"
ELITE_FOUR_PHOEBE_TEAM = "ELITE_FOUR_PHOEBE_TEAM"
ELITE_FOUR_GLACIA_TEAM = "ELITE_FOUR_GLACIA_TEAM"
ELITE_FOUR_DRAKE_TEAM = "ELITE_FOUR_DRAKE_TEAM"
ZONE_START_RUN_TRACKING = "ZONE_START_RUN_TRACKING"
LANG = "LANG"

ZONES_START_TRACKING = [
    ["Route 101"],
    ["Dewford Town", "Route 106", "Route 107"],
    ["Route 110"]
]

POKEMON_SPRITE_WIDTH = 80
POKEMON_SPRITE_HEIGHT = 60
ITEMS_SPRITE_SIZE = 32
LEVEL_UP_SPRITE_SIZE = 18

ITEM_X_POSITION = 42
ITEM_Y_POSITION = 28

LEVELUP_X_POSITION = 49
LEVELUP_Y_POSITION = 4

SPACING_X = -30
SPACING_Y = -10

TRAINER_SPRITE_SIZE = 256
TRAINER_SMALL_SPRITE_SIZE = 192
TRAINER_POKEMON_SPRITE_WIDTH = 160
TRAINER_POKEMON_SPRITE_HEIGHT = 120
TRAINER_ITEMS_SPRITE_SIZE = 64

TRAINER_ITEM_X_POSITION = 84
TRAINER_ITEM_Y_POSITION = 56

BUFF_IMAGE_WIDTH = 400
BUFF_IMAGE_HEIGHT = 450

MOVES_IMAGE_WIDTH = 600
MOVES_IMAGE_HEIGHT = 250

# Retrieve runsHistory.json content once on startup
runsDict = file.loadAllRuns()
runBuffer = {"runs": {}}

class PokemonData:
    def __init__(self, pokedexId, level, itemId):
        self.pokedexId = pokedexId
        self.level = int(level)
        self.itemId = itemId

    def __str__(self):
        return self.pokedexId + " - " + str(self.level) + " - " + self.itemId
    
    def __repr__(self):
        return str(self)

class PokemonFullData:
    def __init__(self, pid, pokedexId, nickname, zoneId, level, ability, nature, move1, move2, move3, move4, hpIV, attackIV, defenseIV, spAttackIV, spDefenseIV, speedIV, alive):
        lang = getLang()

        self.pid = pid
        self.pokedexId = int(pokedexId)
        self.pokemonName = POKEMON_NAMES[lang][self.pokedexId]
        self.nickname = nickname
        self.zoneId = zoneId
        self.zone = getLocation(int(zoneId), self.pokedexId)
        self.level = level
        self.ability = ability if lang == "EN" or ability not in ABILITIES_DICO_FR else ABILITIES_DICO_FR[ability]
        self.nature = nature if lang == "EN" or nature not in NATURES_DICO_FR else NATURES_DICO_FR[nature]
        self.movesId = [int(move1), int(move2), int(move3), int(move4)]
        self.moves = [MOVE_NAMES[lang][self.movesId[0]], MOVE_NAMES[lang][self.movesId[1]], MOVE_NAMES[lang][self.movesId[2]], MOVE_NAMES[lang][self.movesId[3]]]
        self.IVs = [hpIV, attackIV, defenseIV, spAttackIV, spDefenseIV, speedIV]
        self.alive = int(alive)

    def getSimplifiedData(self):
        return [self.pid, self.pokedexId, self.nickname, self.zoneId, self.level, self.ability, self.nature, *self.movesId, *self.IVs, self.alive]

    def __eq__(self, pokemon):
        return (pokemon != None and self.pid == pokemon.pid and self.pokedexId == pokemon.pokedexId and self.nickname == pokemon.nickname and self.zoneId == pokemon.zoneId and self.level == pokemon.level
                and self.ability == pokemon.ability and self.nature == pokemon.nature and self.moves == pokemon.moves and self.IVs == pokemon.IVs and self.alive == pokemon.alive)

    def __str__(self):
        return f'{self.pid} - {self.nickname} ({POKEMON_NAMES[getLang()][self.pokedexId]}) - lvl {self.level} - {self.zone} - {self.ability} - {self.nature} - {"/".join(self.moves)} - {"/".join(self.IVs)}{("" if self.alive else " - 💀")}'

    def __repr__(self):
        return "\n\t" + str(self) + "\n"


# Create env variable for pokemonData.txt file so lua script can know its path
def ensureSetup():

    # Read from .exe script
    if getattr(sys, 'frozen', False):
        ownPath = os.path.dirname(sys.executable)

    # Read from python script
    else:
        ownPath = os.path.dirname(os.path.abspath(__file__))
        
    # Set path as global env variable
    confFilePath = os.path.join(ownPath, INPUT_FILE)
    os.system(f'setx RUNANDBUNREADER_CONFFILE "{confFilePath}"')


def getLang():
    configuration = file.readConfFile()
    return configuration[LANG] if configuration[LANG] in ["EN","FR"] else "EN"


# Parse PARTY|1¤10¤1|2¤25¤2|3¤3¤0 style lines into Pokémon data
def parseLine(line):
    parsedLine = []
    pokemonList = line.split("|")[1:]
    dataType = line.split("|")[0]

    for pokemonData in pokemonList:

        # No Pokémon
        if not pokemonData:
            parsedLine.append(None)

        # No "¤" in line : raw data, add it directly
        elif ("¤" not in pokemonData):
            parsedLine.append(pokemonData)

        # Opponent moves : store split raw data
        elif (dataType == "OPPONENTMOVES"):
            parsedLine.append(pokemonData.split("¤"))

        # Full data, store it in a PokemonFullData object
        elif (dataType == "FULLDATA"):
            parsedLine.append(PokemonFullData(*pokemonData.split("¤")))

        # Multiple info, store them in PokemonData object
        else:
            parsedLine.append(PokemonData(*pokemonData.split("¤")))

    return parsedLine



# Create images from Pokémon sprites
def generatePlayerPartyImage(label, pokemonList, columnNumber, rowNumber, levelCap = None):

    # Retrieve conf file content to check user preferences
    configuration = file.readConfFile()

    # Initialise transparent image
    imageWidth = POKEMON_SPRITE_WIDTH * columnNumber + SPACING_X * (columnNumber - 1)
    imageHeight = POKEMON_SPRITE_HEIGHT * rowNumber + SPACING_Y * (rowNumber - 1)
    outputImage = Image.new("RGBA", (imageWidth, imageHeight), (0,0,0,0))

    # Retrieve level up sprite if needed
    if (configuration[DISPLAY_SPRITE_LEVELUP] and levelCap):
        levelUpPath = os.path.join(MISCSPRITE_FOLDER, "levelup.png")
        levelUpSprite = Image.open(levelUpPath).convert("RGBA").resize((LEVEL_UP_SPRITE_SIZE, LEVEL_UP_SPRITE_SIZE), Image.NEAREST)

    # Iterate on each non-None Pokémon
    for i, pokemonData in enumerate(pokemonList):
        if pokemonData is None:
            continue

        # Retrieve Pokémon sprite (default sprite : Pokéball)
        pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, f"{pokemonData.pokedexId}.png")
        if not os.path.exists(pokemonSpritePath):
            pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, "0.png")

        # Retrieve and resize Pokémon sprite to 80x60 so items can appear small without sizing them down
        pokemonSprite = Image.open(pokemonSpritePath).convert("RGBA").resize((POKEMON_SPRITE_WIDTH, POKEMON_SPRITE_HEIGHT), Image.NEAREST)

        # Compute Pokémon sprite position with spacing (sligh overlap between sprites so they appear closer)
        x = (i % columnNumber) * (POKEMON_SPRITE_WIDTH + SPACING_X)
        y = (i // columnNumber) * (POKEMON_SPRITE_HEIGHT + SPACING_Y)

        # Display Pokémon sprite
        outputImage.paste(pokemonSprite, (x, y), pokemonSprite)

        # Display held item
        if (configuration[DISPLAY_SPRITE_ITEMS] and int(pokemonData.itemId)):

            # Retrieve item sprite (default sprite : blank item)
            itemPath = os.path.join(ITEMSPRITE_FOLDER, f"{pokemonData.itemId}.png")
            if not os.path.exists(itemPath):
                itemPath = os.path.join(ITEMSPRITE_FOLDER, "0.png")

            # Display item sprite
            itemSprite = Image.open(itemPath).convert("RGBA").resize((ITEMS_SPRITE_SIZE, ITEMS_SPRITE_SIZE), Image.NEAREST)
            outputImage.paste(itemSprite, (x + ITEM_X_POSITION, y + ITEM_Y_POSITION), itemSprite)

        # Display level up sprite if current level is lower than level cap
        if (configuration[DISPLAY_SPRITE_LEVELUP] and levelCap and pokemonData.level < int(levelCap)):
            outputImage.paste(levelUpSprite, (x + LEVELUP_X_POSITION, y + LEVELUP_Y_POSITION + LEVELUP_CLOCK), levelUpSprite)

    # Save final image in output folder
    file.safeWriteFile(outputImage, label)



# Generate an image displaying the trainer sprite, Pokémon team and items
def generateTrainerCard(trainer):
    pokemonSprites = []
    itemSprites = []

    # Retrieve conf file content to check user preferences
    configuration = file.readConfFile()

    # Calculate canvas size
    pokemonTeamWidth = 3 * TRAINER_POKEMON_SPRITE_WIDTH - 80
    imageWidth = TRAINER_SPRITE_SIZE + pokemonTeamWidth
    imageHeight = TRAINER_SPRITE_SIZE

    # Custom trainer background is enabled
    if (configuration[DISPLAY_TRAINER_BACKGROUND]):
        backgroundImagePath = os.path.join(BACKGROUNDPRITE_FOLDER, f"{trainer.zone}.png")

        # Cannot find background : set background transparent
        if not os.path.exists(backgroundImagePath):
            outputImage = Image.new("RGBA", (imageWidth, imageHeight), (0,0,0,0))

        else:
            # Retrieve custom background from trainer zone
            backgroundImage = Image.open(backgroundImagePath).convert("RGBA").resize((imageWidth, imageHeight), Image.NEAREST)

            # Darken it and set it as background of outputImage
            enhancer = ImageEnhance.Brightness(backgroundImage)
            backgroundImage = enhancer.enhance(0.6)
            outputImage = backgroundImage.copy()

    # Transparent background
    else:
        outputImage = Image.new("RGBA", (imageWidth, imageHeight), (0,0,0,0))

    # Make sure trainer sprite exists, else don't paste it
    trainerPath = os.path.join(TRAINERSPRITE_FOLDER, f"{trainer.spriteName}.png")
    if os.path.exists(trainerPath):

        # Regular single trainer battle, paste the trauiner sprite
        if (not trainer.doubleSpriteName):
            trainerSprite = Image.open(trainerPath).convert("RGBA").resize((TRAINER_SPRITE_SIZE, TRAINER_SPRITE_SIZE), Image.NEAREST)
            outputImage.paste(trainerSprite, (0,0), trainerSprite)

        # Double battle : display both trainer sprites in smaller size
        else:
            trainerSprite = Image.open(trainerPath).convert("RGBA").resize((TRAINER_SMALL_SPRITE_SIZE, TRAINER_SMALL_SPRITE_SIZE), Image.NEAREST)
            outputImage.paste(trainerSprite, (0,0), trainerSprite)
            
            # Make sure second trainer sprite exists, else don't paste it
            doubleSpritePath = os.path.join(TRAINERSPRITE_FOLDER, f"{trainer.doubleSpriteName}.png")
            
            if os.path.exists(doubleSpritePath):
                doubleSprite = Image.open(doubleSpritePath).convert("RGBA").resize((TRAINER_SMALL_SPRITE_SIZE, TRAINER_SMALL_SPRITE_SIZE), Image.NEAREST)
                outputImage.paste(doubleSprite, (TRAINER_SPRITE_SIZE - TRAINER_SMALL_SPRITE_SIZE, TRAINER_SPRITE_SIZE - TRAINER_SMALL_SPRITE_SIZE), doubleSprite)

    # Retrieve each Pokémon and held item sprites in trainer team
    for pokemonId in range(len(trainer.pokemonTeam)):
        pokedexId = trainer.pokemonTeam[pokemonId]
        itemId = trainer.itemList[pokemonId] if pokemonId < len(trainer.itemList) else None

        # Retrieve Pokémon sprite from pokedexId and display it
        if (pokedexId):
            pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, f"{pokedexId}.png")
            if not os.path.exists(pokemonSpritePath):
                pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, "0.png")

            pokemonSprites.append(Image.open(pokemonSpritePath).convert("RGBA").resize((TRAINER_POKEMON_SPRITE_WIDTH, TRAINER_POKEMON_SPRITE_HEIGHT), Image.NEAREST))
        else:
            pokemonSprites.append(None)

        # Retrieve item sprite from itemId and display it
        if (itemId and configuration[DISPLAY_TRAINER_ITEMS]):
            itemSpritePath = os.path.join(ITEMSPRITE_FOLDER, f"{itemId}.png")
            if not os.path.exists(itemSpritePath):
                itemSpritePath = os.path.join(ITEMSPRITE_FOLDER, "0.png")

            itemSprites.append(Image.open(itemSpritePath).convert("RGBA").resize((TRAINER_ITEMS_SPRITE_SIZE, TRAINER_ITEMS_SPRITE_SIZE), Image.NEAREST))
        else:
            itemSprites.append(None)

    # Paste Pokémon team and items with negative padding to make them closer
    baseX = TRAINER_SPRITE_SIZE - 20
    baseY = 2

    for i, poke in enumerate(pokemonSprites):
        if (poke):
            x = baseX + (i % 3) * (TRAINER_POKEMON_SPRITE_WIDTH - 30)
            y = baseY + (i // 3) * (TRAINER_POKEMON_SPRITE_HEIGHT)
            outputImage.paste(poke, (x,y), poke)

            if (itemSprites[i]):
                x = x + TRAINER_ITEM_X_POSITION
                y = y + TRAINER_ITEM_Y_POSITION
                outputImage.paste(itemSprites[i], (x,y), itemSprites[i])

    # Save image in output folder
    file.safeWriteFile(outputImage, "trainer")


def generateMovesImage(fileName, moveList):
    lang = getLang()

    ppImage = Image.new("RGBA", (MOVES_IMAGE_WIDTH, MOVES_IMAGE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ppImage)
    font = ImageFont.truetype(POKEMON_FONT, 40)

    # Generate an image with each move and remaining PP
    for i in range(len(moveList)):
        moveId, ppLeft = int(moveList[i][0]), moveList[i][1]

        if (moveId):
            draw.text(
                (20, 8 + i * (60)),
                f"PP {MOVE_NAMES[lang][moveId]} : {ppLeft}",
                font = font,
                fill = (255,255,255,255),
                stroke_fill = (0,0,0,255),
                stroke_width = 5
            )

    # Save image in output folder
    file.safeWriteFile(ppImage, fileName)


def generateBuffsImage(fileName, buffsList):
    lang = getLang()
    statId = 0

    buffImage = Image.new("RGBA", (BUFF_IMAGE_WIDTH, BUFF_IMAGE_HEIGHT), (0,0,0,0))
    draw = ImageDraw.Draw(buffImage)
    font = ImageFont.truetype(POKEMON_FONT, 40)

    buffSprite = Image.open(os.path.join(MISCSPRITE_FOLDER, "buff.png")).convert("RGBA")
    debuffSprite = Image.open(os.path.join(MISCSPRITE_FOLDER, "debuff.png")).convert("RGBA")

    # Move Speed buff from 3rd to 5th position
    if (buffsList):
        speedBuff = buffsList.pop(2)
        buffsList.insert(4, speedBuff)

    # Generate an image with each buff/debuff
    for i in range(len(buffsList)):
        statLevel = int(buffsList[i])

        # 6 is default stat level, higher is buff and lower is debuff
        if (statLevel != 6):
            draw.text(
                (20, 8 + statId * (60)),
                f"{STATS_NAMES[lang][i]}",
                font = font,
                fill = (255,255,255,255),
                stroke_fill = (0,0,0,255),
                stroke_width = 5
            )

            # Lower than 6 : debuff
            if (0 <= statLevel < 6):
                buffLevel = 6 - statLevel
                sprite = debuffSprite

            # Higher than 6 : buff
            elif (6 < statLevel <= 12):
                buffLevel = statLevel - 6
                sprite = buffSprite

            # Default : no buff/debuff
            else:
                buffLevel = 0

            # Generate a blue (debuff) or red (buff) triangle for each buff level
            for buffId in range(buffLevel):
                buffImage.paste(sprite, (100 + 47 * buffId, 18 + statId * (60)), sprite)

            statId += 1

    # Save image in output folder
    file.safeWriteFile(buffImage, fileName)


# Retrieve trainer data to determine who has been beaten and who is next
def processDefeatedTrainers(defeatedTrainers, pickedStarter):
    nextTrainer = None
    eliteFourId = 0
    veryNextTrainerId = -1
    lastDefeatedTrainerId = -1
    trainerAddressDict = {}
    configuration = file.readConfFile()

    # Default level cap is 12 when you start a playthrough
    levelCap = 12

    # Save number of gym badges and won battles for run tracking
    gymBadges = 0
    wonBattles = 0

    # Extract original trainer list and add optional fights
    trainerList = copy.deepcopy(TRAINERLIST)
    optionalTrainerList = copy.deepcopy(
        (OPTIONALS_FIGHTS["Route 123"] if configuration[OPTIONAL_ROUTE_123] else []) +
        (OPTIONALS_FIGHTS["Meteor Falls"] if configuration[OPTIONAL_METEOR_FALLS] else []) +
        (OPTIONALS_FIGHTS["Route 115"] if configuration[OPTIONAL_ROUTE_115] else [])
    )

    # Retrieve where elite four starts
    for trainerId in range(len(trainerList) - 1, -1, -1):
        if trainerList[trainerId].name == "Elite Four Sidney":
            eliteFourId = trainerId
            break

    # Swap Singles with Doubles Elite 4 team
    for i, eliteFourConf in enumerate([ELITE_FOUR_SIDNEY_TEAM, ELITE_FOUR_PHOEBE_TEAM, ELITE_FOUR_GLACIA_TEAM, ELITE_FOUR_DRAKE_TEAM]):
        if ("DOUBLE" in configuration[eliteFourConf].upper()):
            eliteFourTrainer = trainerList[eliteFourId + i]
            eliteFourTrainer.pokemonTeam = ELITE_FOUR_DOUBLE_TEAMS[eliteFourTrainer.name]["pokemon"]
            eliteFourTrainer.itemList = ELITE_FOUR_DOUBLE_TEAMS[eliteFourTrainer.name]["items"]

    # Insert optional fights in trainer list
    if (optionalTrainerList):
        trainerList = trainerList[:eliteFourId] + optionalTrainerList + trainerList[eliteFourId:]

    # Create Address -> Bit Number -> Trainer dict
    for trainer in trainerList:
        trainerAddressDict.setdefault(trainer.address, {})[trainer.bitNumber] = trainer

    # Retrieve trainers data from emulator and determine who has been defeated
    for i in range(len(defeatedTrainers)):
        trainerData = defeatedTrainers[i]
        trainerAddress = TRAINERS_START + i

        for bitNumber in range(8):
            if (trainerAddress in trainerAddressDict and bitNumber in trainerAddressDict[trainerAddress]):
                trainerAddressDict[trainerAddress][bitNumber].defeated = bool((int(trainerData) >> bitNumber) & 1)

    # Check which trainer is the next needed to defeat
    for trainerId in range(len(trainerList)):
        trainer = trainerList[trainerId]

        # Defeated trainer (Elite Four resets after Wallace is defeated)
        if (trainer.defeated or "Elite Four" in trainer.name and trainerList[-1].defeated):
            lastDefeatedTrainerId = trainerId
            wonBattles += 1

            # Increase level cap when a boss is defeated
            if ("[Boss]" in trainer.name and trainer.name in LEVEL_CAPS):
                levelCap = LEVEL_CAPS[trainer.name]

            # Defeated a trainer in Petalburg Gym : mark all trainers in the same level as defeated
            if ("Room]" in trainer.name):
                for sameLevelId in PETALBURG_GYM_SAMELEVELS[trainer.name]:
                    trainerList[trainerId + sameLevelId].defeated = True

            # Increase number of badges if a gym leader is defeated, except Leader Tate because only Liza gives the badge
            if (trainer.name.startswith("Leader") and "Tate" not in trainer.name):
                gymBadges += 1

        # Trainer not defeated
        else:
            if (veryNextTrainerId < 0):
                veryNextTrainerId = trainerId

            # Rival team depends in picked starter
            if ("Rival" in trainer.name):
                trainer.pokemonTeam = TRAINER_RIVAL[trainer.name][pickedStarter]["pokemonTeam"]
                trainer.itemList = TRAINER_RIVAL[trainer.name][pickedStarter]["itemList"]

    # Nominal case : next trainer is the first undefeated trainer
    nextTrainer = trainerList[veryNextTrainerId]

    # Particular case : we defeated a trainer in a later zone
    if (veryNextTrainerId < lastDefeatedTrainerId):
        lastDefeatedTrainer = trainerList[lastDefeatedTrainerId]

        # All trainers have been defeated : hardcode last trainer
        if (lastDefeatedTrainerId + 1 == len(trainerList)):
            nextTrainer = lastDefeatedTrainer

        # Stay in the same zone as the last defeated trainer if there are still trainers there
        elif (trainerList[lastDefeatedTrainerId + 1].zone == lastDefeatedTrainer.zone):
            nextTrainer = trainerList[lastDefeatedTrainerId + 1]

    # Generate trainer image
    generateTrainerCard(nextTrainer)

    # Save level cap, won battles, gym badges and lastDefeatedTrainer so we can use them for level up sprites and run tracking
    return levelCap, wonBattles, gymBadges, trainerList[lastDefeatedTrainerId if lastDefeatedTrainerId >= 0 else 0]



# Send data to RunAndBunStats API
def sendRunData(updatedData, fullData):
    keys = file.loadKeys()

    # Only send data with valid keys
    if (keys):
        jsonData = json.dumps({
            "keys": keys["spreadsheet"],
            "updatedData": updatedData,
            "fullData": fullData,
            "lang": getLang()
        }, default = lambda o: o.__dict__)

        # Send keys and updatedData to RunAndBunStats API
        response = requests.post(keys["api"]["url"] + "/updateRun",
            data = jsonData,
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {keys["api"]["password"]}"
            }
        )

        # Logs API repsonse
        if response.status_code != 200:
            print(f"❌ Failed to send data: {response.status_code} - {response.text}\n")


def mapPokemonToZone(fullDataLine):
    pokemonDataZone = copy.deepcopy(FULLDATA_ZONE)
    tradedPokemonList = {}
    possibleOriginalZones = {}

    # Parse each in-game Pokemon and map it to Zone -> Pokémon
    for pokemonData in fullDataLine:
        if (pokemonData.zone in pokemonDataZone):
            pokemonDataZone[pokemonData.zone] = pokemonData
        else:
            customZone = f"{pokemonData.zone} ({pokemonData.pid}-{pokemonData.nickname})"
            pokemonDataZone[customZone] = pokemonData

            if (pokemonData.zone == "In-game Trade"):
                tradedPokemonList[customZone] = pokemonData

    # Process traded Pokémon : assign traded Pokémon to original Pokemon zone
    for customZone, tradedPokemon in tradedPokemonList.items(): 

        # Weezing-Galar
        if (tradedPokemon.pokedexId == 980):
            possibleOriginalZones[customZone] = [originalZone for originalZone, caughtPokemon in pokemonDataZone.items() 
                                                    if originalZone in ["Route 113","Route 112","Fiery Path","Magma Hideout"] and caughtPokemon == None]
        # Growlithe-Hisui / Arcanine-Hisui
        if (993 <= tradedPokemon.pokedexId <= 994):
            possibleOriginalZones[customZone] = [originalZone for originalZone, caughtPokemon in pokemonDataZone.items() 
                                                    if originalZone in ["Oldale Town","Rustboro City","Route 112","Magma Hideout"] and caughtPokemon == None]
        # Zorua-Hisui / Zoroark-Hisui
        if (1002 <= tradedPokemon.pokedexId <= 1003):
            possibleOriginalZones[customZone] = [originalZone for originalZone, caughtPokemon in pokemonDataZone.items() 
                                                    if originalZone in ["Mirage Tower","Route 113","Seafloor Cavern","Route 130"] and caughtPokemon == None]

    # If traded Pokemon have been found with multiple potential zones, find the best one (not used by other trade, first available)
    if (len(possibleOriginalZones) > 0):
        bestZones = pickBestZones(possibleOriginalZones)

        # Replace "In-game Trade" zone by zone used by traded Pokemon
        for customZone, bestZoneName in bestZones.items():
            pokemonDataZone[bestZoneName] = pokemonDataZone[customZone]
            del pokemonDataZone[customZone]

    return pokemonDataZone


# Set current time as end date for all non-ended runs
def updateOldRunsEndDate(currentRunId, currentTime):
    for runId, runData in runsDict["runs"].items():
        if (runId != currentRunId and not runData["runData"]["runEnd"]):

            # Update run end date in runsHistory.json
            runsDict["runs"][runId]["runData"]["runEnd"] = currentTime

            # Save run end update in buffer
            if runId not in runBuffer["runs"]:
                runBuffer["runs"][runId] = {"pokemonToUpdate": {}, "runDataToUpdate": {}, "releasedPokemon": {}}
            runBuffer["runs"][runId]["runDataToUpdate"] = runsDict["runs"][runId]["runData"]


# Save each update in a buffer that is uploaded every minute
def updateRunBuffer(fullDataLine, wonBattles, gymBadges, lastDefeatedTrainer):
    global runBuffer
    currentPokemon = {}
    configuration = file.readConfFile()

    # Don't track runs if disabled by user
    if (configuration[ZONE_START_RUN_TRACKING]):

        # Map each encounter to its caught zone
        pokemonDataZone = mapPokemonToZone(fullDataLine)

        # Only take into accounts runs with Pokémons from Routes 101-102-103 (for runId)
        if (pokemonDataZone["Route 101"] and pokemonDataZone["Route 102"] and pokemonDataZone["Route 103"]):
            
            # Create unique runId from Route 101-102-103 encounters PIDs
            currentRunId = pokemonDataZone["Route 101"].pid + "-" + pokemonDataZone["Route 102"].pid + "-" + pokemonDataZone["Route 103"].pid

            # New run : initialize it
            if currentRunId not in runsDict["runs"]:
                currentTime = datetime.now().strftime("%d/%m/%Y %H:%M")
                runStart = currentTime

                # Initialize dict and run start time
                runsDict["runs"][currentRunId] = {"runData": {
                    "runNumber": -1, "runStart": "", "runEnd": "", "deadPokemon": "", "wonBattles": "", "gymBadges": 0, "personalBest": {"trainerName": {}, "trainerTeam": []}
                }, "pokemonData": {}}

                # We started a new run : update old run end date
                updateOldRunsEndDate(currentRunId, currentTime)

            # Existing run : retrieve runStart from runsHistory.json
            else:
                runStart = runsDict["runs"][currentRunId]["runData"]["runStart"]
            
            # Init buffer for current run
            if currentRunId not in runBuffer["runs"]:
                runBuffer["runs"][currentRunId] = {"pokemonToUpdate": {}, "runDataToUpdate": {}, "releasedPokemon": {}}

            # Populate currentPokemon object with runsHistory.json file data
            for zone, pokemonData in runsDict["runs"][currentRunId]["pokemonData"].items():
                currentPokemon[zone] = PokemonFullData(*pokemonData)

            # Track run data
            deadPokemon = 0
            totalPokemon = 0
            runNumber = runsDict["runs"][currentRunId]["runData"]["runNumber"]

            # Check which Pokémon have been updated
            for zone, pokemon in pokemonDataZone.items():

                # Missing Pokémon
                if (pokemon == None and zone in currentPokemon):
                    releasedPokemon = runBuffer["runs"][currentRunId]["releasedPokemon"]

                    # Increase number of occurrences missing
                    releasedPokemon[zone] = releasedPokemon.get(zone, 0) + 1

                    # Pokémon disappear and reappear when picked up in PC, so only considered them released when gone for the whole BUFFER_UPLOAD_FREQUENCY
                    if (releasedPokemon[zone] == BUFFER_UPLOAD_FREQUENCY):
                        runBuffer["runs"][currentRunId]["pokemonToUpdate"][zone] = None
                        del runsDict["runs"][currentRunId]["pokemonData"][zone]
                    
                    # Default : Replace missing pokemon with previously saved data
                    else:
                        pokemon = currentPokemon[zone]

                # Pokemon currently in the run
                if (pokemon):
                    if (not pokemon.alive):
                        deadPokemon += 1
                    totalPokemon += 1

                    # New or updated Pokémon : save it in Sheets
                    if (zone not in currentPokemon or currentPokemon[zone] != pokemon):
                        runBuffer["runs"][currentRunId]["pokemonToUpdate"][zone] = pokemon

            # Only start tracking runs when reached the tracking zone
            trackRun = False
            trackingZones = ZONES_START_TRACKING[configuration[ZONE_START_RUN_TRACKING] - 1 if 1 <= configuration[ZONE_START_RUN_TRACKING] <= 3 else 1]

            for zone in trackingZones:
                if pokemonDataZone[zone]: trackRun = True

            # If a run reached a tracking zone, consider it valid and assign it a run number
            if (runNumber == -1 and trackRun):
                runNumber = getNumberOfRuns() + 1

                # Include all run data from the run in the buffer
                runBuffer["runs"][currentRunId]["runDataToUpdate"] = runsDict["runs"][currentRunId]["runData"]

                # Include all Pokémon from the run in the buffer
                for zone, pokemonData in runsDict["runs"][currentRunId]["pokemonData"].items():
                    runBuffer["runs"][currentRunId]["pokemonToUpdate"][zone] = PokemonFullData(*pokemonData)

            # Determine number of battles from enabled optional battles
            numberOfBattles = len(TRAINERLIST +
                (OPTIONALS_FIGHTS["Route 123"] if configuration[OPTIONAL_ROUTE_123] else []) +
                (OPTIONALS_FIGHTS["Meteor Falls"] if configuration[OPTIONAL_METEOR_FALLS] else []) +
                (OPTIONALS_FIGHTS["Route 115"] if configuration[OPTIONAL_ROUTE_115] else [])
            )

            # Convert current run data to dict
            currentRunData = {
                "runNumber": runNumber,
                "runStart": runStart,
                "runEnd": runsDict["runs"][currentRunId]["runData"]["runEnd"],
                "wonBattles": f"{wonBattles}/{numberOfBattles}",
                "deadPokemon": f"{deadPokemon}/{totalPokemon}",
                "gymBadges": gymBadges,
                "personalBest": {
                    "trainerName": lastDefeatedTrainer.name,
                    "trainerSprite": lastDefeatedTrainer.spriteName,
                    "trainerTeam": lastDefeatedTrainer.pokemonTeam
                }
            }

            # Check which run parameter has been updated
            for parameterName, parameterValue in currentRunData.items():
                if (runsDict["runs"][currentRunId]["runData"][parameterName] != parameterValue):
                    runBuffer["runs"][currentRunId]["runDataToUpdate"][parameterName] = parameterValue

            # If runEnd date was set and runData has been updated : continue run
            if (runsDict["runs"][currentRunId]["runData"]["runEnd"] and runBuffer["runs"][currentRunId]["runDataToUpdate"]):

                # We continued a run : remove current run end date
                currentRunData["runEnd"] = ""
                runBuffer["runs"][currentRunId]["runDataToUpdate"]["runEnd"] = ""
                
                # We continued a run : update old run end date
                updateOldRunsEndDate(currentRunId, datetime.now().strftime("%d/%m/%Y %H:%M"))

            # Save current run data
            runsDict["runs"][currentRunId]["runData"] = currentRunData

            # Save current run pokemon data
            for zone, pokemon in pokemonDataZone.items():
                if (pokemon): runsDict["runs"][currentRunId]["pokemonData"][zone] = pokemon.getSimplifiedData()

            # Sort runs by runNumber desc and Pokémon list by zone
            runsDict["runs"] = sortRuns(runsDict["runs"])
            runsDict["runs"][currentRunId]["pokemonData"] = sortPokemon(runsDict["runs"][currentRunId]["pokemonData"])
            runBuffer["runs"][currentRunId]["pokemonToUpdate"] = sortPokemon(runBuffer["runs"][currentRunId]["pokemonToUpdate"])

            # Save runsHistory.json
            file.saveRuns(runsDict)


def uploadRunBuffer():
    global runBuffer

    updatedData = {"runs": {}}
    fullData = {"runs": {}}
    newData = False

    # Iterate over each updated run
    for runId, bufferData in runBuffer["runs"].items():
        runNumber = runsDict["runs"][runId]["runData"]["runNumber"]

        # Only upload data for runs that reached tracking zones
        if (runNumber > 0 and (bufferData["pokemonToUpdate"] or bufferData["runDataToUpdate"])):
            newData = True

            # Populate updatedData with data to update
            updatedData["runs"][runId] = {"runData": {}, "pokemonData": {}}
            updatedData["runs"][runId]["pokemonData"] = bufferData["pokemonToUpdate"]
            updatedData["runs"][runId]["runData"] = bufferData["runDataToUpdate"]

            # Populate fullData with full runs data
            fullData["runs"][runId] = {"runData": {}, "pokemonData": {}}
            fullData["runs"][runId]["runData"] = runsDict["runs"][runId]["runData"]
            fullData["runs"][runId]["pokemonData"] = {zone: PokemonFullData(*pokemonData) for zone, pokemonData in runsDict["runs"][runId]["pokemonData"].items()}


    # Call RunAndBunStats API to update Google Sheets runs file
    if (newData):

        # Send updated data to RunAndBunStats API
        sendRunData(updatedData, fullData)

    # Reset runBuffer
    runBuffer = {"runs": {}}



def sortRuns(runs):
    return dict(sorted(
        runs.items(),
        key = lambda item: item[1]["runData"]["runNumber"],
        reverse = True
    ))

def sortPokemon(pokemonDict):
    return dict(sorted(
        pokemonDict.items(),
        key = lambda item: ZONE_ORDER.index(item[0]) if item[0] in ZONE_ORDER else len(ZONE_ORDER)
    ))

# Runs are sorted by runNumber desc, so just retrieve the first one
def getNumberOfRuns():
    topRun = next(iter(runsDict["runs"].values()))
    return topRun["runData"]["runNumber"] if topRun["runData"]["runNumber"] > 0 else 0


# Retrieve zone name from zoneId
def getLocation(zoneId, pokedexId):

    # Starter is met through "Fateful encounter", counts as a dedicated zone
    if (zoneId == FATEFUL_ENCOUNTER and 387 <= pokedexId <= 395):
        return "Starter"
    
    # Hoenn starter is hatched from Gift Eff, hardcode Lavaridge Town zone
    elif (zoneId == GIFT_EGG and 252 <= pokedexId <= 260):
        return "Lavaridge Town"
    
    # Default : retrieve zone from zoneId
    else:
        return ZONE_NAMES[zoneId]


# Find most probable zone for traded Pokémon
def pickBestZones(zoneDict):
    usedZones = set()
    keys = list(zoneDict.keys())
    result = {key: None for key in keys}

    def backtrack(i):
        if i == len(keys):
            return True # all keys assigned

        key = keys[i]
        for zone in zoneDict[key]:
            if zone in usedZones:
                continue

            # Assign this zone
            usedZones.add(zone)
            result[key] = zone

            if backtrack(i + 1):
                return True

            # Backtrack
            usedZones.remove(zone)
            result[key] = None

        return False

    backtrack(0)
    return result


# Main loop
def mainLoop():
    global LEVELUP_CLOCK # global LEVELUP_CLOCK to alternate between up and down level up sprite position every second
    global BUFFER_UPLOAD_CLOCK
    global runBuffer
    os.makedirs(OUTPUT_FOLDER, exist_ok = True) # Create outputImage folder is not exists
    os.makedirs(TEMPOUTPUT_FOLDER, exist_ok = True) # Create .tmp folder is not exists
    subprocess.run(["attrib", "+h", TEMPOUTPUT_FOLDER], shell = True)
    print("Run&BunDisplay en cours d'exécution...") # Notify user when ready to use

    boxClock = 0 # Alternate between every box every 5 seconds
    boxDisplayTime = 5 # Default : 5 seconds
    boxNumber = 0 # Track which box we're currently displaying
    BUFFER_UPLOAD_CLOCK = 0 # Upload all data retrieved in a minute to Google Sheets API

    while True:
        try:
            # Retrieve data written by lua scipt
            emulatorData = file.safeReadFile(INPUT_FILE)

            if emulatorData:
                lines = emulatorData.splitlines()

                # Retrieve conf file content to check user preferences
                configuration = file.readConfFile()
                displayMultipleBoxes = configuration[DISPLAY_MULTIPLE_BOXES]
                boxDisplayTime = configuration[BOX_DISPLAY_TIME]

                # Retrieve each line and parse its data
                for line in lines:
                    if line.startswith("BOX"):
                        fullBox = parseLine(line)
                        numberOfBoxes = int(len(fullBox) / 30) if fullBox else 1

                        # 5th second : display next box
                        if (boxClock == boxDisplayTime - 1):
                            boxNumber = (boxNumber + 1) % numberOfBoxes if displayMultipleBoxes else 0

                        # Take the 30 Pokémon from the provided box
                        boxLine = fullBox[30*boxNumber : 30*(boxNumber + 1)]
                        
                    elif line.startswith("DEAD"):
                        deadLine = parseLine(line)

                    elif line.startswith("PARTYBUFFS"):
                        partyBuffs = parseLine(line)

                    elif line.startswith("OPPONENTBUFFS"):
                        opponentBuffs = parseLine(line)

                    elif line.startswith("OPPONENTMOVES"):
                        opponentMoves = parseLine(line)
                    
                    elif line.startswith("PARTY"):
                        partyLine = parseLine(line)

                    elif line.startswith("TRAINERS"):
                        defeatedTrainers = parseLine(line)

                    elif line.startswith("STARTER"):
                        pickedStarter = int(parseLine(line)[0])

                    elif line.startswith("FULLDATA"):
                        fullDataLine = parseLine(line)

                # Process trainers data to generate next trainer card and retrieve current level cap
                levelCap, wonBattles, gymBadges, lastDefeatedTrainer = processDefeatedTrainers(defeatedTrainers, pickedStarter)

                # Create png images from parsed data
                generatePlayerPartyImage("party", partyLine, 6, 1, levelCap)
                generatePlayerPartyImage("box", boxLine, 6, 5, levelCap)
                generatePlayerPartyImage("dead", deadLine, 6, 5)

                # Generate opponent moves and PP left if in battle
                generateMovesImage("moves-opponent-1", opponentMoves[:4])
                generateMovesImage("moves-opponent-2", opponentMoves[4:])

                # Generate buffs/debuffs for player and opponent in battle
                generateBuffsImage("buffs-opponent-1", opponentBuffs[:7])
                generateBuffsImage("buffs-opponent-2", opponentBuffs[7:])
                generateBuffsImage("buffs-player-1", partyBuffs[:7])
                generateBuffsImage("buffs-player-2", partyBuffs[7:])

                # Track every update performed in-game (new battle, level up, )
                updateRunBuffer(fullDataLine, wonBattles, gymBadges, lastDefeatedTrainer)
            
                # Once every minute, upload buffer to RunAndBunStats API
                if (BUFFER_UPLOAD_CLOCK == 0):
                    uploadRunBuffer()
            
            # Check file every second
            time.sleep(1)
            LEVELUP_CLOCK = 1 - LEVELUP_CLOCK # Two positions
            BUFFER_UPLOAD_CLOCK = (BUFFER_UPLOAD_CLOCK + 1) % BUFFER_UPLOAD_FREQUENCY # Every 60 seconds
            boxClock = (boxClock + 1) % boxDisplayTime # Every 5 seconds by default, customizable
        
        # Don't stop script if an error occurs, just print it in the logs
        except Exception as e:
            print("An error occurred :", e)


# Upload buffer before exiting program
def onExit(event):
    uploadRunBuffer()
    return False
win32api.SetConsoleCtrlHandler(onExit, True)

# Start script
if __name__ == "__main__":
    ensureSetup()
    mainLoop()