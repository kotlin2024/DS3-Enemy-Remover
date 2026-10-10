from pathlib import Path
import shutil
from zipfile import ZipFile,ZIP_DEFLATED

root=Path(__file__).parent
release=root.parent/'_release'
name='DS3-Enemy-Trainer-0.3.4-desktop'
binary=release/name
for file in ('README_KO.md','README_EN.md','NAME_SOURCES.md','ART_SOURCES.md','THIRD_PARTY_NOTICES.txt'):
    shutil.copy2(root/file,binary/file)
groups=[('Windows',binary,['DS3-Enemy-Trainer.exe','README_KO.md','README_EN.md','NAME_SOURCES.md','ART_SOURCES.md','THIRD_PARTY_NOTICES.txt']),
        ('Source',root,['app.py','desktop.py','memory.py','mod_detection.py','trainer.py','probe.py','catalog.py','msb3.py',
                        'build_manifest.py','build_mod_manifests.py','event_policy.py','verify.py','localization.py','ui.html','ui.js','i18n.js','placements.json','placements_convergence.json','placements_cinders.json','versions.json',
                        'supported_maps.json','README_KO.md','DEVELOPMENT_KO.md',
                        'README_EN.md','NAME_SOURCES.md','ART_SOURCES.md','THIRD_PARTY_NOTICES.txt','assets/mascots.png','assets/mascots_convergence.png','assets/mascots_cinders.png','assets/mod-art.json','assets/mod-art-prompts.json','assets/app-icon.png','assets/app-icon.ico','package_release.py','requirements-desktop.txt','DS3-Enemy-Trainer.spec'])]
for suffix,folder,files in groups:
    path=release/f'{name}-{suffix}.zip'
    with ZipFile(path,'w',ZIP_DEFLATED) as archive:
        for file in files: archive.write(folder/file,f'{name}/{file}')
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(files)
    print(path,path.stat().st_size)
