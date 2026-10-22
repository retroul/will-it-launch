#!/usr/bin/env python3
"""Rebuild data/games.js.

Linux status, anti-cheats, notes and history come from the AreWeAntiCheatYet
project (MIT): https://github.com/AreWeAntiCheatYet/AreWeAntiCheatYet
Windows, macOS, Android and iOS availability is curated by hand in GAMES below.

Usage:  python3 tools/update_data.py            (downloads the latest upstream list)
        python3 tools/update_data.py games.json (uses a local copy)
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UPSTREAM = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "games.js"
FEED = OUT.parent.parent / "feed.xml"
SITE_URL = "https://retroul.github.io/will-it-launch/"

STATUS = {"S": "supported", "R": "running", "P": "planned", "B": "broken", "D": "denied", "U": "unavailable"}
COD_MOBILE = ("S", "Separate game: Call of Duty: Mobile")


def G(name, genre, mac="U", android="U", ios="U", title=None, steam=None, url=None):
    """One curated game. `name` must match the upstream entry exactly.
    Platform values are a status letter (see STATUS) or (letter, note)."""
    return dict(name=name, genre=genre, mac=mac, android=android, ios=ios,
                title=title, steam=steam, url=url)


# Popular games (roughly 100k+ monthly players) that ship with an anti-cheat.
GAMES = [
    # --- Shooters -----------------------------------------------------------
    G("Counter-Strike 2", "Shooter", mac=("U", "macOS support ended when CS:GO became CS2 (2023)"), steam="730"),
    G("Valorant", "Shooter", android=("U", "Valorant Mobile is only released in China"),
      ios=("U", "Valorant Mobile is only released in China")),
    G("Call of Duty: Black Ops 7", "Shooter", android=COD_MOBILE, ios=COD_MOBILE),
    G("Call of Duty: Black Ops 6", "Shooter"),
    G("Overwatch 2", "Shooter", url="https://overwatch.blizzard.com/"),
    G("Tom Clancy's Rainbow Six® Siege X", "Shooter", title="Rainbow Six Siege X",
      android=("S", "Separate game: Rainbow Six Mobile"), ios=("S", "Separate game: Rainbow Six Mobile")),
    G("Escape from Tarkov", "Shooter"),
    G("Battlefield 6", "Shooter"),
    G("Battlefield™ 2042", "Shooter", title="Battlefield 2042"),
    G("Halo Infinite", "Shooter"),
    G("Halo: The Master Chief Collection", "Shooter"),
    G("Destiny 2", "Shooter"),
    G("Team Fortress 2", "Shooter", mac=("U", "macOS support was dropped in the 2024 64-bit update")),
    G("THE FINALS", "Shooter", title="The Finals"),
    G("Hunt: Showdown 1896", "Shooter"),
    G("Marvel Rivals", "Shooter"),
    G("Delta Force: Hawk Ops", "Shooter", title="Delta Force",
      android=("S", "Delta Force mobile, released April 2025"), ios=("S", "Delta Force mobile, released April 2025")),
    G("ARC Raiders", "Shooter"),
    G("Marathon", "Shooter"),
    G("Helldivers 2", "Shooter"),
    G("Squad", "Shooter"),
    G("Hell Let Loose", "Shooter"),
    G("Insurgency: Sandstorm", "Shooter"),
    G("ArmA 3", "Shooter", title="Arma 3", mac=("B", "Legacy Mac port is discontinued and can't join BattlEye servers")),
    G("ArmA Reforger", "Shooter", title="Arma Reforger"),
    G("Warframe", "Shooter", mac=("S", "Mac App Store, Apple silicon (2025)"),
      android=("S", "Released February 2026, cross-play and cross-save"), ios=("S", "Released February 2024, cross-play and cross-save")),
    G("War Thunder", "Shooter", mac="S",
      android=("S", "Separate game: War Thunder Mobile"), ios=("S", "Separate game: War Thunder Mobile")),
    G("World of Tanks", "Shooter", url="https://worldoftanks.com/",
      android=("S", "Separate game: World of Tanks Blitz"), ios=("S", "Separate game: World of Tanks Blitz")),
    G("Gray Zone Warfare", "Shooter"),
    G("Arena Breakout: Infinite", "Shooter",
      android=("S", "Separate game: Arena Breakout"), ios=("S", "Separate game: Arena Breakout")),
    G("BLOODSTRIKE", "Shooter", title="Blood Strike", android="S", ios="S"),
    G("Strinova", "Shooter"),
    G("Tom Clancy's The Division 2", "Shooter", title="The Division 2"),
    G("Tom Clancy's Ghost Recon Breakpoint", "Shooter", title="Ghost Recon Breakpoint"),

    # --- Battle royale --------------------------------------------------------
    G("Fortnite", "Battle Royale",
      mac=("U", "Removed in 2020 after Epic v. Apple; cloud gaming only"),
      android=("S", "Google Play (US since Dec 2025, wider rollout 2026) and the Epic Games Store"),
      ios=("S", "Back on the US App Store since May 2025; Epic Games Store in the EU")),
    G("Apex Legends", "Battle Royale", android=("U", "Apex Legends Mobile shut down in 2023"),
      ios=("U", "Apex Legends Mobile shut down in 2023")),
    G("PUBG: Battlegrounds", "Battle Royale",
      android=("S", "Separate game: PUBG Mobile"), ios=("S", "Separate game: PUBG Mobile")),
    G("Call of Duty: Warzone", "Battle Royale",
      android=("U", "Warzone Mobile was shut down in 2025; see Call of Duty: Mobile"),
      ios=("U", "Warzone Mobile was shut down in 2025; see Call of Duty: Mobile")),
    G("Battlefield REDSEC", "Battle Royale"),
    G("NARAKA: BLADEPOINT", "Battle Royale", title="Naraka: Bladepoint"),
    G("Fall Guys: Ultimate Knockout", "Battle Royale", title="Fall Guys"),

    # --- MOBA / strategy ------------------------------------------------------
    G("League of Legends", "MOBA", mac=("S", "Native client"),
      android=("S", "Separate game: League of Legends: Wild Rift"), ios=("S", "Separate game: League of Legends: Wild Rift")),
    G("Teamfight Tactics", "MOBA", mac="S", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("DotA 2", "MOBA", title="Dota 2", mac="S"),
    G("Deadlock", "MOBA"),
    G("Smite 2", "MOBA", title="SMITE 2"),
    G("Predecessor", "MOBA"),

    # --- MMO / online RPG -----------------------------------------------------
    G("World of Warcraft", "MMO", mac=("S", "Native Apple silicon client")),
    G("Final Fantasy XIV", "MMO", mac=("S", "Official Mac client"), steam="39210"),
    G("Black Desert Online", "MMO", title="Black Desert",
      android=("S", "Separate game: Black Desert Mobile"), ios=("S", "Separate game: Black Desert Mobile")),
    G("Lost Ark", "MMO"),
    G("New World: Aeternum", "MMO"),
    G("Throne and Liberty", "MMO"),
    G("Albion Online", "MMO", mac="S", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("MapleStory", "MMO", android=("S", "Separate game: MapleStory M"), ios=("S", "Separate game: MapleStory M")),
    G("Diablo® IV", "MMO", title="Diablo IV",
      android=("S", "Separate game: Diablo Immortal"), ios=("S", "Separate game: Diablo Immortal")),
    G("Once Human (ROW/INTL)", "MMO", title="Once Human",
      android=("S", "Mobile version released April 2025"), ios=("S", "Mobile version released April 2025")),
    G("Dune: Awakening", "MMO"),
    G("The First Descendant", "MMO"),
    G("Star Citizen", "MMO"),
    G("VRChat", "Social", android=("S", "Full release October 2025"), ios=("S", "Full release October 2025")),
    G("Rec Room", "Social", android="S", ios="S"),
    G("Roblox", "Social", mac="S", android="S", ios="S"),
    G("Garry's Mod", "Social", mac="S"),

    # --- Survival -------------------------------------------------------------
    G("Rust", "Survival", mac="S"),
    G("DayZ", "Survival"),
    G("ARK: Survival Ascended", "Survival"),
    G("ARK: Survival Evolved", "Survival", mac="S",
      android=("S", "Separate game: ARK: Ultimate Mobile Edition"), ios=("S", "Separate game: ARK: Ultimate Mobile Edition")),
    G("7 Days to Die", "Survival", mac="S"),
    G("Conan Exiles", "Survival"),
    G("Unturned", "Survival", mac="S"),
    G("Dead By Daylight", "Survival", title="Dead by Daylight",
      android=("U", "The global mobile version shut down in 2025"), ios=("U", "The global mobile version shut down in 2025")),

    # --- Action / adventure ---------------------------------------------------
    G("Elden Ring", "Action"),
    G("Elden Ring: Nightreign", "Action"),
    G("Sea of Thieves", "Action"),
    G("Grand Theft Auto V", "Action"),
    G("For Honor", "Action"),
    G("Chivalry 2", "Action"),
    G("Warhammer 40,000: Darktide", "Action"),
    G("The Crew™ Motorfest", "Racing & Sports", title="The Crew Motorfest"),

    # --- Sports, racing & fighting -------------------------------------------
    G("Rocket League®", "Racing & Sports", title="Rocket League", mac=("U", "macOS support ended in 2020")),
    G("EA SPORTS FC™ 26", "Racing & Sports", title="EA SPORTS FC 26",
      android=("S", "Separate game: EA SPORTS FC Mobile"), ios=("S", "Separate game: EA SPORTS FC Mobile")),
    G("NBA 2K25", "Racing & Sports"),
    G("EFootball 2025", "Racing & Sports", title="eFootball", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("REMATCH", "Racing & Sports", title="Rematch"),
    G("Brawlhalla", "Fighting", mac="S", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("DRAGON BALL: Sparking! ZERO", "Fighting", title="Dragon Ball: Sparking! Zero"),
    G("2XKO", "Fighting"),

    # --- Gacha / anime RPG ----------------------------------------------------
    G("Genshin Impact", "Anime RPG", android="S", ios="S"),
    G("Honkai Star Rail", "Anime RPG", title="Honkai: Star Rail", android="S", ios="S"),
    G("Zenless Zone Zero", "Anime RPG", android="S", ios="S"),
    G("Wuthering Waves", "Anime RPG", mac=("S", "Mac App Store, Apple silicon (March 2025)"), android="S", ios="S"),
    G("Blue Archive", "Anime RPG", android="S", ios="S"),
    G("Nikke: Goddess of Victory", "Anime RPG", android="S", ios="S"),
    G("Infinity Nikki", "Anime RPG", android="S", ios="S"),
    G("Umamusume: Pretty Derby", "Anime RPG", android="S", ios="S"),
    G("Reverse: 1999", "Anime RPG", android="S", ios="S"),
    G("Punishing: Gray Raven", "Anime RPG", android="S", ios="S"),
    G("Honkai Impact 3rd", "Anime RPG", android="S", ios="S"),
    G("Tower of Fantasy", "Anime RPG", android="S", ios="S"),
    G("Snowbreak: Containment Zone (ROW/INTL)", "Anime RPG", title="Snowbreak: Containment Zone", android="S", ios="S"),
    G("AFK Journey", "Anime RPG", android="S", ios="S"),
    G("Girls' Frontline", "Anime RPG", android="S", ios="S"),
    G("Princess Connect! Re:Dive", "Anime RPG", android=("S", "Japan only"), ios=("S", "Japan only")),
    G("ヘブンバーンズレッド (Heaven Burns Red)", "Anime RPG", title="Heaven Burns Red", android="S", ios="S"),
    G("Solo Leveling: Arise OVERDRIVE", "Anime RPG",
      android=("S", "Separate game: Solo Leveling: Arise"), ios=("S", "Separate game: Solo Leveling: Arise")),

    # --- More shooters ------------------------------------------------------
    G("Battlefield 4", "Shooter"),
    G("Battlefield 1", "Shooter"),
    G("Battlefield V", "Shooter"),
    G("Call of Duty: Modern Warfare III (2023)", "Shooter", title="Call of Duty: Modern Warfare III"),
    G("Call of Duty®: Black Ops III", "Shooter", title="Call of Duty: Black Ops III", mac="S"),
    G("Left 4 Dead 2", "Shooter"),
    G("Paladins", "Shooter"),
    G("Titanfall 2", "Shooter"),
    G("Rogue Company", "Shooter"),
    G("Enlisted", "Shooter"),
    G("Crossout", "Shooter", android=("S", "Separate game: Crossout Mobile"), ios=("S", "Separate game: Crossout Mobile")),
    G("Warface", "Shooter"),
    G("CrossFire", "Shooter"),
    G("Point Blank", "Shooter"),
    G("Rising Storm 2: Vietnam", "Shooter"),
    G("Squad 44", "Shooter"),
    G("Foxhole", "Shooter"),
    G("Pavlov VR", "Shooter"),
    G("Warhammer 40,000: Space Marine 2", "Shooter"),
    G("Killing Floor 2", "Shooter"),
    G("Killing Floor 3", "Shooter"),
    G("Gears 5", "Shooter"),
    G("Gears of War: Reloaded", "Shooter"),
    G("FragPunk", "Shooter"),
    G("Mecha BREAK", "Shooter", title="Mecha Break"),
    G("Pixel Gun 3D: PC Edition", "Shooter", title="Pixel Gun 3D",
      android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("War Robots", "Shooter", android="S", ios="S"),
    G("War Robots: Frontiers", "Shooter"),
    G("Escape from Tarkov: Arena", "Shooter"),
    G("Lost Light", "Shooter", android="S", ios="S"),
    G("Vigor", "Shooter"),
    G("Dark and Darker", "Action"),
    G("Watch Dogs®: Legion", "Action", title="Watch Dogs: Legion"),
    G("Sniper Elite 5", "Shooter"),
    G("Sniper Elite: Resistance", "Shooter"),
    G("Gunfire Reborn", "Shooter", android="S", ios="S"),
    G("Outriders", "Shooter"),
    G("Back 4 Blood", "Shooter"),

    # --- More battle royale -------------------------------------------------
    G("Farlight 84", "Battle Royale", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("Super Animal Royale", "Battle Royale", mac="S"),

    # --- More MOBA / strategy ----------------------------------------------
    G("Heroes of the Storm", "MOBA", mac="S"),
    G("StarCraft II", "Strategy", mac="S"),
    G("WarCraft III: Reforged", "Strategy", title="Warcraft III: Reforged", mac="S"),
    G("Legends of Runeterra", "Strategy", android="S", ios="S"),
    G("Conqueror's Blade", "Strategy"),
    G("Mount & Blade II: Bannerlord", "Strategy"),

    # --- More MMO / online RPG ---------------------------------------------
    G("Blue Protocol: Star Resonance", "MMO", android=("S", "Cross-play with PC"), ios=("S", "Cross-play with PC")),
    G("Fallout 76", "MMO"),
    G("Phantasy Star Online 2 New Genesis", "MMO"),
    G("Lineage II", "MMO"),
    G("Blade & Soul NEO", "MMO"),
    G("Dungeon Fighter Online", "MMO"),
    G("Mabinogi", "MMO"),
    G("Vindictus", "MMO"),
    G("Elsword", "MMO"),
    G("Dragon Nest", "MMO"),
    G("Metin2", "MMO"),
    G("RF ONLINE NEXT", "MMO", title="RF Online Next", android="S", ios="S"),
    G("Toram Online", "MMO", android="S", ios="S"),
    G("Ragnarok Online", "MMO"),
    G("Ragnarok Origin: ROO", "MMO", title="Ragnarok Origin", android="S", ios="S"),
    G("MIR4", "MMO", android="S", ios="S"),
    G("Summoners War", "Strategy", android="S", ios="S"),
    G("Undecember", "Action", android="S", ios="S"),
    G("Diablo® III", "Action", title="Diablo III", mac="S"),
    G("Diablo® II: Resurrected", "Action", title="Diablo II: Resurrected"),

    # --- More survival / sandbox -------------------------------------------
    G("SCUM", "Survival"),
    G("The Front", "Survival"),
    G("Deadside", "Survival"),
    G("V Rising", "Survival"),
    G("Path Of Titans", "Survival", title="Path of Titans", mac="S", android="S", ios="S"),
    G("The Isle", "Survival"),
    G("Phasmophobia", "Survival"),
    G("The Texas Chain Saw Massacre", "Survival"),
    G("Dying Light", "Survival"),
    G("FiveM", "Social", title="FiveM (GTA V roleplay)"),
    G("Goose Goose Duck", "Social", mac="S", android="S", ios="S"),
    G("SCP: Secret Laboratory", "Social"),
    G("s&box", "Social"),

    # --- More action --------------------------------------------------------
    G("Ghost of Tsushima Director's Cut", "Action", title="Ghost of Tsushima"),
    G("Armored Core VI: Fires of Rubicon", "Action", title="Armored Core VI"),
    G("Lords of the Fallen (2023)", "Action", title="Lords of the Fallen"),
    G("Warhammer: Vermintide 2", "Action"),
    G("FANTASY LIFE i: The Girl Who Steals Time", "Action", title="Fantasy Life i"),

    # --- More sports, racing & fighting ------------------------------------
    G("EA SPORTS™ Madden NFL 26", "Racing & Sports", title="Madden NFL 26"),
    G("F1® 25", "Racing & Sports", title="F1 25"),
    G("EA SPORTS™ WRC 24", "Racing & Sports", title="EA SPORTS WRC"),
    G("iRacing", "Racing & Sports"),
    G("Test Drive Unlimited Solar Crown", "Racing & Sports"),
    G("The Crew™ 2", "Racing & Sports", title="The Crew 2"),
    G("Riders Republic", "Racing & Sports"),
    G("skate.", "Racing & Sports"),
    G("CarX Street", "Racing & Sports", android="S", ios="S"),
    G("MotoGP™25", "Racing & Sports", title="MotoGP 25"),
    G("INAZUMA ELEVEN: Victory Road", "Racing & Sports", title="Inazuma Eleven: Victory Road"),
    G("DRAGON BALL FighterZ", "Fighting", title="Dragon Ball FighterZ"),
    G("DRAGON BALL XENOVERSE 2", "Fighting", title="Dragon Ball Xenoverse 2"),
    G("MY HERO ULTRA RUMBLE", "Fighting", title="My Hero Ultra Rumble"),
    G("NARUTO TO BORUTO: SHINOBI STRIKER", "Fighting", title="Naruto to Boruto: Shinobi Striker"),
    # --- Added October 2026 -------------------------------------------------
    G("Counter-Strike", "Shooter", title="Counter-Strike 1.6", mac="S"),
    G("Counter-Strike: Source", "Shooter"),
    G("Day of Defeat: Source", "Shooter"),
    G("Insurgency", "Shooter", mac="S"),
    G("Black Squad", "Shooter"),
    G("Mordhau", "Action"),
    G("Tom Clancy's Ghost Recon Wildlands", "Shooter", title="Ghost Recon Wildlands", steam="460930",
      url="https://www.ubisoft.com/en-us/game/ghost-recon/wildlands"),
    G("Tom Clancy's The Division", "Shooter", title="The Division"),
    G("Tom Clancy\u2019s Rainbow Six® Extraction", "Shooter", title="Rainbow Six Extraction"),
    G("Quake Champions", "Shooter"),
    G("BattleBit Remastered", "Shooter"),
    G("Sniper Elite 4", "Shooter"),
    G("Ghosts of Tabor", "Shooter", steam="1957780"),
    G("Onward", "Shooter"),
    G("Breachers", "Shooter"),
    G("Exoprimal", "Shooter"),
    G("World of Tanks Blitz", "Shooter", mac="S", android="S", ios="S", steam="444200"),
    G("Eternal Return", "MOBA", mac="S"),
    G("SMITE", "MOBA"),
    G("StarCraft: Remastered", "Strategy", mac="S"),
    G("Skull and Bones", "Action"),
    G("Watch_Dogs® 2", "Action", title="Watch Dogs 2"),
    G("Far Cry 5", "Action"),
    G("Fellowship", "Action", steam="2352620"),
    G("Myth of Empires", "Survival"),
    G("Deceit 2", "Social"),
    G("Predator: Hunting Grounds", "Survival", steam="1556200"),
    G("DiRT Rally 2.0", "Racing & Sports", steam="690790"),
    G("Sonic Rumble", "Battle Royale", android="S", ios="S"),
    G("Undawn", "Survival", android="S", ios="S"),
    G("Game of Thrones: Kingsroad", "Action", android="S", ios="S", steam="4214820"),
    G("Dragonheir: Silent Gods", "Anime RPG", android="S", ios="S"),
    G("Madoka Magica Magia Exedra", "Anime RPG", android="S", ios="S"),
    G("MapleStory Worlds", "MMO", android="S", ios="S"),
    # --- Added after October 2026 -------------------------------------------
    G("Call of Duty: Modern Warfare II (2022)", "Shooter", title="Call of Duty: Modern Warfare II"),
    G("Call of Duty: Vanguard", "Shooter"),
    G("Call of Duty Black Ops: Cold War", "Shooter", title="Call of Duty: Black Ops Cold War"),
    G("Call of Duty: Black Ops II", "Shooter"),
    G("PlanetSide 2", "Shooter"),
    G("STAR WARS™ Battlefront™ II (2017)", "Shooter", title="Star Wars Battlefront II"),
    G("STAR WARS™: Squadrons", "Shooter", title="Star Wars: Squadrons"),
    G("Aimlabs", "Shooter"),
    G("KovaaK", "Shooter", title="KovaaK's", steam="824270"),
    G("PROJECT: PLAYTIME", "Survival", title="Project: Playtime"),
    G("Killer Klowns from Outer Space: The Game", "Action"),
    G("DRAGON BALL: THE BREAKERS", "Action", title="Dragon Ball: The Breakers"),
    G("Harry Potter: Quidditch Champions", "Racing & Sports"),
    G("Pax Dei", "MMO"),
]

# Steam store IDs the upstream list doesn't have (used for cover art and store links).
EXTRA_STEAM = {
    "AFK Journey": "4195600", "Battlefield REDSEC": "3028330", "BLOODSTRIKE": "3199170",
    "Blue Protocol: Star Resonance": "3681810", "Call of Duty: Modern Warfare III (2023)": "3595270",
    "CarX Street": "1114150", "Chivalry 2": "1824220", "Delta Force: Hawk Ops": "2507950",
    "Diablo® II: Resurrected": "2536520", "EA SPORTS FC™ 26": "3405690", "EFootball 2025": "1665460",
    "Enlisted": "2051620", "Escape from Tarkov": "3932890", "F1® 25": "3059520",
    "FANTASY LIFE i: The Girl Who Steals Time": "2993780", "Gears of War: Reloaded": "2523720",
    "Girls' Frontline": "3887700", "Infinity Nikki": "3164330", "Killing Floor 3": "1430190",
    "Lords of the Fallen (2023)": "1501750", "MIR4": "1623660", "Outriders": "680420",
    "Pixel Gun 3D: PC Edition": "2524890", "Punishing: Gray Raven": "4125930", "REMATCH": "2138720",
    "s&box": "590830", "skate.": "3354750", "Sniper Elite: Resistance": "2169200",
    "Summoners War": "2426960", "Warhammer 40,000: Space Marine 2": "2183900",
    "Watch Dogs®: Legion": "2239550", "Zenless Zone Zero": "4162040",
}

# Linux news newer than the upstream list. Overrides its status and adds notes and timeline entries.
# Each fix: status letter (or None to keep upstream), notes [(text, url)], history [(event, "YYYY-MM-DD", url)].
LINUX_FIXES = {
    "Fortnite": ("P", [
        ("Epic confirmed Fortnite is coming to Linux via the Epic Games Launcher with Easy Anti-Cheat Linux v2. No release date yet.",
         "https://onlineservices.epicgames.com/news/introducing-easy-anti-cheat-linux-v2"),
        ("Needs Secure Boot, TPM 2.0 and a signed kernel. Steam Deck isn't supported yet; Epic is talking with Valve.",
         "https://www.gamingonlinux.com/2026/10/epic-games-launcher-preview-arrives-native-linux-support-fortnite-for-linux-is-coming-and-upgraded-easy-anti-cheat/"),
    ], [("Epic announces Fortnite for Linux", "2026-10-14",
         "https://onlineservices.epicgames.com/news/introducing-easy-anti-cheat-linux-v2")]),
    "skate.": (None, [
        ("Unofficial: the ReSkate fan project runs skate. on Linux and Steam Deck (offline and community servers, without EA's anti-cheat). Not supported by EA.",
         "https://github.com/Dingo-Shenanigans/ReSkate"),
    ], [("ReSkate fan project released", "2026-10-02", "https://www.pcgamer.com/games/sports/reskate-modding-platform-released/")]),
    "For Honor": ("D", [
        ("Ubisoft blocked Linux and Steam Deck from September 10, 2026, saying it can't get the anti-cheat protection it needs there.",
         "https://steamdeckhq.com/news/for-honor-drops-linux-support/"),
    ], [("Ubisoft blocks Linux and Steam Deck", "2026-09-10", "https://www.digitalcitizen.life/ubisoft-will-block-for-honor-on-linux-and-steam-deck-from-september-10/")]),
    "Battlefield 4": ("R", [
        ("Online play needs a manual PunkBuster update first.", "https://www.gamingonlinux.com/anticheat/"),
    ], []),
}

# Games not on Steam: a chosen cover image (official share image, App Store screenshot or Wikipedia),
# downloaded once into images/covers/ so the site doesn't depend on other servers.
COVER_URL = {
    "2XKO": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/0d8da14d9cc0c69376e8fb42cc6344276bf937ad-1200x600.jpg",
    "Blade & Soul NEO": "https://fizz-download.playnccdn.com/download/v2/buckets/marketing-platform/files/19fcb518a29-1423cb55-435c-46a7-ac98-e8535f1be781",
    "CrossFire": "https://upload.wikimedia.org/wikipedia/en/b/bd/CrossFire_%28video_game%29_logo.png",
    "Diablo® III": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blte3178c04d93773f1/67ce27f440e6651e27e17582/og_image.webp",
    "Escape from Tarkov: Arena": "https://arena.tarkov.com/_nuxt/img/main.98acbc0.jpg",
    "FiveM": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/271590/header.jpg?t=1765387725",
    "Fortnite": "https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/bd/a7/e3/bda7e31a-7341-2cf8-d54f-880aec955620/EN_FNBR_42-00_C7S4_Shot_1_iOS_AppStore_Screenshot_iPhone_2868x1320.jpg/1000x460bb.jpg",
    "Genshin Impact": "https://upload-static.hoyoverse.com/hk4e/upload/fb/common.jpg",
    "Heroes of the Storm": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt8c01f980b76eb350/67ce291560fcdc2c6cfed487/og_image.webp",
    "Honkai Star Rail": "https://fastcdn.hoyoverse.com/mi18n/hkrpg_global/m20260904hy5hcii9ds/upload/f0981b5c04af1c7a720d0bd65d958c52_1494770406828241360.png",
    "League of Legends": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news/565197caf987af4e4da307df6e2b235a28714736-837x469.jpg",
    "Legends of Runeterra": "https://playruneterra.com/assets/ccc9b55ec5fec88d1a616e7dec4795282a3aba52/static/image/share-image.jpg",
    "Lineage II": "https://fizz-download.playnccdn.com/download/v2/buckets/marketing-platform/files/1a12f0800cd-8c0443b1-524b-4e56-93a0-fc80a50831aa",
    "Nikke: Goddess of Victory": "https://nikke-en.com/pc/ossweb-img/og_image.jpg",
    "Path Of Titans": "https://alderongames.com/images/og/og-default-pot.png",
    "Point Blank": "https://upload.wikimedia.org/wikipedia/en/5/57/Pointblanklogo.jpg",
    "Princess Connect! Re:Dive": "https://dmg.priconne-redive.jp/ogp.jpg",
    "Ragnarok Origin: ROO": "https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/d0/e9/99/d0e99911-a695-ad4d-2a9d-d50f02cdb66a/004e4033-1606-4f40-a405-9bfb4cfb855a_1-_U8054_U52a8_U65f6_U88c5-2208X1242-_U82f1.jpg/1000x563bb.jpg",
    "RF ONLINE NEXT": "https://sgimage.netmarble.com/images/netmarble/rfnext/20250122/uct91737511657458.jpg",
    "Roblox": "https://images.rbxcdn.com/5348266ea6c5e67b19d6a814cbbb70f6.jpg",
    "Star Citizen": "https://upload.wikimedia.org/wikipedia/en/9/91/Star_Citizen_logo.png",
    "StarCraft II": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/bltbe2068a317e02d9f/6966bac0fb2fd910dbda4a26/og_image.webp",
    "Teamfight Tactics": "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/d63adacd93e313c1e61bbeb2eb37d8c4ca85848d-1920x1080.jpg",
    "StarCraft: Remastered": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt9cbae43d0642e6ba/6a9b42028102310ecb81e0e3/OG_Image.png",
    "Madoka Magica Magia Exedra": "https://madoka-exedra.com/ogp.jpg",
    "MapleStory Worlds": "https://maplestoryworlds.nexon.com/msw.jpg",
    "Valorant": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/500px-Valorant_logo_-_pink_color_version.svg.png",
    "WarCraft III: Reforged": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt806d59ff0b4e0508/6aa88158ad9209ba7f5629ef/rebirth_og.png",
    "World of Warcraft": "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/bltb5a24e5ab1e2cfb0/6a88e3589b942efdb6f74110/wow-thumbnail-homepage.jpg",
}

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "images" / "covers"
USER_AGENT = "WillItLaunch/1.0 (https://github.com/retroul/will-it-launch)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def steam_cover(appid):
    """Steam's own header image URL (newer games use hashed paths, so don't guess it)."""
    try:
        info = json.loads(fetch(f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic"))[appid]
        if info.get("success") and info["data"].get("header_image"):
            return info["data"]["header_image"]
    except Exception as err:
        print(f"  Steam lookup failed for {appid}: {err}")
    finally:
        time.sleep(0.4)  # stay well under Steam's rate limit
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


def saved_cover(url, slug):
    """Download a cover once into images/covers/ (shrunk to 600px wide); returns its site path or ''."""
    saved = sorted(COVERS.glob(f"{slug}.*"))
    if saved:
        return saved[0].relative_to(ROOT).as_posix()
    try:
        raw = fetch(url)
        COVERS.mkdir(parents=True, exist_ok=True)
        try:
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(raw))
            img.thumbnail((600, 600))
            img.info = {}  # drop embedded comments/metadata
            keep_alpha = img.mode in ("RGBA", "LA", "P") and "A" in img.convert("RGBA").getbands()
            path = COVERS / f"{slug}.{'png' if keep_alpha else 'jpg'}"
            if keep_alpha:
                img.convert("RGBA").save(path, optimize=True)
            else:
                img.convert("RGB").save(path, quality=82, optimize=True, progressive=True)
        except ImportError:  # no Pillow: keep the original file
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
            path = COVERS / f"{slug}{ext}"
            path.write_bytes(raw)
        print(f"  Saved cover {path.name}")
        return path.relative_to(ROOT).as_posix()
    except Exception as err:
        print(f"  Cover download failed for {slug}: {err}")
        return ""


DECK = {1: "unsupported", 2: "playable", 3: "verified"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def steam_ratings(appid, old):
    """Valve's Steam Deck rating and ProtonDB's recent tier; keeps the old values if a lookup fails."""
    deck, proton = old.get("deck", ""), old.get("protondb", "")
    try:
        res = json.loads(fetch(f"https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={appid}&l=english")).get("results") or {}
        deck = DECK.get(res.get("resolved_category"), "")
    except Exception as err:
        print(f"  Deck rating failed for {appid}: {err}")
    try:
        summary = json.loads(fetch(f"https://www.protondb.com/api/v1/reports/summaries/{appid}.json"))
        proton = summary.get("trendingTier") or summary.get("tier") or ""
    except urllib.error.HTTPError as err:
        proton = "" if err.code == 404 else proton
    except Exception as err:
        print(f"  ProtonDB lookup failed for {appid}: {err}")
    time.sleep(0.25)
    return deck, proton


def parse_day(text):
    """Turn upstream's mixed date formats ("Apr 12, 2022", "Mon 28, March 2022", "26 November 2019", ISO) into YYYY-MM-DD."""
    text = text or ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)
    year = re.search(r"\b(19|20)\d{2}\b", text)
    month = next((MONTHS[w[:3].lower()] for w in re.findall(r"[A-Za-z]{3,}", text) if w[:3].lower() in MONTHS), None)
    day = re.search(r"(?<![\d:])(\d{1,2})(?![\d:])", text[:year.start()] if year else text)
    if year and month and day:
        return f"{year.group(0)}-{month:02d}-{int(day.group(1)):02d}"
    return ""


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def platform(value):
    code, note = (value, None) if isinstance(value, str) else value
    return {"status": STATUS[code], "notes": [{"text": note}] if note else []}


def build(upstream, previous):
    by_name = {g["name"]: g for g in upstream}
    missing = [g["name"] for g in GAMES if g["name"] not in by_name]
    ours = {g["name"] for g in GAMES}
    missing += [f"{n} (in EXTRA_STEAM/COVER_URL/LINUX_FIXES but not in GAMES)" for n in {*EXTRA_STEAM, *COVER_URL, *LINUX_FIXES} - ours]
    if missing:
        sys.exit("Not found (fix the name):\n  " + "\n  ".join(missing))

    games = []
    for cur in GAMES:
        up = by_name[cur["name"]]
        title = cur["title"] or up["name"]
        slug = slugify(title)
        steam = cur["steam"] or EXTRA_STEAM.get(cur["name"]) or up.get("storeIds", {}).get("steam") or ""
        old = previous.get(slug, {})
        if steam:
            image = old["image"] if old.get("steam") == steam and old.get("image") else steam_cover(steam)
        elif cur["name"] in COVER_URL:
            image = saved_cover(COVER_URL[cur["name"]], slug)
        else:
            image = ""
        linux_notes = [{"text": t, "url": u} if u else {"text": t} for t, u in up.get("notes", [])]
        if up.get("native"):
            linux_notes.insert(0, {"text": "Native Linux version"})
        linux_status = up["status"].lower()
        history = [{"name": u["name"], "date": u["date"], "url": u.get("reference", "")} for u in up.get("updates", [])]
        updated = (up.get("dateChanged") or "")[:10]
        if cur["name"] in LINUX_FIXES:
            code, notes, events = LINUX_FIXES[cur["name"]]
            linux_status = STATUS[code] if code else linux_status
            linux_notes = [{"text": t, "url": u} for t, u in notes] + linux_notes
            history += [{"name": n, "date": d, "url": u} for n, d, u in events]
            updated = max([updated] + [d for _, d, _ in events])
        for h in history:
            h["day"] = parse_day(h["date"])
        deck, proton = steam_ratings(steam, old) if steam else ("", "")
        games.append({
            "slug": slug,
            "name": title,
            "genre": cur["genre"],
            "anticheats": up.get("anticheats", []),
            "url": cur["url"] or up.get("url") or "",
            "steam": steam,
            "image": image,
            "deck": deck,
            "protondb": proton,
            "updated": updated,
            "history": history,
            "platforms": {
                "windows": {"status": "supported", "notes": []},
                "macos": platform(cur["mac"]),
                "linux": {"status": linux_status, "notes": linux_notes},
                "android": platform(cur["android"]),
                "ios": platform(cur["ios"]),
            },
        })
    return sorted(games, key=lambda g: g["name"].lower())


def status_changes(old_games, games):
    """Status changes on any platform since the last build, for the "Recently changed" feed."""
    old = {g["slug"]: g for g in old_games}
    today = date.today().isoformat()
    changes = []
    for g in games:
        before = old.get(g["slug"])
        for plat, info in g["platforms"].items():
            if before and before["platforms"][plat]["status"] != info["status"]:
                changes.append({"day": today, "slug": g["slug"], "name": g["name"], "platform": plat,
                                "from": before["platforms"][plat]["status"], "to": info["status"]})
    return changes


PLATFORM_NAMES = {"windows": "Windows", "macos": "Mac", "linux": "Linux", "android": "Android", "ios": "iOS"}
STATUS_WORDS = {"supported": "works", "running": "works unofficially", "planned": "coming soon",
                "broken": "doesn't work", "denied": "blocked by devs", "unavailable": "not released"}


def news(games, changes, limit=60):
    """Newest events first: status changes plus dated timeline entries."""
    items = [{"day": c["day"], "slug": c["slug"], "name": c["name"], "url": "",
              "text": f"{PLATFORM_NAMES[c['platform']]}: {STATUS_WORDS[c['from']]} \u2192 {STATUS_WORDS[c['to']]}"}
             for c in changes]
    items += [{"day": h["day"], "slug": g["slug"], "name": g["name"], "text": h["name"], "url": h["url"]}
              for g in games for h in g["history"] if h["day"]]
    return sorted(items, key=lambda i: (i["day"], i["name"]), reverse=True)[:limit]


def write_feed(items):
    from email.utils import format_datetime
    from datetime import datetime, timezone
    from xml.sax.saxutils import escape
    entries = []
    for i in items[:40]:
        when = format_datetime(datetime.fromisoformat(i["day"]).replace(tzinfo=timezone.utc))
        link = f"{SITE_URL}#{i['slug']}"
        entries.append(f"""  <item>
    <title>{escape(i['name'])}: {escape(i['text'])}</title>
    <link>{escape(link)}</link>
    <guid isPermaLink="false">{escape(i['day'] + ':' + i['slug'] + ':' + i['text'])}</guid>
    <pubDate>{when}</pubDate>{f"{chr(10)}    <description>Source: {escape(i['url'])}</description>" if i['url'] else ""}
  </item>""")
    FEED.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Will It Launch? - recent changes</title>
  <link>{SITE_URL}</link>
  <description>Anti-cheat status changes for popular games on Windows, Mac, Linux, Steam Deck, Android and iOS.</description>
{chr(10).join(entries)}
</channel>
</rss>
""", encoding="utf-8")


def main():
    if len(sys.argv) > 1:
        upstream = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        with urllib.request.urlopen(UPSTREAM, timeout=30) as resp:
            upstream = json.load(resp)
    current = {}
    if OUT.exists():
        current = json.loads(OUT.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
    games = build(upstream, {g["slug"]: g for g in current.get("games", [])})
    changes = current.get("changes", []) + status_changes(current.get("games", []), games)
    if current.get("games") == games and current.get("changes", []) == changes and FEED.exists():
        print(f"No changes ({len(games)} games)")
        return
    items = news(games, changes)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        "// Generated by tools/update_data.py - edit that file, not this one.\n"
        f"window.AC_DATA = {json.dumps({'generated': date.today().isoformat(), 'games': games, 'changes': changes, 'news': items}, ensure_ascii=False, indent=1)};\n",
        encoding="utf-8")
    write_feed(items)
    print(f"Wrote {len(games)} games, {len(items)} news items to {OUT.name} and {FEED.name}")


if __name__ == "__main__":
    main()
