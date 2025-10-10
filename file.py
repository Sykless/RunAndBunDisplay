import os
import re
import json
import orjson

TEMPOUTPUT_FOLDER = ".tmp"
OUTPUT_FOLDER = "outputImage"
CONF_FILE = "configuration.txt"
RUNS_FILE = "runs.json"

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


# Load runs.json into json data
def loadJsonRuns():
    if os.path.exists(RUNS_FILE):
        with open(RUNS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ runs.json corrupted, reinitializing.")
    return {"runs": {}}


# Parse json runs into object and make sure it's initialized
def loadRunDict(runId):
    runsData = loadJsonRuns()

    if "runs" not in runsData:
        runsData["runs"] = {}

    if runId not in runsData["runs"]:
        runsData["runs"][runId] = {}

    return runsData


# Dump all runs in json format with specific formatting
def saveRuns(runsData):
    data = orjson.dumps(runsData, option = orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE).decode("utf-8")
    data = re.sub(r'\[\s+([^]]+?)\s+\]', lambda m: '[' + ' '.join(m.group(1).split()) + ']', data)
    
    with open("runs.json", "w", encoding = "utf-8") as f:
        f.write(data)


# Read keys inside .key file to contact RunAndBunStats
def loadKeys():

    # Find all .key files in the 
    keyFiles = [f for f in os.listdir(".") if f.endswith(".key")]
    if not keyFiles:
        return None

    # Take first one available (should only be one anyway)
    keyPath = keyFiles[0]

    try:
        with open(keyPath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Make sure every parameter is present
        sheetId = data.get("spreadsheet", {}).get("sheetId")
        spreadsheetId = data.get("spreadsheet", {}).get("spreadsheetId")

        if not sheetId or not spreadsheetId:
            return None

        return data

    except (OSError, json.JSONDecodeError):
        return None

