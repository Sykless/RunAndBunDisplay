
# Description <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="20"> &nbsp;/&nbsp; <img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="20">

- [Utilisation](#utilisation-) - [Installation](#installation-) - [Configuration](#configuration-) &nbsp;<img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="15">
- [Usage](#usage-) - [Installation](#installation--1) - [Configuration](#configuration--1) &nbsp;<img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="15">
- [Contact](#contact)

<img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="15">&nbsp; RunAndBunDisplay est un programme développé pour la Rom Hack Pokémon RunAndBun générant des images des Pokémons capturés en jeu. Ces images s'actualisent en temps réel et peuvent être ajoutées dans OBS pour afficher l'état du jeu en direct. Le programme génère quatre images : <br />

<img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="15">&nbsp; RunAndBunDisplay is a program developed for the Rom Hack Pokémon RunAndBun that generates images of in-game caught Pokémon. Those images refresh in real time and can be added to OBS to display the current state of the game. Four images are generated : <br />
<br />

| Party     | Box      | Dead       | Next Trainer       |
| :-------- | :------- | :--------- | :--------- |
| <img width="500" alt="party" src="https://github.com/user-attachments/assets/2e442ec5-9e35-467f-be30-e74d88ba5226" /> | <img width="500" alt="box" src="https://github.com/user-attachments/assets/cbdfe4e3-2b13-4d9a-8ef3-fd50d2cd4d41" /> | <img width="500" alt="dead" src="https://github.com/user-attachments/assets/3bc9e2eb-fdd7-477b-8c69-3b90ee61a7cf" /> | <img width="500" alt="trainer" src="https://github.com/user-attachments/assets/259e6cd0-5e06-4805-b392-f9126c24e68a" />

### Exemple de layout <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="15"> &nbsp;/&nbsp; Layout example <img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="15">
<img width="720" src="https://github.com/user-attachments/assets/a8da6723-7ff6-4e03-acb5-c9a2d15be136" />

### Run tracking (BETA)
<img width="1920" alt="image" src="https://github.com/user-attachments/assets/c682a1c8-c21b-464e-9b7f-930345e9cfe9" />

<br />
<br />

<img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="15">&nbsp; Le run tracking permet d'historiser toutes les runs dans un Google Sheets publiquement accessible pour les viewers. Il renseigne des informations sur la run (Nombre de combats restants, date de début/fin de la run) ainsi que les Pokémons capturés dans chaque zone et leurs statistiques (Talent, Capacités, Nature, IVs) <br />
⚠️ *Le run tracking utilise Google Cloud qui limite le nombre d'accès, cette fonctionnalité est pour le moment réservée à certains streamers sélectionnés, merci de [contacter le développeur](#contact) si besoin*

<img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="15">&nbsp; Run tracking allows to save runs history in a Google Sheets document publicly accessible by viewers. It registers info on the run itself (Number of fights remamining, run start/end time) as well as on Pokémon caught in each zone with their stats (Ability, Moves, Nature, IVs) <br />
⚠️ *Run tracking uses Google Cloud which limits the number of access, this feature is for now only available for selected streamers, please [contact developer](#contact) if needed*

<br />

# Utilisation <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="20">

Une fois [l'installation](#installation-) réalisée, à chaque utilisation :
- Lancer le programme **RunAndBunDisplay.exe**
- Attacher le script **RunAndBunDisplay.lua** à mGBA (voir [Étape 2 de l'installation](#%EF%B8%8F-étape-2--ajout-du-script-lua-à-lémulateur)) <br />
<br />

# Installation <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="20">

## ➡️ Étape 1 : Initialisation du programme

Fermer l'émulateur mGBA s'il est en cours d'exécution. Télécharger puis unzipper la [dernière version du programme](https://github.com/Sykless/RunAndBunDisplay/releases) dans le dossier de votre choix (_éviter les dossier protégés comme C:\Program Files_). Lancer ensuite le programme RunAndBunDisplay.exe : le message "**Run&BunDisplay en cours d'exécution...**" devrait apparaître. <br />

## ➡️ Étape 2 : Ajout du script lua à l'émulateur

Ajouter ensuite le script "RunAndBunDisplay.lua" à mGBA : aller dans "Outils" -> "Scripting", puis dans la fenêtre qui s'ouvre, aller dans "File" -> "Load script" et sélectionner le script "RunAndBunDisplay.lua" : le message "**Run&BunDisplay en cours d'exécution...**" devrait apparaître. Lancer ensuite la ROM et vérifiez que les quatre images ont été générées dans le dossier **outputImage**. <br />

## ➡️ Étape 3 : Ajout des images dans OBS

Dans OBS, ajouter une source de type "Image" et choisir une des quatre images générées dans le dossier **outputImage**. Une fois l'image affichée, clic droit sur l'image, "Filtre de mise à l'échelle" -> "Point" pour obtenir image plus nette. L'image devrait maintenant s'actualiser à chaque mise à jour en jeu. <br />
<br />

# Configuration <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" height="20">

Le fichier **configuration.txt** permet d'activer ou désactiver certaines options en passant les variables suivantes à 1 pour activer ou 0 pour désactiver : 

| Variable             | Description                                                                |
| ----------------- | ------------------------------------------------------------------ |
| **DISPLAY_SPRITE_LEVELUP** | Affiche ou non l'icône <img width="18" alt="levelup" src="https://github.com/user-attachments/assets/63f5aa4d-0a73-4c51-83a2-da35c6ca31e2" /> indiquant qu'un Pokémon est prêt à monter de niveau |
| **DISPLAY_SPRITE_ITEMS** | Affiche ou non les objets tenus par les Pokémons du PC et de l'équipe |
| **DISPLAY_TRAINER_ITEMS** | Affiche ou non les objets tenus par les Pokémons du prochain dresseur |
| **DISPLAY_TRAINER_BACKGROUND** | Affiche ou non le background personnalisé sur l'image du prochain dresseur |
| **DISPLAY_MULTIPLE_BOXES** | Affiche ou non les Pokémons des autres boîtes que la Boîte 1 |
| **BOX_DISPLAY_TIME** | Durée d'affichage de chaque boîte si l'option précédente est activée |
| **ZONE_START_RUN_TRACKING** | Zone à partir de laquelle le run tracking est activé :<br />➡️ 0 : Run tracking désactivé<br />➡️ 1 : Starter Pack (Route 101 - Route 102 - Route 103)<br />➡️ 2 : Myokara (valeur par défaut)<br />➡️ 3 : Route 110 |

<br />

# Usage <img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="20">

After [installation](#installation--1) is done, whenever you use it :
- Execute program **RunAndBunDisplay.exe**
- Attach script **RunAndBunDisplay.lua** to mGBA (see [Installation Step 2](#%EF%B8%8F-step-2--add-lua-script-to-emulator)) <br />
<br />

# Installation <img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="20">&nbsp;

## ➡️ Step 1 : Setup program

Close mGBA emulator if running. Download then unzip the [latest program version](https://github.com/Sykless/RunAndBunDisplay/releases) in the folder of your choice (_avoid protected folders like C:\Program Files_). Then, run RunAndBunDisplay.exe : the message "**Run&BunDisplay en cours d'exécution...**" should appear. <br />

## ➡️ Step 2 : Add lua script to emulator

Add "RunAndBunDisplay.lua" script to mGBA : go to "Tools" -> "Scripting", then in the next window, go to "File" -> "Load script" and select "RunAndBunDisplay.lua" script : the message "**Run&BunDisplay en cours d'exécution...**" should appear. Launch the ROM and make sure the four images have been generated in the folder **outputImage**. <br />

## ➡️ Step 3 : Add images to OBS

In OBS, add a new "Image" source, and select one of the four generated images in the folder **outputImage**. When the image is displayed, right click on it, "Scale Filtering" -> "Point" for a better image quality. The image should now update after any in-game modification. <br />
<br />

# Configuration <img src="https://upload.wikimedia.org/wikipedia/en/a/ae/Flag_of_the_United_Kingdom.svg" height="20">

The **configuration.txt** file allows to enable or disable certain options by setting those variables to 1 to enable or 0 to disable

| Variable             | Description                                                                |
| ----------------- | ------------------------------------------------------------------ |
| **DISPLAY_SPRITE_LEVELUP** | Display or not the icon <img width="18" alt="levelup" src="https://github.com/user-attachments/assets/63f5aa4d-0a73-4c51-83a2-da35c6ca31e2" /> indicating if a Pokémon is ready to level up |
| **DISPLAY_SPRITE_ITEMS** | Display or not the items held by Pokémon in the PC or in the team |
| **DISPLAY_TRAINER_ITEMS** | Display or not the items held by Pokémon in the next trainer team |
| **DISPLAY_TRAINER_BACKGROUND** | Display or not the custom background in the next trainer image |
| **DISPLAY_MULTIPLE_BOXES** | Display or not the Pokémon in the other boxes than Box 1 |
| **BOX_DISPLAY_TIME** | Display time of each box if the previous option is enabled |
| **ZONE_START_RUN_TRACKING** | Zone from which we start run tracking<br />➡️ 0 : Run tracking disabled<br />➡️ 1 : Starter Pack (Route 101 - Route 102 - Route 103)<br />➡️ 2 : Dewford Town (default value)<br />➡️ 3 : Route 110 |

<br />

# Contact
- Discord : [@Sykless](https://discordapp.com/users/Sykless#2124)
- Twitch : [@TristanPelleteuse](https://www.twitch.tv/tristanpelleteuse)
