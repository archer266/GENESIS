# Run using tools/Build-Release.ps1 from a Windows Python 3.11 x64 environment.
from pathlib import Path
root = Path(SPECPATH).parent
a = Analysis([str(root / 'desktop_entry.py')], pathex=[str(root)],
             binaries=[], datas=[(str(root / 'genesis/assets'), 'genesis/assets')],
             hiddenimports=['pygame._sdl2.video'], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=['tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GENESIS',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          icon=str(root / 'genesis/assets/genesis.ico'),
          version=str(root / 'release/build/version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GENESIS')
