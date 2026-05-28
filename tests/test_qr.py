import base64

from queue_system.utils.qr import gerar_qr_code_base64


def test_gerar_qr_code_base64_retorna_base64():
    payload = "teste:123"
    qr_texto = gerar_qr_code_base64(payload)
    decoded = base64.b64decode(qr_texto)
    assert decoded.startswith(b"\x89PNG")
