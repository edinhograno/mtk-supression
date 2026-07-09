import os
import sys
import subprocess
import tempfile
import urllib.request
import zipfile
import sounddevice as sd

INSTALLER_NAME = 'VBCABLE_Setup_x64.exe'
_DOWNLOAD_URL = 'https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip'
_ZIP_ENTRY = 'VBCABLE_Setup_x64.exe'


def is_installed() -> bool:
    devices = sd.query_devices()
    return any('CABLE Input' in d['name'] for d in devices)


def get_bundled_installer_path() -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', INSTALLER_NAME)


def _download_installer(progress_callback=None) -> str:
    """Downloads VB-Cable zip and extracts installer to a temp dir. Returns path to exe."""
    tmp_dir = tempfile.mkdtemp(prefix='mtk_vbcable_')
    zip_path = os.path.join(tmp_dir, 'vbcable.zip')

    if progress_callback:
        progress_callback('Baixando driver VB-Cable...')

    def _reporthook(count, block_size, total_size):
        if progress_callback and total_size > 0:
            pct = min(100, int(count * block_size * 100 / total_size))
            progress_callback(f'Baixando driver VB-Cable... {pct}%')

    urllib.request.urlretrieve(_DOWNLOAD_URL, zip_path, reporthook=_reporthook)

    if progress_callback:
        progress_callback('Extraindo instalador...')

    with zipfile.ZipFile(zip_path, 'r') as z:
        names = z.namelist()
        match = next((n for n in names if n.endswith(_ZIP_ENTRY)), None)
        if match is None:
            raise FileNotFoundError(f'{_ZIP_ENTRY} not found in zip')
        z.extractall(tmp_dir)
        extracted = os.path.join(tmp_dir, match)

    os.remove(zip_path)
    return extracted


def install(progress_callback=None) -> bool:
    installer = get_bundled_installer_path()

    if not os.path.exists(installer):
        try:
            installer = _download_installer(progress_callback)
        except Exception:
            return False

    if not os.path.exists(installer):
        return False

    if progress_callback:
        progress_callback('Instalando driver VB-Cable...')

    exe = sys.executable
    cwd = os.path.dirname(installer)
    ps1 = (
        f'$p = Start-Process -FilePath "{installer}" -ArgumentList "/S"'
        f' -Wait -WorkingDirectory "{cwd}" -PassThru\n'
        f'if ($p.ExitCode -eq 0) {{\n'
        f'    Start-Sleep -Milliseconds 1500\n'
        f'    & "{exe}" --rename-device\n'
        f'}}\n'
        f'exit $p.ExitCode\n'
    )

    ps_file = os.path.join(tempfile.gettempdir(), 'mtk_rename.ps1')
    with open(ps_file, 'w', encoding='utf-8') as f:
        f.write(ps1)

    try:
        subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden '
             f'-ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "{ps_file}")'],
            capture_output=True,
            timeout=180,
        )
    finally:
        try:
            os.unlink(ps_file)
        except OSError:
            pass

    if progress_callback:
        progress_callback('Configurando dispositivo de áudio...')

    return is_installed()
