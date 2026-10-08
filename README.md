# DS3 Enemy Remover - Choose Your Enemies

Developed by **HJP**. Nexus Mods username: **UNITYDEVELOPER**.

[Nexus Mods page](https://www.nexusmods.com/darksouls3/mods/2391)

Source for application version **0.2.14** (listed as version 1 on Nexus Mods).

A Windows desktop trainer for Dark Souls III. Select ordinary enemy types using illustrated cards, search by Korean/English name or model ID, browse area lists, and switch between Korean and English. Selections, language and removal mode are saved locally. Additional selections apply while removal is running.

**Removal applies only while the program is open and removal is running.** Pausing or exiting stops processing and attempts to restore still-valid affected instances. Reload the area if enemies do not return immediately. Minimizing keeps it running. Selections are remembered, but each new session requires starting removal again.

## Scope and compatibility

- Offline use only. The offline checkbox is user confirmation, not automatic online detection.
- Supported executable fingerprint: see `versions.json` (file version 1.15.0.0). Other fingerprints are rejected.
- Default mode matches selected model IDs across areas. A second mode restricts removal to recognized vanilla placements.
- Known base-game bosses and NPCs are excluded. Other mods may reuse ordinary enemy models as bosses or NPCs, so universal mod compatibility is not guaranteed.
- Removal complete means the relevant flags were read back on currently loaded eligible targets. It does not confirm every enemy in every area has disappeared.
- In-game removal has been reported by the developer's testing user. Complete compatibility, collision and travel behavior are not verified across all environments. A loading stall was reported in an earlier version; the current version suspends writes and restores valid instances during loading, with a stable-state delay before resuming.

## Windows requirements

- Python **3.10** to build or run the source. The packaged EXE does not require a Python installation.
- Microsoft Edge WebView2 Runtime and .NET Framework 4.6.2 or newer to run the desktop window.
- [Official WebView2 download](https://developer.microsoft.com/microsoft-edge/webview2/)

## Build from source

Open PowerShell in this repository directory. Create an isolated environment and install the pinned top-level build dependencies:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm DS3-Enemy-Trainer.spec
```

Output: `dist/DS3-Enemy-Trainer.exe`.

The specification embeds the UI, translation strings, illustration atlas, icon, placement identities and executable profile. Game installation files are not required to build. Dependency versions and packaging metadata can change the exact EXE bytes, so a rebuild is not promised to be byte-for-byte identical.

## Verification without game memory access

```powershell
.\.venv\Scripts\python.exe verify.py
.\dist\DS3-Enemy-Trainer.exe --desktop-smoke --home "$PWD\runtime\desktop-smoke"
```

`verify.py` uses fake memory adapters. `--desktop-smoke` uses a hidden native window and an adapter that cannot connect to the game. It checks UI behavior and shutdown, and writes diagnostic JSON under the supplied home directory. These checks do not replace in-game compatibility testing.

To run the source normally:

```powershell
.\.venv\Scripts\python.exe app.py
```

## What the program does

The program reads the running game's enemy list and writes selected flag bits on validated enemy instances. It uses no injected DLL or remote code execution. It directly modifies neither game files nor save files. Flags are restored only when the corresponding instance identity and memory context remain valid. The game can still record its own progression independently.

Session requests use a locally generated token and Host/Origin checks. No account password, API key or pre-generated session token is included in this repository. Personal selections, logs and caches are excluded.

`SOURCE_MANIFEST.json` lists SHA-256 hashes of the audited application files copied from the local 0.2.14 source. This repository contains source and assets for review, not the user's settings or raw game map files.

## Credits and notices

See `NAME_SOURCES.md` for English naming references and `THIRD_PARTY_NOTICES.txt` for bundled dependency notices. Public technical references used during development include [SilkySouls3](https://github.com/borgCode/SilkySouls3), [Dark Souls III CT TGA](https://github.com/The-Grand-Archives/Dark-Souls-III-CT-TGA), and [SoulSplitter](https://github.com/FrankvdStam/SoulSplitter). Source from these reference repositories is not bundled here.

## 한국어 안내

HJP가 제작한 다크소울3 몬스터 제거 트레이너의 공개용 소스입니다. 넥서스 계정은 UNITYDEVELOPER이며, 모드 페이지 번호는 2391입니다.

프로그램을 켜 두고 몹 제거를 실행하는 동안에만 적용됩니다. 종료하면 복원 가능한 개체의 비활성화를 해제합니다. 바로 돌아오지 않는 몬스터는 지역을 다시 불러오세요. 다음 실행에는 몹 제거 시작을 다시 눌러야 합니다.

오프라인에서만 사용하세요. 다른 모드가 같은 모델을 보스나 NPC로 재사용하면 함께 제거될 수 있습니다. 모든 모드 호환성을 보장하지 않습니다.

위의 Build from source 순서로 Windows에서 EXE를 만들 수 있습니다. 개인 설정, 실행 기록 및 원본 게임 파일은 포함하지 않았습니다.
