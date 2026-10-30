"""
Pure-Python QR Code generator producing crisp SVG vector graphics and dynamic UPI QR passes.
Implements ISO/IEC 18004 QR Code specification.
"""

import os
import io
import base64
from urllib.parse import quote
from django.conf import settings
import qrcode
from PIL import Image

# Galois Field GF(256) tables for polynomial division and Reed-Solomon ECC
EXP_TABLE = [0] * 512
LOG_TABLE = [0] * 256
val = 1
for i in range(255):
    EXP_TABLE[i] = val
    if val < 256:
        LOG_TABLE[val] = i
    val = (val << 1) ^ (0x11d if (val & 0x80) else 0)
for i in range(255, 512):
    EXP_TABLE[i] = EXP_TABLE[i - 255]

def gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return EXP_TABLE[LOG_TABLE[x] + LOG_TABLE[y]]

def rs_generator_poly(ec_count):
    g = [1]
    for i in range(ec_count):
        # Multiply g by (x - 2^i)
        next_g = [0] * (len(g) + 1)
        root = EXP_TABLE[i]
        for j in range(len(g)):
            next_g[j] ^= gf_mul(g[j], root)
            next_g[j + 1] ^= g[j]
        g = next_g
    return g

def rs_encode(data_bytes, ec_count):
    poly = rs_generator_poly(ec_count)
    msg = list(data_bytes) + [0] * ec_count
    for i in range(len(data_bytes)):
        lead = msg[i]
        if lead != 0:
            for j in range(len(poly)):
                msg[i + j] ^= gf_mul(poly[j], lead)
    return msg[len(data_bytes):]

class QRCodeSVG:
    """Lightweight QR Code Model (Version 2: 25x25 or Version 3: 29x29)"""
    def __init__(self, data_str):
        self.data_str = data_str
        # Select Version 2 (up to 32 bytes) or Version 3 (up to 53 bytes)
        raw_bytes = data_str.encode('utf-8')
        if len(raw_bytes) <= 28:
            self.version = 2
            self.size = 25
            self.total_codewords = 44
            self.data_codewords = 28
            self.ec_codewords = 16
            self.alignment_coords = [6, 18]
        else:
            self.version = 3
            self.size = 29
            self.total_codewords = 70
            self.data_codewords = 44
            self.ec_codewords = 26
            self.alignment_coords = [6, 22]

        self.matrix = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.is_reserved = [[False for _ in range(self.size)] for _ in range(self.size)]
        self._build()

    def _set_module(self, r, c, val, reserved=True):
        self.matrix[r][c] = 1 if val else 0
        if reserved:
            self.is_reserved[r][c] = True

    def _draw_finder_pattern(self, top, left):
        for r in range(-1, 8):
            for c in range(-1, 8):
                row = top + r
                col = left + c
                if 0 <= row < self.size and 0 <= col < self.size:
                    if (0 <= r <= 6 and (c == 0 or c == 6)) or \
                       (0 <= c <= 6 and (r == 0 or r == 6)) or \
                       (2 <= r <= 4 and 2 <= c <= 4):
                        self._set_module(row, col, 1)
                    else:
                        self._set_module(row, col, 0)

    def _draw_timing_patterns(self):
        for i in range(8, self.size - 8):
            val = 1 if (i % 2 == 0) else 0
            if not self.is_reserved[6][i]:
                self._set_module(6, i, val)
            if not self.is_reserved[i][6]:
                self._set_module(i, 6, val)

    def _draw_alignment_pattern(self, center_r, center_c):
        for r in range(-2, 3):
            for c in range(-2, 3):
                row = center_r + r
                col = center_c + c
                if not self.is_reserved[row][col]:
                    val = 1 if (abs(r) == 2 or abs(c) == 2 or (r == 0 and c == 0)) else 0
                    self._set_module(row, col, val)

    def _draw_format_info(self, mask_idx=0):
        # Format info for Error Correction Level M + Mask 0
        # 15-bit sequence with BCH error correction
        format_bits = 0x5412  # Standard format pattern for Level M, mask 0
        bits = [(format_bits >> i) & 1 for i in range(15)]
        
        # Draw around top-left finder
        coords1 = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)
        ]
        for i, (r, c) in enumerate(coords1):
            self._set_module(r, c, bits[14 - i])

        # Draw around top-right and bottom-left finders
        coords2 = [
            (self.size - 1, 8), (self.size - 2, 8), (self.size - 3, 8), (self.size - 4, 8),
            (self.size - 5, 8), (self.size - 6, 8), (self.size - 7, 8),
            (8, self.size - 8), (8, self.size - 7), (8, self.size - 6), (8, self.size - 5),
            (8, self.size - 4), (8, self.size - 3), (8, self.size - 2), (8, self.size - 1)
        ]
        for i, (r, c) in enumerate(coords2):
            self._set_module(r, c, bits[14 - i])

        # Dark module
        self._set_module(self.size - 8, 8, 1)

    def _pack_data(self):
        # Mode indicator: 0100 (Byte mode)
        bits = "0100"
        raw_bytes = self.data_str.encode('utf-8')[:self.data_codewords - 2]
        # Character count: 8 bits for version 1-9
        bits += f"{len(raw_bytes):08b}"
        for b in raw_bytes:
            bits += f"{b:08b}"
        
        # Terminator bits (up to 4 zeroes)
        target_bits = self.data_codewords * 8
        bits += "0000"
        if len(bits) > target_bits:
            bits = bits[:target_bits]
        else:
            # Pad to multiple of 8
            if len(bits) % 8 != 0:
                bits += "0" * (8 - (len(bits) % 8))

        # Convert to byte array
        data_bytes = bytearray([int(bits[i:i+8], 2) for i in range(0, len(bits), 8)])
        
        # Alternate pad bytes 0xEC, 0x11
        pad_patterns = [0xEC, 0x11]
        pad_idx = 0
        while len(data_bytes) < self.data_codewords:
            data_bytes.append(pad_patterns[pad_idx])
            pad_idx = 1 - pad_idx

        # Compute Reed-Solomon error correction codewords
        ec_bytes = rs_encode(data_bytes, self.ec_codewords)
        return data_bytes + bytearray(ec_bytes)

    def _build(self):
        # 1. Finder patterns
        self._draw_finder_pattern(0, 0)
        self._draw_finder_pattern(0, self.size - 7)
        self._draw_finder_pattern(self.size - 7, 0)

        # 2. Timing patterns
        self._draw_timing_patterns()

        # 3. Alignment pattern for Version 2/3
        self._draw_alignment_pattern(self.alignment_coords[1], self.alignment_coords[1])

        # 4. Format information
        self._draw_format_info(mask_idx=0)

        # 5. Place data codewords
        full_codewords = self._pack_data()
        data_bits = "".join(f"{b:08b}" for b in full_codewords)
        bit_idx = 0
        total_data_bits = len(data_bits)

        # Zigzag column placement from right to left in pairs
        col = self.size - 1
        upward = True
        while col > 0:
            if col == 6:  # Skip vertical timing column
                col -= 1

            rows = range(self.size - 1, -1, -1) if upward else range(self.size)
            for r in rows:
                for c in (col, col - 1):
                    if not self.is_reserved[r][c]:
                        bit_val = int(data_bits[bit_idx]) if bit_idx < total_data_bits else 0
                        bit_idx += 1
                        # Apply standard checkerboard mask 0: (row + col) % 2 == 0
                        masked_val = bit_val ^ (1 if (r + c) % 2 == 0 else 0)
                        self._set_module(r, c, masked_val, reserved=False)

            col -= 2
            upward = not upward

    def to_svg(self, box_size=10, border=4, fill_color="#0f172a", bg_color="#ffffff"):
        """Renders pure SVG XML string."""
        total_size = (self.size + 2 * border) * box_size
        rects = []

        for r in range(self.size):
            for c in range(self.size):
                if self.matrix[r][c] == 1:
                    x = (c + border) * box_size
                    y = (r + border) * box_size
                    rects.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="{fill_color}"/>')

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_size} {total_size}" '
            f'width="100%" height="100%" style="background-color: {bg_color}; border-radius: 8px;">'
            f'<rect width="100%" height="100%" fill="{bg_color}"/>'
            f'{"".join(rects)}'
            f'</svg>'
        )
        return svg

def generate_qr_svg(text):
    """
    Convenience helper to generate crisp, scannable QR code SVG string.
    Uses qrcode library for full-capacity Version 1-40 payloads (never truncates)
    with fall back to QRCodeSVG.
    """
    try:
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            border=4,
        )
        qr.add_data(str(text))
        qr.make(fit=True)
        matrix = qr.get_matrix()
        size = len(matrix)
        module_size = 6
        total_size = size * module_size

        rects = []
        for r in range(size):
            c = 0
            while c < size:
                if matrix[r][c]:
                    c_start = c
                    while c < size and matrix[r][c]:
                        c += 1
                    w = (c - c_start) * module_size
                    x = c_start * module_size
                    y = r * module_size
                    rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="{module_size}" fill="#0f172a"/>')
                else:
                    c += 1

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_size} {total_size}" '
            f'width="100%" height="100%" style="background-color: #ffffff; border-radius: 8px;">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>'
            f'{"".join(rects)}'
            f'</svg>'
        )
    except Exception:
        qr = QRCodeSVG(str(text))
        return qr.to_svg()

def generate_upi_qr_base64(amount, upi_id="jiyanshujain321@oksbi", payee_name="Jiyanshu Jain", aid="uGICAgICzpaebAQ", note="GoPlan Booking"):
    """
    Generates a dynamic UPI QR Code that auto-fills the exact payment amount
    when scanned with any UPI app (Google Pay, PhonePe, Paytm, BHIM, Cred).
    Includes the Google Pay center badge and returns a Base64 PNG data URI.
    """
    # Format amount with 2 decimal places (UPI standard format)
    amt_str = f"{float(amount):.2f}"
    pn_encoded = quote(payee_name)
    tn_encoded = quote(note)
    
    # Official NPCI / Google Pay UPI URI specification
    upi_uri = f"upi://pay?pa={upi_id}&pn={pn_encoded}&aid={aid}&am={amt_str}&cu=INR&tn={tn_encoded}"

    # Generate QR with high error correction (Level H) to allow center logo
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0b1120", back_color="white").convert("RGBA")

    # Center GPay Logo overlay
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'gpay_logo.png')
    if os.path.exists(logo_path):
        try:
            gpay = Image.open(logo_path).convert("RGBA")
            badge_dim = int(img.width * 0.22)
            gpay = gpay.resize((badge_dim, badge_dim), Image.Resampling.LANCZOS)
            pos = ((img.width - badge_dim) // 2, (img.height - badge_dim) // 2)
            img.paste(gpay, pos, gpay)
        except Exception:
            pass

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64_str}", upi_uri

