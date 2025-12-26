# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 스펙 파일
송장번호 일괄 처리 시스템 빌드 설정
"""

block_cipher = None

a = Analysis(
    ['src/gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),  # 설정 파일 포함
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'serial',
        'serial.tools.list_ports',
        'openpyxl',
        'colorama',
        'requests',
        'pathlib',
        'json',
        'threading',
        'datetime',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='송장번호일괄처리시스템',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 모드 (콘솔 창 숨김)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 여기에 경로 지정
)

