# -*- mode: python -*-
a = Analysis(['Python/sonicrelay.py'],
             pathex=['/home/jstroud/Unison/Code/SonicRelay/SonicRelay'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='SonicRelay',
          debug=False,
          strip=None,
          upx=True,
          console=True )
