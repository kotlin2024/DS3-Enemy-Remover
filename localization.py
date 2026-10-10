"""Display-only localization. Game identities and protection policy stay unchanged.

English names checked against Souls Modding Wiki's DS3 character/map references
and Dark Souls III Wiki's enemy, boss and NPC pages. Internal variants use
parenthetical descriptions; they do not pretend to have separate official names.
"""
EN_ROWS = '''
c0000|Human NPC
c0100|Human Character
c1000|Invisible
c1070|Skeleton
c1071|Skeleton (The Ringed City)
c1090|Pus of Man
c1100|Hollow Soldier
c1101|Hollow Soldier (Lothric Castle)
c1102|Hollow Soldier (Grand Archives)
c1105|Large Hollow Soldier
c1106|Large Hollow Soldier (Lothric Castle)
c1130|Rotten Slug
c1170|Carthus Curved Sword Skeleton
c1180|Carthus Shotel Skeleton
c1190|Cathedral Knight
c1200|Hollow Slave
c1201|Hollow Slave (The Dreg Heap)
c1210|Ghru
c1211|Smouldering Ghru
c1220|Reanimated Corpse
c1230|Cathedral Evangelist
c1240|Peasant Hollow
c1241|Peasant Hollow (Irithyll Dungeon)
c1250|Grave Warden
c1260|Hollow Manservant
c1280|Lothric Knight (High Wall of Lothric)
c1281|Lothric Knight (Lothric Castle)
c1282|Lothric Knight (Red-Eyed)
c1283|Lothric Knight (The Dreg Heap)
c1290|Winged Knight
c1300|Black Knight
c1310|Boreal Outrider Knight
c1320|Crystal Sage
c1321|Crystal Sage (Grand Archives)
c1340|Grand Archives Scholar
c1350|Irithyllian Slave
c1360|Lycanthrope
c1370|Lycanthrope Hunter
c1380|Serpent-Man Summoner
c1390|Serpent-Man
c1391|Large Serpent-Man
c1400|Fire Keeper
c1410|Silver Knight
c1430|Cemetery Hollow
c1440|Hollow Soldier (Cathedral of the Deep)
c1441|Hollow Soldier (Road of Sacrifices)
c1442|Lothric Priest
c1445|Large Hollow Soldier (Cathedral of the Deep)
c1446|Sorcerer (Road of Sacrifices)
c1450|Ludleth of Courland
c1470|Bonewheel Skeleton
c1480|Irithyll Phantom
c1490|Irithyll Phantom (Variant)
c2020|Large Starved Hound
c2021|Starved Hound
c2030|Pontiff Knight
c2040|Monstrosity of Sin
c2060|Infested Corpse
c2070|Wretch
c2080|Festering Starved Hound
c2090|Oceiros, the Consumed King
c2100|Sewer Centipede
c2110|Hound-rat
c2120|Mimic
c2130|Writhing Rotten Flesh
c2131|Rotten Flesh of Aldrich
c2132|Smouldering Rotten Flesh
c2140|Basilisk
c2150|Crystal Lizard
c2160|Yoel of Londor / Pilgrim
c2170|Company Captain Yorshka
c2180|Corpse-grub
c2190|Gargoyle (Grand Archives)
c2191|Headless Gargoyle
c2200|Carthus Sandworm
c2210|Corvian
c2230|Jailer
c2240|Vordt of the Boreal Valley
c2250|Sulyvahn's Beast
c2260|Ballista
c2270|Great Crab
c2271|Lesser Crab
c2280|Large Hound-rat
c2290|Irithyllian Beast-hound
c3020|Giant Slave (Irithyll)
c3021|Giant Slave
c3040|Abyss Watchers
c3050|Old Demon King
c3060|Demon
c3070|Demon Cleric
c3071|Demon Cleric (Helper)
c3080|Pilgrim Butterfly
c3090|Cage Spider
c3100|Ravenous Crystal Lizard
c3110|Deep Accursed
c3120|Elder Ghru
c3140|Ancient Wyvern (Enemy)
c3141|Ancient Wyvern
c3160|Dragonslayer Armour
c3170|Darkwraith
c3190|Blacksmith Andre
c3200|Shrine Handmaid
c3210|Poisonhorn Bug
c3220|Rock Lizard
c3230|Demon Statue
c3250|Emma
c5010|Nameless King
c5020|Demon Prince
c5021|Demon Prince (Helper)
c5022|Demon Prince (Helper Variant)
c5030|King of the Storm
c5110|Gundyr
c5140|Pontiff Sulyvahn
c5150|Aldrich, Devourer of Gods
c5160|High Lord Wolnir
c5180|Curse-rotted Greatwood
c5200|Stray Demon
c5210|Rosaria, Mother of Rebirth
c5220|Deacons of the Deep
c5221|Deacons of the Deep (Helper)
c5222|Deacons of the Deep (Helper Variant)
c5223|Deacon of the Deep
c5225|Deacon of the Deep (Large, Irithyll)
c5226|Deacon of the Deep (Irithyll Variant)
c5227|Deacon of the Deep (Irithyll)
c5240|Fire Witch
c5250|Twin Princes
c5251|Twin Princes (Helper)
c5260|Yhorm the Giant
c5270|Dancer of the Boreal Valley
c5280|Soul of Cinder
c6000|Farron Follower
c6010|Father Ariandel
c6020|Sister Friede
c6030|Gravetender Greatwolf
c6040|Wolf
c6050|Wolf (Variant)
c6060|Birch Woman
c6070|Corvian Knight
c6080|Corvian Settler
c6081|Corvian Settler (Variant)
c6090|Giant Fly
c6100|Millwood Knight
c6120|The Painter
c6121|The Painter (Helper)
c6130|Great Crab (Painted World of Ariandel)
c6200|Slave Knight Gael
c6201|Slave Knight Gael (Helper)
c6210|Darkeater Midir (Bridge)
c6211|Darkeater Midir
c6230|Murkman (Summoner)
c6231|Murkman
c6232|Humanity Sprite
c6240|Pilgrim Pupa
c6250|Angel
c6260|Ringed Knight
c6270|Lothric Thief
c6280|Judicator
c6281|Judicator (Summoned Entity)
c6290|Hollow Cleric
c6300|Locust Preacher (Friendly)
c6310|Filianore
c6320|Harald Legion Knight
c6330|Locust Preacher
c6331|Locust Preacher (Small)
'''
EN_NAMES=dict(line.split('|',1) for line in EN_ROWS.strip().splitlines())
EN_MAPS={
 'm30_00_00_00':"High Wall of Lothric / Consumed King's Garden",
 'm30_01_00_00':'Lothric Castle',
 'm30_02_00_00':'Eclipsed Royal Castle 2 (Unused)',
 'm31_00_00_00':'Undead Settlement',
 'm32_00_00_00':'Archdragon Peak',
 'm33_00_00_00':'Road of Sacrifices / Farron Keep',
 'm34_00_00_00':'Eclipsed Royal Castle 2 (Unused)',
 'm34_01_00_00':'Grand Archives',
 'm35_00_00_00':'Cathedral of the Deep',
 'm36_00_00_00':'The Grave of God (Unused)',
 'm36_90_00_00':'The Grave of God 2 (Unused)',
 'm37_00_00_00':'Irithyll of the Boreal Valley / Anor Londo',
 'm38_00_00_00':'Catacombs of Carthus / Smouldering Lake',
 'm39_00_00_00':'Irithyll Dungeon / Profaned Capital',
 'm40_00_00_00':'Cemetery of Ash / Firelink Shrine / Untended Graves',
 'm41_00_00_00':'Kiln of the First Flame',
 'm45_00_00_00':'Painted World of Ariandel (DLC)',
 'm46_00_00_00':'Undead Match / Grand Roof',
 'm47_00_00_00':'Undead Match / Kiln of Flame',
 'm50_00_00_00':'The Dreg Heap (DLC)',
 'm51_00_00_00':'The Ringed City (DLC)',
 'm51_01_00_00':"Filianore's Rest (DLC)",
 'm53_00_00_00':'Undead Match / Dragon Ruins',
 'm54_00_00_00':'Undead Match / Round Plaza',
}
MESSAGES={
 '소울은 0부터 999999999까지의 정수로 입력해 주세요.':'Enter a whole number from 0 to 999999999.',
 '소울 변경은 캐릭터 로딩이 끝난 뒤 사용할 수 있습니다.':'Soul changes are available after your character finishes loading.',
 '소울 정보를 확인할 수 없습니다.':'Could not verify the soul balance.',
 '소울 적용을 확인하지 못했습니다. 현재 소울을 확인해 주세요.':'Could not confirm the change. Check your current soul balance.',
 '게임 종류를 변경했습니다. 몹 제거 시작을 눌러 주세요.':'Game profile changed. Click Start enemy removal to continue.',
 '실행 중인 게임과 탭이 다릅니다. 맞는 게임 탭을 선택해 주세요.':'The tab does not match the running game. Choose the matching game tab.',

 '제거 완료':'Removal complete',
 '현재 불러온 제거 대상 없음':'No removal targets currently loaded',
 '제거할 몬스터를 선택하세요.':'Select enemies to remove.',
 '읽기 전용 진단 중 · 몹 제거 사용을 체크하면 선택한 몬스터를 제거합니다.':'Read-only diagnostics · Enable enemy removal to remove selected enemies.',
 '일시중지 · 가능한 개체를 복원했습니다.':'Paused · Available enemies restored.',
 '로딩 중 · 몹 제거를 잠시 멈춥니다.':'Loading · Enemy removal is temporarily paused.',
 '로딩 완료 확인 중 · 잠시 후 몹 제거를 재개합니다.':'Checking loading completion · Enemy removal will resume shortly.',
 '제거 방식을 변경했습니다. 몹 제거 시작을 눌러 주세요.':'Removal mode changed. Click Start enemy removal to continue.',
 '모드 주의사항을 확인한 뒤 몹 제거를 시작해 주세요.':'Read and acknowledge the mod warning before starting enemy removal.',
 '모드가 감지되었습니다. 몹 제거 시작을 눌러 주의사항을 확인해 주세요.':'A mod loader was detected. Click Start enemy removal to review the warning.',
 '게임 실행을 기다리고 있습니다.':'Waiting for DARK SOULS III.',
 '게임이 여러 개 실행되어 연결하지 않았습니다.':'Multiple game processes detected. Connection paused.',
 '지원 지문과 다른 게임 실행 파일입니다. 메모리를 변경하지 않습니다.':'Unsupported game executable. No memory changes will be made.',
 '타이틀 또는 로딩 화면입니다.':'Title screen or loading.',
 '캐릭터 로드를 기다리고 있습니다.':'Waiting for your character to load.',
 '적 모델 식별자가 예상 구조와 다릅니다.':'Unexpected enemy model identifier.',
 '적 목록 범위가 예상 구조와 다릅니다.':'Unexpected enemy list structure.',
 '지역이 바뀌고 있습니다.':'Changing areas.',
 '연결됨 · 읽기 전용 대기':'Connected · Read-only standby',
 '연결됨 · 읽기 전용 대기 · 모드 로더 감지(연결 허용)':'Connected · Read-only standby · Mod loader detected (allowed)',
 '적 목록 진단 중 · 이 버전은 게임 내 검증 전이라 자동 제거는 잠겨 있습니다.':'Reading enemies · Enable enemy removal to apply your selection.',
 '오프라인 확인이 필요합니다.':'Confirm that your game is offline.',
 '게임의 오프라인 설정을 확인해 주세요.':'Confirm that your game is offline.',
 '몹 제거 중':'Removing enemies',
 '게임 상태 변경을 기다리고 있습니다.':'Waiting for the game state to settle.',
 '전용 창 진단 · 게임 메모리는 변경하지 않습니다.':'Window diagnostics · Game memory is not modified.',
 '잘못된 몬스터 선택입니다.':'Invalid enemy selection.',
 '보스/NPC 또는 미지원 종류가 포함되어 있습니다.':'Selection contains a boss, NPC or unsupported enemy.',
 '잘못된 요청 형식입니다.':'Invalid request format.',
 '잘못된 요청입니다.':'Invalid request.',
 '허용되지 않은 요청입니다.':'Request not allowed.',
 '없는 경로입니다.':'Unknown endpoint.',
 '전용 창을 표시하려면 Microsoft Edge WebView2 Runtime이 필요합니다. README의 공식 설치 안내를 확인해 주세요.':'Microsoft Edge WebView2 Runtime is required. See the installation link in the README.',
 '다른 DS3 Enemy Trainer가 이미 실행 중입니다. 이전 버전의 화면에서 프로그램 종료를 누르거나 전용 창을 닫은 뒤 다시 실행해 주세요. 브라우저 탭을 닫는 것만으로는 이전 버전이 종료되지 않습니다.':'Another DS3 Enemy Trainer is already running. Exit it using its Exit button or close its app window. Closing an old browser tab does not exit the trainer.',
}
def translate(message,language):
    if language!='en': return message
    if message in MESSAGES: return MESSAGES[message]
    if any('\uac00'<=c<='\ud7a3' for c in message):
        return 'Game connection error. Check the game state and permissions.'
    return message
