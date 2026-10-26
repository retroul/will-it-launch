// Short notes on the anti-cheats, shown on the Anti-cheats page. Edited by hand.
// Keys must match the anti-cheat names in data/games.js. Only add facts you can source;
// how each game actually does on each platform comes from the game data, not from here.
window.AC_INFO = {
  "Easy Anti-Cheat": "Made by Epic Games. Runs a kernel driver on Windows. It also has a Linux and Proton mode, but each developer has to switch it on, so two games with Easy Anti-Cheat can behave very differently.",
  "BattlEye": "Runs a kernel driver on Windows. Like Easy Anti-Cheat it can run under Proton, but only in games whose developer opted in.",
  "Vanguard": "Riot Games' anti-cheat. Its driver starts with Windows, before you open any game, and it doesn't run on Linux or under Proton.",
  "VAC": "Valve Anti-Cheat, used in Steam games like Counter-Strike 2 and Dota 2. It has no kernel driver and works on Linux, including in native Linux versions.",
  "Ricochet": "Activision's anti-cheat for Call of Duty. Adds a kernel driver on Windows.",
  "EA anticheat": "EA's own anti-cheat, also called EA Javelin. Runs a kernel driver on Windows.",
  "FACEIT": "Anti-cheat for FACEIT's competitive servers, mostly used with Counter-Strike 2. Kernel driver, Windows only. It only guards FACEIT matches: the game itself can still run elsewhere.",
  "PunkBuster": "An old anti-cheat by Even Balance, found in older games such as Battlefield 4.",
  "nProtect GameGuard": "Made by INCA Internet and common in Korean online games. Uses a kernel driver, and often stops games from starting under Wine or Proton.",
  "XIGNCODE3": "Made by Wellbia and common in Asian MMOs. Uses a kernel driver, and games with it often fail under Wine or Proton.",
  "Anti-Cheat Expert": "Tencent's anti-cheat, also called ACE, used in many games Tencent publishes. Runs a kernel driver on Windows.",
  "Denuvo Anti-Cheat": "Made by Irdeto, the company behind Denuvo. Runs a kernel driver on Windows. It's a different product from Denuvo's copy protection.",
  "miHoYo Protect": "HoYoverse's anti-cheat, used in games like Genshin Impact and Honkai: Star Rail. Runs a kernel driver on Windows.",
  "Hyperion": "Anti-tamper software made by Byfron, which Roblox bought in 2022.",
  "Warden": "Blizzard's anti-cheat, built into its Battle.net games.",
  "Unknown (Custom)": "The developer built its own anti-cheat, or hasn't said which one it uses.",
};
