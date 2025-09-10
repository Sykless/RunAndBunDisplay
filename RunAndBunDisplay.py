import os
import sys
import time
import subprocess
from PIL import Image

class PokemonData:
    def __init__(self, pokedexId, level, itemId):
        self.pokedexId = pokedexId
        self.level = int(level)
        self.itemId = itemId

    def __str__(self):
        return self.pokedexId + " - " + str(self.level) + " - " + self.itemId
    
    def __repr__(self):
        return str(self)

CLOCK = 0

SPRITE_FOLDER = "sprites"
POKEMONSPRITE_FOLDER = SPRITE_FOLDER + "/pokemon"
ITEMSPRITE_FOLDER = SPRITE_FOLDER + "/items"
MISCSPRITE_FOLDER = SPRITE_FOLDER + "/misc"

TEMPOUTPUT_FOLDER = ".tmp"
OUTPUT_FOLDER = "outputImage"
INPUT_FILE = "pokemonData.txt"
CONF_FILE = "configuration.txt"

DISPLAY_SPRITE_LEVELUP = "DISPLAY_SPRITE_LEVELUP"
DISPLAY_SPRITE_ITEMS = "DISPLAY_SPRITE_ITEMS"

SPRITE_WIDTH = 80
SPRITE_HEIGHT = 60

ITEM_X_POSITION = 42
ITEM_Y_POSITION = 28

LEVELUP_X_POSITION = 49
LEVELUP_Y_POSITION = 4

SPACING_X = -30
SPACING_Y = -10

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


# Read configuration.txt and convert user preferences into boolean
def readConfFile():
    configuration = {}
    configurationFile = safeReadFile(CONF_FILE)

    for line in configurationFile.splitlines():
        if (line.count("=") == 1):
            configurationSplit = line.split("=")
            configuration[configurationSplit[0]] = (configurationSplit[1] != "0")

    return configuration


# Create images from Pokémon sprites
def buildImage(label, pokemonList, columnNumber, rowNumber, levelCap = None):

    # Retrieve conf file content to check user preferences
    configuration = readConfFile()

    # Initialise transparent image
    imageWidth = SPRITE_WIDTH * columnNumber + SPACING_X * (columnNumber - 1)
    imageHeight = SPRITE_HEIGHT * rowNumber + SPACING_Y * (rowNumber - 1)
    outputImage = Image.new("RGBA", (imageWidth, imageHeight), (0,0,0,0))

    # Retrieve level up sprite if needed
    if (configuration[DISPLAY_SPRITE_LEVELUP] and levelCap):
        levelUpPath = os.path.join(MISCSPRITE_FOLDER, "levelup.png")
        levelUpSprite = Image.open(levelUpPath).convert("RGBA")

    # Iterate on each non-None Pokémon
    for i, pokemonData in enumerate(pokemonList):
        if pokemonData is None:
            continue

        # Retrieve Pokémon sprite (default sprite : Pokéball)
        pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, f"{pokemonData.pokedexId}.png")
        if not os.path.exists(pokemonSpritePath):
            pokemonSpritePath = os.path.join(POKEMONSPRITE_FOLDER, "0.png")

        # Retrieve and resize Pokémon sprite to 80x60 so items can appear small without sizing them down
        pokemonSprite = Image.open(pokemonSpritePath).convert("RGBA").resize((SPRITE_WIDTH, SPRITE_HEIGHT), Image.NEAREST)

        # Compute Pokémon sprite position with spacing (sligh overlap between sprites so they appear closer)
        x = (i % columnNumber) * (SPRITE_WIDTH + SPACING_X)
        y = (i // columnNumber) * (SPRITE_HEIGHT + SPACING_Y)

        # Display Pokémon sprite
        outputImage.paste(pokemonSprite, (x, y), pokemonSprite)

        # Display held item
        if (configuration[DISPLAY_SPRITE_ITEMS] and int(pokemonData.itemId)):

            # Retrieve item sprite (default sprite : blank item)
            itemPath = os.path.join(ITEMSPRITE_FOLDER, f"{pokemonData.itemId}.png")
            if not os.path.exists(itemPath):
                itemPath = os.path.join(ITEMSPRITE_FOLDER, "0.png")

            # Display item sprite
            itemSprite = Image.open(itemPath).convert("RGBA")
            outputImage.paste(itemSprite, (x + ITEM_X_POSITION, y + ITEM_Y_POSITION), itemSprite)

        # Display level up sprite if current level is lower than level cap
        if (configuration[DISPLAY_SPRITE_LEVELUP] and levelCap and pokemonData.level < int(levelCap)):
            outputImage.paste(levelUpSprite, (x + LEVELUP_X_POSITION, y + LEVELUP_Y_POSITION + CLOCK), levelUpSprite)

    # Save final image in .tmp folder to avoid OBS reading partially written image
    tempOutputPath = os.path.join(TEMPOUTPUT_FOLDER, f"{label.lower()}.png")
    outputPath = os.path.join(OUTPUT_FOLDER, f"{label.lower()}.png")
    outputImage.save(tempOutputPath, "PNG")
    outputImage.close()

    # Swap temp image and output image
    try:
        os.replace(tempOutputPath, outputPath)

    # PermissionError errors might occur because OBS is reading the image, don't print those
    except PermissionError:
        pass


# Main loop
def mainLoop():
    global CLOCK # global clock to alternate between up and down level up sprite position
    os.makedirs(OUTPUT_FOLDER, exist_ok = True) # Create outputImage folder is not exists
    os.makedirs(TEMPOUTPUT_FOLDER, exist_ok = True) # Create .tmp folder is not exists
    subprocess.run(["attrib", "+h", TEMPOUTPUT_FOLDER], shell = True)
    print("Run&BunDisplay en cours d'exécution...") # Notify user when ready to use

    while True:
        try:
            # Retrieve data written by lua scipt
            emulatorData = safeReadFile(INPUT_FILE)

            if emulatorData:
                lines = emulatorData.splitlines()

                # Retrieve each line and parse its data
                for line in lines:
                    if line.startswith("PARTY"):
                        partyLine = parseLine(line)
                        
                    elif line.startswith("BOX"):
                        boxLine = parseLine(line)
                        
                    elif line.startswith("DEAD"):
                        deadLine = parseLine(line)

                    elif line.startswith("LEVELCAP"):
                        levelCap = parseLine(line)[0]

                # Create png images from parsed data
                buildImage("party", partyLine, 6, 1, levelCap)
                buildImage("box", boxLine, 6, 5, levelCap)
                buildImage("dead", deadLine, 6, 5)
                        
            # Check file every second
            time.sleep(1)
            CLOCK = 1 - CLOCK
        
        # Don't stop script if an error occurs, just print it in the logs
        except Exception as e:
            print("An error occurred :", e)

if __name__ == "__main__":
    ensureSetup()
    mainLoop()