#!/usr/bin/env python3
"""
QR 코드 라우팅 테스트 스크립트
"""

import qrcode
import io
import base64

def test_qr_code_generation():
    """QR 코드 생성 테스트"""
    
    # 테스트할 URL들
    test_urls = [
        "https://port-0-buchat-m0t1itev3f2879ad.sel4.cloudtype.app/chat/test_room",
        "https://port-0-buchat-m0t1itev3f2879ad.sel4.cloudtype.app/join_room/test_room",
        "http://localhost:8000/chat/test_room",
        "http://localhost:8000/join_room/test_room"
    ]
    
    print("=== QR 코드 생성 테스트 ===")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. URL: {url}")
        
        # QR 코드 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        # 이미지 크기 확인
        width, height = img.size
        print(f"   QR 코드 크기: {width}x{height} 픽셀")
        
        # 파일로 저장
        filename = f"test_qr_{i}.png"
        img.save(filename)
        print(f"   저장됨: {filename}")

if __name__ == "__main__":
    test_qr_code_generation() 