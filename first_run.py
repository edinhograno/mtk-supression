import sys
import threading
import winreg

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar,
)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QFont

import vbcable_setup
from config import Config
import style

_APP_NAME = 'MTKNoiseCanceller'
_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


class _InstallSignals(QObject):
    progress = Signal(str)
    done = Signal(bool)


class _ProgressDialog(QDialog):
    def closeEvent(self, event):
        event.ignore()


def run_if_needed(config: Config) -> bool:
    if not config.get('first_run', True):
        return True

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(style.app_stylesheet())

    if not vbcable_setup.is_installed():
        if not _ask_install_vbcable():
            return False
        ok = _install_with_progress()
        if not ok:
            _show_install_error()
            return False

    autostart = _ask_autostart()
    config.set('autostart', autostart)
    _set_autostart(autostart)
    config.set('first_run', False)
    config.save()
    return True


def _ask_install_vbcable() -> bool:
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 260)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    ear = QLabel('👂')
    ear.setFont(QFont('Segoe UI', 48))
    ear.setAlignment(Qt.AlignCenter)
    layout.addWidget(ear)

    title = QLabel('MTK Noise Canceller')
    f = QFont('Segoe UI', 14)
    f.setBold(True)
    title.setFont(f)
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)

    body = QLabel(
        'Bem-vindo! Precisamos instalar o VB-Cable para processar o áudio.\n\n'
        'O driver será baixado e instalado automaticamente (~5 MB).'
    )
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignCenter)
    layout.addWidget(body)

    btns = QHBoxLayout()
    cancel = QPushButton('Cancelar')
    ok_btn = QPushButton('Continuar')
    ok_btn.setDefault(True)
    btns.addWidget(cancel)
    btns.addWidget(ok_btn)
    layout.addLayout(btns)

    cancel.clicked.connect(dlg.reject)
    ok_btn.clicked.connect(dlg.accept)
    return dlg.exec() == QDialog.Accepted


def _install_with_progress() -> bool:
    dlg = _ProgressDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 160)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(12)

    status_lbl = QLabel('Iniciando...')
    status_lbl.setAlignment(Qt.AlignCenter)
    layout.addWidget(status_lbl)

    bar = QProgressBar()
    bar.setRange(0, 0)
    layout.addWidget(bar)

    result = [False]
    sig = _InstallSignals()
    sig.progress.connect(status_lbl.setText)
    sig.done.connect(lambda ok: (result.__setitem__(0, ok), dlg.accept()))

    def worker():
        try:
            ok = vbcable_setup.install(progress_callback=sig.progress.emit)
        except Exception:
            ok = False
        sig.done.emit(ok)

    threading.Thread(target=worker, daemon=True).start()
    dlg.exec()
    return result[0]


def _ask_autostart() -> bool:
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 180)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    body = QLabel(
        'Deseja que o MTK Noise Canceller\ninicialize automaticamente com o Windows?'
    )
    body.setAlignment(Qt.AlignCenter)
    body.setWordWrap(True)
    layout.addWidget(body)

    btns = QHBoxLayout()
    no_btn = QPushButton('Não')
    yes_btn = QPushButton('Sim')
    yes_btn.setDefault(True)
    btns.addWidget(no_btn)
    btns.addWidget(yes_btn)
    layout.addLayout(btns)

    no_btn.clicked.connect(dlg.reject)
    yes_btn.clicked.connect(dlg.accept)
    return dlg.exec() == QDialog.Accepted


def _show_install_error():
    dlg = QDialog()
    dlg.setWindowTitle('MTK Noise Canceller')
    dlg.setFixedSize(400, 180)
    dlg.setModal(True)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(30, 30, 30, 30)
    layout.setSpacing(16)

    body = QLabel(
        'Falha ao instalar VB-Cable.\n\n'
        'Verifique sua conexão com a internet e tente novamente.\n'
        'Se o problema persistir, execute o app como administrador.'
    )
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignCenter)
    layout.addWidget(body)

    close_btn = QPushButton('Fechar')
    close_btn.clicked.connect(dlg.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    dlg.exec()


def _set_autostart(enable: bool):
    exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
