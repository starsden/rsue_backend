import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import secrets
import string

def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def make_qr_base64(data: str) -> str:
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgImage)
    bytes_io = BytesIO()
    img.save(bytes_io)
    bytes_io.seek(0)
    return base64.b64encode(bytes_io.read()).decode()