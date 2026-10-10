# DS3 Enemy Trainer 0.3.4

Developed by HJP. A single standalone EXE with Vanilla, The Convergence and Cinders tabs, saved enemy selections, map filters and Korean / English UI.

## Use

1. Close the previous trainer and run DS3-Enemy-Trainer.exe.
2. Run DARK SOULS III offline and load your character.
3. Choose the tab matching your game: Vanilla, The Convergence or Cinders. Choosing a tab changes the trainer’s data, not your installed game mod.
4. Select enemies. To see loaded types, choose Currently loaded types in the map filter. Search also accepts model IDs.
5. Confirm offline mode, check Enable enemy removal, and click Start enemy removal. When prompted, acknowledge the mod warning.
6. While removal is running, selecting additional enemies applies them immediately. You do not need to click Start again.
7. Changing the game tab or removal mode pauses removal and restores valid modified instances. Click Start again after reviewing your selection.

**Removal applies only while the program is open and running. Exiting releases enemy disabling.** Reload the area if enemies do not return immediately. Minimizing keeps it running. A new game launch without the trainer uses the game’s normal enemies.

Each tab remembers its own selections. Language, tab and removal mode are also saved. Removal never starts automatically after reopening: confirm offline mode, enable removal and click Start.

## Game / mod data

- Vanilla: original game catalog and placements.
- The Convergence: local installation corpus, 16 maps, 3,242 placements and 27 additional model IDs.
- Cinders: local installation corpus, 20 maps, 3,827 placements and 21 additional model IDs.
- Known bosses, NPCs, boss health-bar/defeat references and registered protected instances are excluded. This includes additional bosses identified in the supported mod scripts.
- Existing species use original model names. Mods may change their name or appearance. Where available, Cinders placement labels are preserved in their original English. Unidentified additional species use their model ID. Dedicated artwork is mapped to 48 additional model IDs, based on the installed model geometry. Three invisible helpers use symbols instead of invented characters.
- Map filters use the selected tab’s placement data. Area names refer to the original map geography; renamed mod locations may differ. Currently loaded types come from the running game’s entity list, which can also contain off-screen instances.

Detection uses loaded proxy modules and Mod Engine configuration, when available. If a recognized running game disagrees with the selected tab, removal pauses. Detection is not exhaustive, particularly with other loaders or unpacked installations; check the selected tab yourself.

## Removal modes

- **Remove all of each selected type (default):** Matches model IDs across areas, including moved or additional copies. Known protected instances remain excluded.
- **Remove recognized placements only:** Matches the selected tab’s registered map, model and placement IDs. Suited to vanilla or a narrower scope. Changed or newly added placements in another mod version may remain.

The bundled mod data was extracted from the local installations used for development (Convergence 2.2.1 / Cinders 2.15 corpus). Other versions or additional edits may introduce unrecognized bosses, NPCs or models. In all-type mode, reusing a selected model as an unrecognized boss/NPC can affect progression. Review the warning before starting.

On 2026-10-10, the user confirmed in-game enemy removal in Vanilla, and both enemy removal and soul balance setting in Convergence and Cinders. The application also passed 51 automated checks and native desktop UI verification. These results apply to the tested local installations, not every version, area or additional mod configuration.

## Requirements and upgrading

Windows, the supported DS3 1.15.0.0 executable fingerprint, Microsoft Edge WebView2 Runtime and .NET Framework 4.6.2 or newer. Python is not needed to run the EXE. [Official WebView2 installer](https://developer.microsoft.com/microsoft-edge/webview2/).

Copy selection.json and settings.json beside the new EXE to retain previous choices. Old single-list selections migrate to the Vanilla tab. The EXE creates these files when used. It does not directly edit game files, saves, HP or event flags and does not inject code. Offline confirmation is a user checkbox, not automatic network-state detection.

Loading temporarily suspends removal. Removal resumes after a stable playable state. “Removal complete” means disabling flags were read back on all currently loaded eligible targets; it does not mean every map was processed. New targets continue to be monitored. Immediate disappearance, collision removal and restoration are not guaranteed.

## Build from source

Use 64-bit Python 3.10 on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt pyinstaller
.\.venv\Scripts\python.exe verify.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm DS3-Enemy-Trainer.spec
```

The build includes the supplied compact manifests. No mod installation is needed to rebuild. To regenerate mod identity metadata from legally installed local files:

```powershell
python build_mod_manifests.py --convergence "PATH_TO_CONVERGENCE" --cinders "PATH_TO_CINDERS"
```

The generator only reads local maps and event scripts and produces model/placement IDs and boss exclusions. It does not distribute game model, texture, map, parameter, message or script binaries.

English naming references: NAME_SOURCES.md. Third-party licenses: THIRD_PARTY_NOTICES.txt.


## Mod Engine 2 detection

Mod Engine 2 detection reads the running game's loader and launch configuration, considering enabled mod entries only. Unidentified environments allow manual tab selection. A known mismatch pauses removal to avoid using the wrong placement and boss/NPC data. Detection does not install or switch game mods.

## Set souls

The card below Enemy removal shows your current balance. Enter a whole number from 0 to 999,999,999, confirm offline play in the soul card, and click Apply souls. This makes a one-time balance change independently of enemy removal. It does not add to or freeze your balance, change soul level, lifetime souls or recoverable souls, directly edit saves, or force a save. Once saved by the game, the balance persists after the trainer closes. Loading, title screens, no connection and a mismatching game tab disable application.
