import os
import sys
import subprocess
import sounddevice as sd

INSTALLER_NAME = 'VBCABLE_Setup_x64.exe'


def is_installed() -> bool:
    devices = sd.query_devices()
    return any('CABLE Input' in d['name'] for d in devices)


def get_bundled_installer_path() -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', INSTALLER_NAME)


def install(progress_callback=None) -> bool:
    installer = get_bundled_installer_path()
    if not os.path.exists(installer):
        return False
    if progress_callback:
        progress_callback('Instalando driver VB-Cable...')
    result = subprocess.run([installer, '/S'], capture_output=True, timeout=60)
    return result.returncode == 0
