import os
import sys
import copy
import file
import time
import requests
import subprocess
from PIL import Image, ImageEnhance

from data import LEVEL_CAPS, PETALBURG_GYM_SAMELEVELS, TRAINER_RIVAL, MOVE_NAMES, POKEMON_NAMES, ZONE_NAMES, FULLDATA_ZONE
from trainer import TRAINER_ADDRESS_DICT, TRAINERLIST
from file import TEMPOUTPUT_FOLDER, OUTPUT_FOLDER

LEVELUP_CLOCK = 0

GIFT_EGG = 253
FATEFUL_ENCOUNTER = 255
TRAINERS_START = 0X020262DD

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
ENABLE_RUN_TRACKING = "ENABLE_RUN_TRACKING"

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
        self.pid = pid
        self.pokedexId = int(pokedexId)
        self.pokemonName = POKEMON_NAMES[self.pokedexId]
        self.nickname = nickname
        self.zoneId = zoneId
        self.zone = getLocation(int(zoneId), self.pokedexId)
        self.level = level
        self.ability = ability
        self.nature = nature
        self.movesId = [int(move1), int(move2), int(move3), int(move4)]
        self.moves = [MOVE_NAMES[self.movesId[0]], MOVE_NAMES[self.movesId[1]], MOVE_NAMES[self.movesId[2]], MOVE_NAMES[self.movesId[3]]]
        self.IVs = [hpIV, attackIV, defenseIV, spAttackIV, spDefenseIV, speedIV]
        self.alive = int(alive)

    def getSimplifiedData(self):
        return [self.pid, self.pokedexId, self.nickname, self.zoneId, self.level, self.ability, self.nature, *self.movesId, *self.IVs, self.alive]

    def __eq__(self, pokemon):
        return (pokemon != None and self.pid == pokemon.pid and self.pokedexId == pokemon.pokedexId and self.nickname == pokemon.nickname and self.zoneId == pokemon.zoneId and self.level == pokemon.level
                and self.ability == pokemon.ability and self.nature == pokemon.nature and self.moves == pokemon.moves and self.IVs == pokemon.IVs and self.alive == pokemon.alive)

    def __str__(self):
        return f'{self.pid} - {self.nickname} ({POKEMON_NAMES[self.pokedexId]}) - lvl {self.level} - {self.zone} - {self.ability} - {self.nature} - {"/".join(self.moves)} - {"/".join(self.IVs)}{("" if self.alive else " - 💀")}'


# Create env variable for pokemonData.txt file so lua script can know its path
def ensureSetup():

    # Read from .exe script
    if getattr(sys, 'frozen', False):
        ownPath = os.path.dirname(sys.executable)

    # Read from python script
    else:
        ownPath = os.path.dirname(os.path.abspath(__file__))
        
    # Set path as global env variable
    confFilePath = os.path.join(ownPath, 'pokemonData.txt')
    os.system(f'setx RUNANDBUNREADER_CONFFILE "{confFilePath}"')



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



# Retrieve trainer data to determine who has been beaten and who is next
def processDefeatedTrainers(defeatedTrainers, pickedStarter):
    nextTrainer = None
    veryNextTrainerId = -1
    lastDefeatedTrainerId = -1

    # Default level cap is 12 when you start a playthrough
    levelCap = 12

    # Set all trainers as undefeated by default
    for trainer in TRAINERLIST:
        trainer.defeated = False

    # Retrieve trainers data from emulator and determine who has been defeated
    for i in range(len(defeatedTrainers)):
        trainerData = defeatedTrainers[i]
        trainerAddress = TRAINERS_START + i

        for bitNumber in range(8):
            if (trainerAddress in TRAINER_ADDRESS_DICT and bitNumber in TRAINER_ADDRESS_DICT[trainerAddress]):
                TRAINER_ADDRESS_DICT[trainerAddress][bitNumber].defeated = bool((int(trainerData) >> bitNumber) & 1)

    # Check which trainer is the next needed to defeat
    for trainerId in range(len(TRAINERLIST)):
        trainer = TRAINERLIST[trainerId]

        if (trainer.defeated):
            lastDefeatedTrainerId = trainerId

            # Increase level cap when a boss is defeated
            if ("[Boss]" in trainer.name and trainer.name in LEVEL_CAPS):
                levelCap = LEVEL_CAPS[trainer.name]

            # Defeated a trainer in Petalburg Gym : mark all trainers in the same level as defeated
            if ("Room]" in trainer.name):
                for sameLevelId in PETALBURG_GYM_SAMELEVELS[trainer.name]:
                    TRAINERLIST[trainerId + sameLevelId].defeated = True

        # Trainer not defeated
        else:
            if (veryNextTrainerId < 0):
                veryNextTrainerId = trainerId

            # Rival team depends in picked starter
            if ("Rival" in trainer.name):
                trainer.pokemonTeam = TRAINER_RIVAL[trainer.name][pickedStarter]["pokemonTeam"]
                trainer.itemList = TRAINER_RIVAL[trainer.name][pickedStarter]["itemList"]

    # Nominal case : next trainer is the first undefeated trainer
    nextTrainer = TRAINERLIST[veryNextTrainerId]

    # Particular case : we defeated a trainer in a later zone
    if (veryNextTrainerId < lastDefeatedTrainerId):
        lastDefeatedTrainer = TRAINERLIST[lastDefeatedTrainerId]

        # All trainers have been defeated : hardcode last trainer
        if (lastDefeatedTrainerId + 1 == len(TRAINERLIST)):
            nextTrainer = lastDefeatedTrainer

        # Stay in the same zone as the last defeated trainer if there are still trainers there
        elif (TRAINERLIST[lastDefeatedTrainerId + 1].zone == lastDefeatedTrainer.zone):
            nextTrainer = TRAINERLIST[lastDefeatedTrainerId + 1]

    # Generate trainer image
    generateTrainerCard(nextTrainer)

    # Save level cap so we can use it for level up sprites
    return levelCap



# Send data to RunAndBunStats API
def sendPokemonData(methodName, pokemonList):
    keys = file.loadKeys()

    # Only send data with valid keys
    if (keys):

        # Send keys and pokemonData to RunAndBunStats API
        response = requests.post(f"http://127.0.0.1:5000/{methodName}", json = {
            "keys": keys,
            "pokemonData": {key: pokemon.__dict__ if pokemon else None for key, pokemon in pokemonList.items()}
        })

        # Logs API repsonse
        if response.status_code == 200:
            print("✅ Data sent successfully.")
        else:
            print(f"❌ Failed to send data: {response.status_code} - {response.text}")
    else:
        print(f"❌ Invalid keys")


def initRun():
    sendPokemonData("initRun", FULLDATA_ZONE)


def uploadPokemonData(fullDataLine):
    pokemonDataZone = copy.deepcopy(FULLDATA_ZONE)
    pokemonToUpdate = {}
    tradedPokemonList = {}
    possibleOriginalZones = {}

    # Parse each in-game Pokemon and map it to Zone -> Pokémon
    for pokemonData in fullDataLine:
        if (pokemonData.zone in pokemonDataZone):
            pokemonDataZone[pokemonData.zone] = pokemonData
        else:
            customZone = f"{pokemonData.zone} ({pokemonData.pid})"
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

    # Only take into accounts runs with Pokémons from Routes 101-102-103 (for runId) and at least one Pokémon from Myokara
    if (pokemonDataZone["Route 101"] and pokemonDataZone["Route 102"] and pokemonDataZone["Route 103"]
        and (pokemonDataZone["Dewford Town"] or pokemonDataZone["Route 106"] or pokemonDataZone["Route 107"])):
        
        # Create unique runId from Route 101-102-103 encounters PIDs
        runId = pokemonDataZone["Route 101"].pid + "-" + pokemonDataZone["Route 102"].pid + "-" + pokemonDataZone["Route 103"].pid
        runsDict = file.loadRunDict(runId)

        # Populate currentRun object with runs.json file data
        currentRun = {}
        for zone, pokemonData in runsDict["runs"][runId].items():
            currentRun[zone] = PokemonFullData(*pokemonData)
        
        # Iterate over all zones from emulator data
        for zone, pokemon in pokemonDataZone.items():

            # Released Pokémon : remove it from Sheets
            if (pokemon == None and zone in currentRun):
                pokemonToUpdate[zone] = None
                del runsDict["runs"][runId][zone]

            # New or updated Pokémon : save it in Sheets
            if (pokemon and (zone not in currentRun or currentRun[zone] != pokemon)):
                pokemonToUpdate[zone] = pokemon

        # Populate runs.json
        for zone, pokemon in pokemonDataZone.items():
            if (pokemon): runsDict["runs"][runId][zone] = pokemon.getSimplifiedData()
        file.saveRuns(runsDict)

        # Call RunAndBunStats API to update Google Sheets runs file
        if (len(pokemonToUpdate) > 0):
            sendPokemonData("updatePokemonCards", pokemonToUpdate)


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
    os.makedirs(OUTPUT_FOLDER, exist_ok = True) # Create outputImage folder is not exists
    os.makedirs(TEMPOUTPUT_FOLDER, exist_ok = True) # Create .tmp folder is not exists
    subprocess.run(["attrib", "+h", TEMPOUTPUT_FOLDER], shell = True)
    print("Run&BunDisplay en cours d'exécution...") # Notify user when ready to use

    boxClock = 0 # Alternate between every box every 5 seconds
    boxNumber = 0 # Track which box we're currently displaying

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
                    if line.startswith("PARTY"):
                        partyLine = parseLine(line)
                        
                    elif line.startswith("BOX"):
                        fullBox = parseLine(line)
                        numberOfBoxes = int(len(fullBox) / 30) if fullBox else 1

                        # 5th second : display next box
                        if (boxClock == boxDisplayTime - 1):
                            boxNumber = (boxNumber + 1) % numberOfBoxes if displayMultipleBoxes else 0

                        # Take the 30 Pokémon from the provided box
                        boxLine = fullBox[30*boxNumber : 30*(boxNumber + 1)]
                        
                    elif line.startswith("DEAD"):
                        deadLine = parseLine(line)

                    elif line.startswith("TRAINERS"):
                        defeatedTrainers = parseLine(line)

                    elif line.startswith("STARTER"):
                        pickedStarter = int(parseLine(line)[0])

                    elif line.startswith("FULLDATA"):
                        fullDataLine = parseLine(line)
                        # initRun()
                        uploadPokemonData(fullDataLine)
                        return "Test"

                # Process trainers data to generate next trainer card and retrieve current level cap
                levelCap = processDefeatedTrainers(defeatedTrainers, pickedStarter)

                # Create png images from parsed data
                generatePlayerPartyImage("party", partyLine, 6, 1, levelCap)
                generatePlayerPartyImage("box", boxLine, 6, 5, levelCap)
                generatePlayerPartyImage("dead", deadLine, 6, 5)
                
                        
            # Check file every second
            time.sleep(1)
            LEVELUP_CLOCK = (LEVELUP_CLOCK + 1) % 1 # Every second
            boxClock = (boxClock + 1) % boxDisplayTime # Every 5 seconds by default, customizable
        
        # Don't stop script if an error occurs, just print it in the logs
        except Exception as e:
            print("An error occurred :", e)


# Start script
if __name__ == "__main__":
    ensureSetup()
    mainLoop()