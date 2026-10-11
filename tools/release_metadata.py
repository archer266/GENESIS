"""Generate executable metadata and collect installed runtime license notices."""
from pathlib import Path
import json
import platform
import shutil
import zipfile
import os
import sys
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis import __version__


def main():
    build = ROOT / "release/build"
    build.mkdir(parents=True, exist_ok=True)
    version = tuple(int(n) for n in __version__.split('.'))+(0,)
    info = f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f, flags=0, OS=0x40004, fileType=0x1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription', 'GENESIS — Neon artificial life'), StringStruct('FileVersion', '{__version__}'), StringStruct('InternalName', 'GENESIS'), StringStruct('OriginalFilename', 'GENESIS.exe'), StringStruct('ProductName', 'GENESIS'), StringStruct('ProductVersion', '{__version__}')])]), VarFileInfo([VarStruct('Translation', [1033,1200])])])'''
    (build/'version_info.txt').write_text(info, encoding='utf-8')
    if '--zip' in sys.argv:
        source=ROOT/'release/dist/GENESIS'
        destination=ROOT/f'release/GENESIS-{__version__}-windows-x64.zip'
        temporary=destination.with_suffix('.zip.tmp')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for path in sorted(source.rglob('*')):
                if path.is_file():
                    archive.write(path,path.relative_to(source.parent))
        os.replace(temporary,destination)
        return
    if '--collect' not in sys.argv:

        return
    dist = ROOT/'release/dist/GENESIS'
    shutil.copy2(ROOT/'packaging/GETTING_STARTED.txt', dist)
    licenses = dist/'licenses'
    licenses.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('Python LICENSE.txt not found')
    shutil.copy2(python_license, licenses/'Python-LICENSE.txt')
    import pygame
    pgroot=Path(pygame.__file__).parent
    # Wheel ships SDL and pygame notices in generated documentation.
    for path in pgroot.rglob('*'):
        if path.is_file() and ('license' in path.name.lower() or 'copying' in path.name.lower() or path.name=='LGPL.txt'):
            relative = path.relative_to(pgroot)
            target=licenses/'pygame'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path,target)
    shutil.copytree(ROOT/'packaging/licenses', licenses/'runtime', dirs_exist_ok=True)
    packages={name:importlib.metadata.version(name) for name in ('pygame','pyinstaller','pyinstaller-hooks-contrib','altgraph','packaging','pefile','pywin32-ctypes','setuptools')}
    (dist/'build-info.json').write_text(json.dumps(dict(product='GENESIS',version=__version__,python=platform.python_version(),architecture=platform.machine(),platform=platform.platform(),packages=packages),indent=2),encoding='utf-8')
    (dist/'THIRD_PARTY.txt').write_text('''GENESIS runtime notices

Python: Python Software Foundation license; see licenses/Python-LICENSE.txt.
Pygame 2.6.1: LGPL 2.1; https://github.com/pygame/pygame/tree/2.6.1
SDL and supporting libraries: see licenses/runtime and its SOURCES.txt.
This software is based in part on the work of the Independent JPEG Group.
FreeType Project: https://www.freetype.org ? see FreeType notices.
Microsoft Visual C++ runtime: redistributed with the Python runtime;
https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files
Pygame DLLs remain separate in _internal/pygame and may be replaced with
compatible builds. Corresponding pygame source: https://github.com/pygame/pygame
PyInstaller bootloader: GPL with distribution exception allowing bundled apps;
https://pyinstaller.org/en/stable/license.html
Runtime/build versions: build-info.json. No third-party ownership is implied.
''',encoding='utf-8')


if __name__=='__main__':
    main()
