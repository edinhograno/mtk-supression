import sys
import winreg
import tkinter as tk
from tkinter import messagebox

import vbcable_setup
from config import Config

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


def run_if_needed(config: Config) -> bool:
    if not config.get('first_run', True):
        return True

    if not vbcable_setup.is_installed():
        if not _ask_install_vbcable():
            return False
        if not vbcable_setup.install():
            _show_install_error()
            return False

    autostart = _ask_autostart()
    config.set('autostart', autostart)
    _set_autostart(autostart)
    config.set('first_run', False)
    config.save()
    return True


def _ask_install_vbcable() -> bool:
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        'MTK Noise Canceller',
        'Este app precisa instalar um driver de áudio virtual (VB-Cable) para funcionar.\n\n'
        'Deseja instalar agora?',
    )
    root.destroy()
    return result


def _ask_autostart() -> bool:
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        'MTK Noise Canceller',
        'Deseja que o app inicie automaticamente com o Windows?',
    )
    root.destroy()
    return result


def _show_install_error():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        'MTK Noise Canceller',
        'Falha ao instalar VB-Cable.\nTente executar o app como administrador.',
    )
    root.destroy()


def _set_autostart(enable: bool):
    exe = sys.argv[0]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
