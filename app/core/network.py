import socket
import io
import base64
import qrcode
from app.core.config import PORT

def get_local_ip() -> str:
    """Detect local LAN IP address connecting outward."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, initiates routing lookup
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_mobile_access_url() -> str:
    ip = get_local_ip()
    return f"http://{ip}:{PORT}"

def print_terminal_qr(url: str = None) -> None:
    """Prints ASCII QR code in terminal on server launch."""
    if not url:
        url = get_mobile_access_url()
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    print("\n" + "=" * 55)
    print(f"🌸 [HouseholdAccountBook 가계부 서버 시작]")
    print(f" * PC 접속 URL     : http://localhost:{PORT}")
    print(f" * 모바일 접속 URL  : {url}")
    print(f" * 스마트폰 기본 카메라로 아래 QR 코드를 스캔하세요:")
    print("=" * 55)
    try:
        qr.print_ascii(invert=True)
    except Exception:
        print(f"[QR Code: {url}]")
    print("=" * 55 + "\n")

def get_qr_base64(url: str = None) -> str:
    """Generates base64 PNG data URI for web UI display."""
    if not url:
        url = get_mobile_access_url()
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2D3748", back_color="#FFFFFF")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
