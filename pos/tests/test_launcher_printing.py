import re
from datetime import datetime
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication, QWidget

from launcher import enable_receipt_pdf_saving, receipt_pdf_filename


def test_receipt_pdf_filename_includes_sale_and_timestamp():
    filename = receipt_pdf_filename(
        "http://127.0.0.1:8001/pos/sale/8/receipt/",
        datetime(2026, 10, 14, 2, 25, 35),
    )

    assert filename == "Receipt-8-20261014-022535.pdf"


def test_print_request_saves_pdf_with_generated_default_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = Mock()
    webview_widget = Mock()
    window.native = QWidget()
    window.native.webview = webview_widget
    webview_widget.url.return_value.toString.return_value = (
        "http://127.0.0.1:8001/pos/sale/8/receipt/"
    )
    output_path = tmp_path / "receipt"

    with patch(
        "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(str(output_path), "PDF files (*.pdf)"),
    ) as save_dialog:
        enable_receipt_pdf_saving(window)
        app.processEvents()

        print_requested = webview_widget.page.return_value.printRequested.connect.call_args.args[0]
        print_requested()
        save_pdf = webview_widget.page.return_value.printToPdf.call_args.args[0]
        save_pdf(b"%PDF-receipt")

    suggested_path = save_dialog.call_args.args[2]
    assert re.fullmatch(r"Receipt-8-\d{8}-\d{6}\.pdf", suggested_path.rsplit("/", 1)[-1])
    assert (tmp_path / "receipt.pdf").read_bytes() == b"%PDF-receipt"
