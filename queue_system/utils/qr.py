from __future__ import annotations

import base64
from io import BytesIO

import qrcode

# comnetraio: marcador no utilitario de QR


def gerar_qr_code_base64(payload: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")
