# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

block_cipher = None

# Base directory of the repository
BASE_DIR = Path.cwd()

# Collect Streamlit assets & metadata
streamlit_datas = collect_data_files('streamlit')
streamlit_metadatas = copy_metadata('streamlit')
streamlit_submodules = collect_submodules('streamlit')

# Collect pywebview assets & submodules
webview_datas = collect_data_files('webview')
webview_submodules = collect_submodules('webview')

# Collect app data and config files
app_datas = [
    (str(BASE_DIR / 'app.py'), '.'),
    (str(BASE_DIR / 'settings_ui.py'), '.'),
    (str(BASE_DIR / 'shipping_ui.py'), '.'),
    (str(BASE_DIR / '.streamlit'), '.streamlit'),
    (str(BASE_DIR / 'services'), 'services'),
    (str(BASE_DIR / 'data'), 'data'),
]

all_datas = streamlit_datas + streamlit_metadatas + webview_datas + app_datas

all_hiddenimports = (
    streamlit_submodules
    + webview_submodules
    + [
        'streamlit.web.cli',
        'streamlit.runtime.caching',
        'openpyxl',
        'openpyxl.utils',
        'xlrd',
        'rapidfuzz',
        'pandas',
        'sqlite3',
        'uvicorn',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'uvicorn.logging',
        'starlette',
    ]
)

a = Analysis(
    ['desktop.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CDC_Excel_Matcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

output_folder = 'CDC_Excel_Matcher_Windows' if sys.platform == 'win32' else 'CDC_Excel_Matcher'

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=output_folder,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='CDC_Excel_Matcher.app',
        icon=None,
        bundle_identifier='com.xincaifu.cdcexcelmatcher',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
