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
import urllib.request
from datetime import date
from pathlib import Path

UPSTREAM = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "games.js"

STATUS = {"S": "supported", "R": "running", "P": "planned", "B": "broken", "D": "denied", "U": "unavailable"}
COD_MOBILE = ("S", "Separate game: Call of Duty: Mobile")


def G(name, genre, mac="U", android="U", ios="U", title=None, steam=None, url=None, linux_note=None):
    """One curated game. `name` must match the upstream entry exactly.
    Platform values are a status letter (see STATUS) or (letter, note)."""
    return dict(name=name, genre=genre, mac=mac, android=android, ios=ios,
                title=title, steam=steam, url=url, linux_note=linux_note)


# Popular games (roughly 100k+ monthly players) that ship with an anti-cheat.
GAMES = [
    # --- Shooters -----------------------------------------------------------
    G("Counter-Strike 2", "Shooter", mac=("U", "macOS support ended when CS:GO became CS2 (2023)"), steam="730"),
    G("Valorant", "Shooter", android=("U", "Valorant Mobile is only released in China"),
      ios=("U", "Valorant Mobile is only released in China")),
    G("Call of Duty: Black Ops 7", "Shooter", android=COD_MOBILE, ios=COD_MOBILE),
    G("Call of Duty: Black Ops 6", "Shooter"),
    G("Overwatch 2", "Shooter"),
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
    G("World of Tanks", "Shooter",
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
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def platform(value):
    code, note = (value, None) if isinstance(value, str) else value
    return {"status": STATUS[code], "notes": [{"text": note}] if note else []}


def build(upstream):
    by_name = {g["name"]: g for g in upstream}
    missing = [g["name"] for g in GAMES if g["name"] not in by_name]
    if missing:
        sys.exit("Not found upstream (fix the name in GAMES):\n  " + "\n  ".join(missing))

    games = []
    for cur in GAMES:
        up = by_name[cur["name"]]
        title = cur["title"] or up["name"]
        linux_notes = [{"text": t, "url": u} if u else {"text": t} for t, u in up.get("notes", [])]
        if up.get("native"):
            linux_notes.insert(0, {"text": "Native Linux version"})
        games.append({
            "slug": slugify(title),
            "name": title,
            "genre": cur["genre"],
            "anticheats": up.get("anticheats", []),
            "url": cur["url"] or up.get("url") or "",
            "steam": cur["steam"] or up.get("storeIds", {}).get("steam") or "",
            "updated": (up.get("dateChanged") or "")[:10],
            "history": [{"name": u["name"], "date": u["date"], "url": u.get("reference", "")}
                        for u in up.get("updates", [])],
            "platforms": {
                "windows": {"status": "supported", "notes": []},
                "macos": platform(cur["mac"]),
                "linux": {"status": up["status"].lower(), "notes": linux_notes},
                "android": platform(cur["android"]),
                "ios": platform(cur["ios"]),
            },
        })
    return sorted(games, key=lambda g: g["name"].lower())


def main():
    if len(sys.argv) > 1:
        upstream = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        with urllib.request.urlopen(UPSTREAM, timeout=30) as resp:
            upstream = json.load(resp)
    games = build(upstream)
    if OUT.exists():
        current = json.loads(OUT.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
        if current.get("games") == games:
            print(f"No changes ({len(games)} games)")
            return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        "// Generated by tools/update_data.py - edit that file, not this one.\n"
        f"window.AC_DATA = {json.dumps({'generated': date.today().isoformat(), 'games': games}, ensure_ascii=False, indent=1)};\n",
        encoding="utf-8")
    print(f"Wrote {len(games)} games to {OUT}")


if __name__ == "__main__":
    main()
