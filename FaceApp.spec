# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
import os
import glob

# Data files to include
datas = [
    ('style.qss', '.'),
    ('stats.json', '.'),
    ('yolov8n.pt', '.'),
    ('known_objects', 'known_objects'),
    ('logs', 'logs'),
]

# Collect PySide6 data files and modules
try:
    pyside6_data = collect_data_files('PySide6')
    datas += pyside6_data
except Exception:
    pass

try:
    pyside6_modules = collect_submodules('PySide6')
    hiddenimports = [
        'cv2', 'numpy', 'ultralytics', 'torch', 'torchvision',
        'geocoder', 'requests',
        'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets'
    ]
except Exception:
    hiddenimports = [
        'cv2', 'numpy', 'ultralytics', 'torch', 'torchvision',
        'geocoder', 'requests'
    ]

binaries = []

# Collect all dependencies for ultralytics, torch, torchvision
try:
    tmp_ret = collect_all('ultralytics')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    pass

try:
    tmp_ret = collect_all('torch')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    pass

try:
    tmp_ret = collect_all('torchvision')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    pass

try:
    tmp_ret = collect_all('cv2')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    pass

# Add OpenCV DLLs for video backends (MSMF, FFMPEG, etc.)
# These DLLs are needed for camera functionality on Windows
import cv2
import numpy as np

# Try to find OpenCV DLLs in the installation
def get_opencv_dlls():
    opencv_dlls = []
    try:
        # Get cv2 package location
        cv2_path = os.path.dirname(cv2.__file__)
        
        # Look for DLLs in the cv2 package
        for dll in glob.glob(os.path.join(cv2_path, '*.dll')):
            opencv_dlls.append((dll, '.'))
        
        # Also check for opencv_videoio*.dll files (video backends)
        # These might be in a different location
        try:
            import sys
            for path in sys.path:
                opencv_dir = os.path.join(path, 'cv2')
                if os.path.exists(opencv_dir):
                    for dll in glob.glob(os.path.join(opencv_dir, '*.dll')):
                        if (dll not in [x[0] for x in opencv_dlls]):
                            opencv_dlls.append((dll, '.'))
        except Exception:
            pass
            
    except Exception:
        pass
    return opencv_dlls

# Add OpenCV DLLs to binaries
opencv_dlls = get_opencv_dlls()
binaries += opencv_dlls

# Add ffmpeg DLLs if available (for video I/O)
def get_ffmpeg_dlls():
    ffmpeg_dlls = []
    try:
        # Check common locations for ffmpeg
        import subprocess
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_path = os.path.dirname(result.stdout.strip().split('\n')[0])
            for dll in glob.glob(os.path.join(ffmpeg_path, '*.dll')):
                ffmpeg_dlls.append((dll, '.'))
    except Exception:
        pass
    return ffmpeg_dlls

# Don't add ffmpeg DLLs automatically as they may not be in PATH

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FaceApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
