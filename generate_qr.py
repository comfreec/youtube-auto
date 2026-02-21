"""
QR 코드 생성기
"""
import qrcode
from PIL import Image

# QR 코드 생성
url = "https://free-clean-mattress.vercel.app"
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

# 이미지 생성
img = qr.make_image(fill_color="black", back_color="white")

# 저장
output_path = "vercel_app_qr.png"
img.save(output_path)

print(f"✅ QR 코드 생성 완료!")
print(f"📁 파일: {output_path}")
print(f"🔗 URL: {url}")
print(f"\n스마트폰 카메라로 QR 코드를 스캔하면 사이트로 이동합니다.")
