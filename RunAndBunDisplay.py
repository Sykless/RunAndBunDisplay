import os
import sys
import time
import subprocess
from PIL import Image, ImageEnhance

LEVELUP_CLOCK = 0

TRAINERS_START = 0X020262DD

SPRITE_FOLDER = "sprites"
POKEMONSPRITE_FOLDER = SPRITE_FOLDER + "/pokemon"
ITEMSPRITE_FOLDER = SPRITE_FOLDER + "/items"
TRAINERSPRITE_FOLDER = SPRITE_FOLDER + "/trainers"
BACKGROUNDPRITE_FOLDER = SPRITE_FOLDER + "/background"
MISCSPRITE_FOLDER = SPRITE_FOLDER + "/misc"

TEMPOUTPUT_FOLDER = ".tmp"
OUTPUT_FOLDER = "outputImage"
INPUT_FILE = "pokemonData.txt"
CONF_FILE = "configuration.txt"

DISPLAY_SPRITE_LEVELUP = "DISPLAY_SPRITE_LEVELUP"
DISPLAY_SPRITE_ITEMS = "DISPLAY_SPRITE_ITEMS"
DISPLAY_TRAINER_ITEMS = "DISPLAY_TRAINER_ITEMS"
DISPLAY_TRAINER_BACKGROUND = "DISPLAY_TRAINER_BACKGROUND"
DISPLAY_MULTIPLE_BOXES = "DISPLAY_MULTIPLE_BOXES"
BOX_DISPLAY_TIME = "BOX_DISPLAY_TIME"

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

class TrainerData:
    def __init__(self, name, zone, address, bitNumber, pokemonTeam, itemList, spriteName, doubleSpriteName = None):
        self.name = name
        self.zone = zone
        self.address = address
        self.bitNumber = bitNumber
        self.pokemonTeam = pokemonTeam
        self.itemList = itemList
        self.spriteName = spriteName
        self.doubleSpriteName = doubleSpriteName

        # Populate TRAINER_ADDRESS_DICT so we find the trainer with its address
        TRAINER_ADDRESS_DICT.setdefault(address, {})[bitNumber] = self

    def __str__(self):
        return f'TrainerData("{self.name}", {self.address:#010X}, {self.bitNumber}, [{",".join(str(pokedexId) for pokedexId in self.pokemonTeam)}], "{self.spriteName}")'

    # Generate an image displaying the trainer sprite, Pokémon team and items
    def generateTrainerCard(self):
        pokemonSprites = []
        itemSprites = []

        # Retrieve conf file content to check user preferences
        configuration = readConfFile()

        # Calculate canvas size
        pokemonTeamWidth = 3 * TRAINER_POKEMON_SPRITE_WIDTH - 80
        imageWidth = TRAINER_SPRITE_SIZE + pokemonTeamWidth
        imageHeight = TRAINER_SPRITE_SIZE

        # Custom trainer background is enabled
        if (configuration[DISPLAY_TRAINER_BACKGROUND]):
            backgroundImagePath = os.path.join(BACKGROUNDPRITE_FOLDER, f"{self.zone}.png")

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
        trainerPath = os.path.join(TRAINERSPRITE_FOLDER, f"{self.spriteName}.png")
        if os.path.exists(trainerPath):

            # Regular single trainer battle, paste the trauiner sprite
            if (not self.doubleSpriteName):
                trainerSprite = Image.open(trainerPath).convert("RGBA").resize((TRAINER_SPRITE_SIZE, TRAINER_SPRITE_SIZE), Image.NEAREST)
                outputImage.paste(trainerSprite, (0,0), trainerSprite)

            # Double battle : display both trainer sprites in smaller size
            else:
                trainerSprite = Image.open(trainerPath).convert("RGBA").resize((TRAINER_SMALL_SPRITE_SIZE, TRAINER_SMALL_SPRITE_SIZE), Image.NEAREST)
                outputImage.paste(trainerSprite, (0,0), trainerSprite)
                
                # Make sure second trainer sprite exists, else don't paste it
                doubleSpritePath = os.path.join(TRAINERSPRITE_FOLDER, f"{self.doubleSpriteName}.png")
                
                if os.path.exists(doubleSpritePath):
                    doubleSprite = Image.open(doubleSpritePath).convert("RGBA").resize((TRAINER_SMALL_SPRITE_SIZE, TRAINER_SMALL_SPRITE_SIZE), Image.NEAREST)
                    outputImage.paste(doubleSprite, (TRAINER_SPRITE_SIZE - TRAINER_SMALL_SPRITE_SIZE, TRAINER_SPRITE_SIZE - TRAINER_SMALL_SPRITE_SIZE), doubleSprite)

        # Retrieve each Pokémon and held item sprites in trainer team
        for pokemonId in range(len(self.pokemonTeam)):
            pokedexId = self.pokemonTeam[pokemonId]
            itemId = self.itemList[pokemonId] if pokemonId < len(self.itemList) else None

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
        safeWriteFile(outputImage, "trainer")



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



# Read file safely even if used by lua script
def safeReadFile(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None



# Write file safely even if used by OBS
def safeWriteFile(image, fileName):

    # Save final image in .tmp folder to avoid OBS reading partially written image
    tempOutputPath = os.path.join(TEMPOUTPUT_FOLDER, f"{fileName.lower()}.png")
    outputPath = os.path.join(OUTPUT_FOLDER, f"{fileName.lower()}.png")
    image.save(tempOutputPath, "PNG")
    image.close()

    # Swap temp image and output image
    try:
        os.replace(tempOutputPath, outputPath)

    # PermissionError errors might occur because OBS is reading the image, don't print those
    except PermissionError:
        pass



# Read configuration.txt and convert user preferences into boolean
def readConfFile():
    configuration = {}
    configurationFile = safeReadFile(CONF_FILE)

    for line in configurationFile.splitlines():
        if (line.count("=") == 1):
            configurationSplit = line.split("=")
            configuration[configurationSplit[0]] = int(configurationSplit[1])

    return configuration



# Parse PARTY|1-10-1|2-25-2|3-3-0 style lines into Pokémon data
def parseLine(line):
    parsedLine = []
    pokemonList = line.split("|")[1:]

    for pokemonData in pokemonList:

        # No Pokémon
        if not pokemonData:
            parsedLine.append(None)

        # No "-" in line : raw data, add it directly
        elif ("-" not in pokemonData):
            parsedLine.append(pokemonData)

        # Multiple info, store them in PokemonData object
        else:
            parsedLine.append(PokemonData(*pokemonData.split("-")))

    return parsedLine



# Create images from Pokémon sprites
def buildPlayerPokemonImage(label, pokemonList, columnNumber, rowNumber, levelCap = None):

    # Retrieve conf file content to check user preferences
    configuration = readConfFile()

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
    safeWriteFile(outputImage, label)



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
    nextTrainer.generateTrainerCard()

    # Save level cap so we can use it for level up sprites
    return levelCap



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
            emulatorData = safeReadFile(INPUT_FILE)

            if emulatorData:
                lines = emulatorData.splitlines()

                # Retrieve conf file content to check user preferences
                configuration = readConfFile()
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

                # Process trainers data to generate next trainer card and retrieve current level cap
                levelCap = processDefeatedTrainers(defeatedTrainers, pickedStarter)

                # Create png images from parsed data
                buildPlayerPokemonImage("party", partyLine, 6, 1, levelCap)
                buildPlayerPokemonImage("box", boxLine, 6, 5, levelCap)
                buildPlayerPokemonImage("dead", deadLine, 6, 5)
                
                        
            # Check file every second
            time.sleep(1)
            LEVELUP_CLOCK = (LEVELUP_CLOCK + 1) % 1 # Every second
            boxClock = (boxClock + 1) % boxDisplayTime # Every 5 seconds by default, customizable
        
        # Don't stop script if an error occurs, just print it in the logs
        except Exception as e:
            print("An error occurred :", e)


LEVEL_CAPS = {
    "Team Aqua Grunt Petalburg Woods [Boss]": 17,
    "Team Aqua Grunt Museum #2 [Boss]": 21,
    "Leader Brawly [Boss]": 25,
    "Leader Roxanne [Boss]": 32,
    "Trainer Chelle Daycare [Boss]": 35,
    "Leader Wattson [Boss]": 38,
    "Trainer Rival Cycling Road [Boss]": 42,
    "Leader Norman [Boss]": 48,
    "Winstrate Vito Fallarbor [Boss]": 54,
    "Magma Leader Maxie Mt. Chimney [Boss]": 57,
    "Leader Flannery [Double] [Boss]": 65,
    "Aqua Admin Shelly Weather Institute [Boss]": 66,
    "Trainer Rival Bridge [Double] [Boss]": 69,
    "Leader Winona [Boss]": 73,
    "Trainer Rival Lilycove [Boss]": 76,
    "Aqua Leader Archie Mt. Pyre [Tag Battle] [Boss]": 79,
    "Magma Leader Maxie Magma Hideout [Boss]": 81,
    "Aqua Admin Matt [Boss]": 85,
    "Leader Liza [Boss]": 89,
    "Aqua Leader Archie Seafloor Cavern [Boss]": 91,
    "Leader Juan [Double] [Boss]": 95,
    "Winstrate Vito Victory Road [Boss]": 99,
    "Champion Wallace [Boss]": 100
}

PETALBURG_GYM_SAMELEVELS = {
    "Cool Trainer Mary [Accuracy Room]": [1],
    "Cool Trainer Randall [Speed Room]": [-1],
    "Cool Trainer Alexia [Defense Room]": [1,2],
    "Cool Trainer George [Recovery Room]": [-1,1],
    "Cool Trainer Parker [Critical-Hit Room]": [-1,-2],
    "Cool Trainer Jody [Strength Room]": [1],
    "Cool Trainer Berke [Recoil Room]": [-1]
}

TRAINER_RIVAL = {
    "Trainer Rival Cycling Road [Boss]" : [
        {"pokemonTeam": [876,257,230,763,461,869], "itemList": [478,460,472,503,481,452]},
        {"pokemonTeam": [876,260,763,229,701,282], "itemList": [478,553,503,480,452,481]},
        {"pokemonTeam": [876,254,229,230,701,210], "itemList": [478,460,480,522,452,503]},
    ],
    "Trainer Rival Bridge [Double] [Boss]" : [
        {"pokemonTeam": [928,272,373,695,376,9], "itemList": [314,479,348,481,503,472]},
        {"pokemonTeam": [929,130,887,462,454,972], "itemList": [315,479,353,576,481,528]},
            {"pokemonTeam": [927,226,706,958,448,423], "itemList": [313,479,472,481,345,553]},
    ],
    "Trainer Rival Lilycove [Boss]" : [
        {"pokemonTeam": [445,68,461,809,982,928], "itemList": [554,472,479,503,522,314]},
        {"pokemonTeam": [445,65,461,809,983,929], "itemList": [554,481,479,503,528,315]},
        {"pokemonTeam": [445,68,65,809,984,927], "itemList": [554,472,481,503,528,313]},
    ]
}

# Address -> Bit Number -> Trainer, built during TRAINERLIST initialisation
TRAINER_ADDRESS_DICT = {}
TRAINERLIST = [
    TrainerData("Youngster Calvin", "Route 102", 0X02026397, 6, [261,506,821], [None,None,None], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Bug Catcher Rick", "Route 102", 0X020263BC, 7, [736,204,850], [520,520,520], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Youngster Allen", "Route 102", 0X02026399, 5, [672,667,54], [522,520,520], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Lass Tiana", "Route 102", 0X020263BB, 3, [684,327], [53,53], "TRAINER_PIC_LASS"),
    TrainerData("Triathlete Mikey", "Route 104", 0X02026397, 7, [98,852,193], [520,520,484], "TRAINER_PIC_RUNNING_TRIATHLETE_M"),
    TrainerData("Fisherman Darian", "Route 104", 0X020263C7, 0, [129,129], [442,481], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Lady Cindy", "Route 104", 0X0202637E, 2, [572,39,231], [520,520,520], "TRAINER_PIC_LADY"),
    TrainerData("Team Aqua Grunt Petalburg Woods [Boss]", "Route 104", 0X020263EC, 5, [318,453,102], [520,569,520], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Fisherman Elliot", "Route 106", 0X0202639A, 3, [120,271,846], [427,522,348], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Ruin Maniac Georgie", "Route 106", 0X0202639A, 4, [557,769,303,446], [53,522,472,569], "TRAINER_PIC_RUIN_MANIAC"),
    TrainerData("Tuber Chandler", "Route 109", 0X020263C7, 2, [238,239,240], [430,428,426], "TRAINER_PIC_TUBER_M"),
    TrainerData("Tuber Lola", "Route 109", 0X02026377, 1, [662,507], [522,522], "TRAINER_PIC_TUBER_F"),
    TrainerData("Sailor Edmond", "Route 109", 0X020263AD, 3, [278,418,536], [520,553,522], "TRAINER_PIC_SAILOR"),
    TrainerData("Fisherman Bill", "Route 109", 0X020263AD, 2, [10,13,265,664,824], [442,442,442,442,443], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Tuber Ricky", "Route 109", 0X02026378, 0, [190,33,404], [425,487,522], "TRAINER_PIC_TUBER_M"),
    TrainerData("Tuber Hailey", "Route 109", 0X020263C7, 1, [619,30,180], [431,522,428], "TRAINER_PIC_TUBER_F"),
    TrainerData("Camper Gavi [Optional]", "Route 110", 0X02026399, 6, [400,77,603,192,269], [522,523,523,522,487], "TRAINER_PIC_CAMPER"),
    TrainerData("Team Aqua Grunt Museum #1 [Boss]", "Slateport Museum", 0X02026372, 4, [198,690,564], [522,487,553], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Museum #2 [Boss]", "Slateport Museum", 0X02026372, 5, [747,592,544], [487,522,496], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Battle Girl Laura", "Dewford Gym", 0X020263A5, 2, [447,759,56], [494,523,522], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Sailor Brenden", "Dewford Gym", 0X020263B7, 4, [979,214], [523,522], "TRAINER_PIC_SAILOR"),
    TrainerData("Battle Girl Lilith", "Dewford Gym", 0X020263B7, 5, [296,56,166], [445,481,475], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Black Belt Cristian", "Dewford Gym", 0X020263B7, 6, [307,67,533], [558,472,431], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Black Belt Takao", "Dewford Gym", 0X02026386, 3, [286,619,427], [446,431,474], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Battle Girl Jocelyn", "Dewford Gym", 0X020263A5, 1, [352,622,499,783], [522,494,522,523], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Leader Brawly [Boss]", "Dewford Gym", 0X020263DD, 0, [891,428,256,237,61,559], [528,501,522,507,477,494], "TRAINER_PIC_LEADER_BRAWLY"),
    TrainerData("Bug Catcher Lyle", "Petalburg Woods", 0X020263BD, 0, [168,402,291], [471,522,460], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Bug Maniac James", "Petalburg Woods", 0X020263BD, 5, [636,329,292,743], [494,554,459,476], "TRAINER_PIC_BUG_MANIAC"),
    TrainerData("Rich Boy Winston", "Route 104", 0X02026381, 0, [676,262], [472,472], "TRAINER_PIC_RICH_BOY"),
    TrainerData("Fisherman Ivan", "Route 104", 0X0202639A, 1, [211,117,364], [487,522,522], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Twins Gina And Mia [Double]", "Route 104", 0X020263AC, 3, [702,35,63,777], [523,494,522,522], "TRAINER_PIC_TWINS"),
    TrainerData("Lass Haley", "Route 104", 0X020263BB, 4, [457,44,397,322], [522,522,345,551], "TRAINER_PIC_LASS"),
    TrainerData("Youngster Joey", "Route 116", 0X02026398, 2, [20,988,17], [475,522,522], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Lass Janice", "Route 116", 0X020263BB, 5, [741,729,547], [522,483,556], "TRAINER_PIC_LASS"),
    TrainerData("Rich Boy Dawson", "Route 116", 0X020263C6, 6, [775,130], [555,523], "TRAINER_PIC_RICH_BOY"),
    TrainerData("School Kid Jerry & Youngster Johnson [Double]", "Route 116", 0X02026392, 1, [516,284,None,432,215], [427,522,None,522,481], "TRAINER_PIC_SCHOOL_KID_M", "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Bug Catcher Jose", "Route 116", 0X020263BD, 1, [127,632,666], [522,522,522], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Lady Sarah", "Route 116", 0X020263C6, 7, [210,863], [523,342], "TRAINER_PIC_LADY"),
    TrainerData("School Kid Karen", "Route 116", 0X02026393, 0, [114,845,26], [522,523,522], "TRAINER_PIC_SCHOOL_KID_F"),
    TrainerData("Hiker Clark", "Route 116", 0X020263BE, 7, [51,964], [433,481], "TRAINER_PIC_HIKER"),
    TrainerData("Hiker Devan", "Route 116", 0X020263CE, 1, [57,834,207], [522,522,348], "TRAINER_PIC_HIKER"),
    TrainerData("Youngster Josh", "Rustboro Gym", 0X02026398, 0, [696,566,408], [522,444,522], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Youngster Tommy", "Rustboro Gym", 0X02026398, 1, [185,838,345,222], [522,551,472,553], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Hiker Marc", "Rustboro Gym", 0X020263B7, 3, [75,968,305,525], [502,557,576,472], "TRAINER_PIC_HIKER"),
    TrainerData("Leader Roxanne [Boss]", "Rustboro Gym", 0X020263DC, 7, [625,1164,699,565,337,338], [481,433,522,553,502,522], "TRAINER_PIC_LEADER_ROXANNE"),
    TrainerData("Hiker Mike", "Rusturf Tunnel", 0X020263BF, 3, [844,476,508,36], [522,472,522,266], "TRAINER_PIC_HIKER"),
    TrainerData("Breeder Lydia", "Route 117", 0X020263B4, 1, [576,107,849,302], [472,522,522,523], "TRAINER_PIC_POKEMON_BREEDER_F"),
    TrainerData("Breeder Corgi", "Route 117", 0X0202638C, 3, [59,676,448,310,836], [523,472,522,522,481], "TRAINER_PIC_POKEMON_BREEDER_M"),
    TrainerData("Psychic Brandi & Battle Girl Aisha [Double]", "Route 117", 0X020263CE, 5, [826,97,None,454,297], [522,523,None,559,522], "TRAINER_PIC_PSYCHIC_F", "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Battle Girl Luna", "Route 117", 0X020263CE, 3, [466,776,763,853,195], [523,523,522,522,553], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Triathlete Dylan", "Route 117", 0X0202639D, 4, [617,966,85], [476,440,522], "TRAINER_PIC_RUNNING_TRIATHLETE_M"),
    TrainerData("Triathlete Maria", "Route 117", 0X0202639E, 1, [78,573,277], [522,522,425], "TRAINER_PIC_RUNNING_TRIATHLETE_F"),
    TrainerData("Breeder Isaac", "Route 117", 0X020263B3, 2, [344,601,101,478], [522,441,522,522], "TRAINER_PIC_POKEMON_BREEDER_M"),
    TrainerData("Sr. And Jr. Anna And Meg [Double]", "Route 117", 0X02026393, 7, [587,119,171,105], [483,481,522,523], "TRAINER_PIC_SR_AND_JR"),
    TrainerData("Trainer Chelle Daycare [Boss]", "Route 117", 0X020263EC, 7, [131,112,468,416,978,301], [523,494,471,522,462,425], "TRAINER_PIC_LEAF"),
    TrainerData("Camper Tyron & Aroma Lady Celina [Double]", "Route 111", 0X020263C8, 1, [83,505,24,None,182,45], [393,522,487,None,522,522], "TRAINER_PIC_CAMPER", "TRAINER_PIC_AROMA_LADY"),
    TrainerData("Picnicker Bianca", "Route 111", 0X020263C8, 2, [12,512,234], [443,460,522], "TRAINER_PIC_PICNICKER"),
    TrainerData("Kindler Hayden", "Route 111", 0X020263C8, 3, [1171,631,323,776], [523,522,522,522], "TRAINER_PIC_KINDLER"),
    TrainerData("Fisherman Dale", "Route 110", 0X0202639A, 5, [55,87,581,230], [345,350,459,339], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Psychic Edward", "Route 110", 0X0202638D, 0, [358,203,528], [503,522,481], "TRAINER_PIC_PSYCHIC_M"),
    TrainerData("Trainer Wally", "Mauville", 0X020263C2, 0, [281,987], [None,None], "TRAINER_PIC_WALLY"),
    TrainerData("Guitarist Kirk", "Mauville Gym", 0X02026387, 7, [871,426,849,958], [523,451,432,522], "TRAINER_PIC_GUITARIST"),
    TrainerData("Battle Girl Vivian", "Mauville Gym", 0X020263C1, 1, [313,135,1169,523,596], [481,522,522,522,522], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Youngster Ben", "Mauville Gym", 0X02026398, 3, [137,479,969,101,25], [494,472,522,522,392], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Guitarist Shawn & Guitarist Angelo [Double]", "Mauville Gym", 0X02026388, 2, [311,702,None,312,601], [557,481,None,506,522], "TRAINER_PIC_GUITARIST", "TRAINER_PIC_GUITARIST"),
    TrainerData("Leader Wattson [Boss]", "Mauville Gym", 0X020263DD, 1, [462,171,1067,807,604,921], [576,472,522,557,472,307], "TRAINER_PIC_LEADER_WATTSON"),
    TrainerData("Psychic Jaclyn", "Route 110", 0X0202638E, 3, [49,178,326,475], [522,523,569,522], "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Triathlete Abigail", "Route 110", 0X0202639C, 6, [620,291,51,82], [474,442,479,494], "TRAINER_PIC_CYCLING_TRIATHLETE_F"),
    TrainerData("Triathlete Anthony", "Route 110", 0X0202639C, 0, [405,319,628], [522,477,523], "TRAINER_PIC_CYCLING_TRIATHLETE_M"),
    TrainerData("Triathlete Alyssa", "Route 110", 0X020263C7, 5, [359,1155], [481,476], "TRAINER_PIC_CYCLING_TRIATHLETE_F"),
    TrainerData("Triathlete Benjamin", "Route 110", 0X0202639C, 1, [417,521,20,189], [478,522,445,348], "TRAINER_PIC_CYCLING_TRIATHLETE_M"),
    TrainerData("Triathlete Jacob", "Route 110", 0X0202639B, 7, [419,586,758], [479,480,487], "TRAINER_PIC_CYCLING_TRIATHLETE_M"),
    TrainerData("Triathlete Jasmine", "Route 110", 0X0202639C, 7, [976,571,865], [522,440,444], "TRAINER_PIC_CYCLING_TRIATHLETE_F"),
    TrainerData("Trainer Rival Cycling Road [Boss]", "Route 110", 0X020263ED, 3, [876,254,229,230,701,210], [478,460,480,522,452,503], "TRAINER_PIC_MAY"),
    TrainerData("Pokéfan Isabel & Pokéfan Kaleb [Double]", "Route 110", 0X02026395, 6, [1174,71,None,115,22], [481,569,None,523,522], "TRAINER_PIC_POKEFAN_F", "TRAINER_PIC_POKEFAN_M"),
    TrainerData("Guitarist Brian", "Route 110", 0X020263C7, 4, [295,441,695,143], [444,522,522,472], "TRAINER_PIC_GUITARIST"),
    TrainerData("Collector Edwin", "Route 110", 0X020263B0, 0, [157,160,154], [426,427,429], "TRAINER_PIC_COLLECTOR"),
    TrainerData("Black Belt Rhett & Guitarist Marcos [Double]", "Route 103", 0X020263C7, 7, [740,214,62,None,169,715], [522,445,523,None,522,522], "TRAINER_PIC_BLACK_BELT", "TRAINER_PIC_GUITARIST"),
    TrainerData("Pokéfan Miguel", "Route 103", 0X02026394, 5, [702,777,778], [481,496,522], "TRAINER_PIC_POKEFAN_M"),
    TrainerData("Aroma Lady Daisy", "Route 103", 0X02026374, 4, [1162,754,972,671], [522,503,523,472], "TRAINER_PIC_AROMA_LADY"),
    TrainerData("Twins Amy And Liv [Double]", "Route 103", 0X020263AC, 1, [94,823,53,124,97], [487,478,481,522,472], "TRAINER_PIC_TWINS"),
    TrainerData("Fisherman Andrew", "Route 103", 0X0202639A, 0, [593,847,779,781], [522,344,341,485], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Cool Trainer Mary [Accuracy Room]", "Petalburg Gym", 0X0202637B, 1, [680,623,1173,68], [494,522,522,472], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Randall [Speed Room]", "Petalburg Gym", 0X02026378, 7, [291,545,469,319,257], [480,475,476,479,481], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Alexia [Defense Room]", "Petalburg Gym", 0X0202637B, 2, [750,598,9,823,344], [523,472,472,522,502], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer George [Recovery Room]", "Petalburg Gym", 0X02026379, 1, [812,59,121,985,36], [472,472,472,487,472], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Parker [Critical-Hit Room]", "Petalburg Gym", 0X02026379, 0, [689,430,818,224,452], [471,471,522,471,471], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Jody [Strength Room]", "Petalburg Gym", 0X0202637B, 3, [409,289,308,534,105], [479,442,481,522,394], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Berke [Recoil Room]", "Petalburg Gym", 0X02026379, 2, [1141,448,398,626,500], [444,523,522,576,444], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Leader Norman [Boss]", "Petalburg Gym", 0X020263DD, 3, [233,184,660,648,573,911], [494,523,481,522,465,297], "TRAINER_PIC_LEADER_NORMAN"),
    TrainerData("Winstrate Victor", "Winstrate House", 0X02026394, 4, [733,587], [522,522], "TRAINER_PIC_POKEFAN_M"),
    TrainerData("Winstrate Victoria", "Winstrate House", 0X02026395, 3, [460,851,537], [522,472,522], "TRAINER_PIC_POKEFAN_F"),
    TrainerData("Winstrate Vivi", "Winstrate House", 0X020263BB, 6, [743,330,185], [481,522,522], "TRAINER_PIC_LASS"),
    TrainerData("Winstrate Vicky", "Winstrate House", 0X02026397, 0, [934,553], [320,522], "TRAINER_PIC_EXPERT_F"),
    TrainerData("Picnicker Irene", "Route 111", 0X020263AB, 4, [542,36,508], [481,472,425], "TRAINER_PIC_PICNICKER"),
    TrainerData("Camper Travis", "Route 111", 0X0202638B, 2, [558,561,221], [522,472,494], "TRAINER_PIC_CAMPER"),
    TrainerData("Ruin Maniac Bryan & Picnicker Celia [Double]", "Route 111", 0X020263CD, 0, [526,34,None,556,423], [523,522,None,523,553], "TRAINER_PIC_RUIN_MANIAC", "TRAINER_PIC_PICNICKER"),
    TrainerData("Camper Branden", "Route 111", 0X020263CD, 1, [227,389,760,464], [498,472,472,472], "TRAINER_PIC_CAMPER"),
    TrainerData("Collector John", "Route 111", 0X020263AA, 5, [879,655,630,745,28], [442,489,496,481,522], "TRAINER_PIC_COLLECTOR"),
    TrainerData("Camper Beau", "Route 111", 0X0202638A, 4, [476,770,863], [481,459,503], "TRAINER_PIC_CAMPER"),
    TrainerData("Ninja Boy Jinra", "Route 111", 0X020263AA, 6, [31,6,76,332], [479,351,459,459], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Ruin Maniac Rigger", "Route 111", 0X02026375, 4, [887,553,91,372], [478,502,522,494], "TRAINER_PIC_RUIN_MANIAC"),
    TrainerData("Camper Drew", "Route 111", 0X0202638A, 3, [450,673,969,530], [522,472,522,497], "TRAINER_PIC_CAMPER"),
    TrainerData("Cool Trainer Wilton", "Route 111", 0X02026379, 6, [212,465,768,164,51], [550,503,503,511,481], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Black Belt Daisuke", "Route 111", 0X02026387, 5, [766,538,214], [None,523,445], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Cool Trainer Brooke", "Route 111", 0X0202637B, 6, [584,73,87,467,614], [522,504,472,504,460], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Pokémaniac Wyatt", "Route 113", 0X020263C8, 7, [695,758,352,206], [479,522,503,522], "TRAINER_PIC_POKEMANIAC"),
    TrainerData("Ninja Boy Lao", "Route 113", 0X020263A4, 3, [169,971,980], [479,487,487], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Picnicker Sophie", "Route 113", 0X020263C8, 4, [685,463,842,869], [523,522,573,472], "TRAINER_PIC_PICNICKER"),
    TrainerData("Ninja Boy Lung", "Route 113", 0X020263A4, 4, [336,617,658], [557,479], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Rich Boy Santos", "Route 113", 0X02026398, 7, [38,473,275,157], [522,522,522,444], "TRAINER_PIC_RICH_BOY"),
    TrainerData("Twins Tori And Tia [Double]", "Route 113", 0X020263C4, 5, [560,779,576,625], [523,522,523,522], "TRAINER_PIC_TWINS"),
    TrainerData("Youngster Jaylen", "Route 113", 0X02026398, 6, [123,663,128], [442,348,522], "TRAINER_PIC_YOUNGSTER"),
    TrainerData("Bird Keeper Coby", "Route 113", 0X020263C8, 5, [623,841,738], [522,573,522], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Parasol Lady Madeline", "Route 113", 0X020263A6, 2, [26,973,464], [522,394,472], "TRAINER_PIC_PARASOL_LADY"),
    TrainerData("Camper Lawrence", "Route 113", 0X020263C8, 6, [398,457,130], [460,481,472], "TRAINER_PIC_CAMPER"),
    TrainerData("Winstrate Vito Fallarbor [Boss]", "Fallarbor", 0X020263ED, 1, [65,169,286,342,277,933], [481,522,345,341,479,319], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Picnicker Charlotte", "Route 114", 0X020263C9, 2, [85,132,470], [442,481,472], "TRAINER_PIC_PICNICKER"),
    TrainerData("Rich Boy Braw", "Route 114", 0X0202638A, 6, [34,430,778,143], [474,522,479,472], "TRAINER_PIC_RICH_BOY"),
    TrainerData("Fisherman Nolan", "Route 114", 0X0202639A, 6, [350,121], [522,476], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Fisherman Kai", "Route 114", 0X020263C9, 1, [186,847,348,768], [472,427,522,350], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Fisherman Claude", "Route 114", 0X0202639A, 2, [211,134,693,395], [481,472,528,472], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Kindler Bernie", "Route 114", 0X02026389, 6, [1064,514,435,621], [460,573,340,496], "TRAINER_PIC_KINDLER"),
    TrainerData("Picnicker Angelina", "Route 114", 0X020263C9, 0, [232,475,432], [576,472,425], "TRAINER_PIC_PICNICKER"),
    TrainerData("Expert Nancy", "Route 114", 0X020263AB, 0, [437,830,865,780,51], [484,501,393,522,433], "TRAINER_PIC_EXPERT_F"),
    TrainerData("Sr. And Jr. Tyra And Ivy [Double]", "Route 114", 0X020263C4, 7, [707,229,861,668], [550,479,523,339], "TRAINER_PIC_SR_AND_JR"),
    TrainerData("Pokémaniac Steve", "Route 114", 0X02026381, 7, [89,855], [557,460], "TRAINER_PIC_POKEMANIAC"),
    TrainerData("Hiker Lucas", "Route 114", 0X020263BE, 5, [208,369,472], [528,522,446], "TRAINER_PIC_HIKER"),
    TrainerData("Hiker Lenny", "Route 114", 0X020263BE, 4, [598,346,340], [550,472,480], "TRAINER_PIC_HIKER"),
    TrainerData("Black Belt Nob", "Route 115", 0X02026386, 7, [620,760], [479,523], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Battle Girl Cyndy", "Route 115", 0X020263A5, 3, [853,286,237], [472,446,479], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Psychic Marlene", "Route 115", 0X020263CE, 0, [866,563], [522,472], "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Collector Hector", "Route 115", 0X020263B0, 1, [631,632,199,335], [477,522,472,446], "TRAINER_PIC_COLLECTOR"),
    TrainerData("Kindler Bryant & Aroma Lady Shayla [Double]", "Route 112", 0X020263CD, 2, [324,6,None,470,3], [522,528,None,343,479], "TRAINER_PIC_KINDLER", "TRAINER_PIC_AROMA_LADY"),
    TrainerData("Camper Merc", "Route 112", 0X0202638A, 5, [57,452,709,123], [477,354,523,494], "TRAINER_PIC_CAMPER"),
    TrainerData("Hiker Trent", "Route 112", 0X020263BE, 3, [411,660,219], [498,555,498], "TRAINER_PIC_HIKER"),
    TrainerData("Hiker Brice", "Route 112", 0X020263BE, 2, [437,338,337,323], [564,512,512,340], "TRAINER_PIC_HIKER"),
    TrainerData("Picnicker Carol", "Route 112", 0X020263AA, 7, [832,181,327], [503,557,555], "TRAINER_PIC_PICNICKER"),
    TrainerData("Team Magma Grunt Mt Chimney #1 & Team Magma Grunt Mt Chimney #2 [Double]", "Mt. Chimney", 0X020263B8, 3, [617,539,None,1225,1155], [481,502,None,476,356], "TRAINER_PIC_MAGMA_GRUNT_M", "TRAINER_PIC_MAGMA_GRUNT_F"),
    TrainerData("Magma Admin Tabitha", "Mt. Chimney", 0X020263BA, 5, [324,348,196,71,940], [462,472,479,522,326], "TRAINER_PIC_MAGMA_ADMIN"),
    TrainerData("Magma Leader Maxie Mt. Chimney [Boss]", "Mt. Chimney", 0X020262E1, 3, [558,202,142,784,893,937], [498,528,354,472,503,323], "TRAINER_PIC_MAGMA_LEADER_MAXIE"),
    TrainerData("Hiker Eric & Picnicker Autumn [Double]", "Jagged Pass", 0X020263BF, 0, [472,874,None,598,497,836], [348,481,None,496,444,479], "TRAINER_PIC_HIKER", "TRAINER_PIC_PICNICKER"),
    TrainerData("Triathlete Julio", "Jagged Pass", 0X020263B6, 6, [523,400,601], [557,462,522], "TRAINER_PIC_CYCLING_TRIATHLETE_M"),
    TrainerData("Camper Ethan", "Jagged Pass", 0X0202638B, 0, [626,468], [555,471], "TRAINER_PIC_CAMPER"),
    TrainerData("Picnicker Diana", "Jagged Pass", 0X020263AB, 2, [812,40,59,828], [503,479,472,454], "TRAINER_PIC_PICNICKER"),
    TrainerData("Kindler Jace", "Lavaridge Gym", 0X02026389, 4, [815,663,1064,609], [474,348,472,444], "TRAINER_PIC_KINDLER"),
    TrainerData("Kindler Cole", "Lavaridge Gym", 0X02026389, 1, [324,224,980,467,776], [528,471,522,523,522], "TRAINER_PIC_KINDLER"),
    TrainerData("Cool Trainer Gerald", "Lavaridge Gym", 0X020263C1, 0, [38,338,733], [481,340,340], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Kindler Keegan", "Lavaridge Gym", 0X02026389, 5, [976,242,555], [479,555,479], "TRAINER_PIC_KINDLER"),
    TrainerData("Kindler Axle", "Lavaridge Gym", 0X02026389, 3, [392,229,851], [481,522,561], "TRAINER_PIC_KINDLER"),
    TrainerData("Kindler Jeff", "Lavaridge Gym", 0X02026389, 2, [324,463,435,136], [576,503,522,446], "TRAINER_PIC_KINDLER"),
    TrainerData("Battle Girl Danielle", "Lavaridge Gym", 0X020263C1, 2, [985,623,500,257,330], [503,472,444,460,479], "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Hiker Eli", "Lavaridge Gym", 0X020263AE, 5, [780,34,464,59,655], [528,487,551,340,479], "TRAINER_PIC_HIKER"),
    TrainerData("Leader Flannery [Double] [Boss]", "Lavaridge Gym", 0X020263DD, 2, [908,758,244,727,663,973], [294,481,522,503,479,394], "TRAINER_PIC_LEADER_FLANNERY"),
    TrainerData("Tuber Simon", "Seashore House", 0X02026378, 1, [419,184,702,335,53,272], [445,503,570,446,472,522], "TRAINER_PIC_TUBER_M"),
    TrainerData("Beauty Johanna", "Seashore House", 0X020263C0, 7, [31,131,350,730,779,763], [487,472,472,472,341,474], "TRAINER_PIC_BEAUTY"),
    TrainerData("Sailor Dwayne", "Seashore House", 0X020263AD, 5, [693,130,689,319,317,68], [522,552,460,354,576,505], "TRAINER_PIC_SAILOR"),
    TrainerData("Swimmer♀ Rose & Swimmer♂ Deandre [Double]", "Route 118", 0X02026374, 5, [119,87,340,None,130,503], [481,523,522,None,348,350], "TRAINER_PIC_SWIMMER_F", "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Fisherman Wade", "Route 118", 0X0202639B, 0, [121,368,367], [478,553,552], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Fisherman Barny", "Route 118", 0X0202639A, 7, [279,550,614], [481,442,522], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Guitarist Dalton", "Route 118", 0X02026388, 4, [812,849,277], [442,487,446], "TRAINER_PIC_GUITARIST"),
    TrainerData("Bird Keeper Perry & Bird Keeper Chester [Double]", "Route 118", 0X020263A1, 6, [738,330,None,22,430], [561,554,None,471,471], "TRAINER_PIC_BIRD_KEEPER", "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Bug Maniac Taylor", "Route 119", 0X0202638C, 1, [589,47,756,141], [503,459,556,350], "TRAINER_PIC_BUG_MANIAC"),
    TrainerData("Bug Catcher Doug", "Route 119", 0X020263BD, 2, [213,414,314], [576,348,443], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Fisherman Phil", "Route 119", 0X020263A2, 0, [370,370,370], [427,427,427], "TRAINER_PIC_FISHERMAN"),
    TrainerData("Ranger Lydian", "Route 119", 0X020263C6, 5, [230,350,695,691], [522,472,477,460], "TRAINER_PIC_POKEMON_RANGER_M"),
    TrainerData("Bug Catcher Greg", "Route 119", 0X020263BD, 3, [596,873,15], [350,472,471], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Bug Maniac Brent", "Route 119", 0X0202638B, 7, [413,1060,1059], [460,472,351], "TRAINER_PIC_BUG_MANIAC"),
    TrainerData("Expert Donald", "Route 119", 0X0202638C, 0, [272,776,254,530], [481,497,353,471], "TRAINER_PIC_EXPERT_M"),
    TrainerData("Ranger Catherine", "Route 119", 0X020263B5, 7, [981,264,724,700], [478,523,354,341], "TRAINER_PIC_POKEMON_RANGER_F"),
    TrainerData("Ranger Jackson", "Route 119", 0X020263B5, 0, [877,424,99], [557,425,503], "TRAINER_PIC_POKEMON_RANGER_M"),
    TrainerData("Bug Catcher Kent", "Route 119", 0X020263BD, 4, [267,752,212], [481,472,355], "TRAINER_PIC_BUG_CATCHER"),
    TrainerData("Ninja Boy Takashi & Psychic Dayton [Double]", "Route 119", 0X020263A4, 0, [275,321,None,765,282], [425,479,None,564,356], "TRAINER_PIC_NINJA_BOY", "TRAINER_PIC_PSYCHIC_M"),
    TrainerData("Bird Keeper Hugh", "Route 119", 0X020263A1, 7, [227,226,841,25], [576,434,567,392], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Parasol Lady Koko", "Route 119", 0X020263CF, 1, [847,407,1065,124,706], [427,487,522,479,472], "TRAINER_PIC_PARASOL_LADY"),
    TrainerData("Team Aqua Grunt Weather Inst #1", "Weather Institute", 0X02026373, 2, [689,286,687,545,121], [459,459,462,465,477], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Weather Inst #2", "Weather Institute", 0X02026372, 1, [780,598,103,139,365], [469,462,462,459,472], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Weather Inst #3", "Weather Institute", 0X02026372, 2, [474,978,612,461], [555,462,341,354], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Weather Inst #4 & Team Aqua Grunt Weather Inst #5 [Double]", "Weather Institute", 0X02026372, 3, [962,510,None,881,883], [344,349,None,522,522], "TRAINER_PIC_AQUA_GRUNT_M", "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Aqua Admin Shelly Weather Institute [Boss]", "Weather Institute", 0X020262E2, 7, [620,793,149,641,171,909], [481,480,442,348,503,295], "TRAINER_PIC_AQUA_ADMIN_F"),
    TrainerData("Trainer Rival Bridge [Double] [Boss]", "Route 119", 0X020262DD, 6, [927,226,706,958,448,423], [313,479,472,481,345,553], "TRAINER_PIC_MAY"),
    TrainerData("Ninja Boy Yasu & Guitarist Fabian [Double]", "Route 119", 0X020263A3, 7, [354,351,None,135,862], [481,481,None,479,339], "TRAINER_PIC_NINJA_BOY", "TRAINER_PIC_GUITARIST"),
    TrainerData("Ninja Boy Gren", "Route 119", 0X020263C1, 3, [205,477,132,777,1113], [576,498,462,502,427], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Parasol Lady Clarissa", "Route 120", 0X020263A6, 3, [820,591,858], [576,487,472], "TRAINER_PIC_PARASOL_LADY"),
    TrainerData("Bird Keeper Robert", "Route 120", 0X020263A2, 6, [738,357,225], [480,523,442], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Expert Kevin", "Fortree Gym", 0X020263A2, 2, [284,1068,233,130,468], [481,460,494,552,472], "TRAINER_PIC_EXPERT_M"),
    TrainerData("Picnicker Ashley", "Fortree Gym", 0X020263C1, 7, [279,724,212,55], [444,573,348,349], "TRAINER_PIC_PICNICKER"),
    TrainerData("Camper Flint & Bird Keeper Edwardo [Double]", "Fortree Gym", 0X020263C1, 6, [743,49,None,1169,741,1170], [481,522,None,528,340,528], "TRAINER_PIC_CAMPER", "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Bird Keeper Darius", "Fortree Gym", 0X020263D4, 3, [36,715,169,472], [479,348,471,554], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Bird Keeper Jared", "Fortree Gym", 0X020263A2, 1, [469,865,823,567,257], [444,522,472,481,348], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Leader Winona [Boss]", "Fortree Gym", 0X020263DD, 4, [398,637,701,797,1072,938], [444,481,348,503,472,324], "TRAINER_PIC_LEADER_WINONA"),
    TrainerData("Bird Keeper Colin", "Route 120", 0X020263A2, 5, [142,6,395], [551,481,341], "TRAINER_PIC_BIRD_KEEPER"),
    TrainerData("Cool Trainer Gian", "Route 120", 0X020263CF, 2, [426,260,884,65,869], [564,553,472,481,565], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Jennifer & Battle Girl Callie [Double]", "Route 120", 0X0202637B, 7, [376,217,523,None,539,62], [503,446,479,None,522,522], "TRAINER_PIC_COOLTRAINER_F", "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Parasol Lady Angelica", "Route 120", 0X020263A6, 4, [618,113,429,518], [522,494,352,564], "TRAINER_PIC_PARASOL_LADY"),
    TrainerData("Ranger Jenna", "Route 120", 0X020263B6, 0, [691,675,576,549], [557,509,481,472], "TRAINER_PIC_POKEMON_RANGER_F"),
    TrainerData("Ranger Lorenzo", "Route 120", 0X020263B5, 1, [768,842,241,122], [350,522,460,479], "TRAINER_PIC_POKEMON_RANGER_M"),
    TrainerData("Bug Maniac Jeffrey", "Route 120", 0X0202638C, 2, [666,666,666], [481,481,479], "TRAINER_PIC_BUG_MANIAC"),
    TrainerData("Ruin Maniac Chip", "Route 120", 0X02026375, 5, [348,346,697,699], [528,472,353,344], "TRAINER_PIC_RUIN_MANIAC"),
    TrainerData("Ninja Boy Keigo", "Route 120", 0X020263C1, 4, [463,864,362,571], [555,576,472,354], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Ninja Boy Riley", "Route 120", 0X020263C1, 5, [658,51,625,632], [479,347,440,481], "TRAINER_PIC_NINJA_BOY"),
    TrainerData("Cool Trainer Tammy & Bug Maniac Cale [Double]", "Route 121", 0X0202637D, 3, [289,567,None,980,110], [522,351,None,497,497], "TRAINER_PIC_COOLTRAINER_F", "TRAINER_PIC_BUG_MANIAC"),
    TrainerData("Beauty Jessica", "Route 121", 0X0202637F, 7, [478,124,671,115], [344,477,472,472], "TRAINER_PIC_BEAUTY"),
    TrainerData("Breeder Pat", "Route 121", 0X020263CF, 6, [185,233,82,569,839], [576,494,494,557,340], "TRAINER_PIC_POKEMON_BREEDER_F"),
    TrainerData("Breeder Myles", "Route 121", 0X020263CF, 5, [668,765,766,750,162], [480,564,522,472,354], "TRAINER_PIC_POKEMON_BREEDER_M"),
    TrainerData("Cool Trainer Gustavo", "Route 121", 0X02026371, 3, [604,534,593,560,635], [522,503,472,346,522], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Cristin", "Route 121", 0X020263CF, 7, [450,248,508,880], [522,555,339,353], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Young Couple Brian And Casey [Double]", "Route 121", 0X02026393, 6, [531,94,214,473], [555,346,481,522], "TRAINER_PIC_YOUNG_COUPLE"),
    TrainerData("Gentleman Walter", "Route 121", 0X0202638F, 6, [210,760,310,1191,184], [528,472,479,285,341], "TRAINER_PIC_GENTLEMAN"),
    TrainerData("Pokéfan Vanessa", "Route 121", 0X02026395, 4, [778,683,579], [484,356,479], "TRAINER_PIC_POKEFAN_F"),
    TrainerData("Trainer Rival Lilycove [Boss]", "Lilycove", 0X020262F4, 4, [445,68,65,809,984,927], [554,472,481,503,528,313], "TRAINER_PIC_MAY"),
    TrainerData("Young Couple Dez And Luke [Double]", "Mt. Pyre", 0X020263C0, 0, [863,678,59,235,957], [528,478,340,472,354], "TRAINER_PIC_YOUNG_COUPLE"),
    TrainerData("Hex Maniac Leah", "Mt. Pyre", 0X02026374, 3, [297,197,606,655], [445,472,480,460], "TRAINER_PIC_HEX_MANIAC"),
    TrainerData("Pokémaniac Mark", "Mt. Pyre", 0X02026382, 1, [845,112,106,469], [552,494,339,351], "TRAINER_PIC_POKEMANIAC"),
    TrainerData("Psychic William", "Mt. Pyre", 0X0202638D, 4, [867,73,103,471], [576,487,523,472], "TRAINER_PIC_PSYCHIC_M"),
    TrainerData("Breeder Gabrielle", "Mt. Pyre", 0X02026371, 1, [36,286,478,958,861], [522,481,344,342,472], "TRAINER_PIC_POKEMON_BREEDER_F"),
    TrainerData("Hex Maniac Tasha", "Mt. Pyre", 0X0202637D, 5, [139,971,455,442,356], [481,487,343,354,494], "TRAINER_PIC_HEX_MANIAC"),
    TrainerData("Black Belt Atsushi", "Mt. Pyre", 0X02026387, 6, [553,1174,392,62,652], [522,351,481,472,569], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Hex Maniac Valerie", "Mt. Pyre", 0X0202637D, 4, [115,429,687,202], [503,479,472,522], "TRAINER_PIC_HEX_MANIAC"),
    TrainerData("Psychic Cedric", "Mt. Pyre", 0X020263AB, 3, [466,862,855,576], [479,566,460,477], "TRAINER_PIC_PSYCHIC_M"),
    TrainerData("Psychic Kayla", "Mt. Pyre", 0X0202638E, 7, [55,437,986,630], [479,564,494,496], "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Black Belt Zander", "Mt. Pyre", 0X02026373, 7, [539,538,448], [522,472,339], "TRAINER_PIC_BLACK_BELT"),
    TrainerData("Team Aqua Grunt Mt Pyre #1", "Mt. Pyre", 0X020263DB, 1, [342,230,735], [481,471,462], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Mt Pyre #2", "Mt. Pyre", 0X020263DB, 2, [149,713,419,130], [460,522,479,459], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Mt Pyre #3", "Mt. Pyre", 0X02026373, 0, [94,224,435,369], [469,341,522,459], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Mt Pyre #4", "Mt. Pyre", 0X02026372, 7, [818,405,91,452], [478,445,465,471], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Mt Pyre #5 & Team Aqua Grunt Mt Pyre #6 [Double]", "Mt. Pyre", 0X02026373, 1, [454,26,None,882,550], [469,469,None,522,442], "TRAINER_PIC_AQUA_GRUNT_M", "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Aqua Leader Archie Mt. Pyre [Tag Battle] [Boss]", "Mt. Pyre", 0X020262EA, 4, [1230,635,1066,691,805,936], [522,353,472,487,503,322], "TRAINER_PIC_AQUA_LEADER_ARCHIE"),
    TrainerData("Team Magma Grunt Magma Hideout #1", "Magma Hideout", 0X020263C9, 4, [324,128,6,210,994], [462,479,459,503,469], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #2", "Magma Hideout", 0X020263C9, 5, [306,336,466,973,229], [469,462,471,394,354], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #3", "Magma Hideout", 0X020263C9, 6, [34,323,142,289,571], [469,462,465,501,354], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #4", "Magma Hideout", 0X020263CB, 1, [310,668,22,359,328], [479,469,471,471,494], "TRAINER_PIC_MAGMA_GRUNT_F"),
    TrainerData("Team Magma Grunt Magma Hideout #5", "Magma Hideout", 0X020263CA, 0, [621,275,105,776], [566,459,394,462], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #6", "Magma Hideout", 0X020263C9, 7, [839,136,338,880,663], [462,446,459,340,469], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #7 & Team Magma Grunt Magma Hideout #8 [Double]", "Magma Hideout", 0X020263CB, 2, [38,241,232,103,189,59], [340,472,576,560,481,528], "TRAINER_PIC_MAGMA_GRUNT_F", "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #9", "Magma Hideout", 0X020263CA, 3, [468,537,80,101,781], [471,459,462,459,503], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #10", "Magma Hideout", 0X020263CA, 2, [1184,571,330,435], [271,481,459,459], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #11", "Magma Hideout", 0X020263CA, 4, [980,971,815,780], [559,557,453,462], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout  #12", "Magma Hideout", 0X020263CB, 3, [867,985,609,332,291], [459,487,472,462,469], "TRAINER_PIC_MAGMA_GRUNT_F"),
    TrainerData("Team Magma Grunt Magma Hideout #13", "Magma Hideout", 0X020263CA, 6, [115,851,169,748], [425,472,443,487], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #14", "Magma Hideout", 0X020263CA, 7, [861,776,463,727,189], [556,509,462,503,472], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Magma Hideout #15", "Magma Hideout", 0X020263CB, 0, [596,467,217,24,455], [481,443,446,459,471], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Magma Admin Tabitha", "Magma Hideout", 0X020263CB, 4, [806,106,469,143,494,940], [481,339,348,472,509,326], "TRAINER_PIC_MAGMA_ADMIN"),
    TrainerData("Magma Leader Maxie Magma Hideout [Boss]", "Magma Hideout", 0X020262DD, 7, [383,465,445,804,151,925], [528,479,496,444,522,311], "TRAINER_PIC_MAGMA_LEADER_MAXIE"),
    TrainerData("Team Aqua Grunt Aqua Hideout #1", "Aqua Hideout", 0X02026370, 2, [966,675,626,853,419,99], [459,462,341,503,469,479], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Aqua Hideout #2", "Aqua Hideout", 0X02026373, 3, [615,297,497,594,604], [469,479,459,496,472], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Aqua Hideout #3", "Aqua Hideout", 0X02026388, 0, [139,589,171,169,319], [481,462,459,348,469], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Aqua Hideout #4", "Aqua Hideout", 0X02026370, 5, [962,960,875,365,36], [478,471,471,459,502], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Aqua Hideout #5", "Aqua Hideout", 0X02026373, 4, [130,673,958,864], [459,503,469,480], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Aqua Hideout #6", "Aqua Hideout", 0X02026370, 4, [186,695,715,598,62], [341,459,459,472,522], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Aqua Hideout #7", "Aqua Hideout", 0X02026370, 3, [565,224,121,472,706], [462,462,479,446,472], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Aqua Hideout #8", "Aqua Hideout", 0X02026388, 1, [812,202,73,272,181,862], [469,472,487,343,462,445], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Aqua Admin Matt [Boss]", "Aqua Hideout", 0X020262DE, 0, [473,882,887,798,243,917], [481,444,353,479,341,303], "TRAINER_PIC_AQUA_ADMIN_M"),
    TrainerData("Swimmer♀ Grace & Swimmer♂ Declan [Double]", "Route 124", 0X020263A8, 2, [658,781,693,None,871,812], [479,355,481,None,342,503], "TRAINER_PIC_SWIMMER_F", "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Swimmer♂ Cranberry", "Route 124", 0X02026383, 7, [685,31,184,143,321], [481,479,523,576,341], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Triathlete Aubrey", "Route 124", 0X020263A8, 1, [876,730,841,65,461,80], [481,508,570,479,354,452], "TRAINER_PIC_SWIMMING_TRIATHLETE_F"),
    TrainerData("Psychic Preston & Psychic Maura [Double]", "Mossdeep Gym", 0X0202638D, 1, [715,282,429,700,376,426], [479,522,481,356,502,502], "TRAINER_PIC_PSYCHIC_M", "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Psychic Blake & Psychic Samantha [Double]", "Mossdeep Gym", 0X0202638D, 3, [233,593,858,863,437,409], [494,341,356,550,472,442], "TRAINER_PIC_PSYCHIC_M", "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Psychic Virgil & Gentleman Nate [Double]", "Mossdeep Gym", 0X0202638D, 2, [553,620,655,576,841,49], [569,569,481,502,567,523], "TRAINER_PIC_PSYCHIC_M", "TRAINER_PIC_GENTLEMAN"),
    TrainerData("Psychic Hannah & Battle Girl Sylvia [Double]", "Mossdeep Gym", 0X0202638E, 4, [1155,350,432,534,130,976], [481,472,425,503,480,481], "TRAINER_PIC_PSYCHIC_F", "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Hex Maniac Kathleen & Psychic Nicholas [Double]", "Mossdeep Gym", 0X020263B8, 7, [169,468,124,530,308,815], [348,528,481,347,481,479], "TRAINER_PIC_HEX_MANIAC", "TRAINER_PIC_PSYCHIC_M"),
    TrainerData("Gentleman Clifford & Psychic Macey [Double]", "Mossdeep Gym", 0X020263B9, 7, [766,658,1174,183,128,55], [481,477,479,462,354,479], "TRAINER_PIC_GENTLEMAN", "TRAINER_PIC_PSYCHIC_F"),
    TrainerData("Leader Tate [Boss]", "Mossdeep Gym", 0X020263DB, 5, [482,945,571,720], [481,331,354,472], "TRAINER_PIC_LEADER_TATE"),
    TrainerData("Leader Liza [Boss]", "Mossdeep Gym", 0X020263DD, 5, [786,380,943,1168], [503,400,329,481], "TRAINER_PIC_LEADER_LIZA"),
    TrainerData("Team Magma Grunt Space Center #1", "Mossdeep Space Center", 0X02026372, 6, [208,842,523,823,514], [459,522,469,502,469], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Space Center #2", "Mossdeep Space Center", 0X020263B9, 3, [560,884,103,142,555,461], [503,528,462,471,479,459], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Space Center #3", "Mossdeep Space Center", 0X020263B9, 2, [660,1186,743,59,601], [462,274,469,459,442], "TRAINER_PIC_MAGMA_GRUNT_F"),
    TrainerData("Magma Admin Courtney", "Mossdeep Space Center", 0X020262E7, 7, [492,51,697,796,794,907], [479,347,481,472,503,293], "TRAINER_PIC_MAGMA_GRUNT_F"),
    TrainerData("Team Magma Grunt Space Center #5", "Mossdeep Space Center", 0X020263B9, 4, [348,1064], [459,460], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Space Center #6", "Mossdeep Space Center", 0X020263B9, 5, [68,663], [462,348], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Team Magma Grunt Space Center #7", "Mossdeep Space Center", 0X020263B9, 6, [625,980,799], [522,487,469], "TRAINER_PIC_MAGMA_GRUNT_M"),
    TrainerData("Magma Leader Maxie & Magma Admin Tabitha [Tag Battle] [Boss]", "Mossdeep Space Center", 0X020262DE, 5, [645,485,947,926,598,146], [479,497,333,312,496,340],  "TRAINER_PIC_MAGMA_LEADER_MAXIE", "TRAINER_PIC_MAGMA_ADMIN"),
    TrainerData("Sis And Bro Lila And Roy [Double]", "Route 124", 0X020263C5, 7, [272,121,149,508,171,9], [481,479,522,339,479,522], "TRAINER_PIC_SIS_AND_BRO"),
    TrainerData("Swimmer♂ Dean", "Route 126", 0X02026384, 4, [558,776,855,774,213,235], [460,460,460,348,472,481], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Bird Keeper Camden & Battle Girl Donny [Double]", "Route 127", 0X0202639E, 6, [398,738,635,448,454,392], [481,522,354,479,487,481], "TRAINER_PIC_BIRD_KEEPER", "TRAINER_PIC_BATTLE_GIRL"),
    TrainerData("Swimmer♀ Carlee & Swimmer♂ Harrison [Double]", "Route 128", 0X020263AA, 0, [1000,1008,997,65,131,637], [503,345,340,481,472,561], "TRAINER_PIC_SWIMMER_F", "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Team Aqua Grunt Seafloor Cavern #1", "Seafloor Cavern", 0X02026370, 6, [230,972,430,462,169,368], [471,462,471,503,479,460], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Seafloor Cavern #2", "Seafloor Cavern", 0X02026370, 7, [260,130,612,971,407,779], [553,552,522,459,459,479], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Seafloor Cavern #3", "Seafloor Cavern", 0X02026371, 0, [91,687,142,478,342], [459,503,442,459,479], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Team Aqua Grunt Seafloor Cavern #4", "Seafloor Cavern", 0X02026371, 6, [545,834,781,367], [522,472,462,460], "TRAINER_PIC_AQUA_GRUNT_F"),
    TrainerData("Team Aqua Grunt Seafloor Cavern #5", "Seafloor Cavern", 0X020263B6, 7, [598,319,376,571,373,454], [462,459,502,522,479,481], "TRAINER_PIC_AQUA_GRUNT_M"),
    TrainerData("Aqua Admin Shelly", "Seafloor Cavern", 0X02026374, 1, [788,701,94,990,646,913], [472,453,481,442,472,299], "TRAINER_PIC_AQUA_ADMIN_F"),
    TrainerData("Aqua Leader Archie Seafloor Cavern [Boss]", "Seafloor Cavern", 0X020262E0, 1, [382,904,497,681,145,929], [576,479,472,502,528,315], "TRAINER_PIC_AQUA_LEADER_ARCHIE"),
    TrainerData("Swimmer♂ Reed", "Route 129", 0X020263C4, 3, [618,658,91,567,59,135], [557,481,460,480,472,479], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Triathlete Chase & Triathlete Allison [Double]", "Route 129", 0X0202639F, 2, [839,695,131,779,733,34], [502,479,344,478,479,481], "TRAINER_PIC_SWIMMING_TRIATHLETE_M", "TRAINER_PIC_SWIMMING_TRIATHLETE_F"),
    TrainerData("Swimmer♀ Tisha", "Route 129", 0X020263C4, 4, [879,134,764,870,614,62], [481,472,266,522,479,523], "TRAINER_PIC_SWIMMER_F"),
    TrainerData("Swimmer♂ Clarence", "Route 129", 0X020263B8, 4, [149,462,124,348,73,537], [554,576,481,522,487,479], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Swimmer♂ Rodney", "Route 130", 0X02026384, 5, [226,1160,426,284,9,771], [341,522,481,479,472,472], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Swimmer♀ Katie", "Route 130", 0X020263A8, 7, [230,1068,454,706,632,834], [353,528,479,472,350,442], "TRAINER_PIC_SWIMMER_F"),
    TrainerData("Swimmer♂ Zappator", "Route 131", 0X02026385, 3, [904,663,685,3,466,199], [522,348,356,481,479,564], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Triathlete Xayah", "Route 131", 0X020263A0, 1, [775,6,1182,472,423,730], [555,426,283,348,553,472], "TRAINER_PIC_SWIMMING_TRIATHLETE_F"),
    TrainerData("Sis And Bro Reli And Ian [Double]", "Route 131", 0X020263C5, 6, [71,142,815,778,901,319], [481,351,528,356,503,479], "TRAINER_PIC_SIS_AND_BRO"),
    TrainerData("Swimmer♂ Herman", "Route 131", 0X02026384, 7, [752,604,560,376,474,593], [558,503,479,528,555,427], "TRAINER_PIC_SWIMMER_M"),
    TrainerData("Lass Andrea & Beauty Connie [Double]", "Sootopolis Gym", 0X02026380, 0, [818,115,1008,763,454,350], [478,502,460,523,481,522], "TRAINER_PIC_LASS", "TRAINER_PIC_BEAUTY"),
    TrainerData("Beauty Bridget", "Sootopolis Gym", 0X02026380, 1, [36,658,960,419,1006], [479,522,479,477,472], "TRAINER_PIC_BEAUTY"),
    TrainerData("Lady Daphne", "Sootopolis Gym", 0X0202637E, 3, [743,779,730,1000,887,407], [481,560,556,555,480,479], "TRAINER_PIC_LADY"),
    TrainerData("Pokéfan Bethany", "Sootopolis Gym", 0X02026395, 5, [186,879,537,904,996,160], [501,528,481,522,479,479], "TRAINER_PIC_POKEFAN_F"),
    TrainerData("Lass Crissy", "Sootopolis Gym", 0X020263BC, 6, [871,1186,635,958,985,693], [576,274,479,481,451,472], "TRAINER_PIC_LASS"),
    TrainerData("Lady Brianna", "Sootopolis Gym", 0X0202637E, 6, [141,576,617,777,340], [481,349,479,569,553], "TRAINER_PIC_LADY"),
    TrainerData("Lass Pearl", "Sootopolis Gym", 0X020263AE, 6, [615,561,466,365,614], [478,502,477,472,344], "TRAINER_PIC_LASS"),
    TrainerData("Beauty Tiffany & Beauty Olivia [Double]", "Sootopolis Gym", 0X02026380, 2, [395,784,473,866,630,883], [504,508,481,481,496,341], "TRAINER_PIC_BEAUTY", "TRAINER_PIC_BEAUTY"),
    TrainerData("Leader Juan [Double] [Boss]", "Sootopolis Gym", 0X020263DD, 6, [903,941,647,373,902,896], [481,327,522,554,341,503], "TRAINER_PIC_LEADER_JUAN"),
    TrainerData("Trainer Wally", "Victory Road", 0X020263B0, 7, [738,407,184,649,862,930], [481,479,523,481,445,316], "TRAINER_PIC_WALLY"),
    TrainerData("Cool Trainer Hope & Cool Trainer Albert [Double]", "Victory Road", 0X0202637C, 0, [473,232,906,918,398,635], [522,576,292,304,348,340], "TRAINER_PIC_COOLTRAINER_F", "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Katelynn", "Victory Road", 0X02026398, 5, [365,469,272,51,462,916], [522,472,509,479,497,302], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Quincy", "Victory Road", 0X02026398, 4, [703,199,709,89,784,910], [472,503,523,487,353,296], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Felix", "Victory Road", 0X02026374, 6, [812,248,36,994,818,921], [481,354,454,522,348,307], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Julie & Cool Trainer Dianne [Double]", "Victory Road", 0X0202637C, 4, [927,865,671,768,430,915], [313,345,569,503,481,301], "TRAINER_PIC_COOLTRAINER_F", "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Samuel", "Victory Road", 0X0202637A, 1, [545,445,128,130,604,928], [481,479,479,522,503,314], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Shannon", "Victory Road", 0X0202637C, 1, [279,368,149,212,547,929], [552,460,522,355,479,315], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Caroline", "Victory Road", 0X0202637C, 3, [750,598,9,1003,1004,950], [503,550,460,481,479,336], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Michelle", "Victory Road", 0X0202637C, 2, [685,555,609,472,635,924], [481,479,443,446,522,310], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Cool Trainer Specter", "Victory Road", 0X0202637A, 3, [143,373,286,376,121,931], [576,479,481,502,480,317], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Cool Trainer Edgar", "Victory Road", 0X02026379, 7, [908,464,1001,962,3,706], [294,472,348,481,479,503], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Triathlete Darren", "Victory Road", 0X020263B3, 4, [567,202,34,887,25,907], [348,528,481,479,392,293], "TRAINER_PIC_RUNNING_TRIATHLETE_M"),
    TrainerData("Cool Trainer Halle", "Victory Road", 0X020263B4, 2, [76,776,1141,589,461,932], [576,472,523,503,481,318], "TRAINER_PIC_COOLTRAINER_F"),
    TrainerData("Winstrate Vito Victory Road [Boss]", "Victory Road", 0X0202637A, 2, [876,306,795,91,701,912], [481,576,479,481,452,298], "TRAINER_PIC_COOLTRAINER_M"),
    TrainerData("Elite Four Sidney", "Elite Four Sidney", 0X0202636F, 3, [658,800,34,892,717,917], [481,472,479,566,264,303], "TRAINER_PIC_ELITE_FOUR_SIDNEY"),
    # TrainerData("Elite Four Sidney Double", "Elite Four Sidney", 0X0202636F, 3, [727,982,904,892,491,917], [528,522,503,481,479,303], "TRAINER_PIC_ELITE_FOUR_SIDNEY"),
    TrainerData("Elite Four Phoebe", "Elite Four Phoebe", 0X0202636F, 4, [169,1003,576,792,802,914], [348,479,503,480,522,300], "TRAINER_PIC_ELITE_FOUR_PHOEBE"),
    # TrainerData("Elite Four Phoebe Double", "Elite Four Phoebe", 0X0202636F, 4, [1008,609,9,792,1071,914], [481,562,528,480,403,300], "TRAINER_PIC_ELITE_FOUR_PHOEBE"),
    TrainerData("Elite Four Glacia", "Elite Four Glacia", 0X0202636F, 5, [473,949,883,1103,1104,1232], [481,335,344,472,503,576], "TRAINER_PIC_ELITE_FOUR_GLACIA"),
    # TrainerData("Elite Four Glacia Double", "Elite Four Glacia", 0X0202636F, 5, [801,740,949,233,1232,1105], [550,481,335,494,344,512], "TRAINER_PIC_ELITE_FOUR_GLACIA"),
    TrainerData("Elite Four Drake", "Elite Four Drake", 0X0202636F, 6, [887,342,718,245,643,942], [479,481,563,472,522,328], "TRAINER_PIC_ELITE_FOUR_DRAKE"),
    # TrainerData("Elite Four Drake Double", "Elite Four Drake", 0X0202636F, 6, [887,245,718,6,644,942], [481,472,472,479,460,328], "TRAINER_PIC_ELITE_FOUR_DRAKE"),
    TrainerData("Champion Wallace [Boss]", "Champion Wallace", 0X02026399, 7, [954,847,1006,484,490,929], [291,442,472,471,472,315], "TRAINER_PIC_CHAMPION_WALLACE")
]

# Start script
if __name__ == "__main__":
    ensureSetup()
    mainLoop()