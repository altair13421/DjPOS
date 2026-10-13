# launcher.py — build entry point, never used in normal dev
import os, sys, threading
import re
from datetime import datetime
from pathlib import Path
from config.paths import data_dir


def receipt_pdf_filename(page_url, now=None):
    match = re.search(r"/sale/(\d+)/receipt/?", page_url)
    receipt_id = match.group(1) if match else None
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    receipt_name = f"Receipt-{receipt_id}" if receipt_id else "Receipt"
    return f"{receipt_name}-{timestamp}.pdf"


def enable_receipt_pdf_saving(window):
    from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

    native_window = window.native

    class PrintBridge(QObject):
        setup_requested = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.setup_requested.connect(
                self.connect_print_signal, Qt.ConnectionType.QueuedConnection
            )

        @pyqtSlot()
        def connect_print_signal(self):
            webview_widget = native_window.webview
            webview_widget.page().printRequested.connect(self.print_receipt)

        @pyqtSlot()
        def print_receipt(self):
            native_window.webview.page().printToPdf(self.save_receipt_pdf)

        def save_receipt_pdf(self, pdf_data):
            if not pdf_data:
                QMessageBox.warning(
                    native_window,
                    "PDF generation failed",
                    "Could not generate receipt PDF.",
                )
                return

            filename = receipt_pdf_filename(native_window.webview.url().toString())
            output_path, _ = QFileDialog.getSaveFileName(
                native_window,
                "Save receipt as PDF",
                str(Path.home() / filename),
                "PDF files (*.pdf)",
            )
            if not output_path:
                return

            if not Path(output_path).suffix:
                output_path += ".pdf"
            try:
                Path(output_path).write_bytes(bytes(pdf_data))
            except OSError as error:
                QMessageBox.critical(
                    native_window,
                    "Could not save receipt",
                    f"The receipt PDF could not be saved: {error}",
                )

    bridge = PrintBridge()
    bridge.moveToThread(QApplication.instance().thread())
    window._qt_print_bridge = bridge
    bridge.setup_requested.emit()


def main():
    data_dir_path = data_dir()
    os.environ.update(
        {
            "APP_ROLE": "terminal",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJPOS_DATA_DIR": str(data_dir_path.parent),
        }
    )

    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", "--noinput")
    call_command("collectstatic", "--noinput")

    from sync.engine import worker

    threading.Thread(target=worker, daemon=True).start()

    from config.wsgi import application
    from waitress import serve

    threading.Thread(
        target=serve,
        args=(application,),
        kwargs={"host": "127.0.0.1", "port": 8001},
        daemon=True,
    ).start()
    import webview

    gui = "qt" if sys.platform in ("linux", "win32") else None

    window = webview.create_window(
        "DJPOS", "http://127.0.0.1:8001", width=1280, height=800
    )

    def setup_printing(*_):
        enable_receipt_pdf_saving(window)

    window.events.shown += setup_printing
    webview.start(gui=gui)  # blocks; closing the window closes the till app — nice kiosk behavior


if __name__ == "__main__":
    main()
