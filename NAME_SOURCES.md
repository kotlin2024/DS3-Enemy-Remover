# English display names

Enemy model IDs and English terminology were checked against:

- [Souls Modding Wiki: Characters (DS3)](https://soulsmodding.com/doku.php?id=ds3-refmat:character-list)
- [Dark Souls III Wiki: Enemies](https://darksouls3.wikidot.com/enemies)
- [Dark Souls III Wiki: NPCs](https://darksouls3.wikidot.com/npcs)
- [Dark Souls III Wiki: Bosses](https://darksouls3.wikidot.com/bosses)
- [Souls Modding Wiki: Map Names (DS3)](https://soulsmodding.com/doku.php?id=ds3-refmat:map-name-list)

Use established English names such as Cathedral Knight, Sewer Centipede, Basilisk,
Mimic, Pus of Man and Cathedral of the Deep, rather than translating the Korean labels.
Some ordinary enemies do not have an on-screen official name; their names here
are established community names. Parenthetical area, variant and helper labels
are this application's descriptions of internal model variants, not extra official
enemy names. Unknown map IDs remain IDs. Unused maps use their documented internal
names and are marked as unused. A single model can represent multiple encounters
(for example Gundyr); display names do not change per-placement protection.

Only identifiers and names are used. No article text or images are redistributed.


## Mod tabs (0.3.0)

Mod Engine 2 launch evidence follows the launcher's [MODENGINE_CONFIG handling](https://github.com/soulsmods/ModEngine2/blob/main/launcher/launcher.cpp). The trainer reads the setting from the target game's process, parses enabled TOML mod entries with tomli, and returns unknown when the evidence is absent or ambiguous. Installed directories alone are not used to identify the active mod.

## Soul balance (0.3.3)

The fingerprinted 1.15.0.0 GameDataMan RVA (0x4740178), PlayerGameData pointer offset (0x10), and signed 32-bit current soul offset (0x74) are cross-checked against the locally archived [SilkySouls3 Offsets](https://github.com/borgCode/SilkySouls3/blob/master/SilkySouls3/Memory/Offsets.cs) and [PlayerService](https://github.com/borgCode/SilkySouls3/blob/master/SilkySouls3/Services/PlayerService.cs). This implementation updates only current balance; it does not update the adjacent lifetime-souls field, invoke game functions, freeze values, or directly modify saves. Pointer identity and loading state are rechecked before writing and the value is read back afterwards.

Cinders labels are taken from names authored in the locally installed mod’s MSB placements. They are not presented as official base-game English names. Convergence models without a confirmed name use their model ID. Existing models retain their original label, which can differ from a mod’s changed appearance. Region names describe the original map geography.

Boss reference extraction follows the binary layout documented by [SoulsFormats EMEVD](https://github.com/JKAnderson/SoulsFormats/tree/master/SoulsFormats/Formats/EMEVD) and the [DS3 EMEDF command definitions](https://soulsmods.github.io/emedf/ds3-emedf.html). This project contains its own small read-only reader; it does not bundle mod scripts or game data binaries.
