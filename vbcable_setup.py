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
    cwd = os.path.dirname(installer)
    # Requires UAC elevation; Start-Process -Verb RunAs triggers the UAC prompt
    ps_cmd = (
        f'$p = Start-Process -FilePath "{installer}" -ArgumentList "/S"'
        f' -Verb RunAs -Wait -WorkingDirectory "{cwd}" -PassThru;'
        f' exit $p.ExitCode'
    )
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_cmd],
        capture_output=True,
        timeout=120,
    )
    return result.returncode == 0
