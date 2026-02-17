"""
ESC/POS receipt builder for thermal printers (network raw socket).
Output is bytes suitable to send to printer on port 9100.
"""

# ESC/POS commands (common subset)
ESC = b"\x1b"
GS = b"\x1d"
INIT = ESC + b"@"           # Initialize
BOLD_ON = ESC + b"E" + b"\x01"
BOLD_OFF = ESC + b"E" + b"\x00"
CENTER = ESC + b"a" + b"\x01"
LEFT = ESC + b"a" + b"\x00"
CUT_FULL = GS + b"V" + b"\x00"  # Full cut
CUT_PARTIAL = GS + b"V" + b"\x01"  # Partial cut
LF = b"\n"


def _text(s: str) -> bytes:
    return s.encode("utf-8", errors="replace")


def build_receipt(sale, store_name: str = "DJPOS", currency: str = "PKR") -> bytes:
    """Build ESC/POS bytes for a Sale. sale must have sale_items with item/bundle."""
    out = bytearray()
    out += INIT
    out += CENTER
    out += BOLD_ON
    out += _text(store_name[:32]) + LF
    out += BOLD_OFF
    out += _text(f"Receipt #{sale.id}") + LF
    out += _text(sale.created_at.strftime("%b %d, %Y %I:%M %p")) + LF
    out += _text("-" * 32) + LF
    out += LEFT

    if sale.customer_id:
        out += _text(f"Customer: {sale.customer.name}") + LF
        out += _text("-" * 32) + LF

    for ci in sale.sale_items.all():
        if ci.bundle_id:
            name = f"{ci.bundle.name} (Bdl)"
        else:
            name = ci.item.name
        # Truncate long names; format: "name x qty" then price on same or next line
        line = f"{name} x{ci.quantity}"
        if len(line) > 24:
            line = line[:21] + "..."
        amt = f"{currency} {ci.line_total:.0f}"
        out += _text(line) + LF
        out += _text(amt.rjust(32)) + LF

    out += _text("-" * 32) + LF
    out += BOLD_ON
    out += _text(f"TOTAL {currency} {sale.total:.0f}".rjust(32)) + LF
    out += BOLD_OFF
    out += _text("-" * 32) + LF
    out += CENTER
    out += _text("Thank you") + LF
    out += LF
    out += LF
    out += CUT_FULL
    return bytes(out)


def send_to_printer(data: bytes, host: str, port: int, timeout: float = 5.0) -> None:
    """Send raw bytes to a network printer. Raises OSError on failure."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(data)
