import json

def check_junggu_actual_info():
    """중구의 실제 대형폐기물 수수료 정보를 확인합니다."""
    
    print("🔍 중구 대형폐기물 수수료 정보 확인")
    print("=" * 60)
    
    # 중구청 홈페이지에서 정보 확인
    junggu_url = "https://www.bsjunggu.go.kr/"
    
    print(f"📋 중구청 홈페이지: {junggu_url}")
    print("💡 중구청 홈페이지에서 '대형폐기물' 또는 '쓰레기처리' 메뉴를 찾아서")
    print("   실제 수수료 정보를 확인해주세요.")
    print()
    
    print("📞 중구청 자원순환과 연락처:")
    print("   - 전화: 051-600-4432")
    print("   - 담당부서: 자원순환과")
    print()
    
    print("🔗 중구 대형폐기물 수거업체:")
    print("   - 업체명: 여기로")
    print("   - 연락처: 1599-0903")
    print("   - 홈페이지: https://yeogiro24.co.kr/")
    print("   - 앱: '여기로' (구글스토어, 앱스토어)")
    print()
    
    print("📝 현재 JSON에 있는 중구 정보:")
    
    # 현재 JSON 파일에서 중구 정보 읽기
    try:
        with open('부산광역시_쓰레기처리정보.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        junggu_info = data.get('중구', {})
        
        print("   대형폐기물 수수료 예시:")
        fee_examples = junggu_info.get('대형폐기물_수수료_예시', [])
        for example in fee_examples:
            print(f"   - {example}")
        
        print()
        print("❌ 문제점: 현재 정보가 너무 간단하고 '책상' 등 구체적인 품목별 수수료가 없습니다.")
        print("✅ 해결방법: 중구청에 직접 문의하거나 홈페이지에서 상세 정보를 확인해야 합니다.")
        print()
        print("📋 임시 해결책:")
        print("   1. 중구청 자원순환과(051-600-4432)에 전화하여 책상 수수료 문의")
        print("   2. '여기로' 앱에서 책상 배출 신청 시 수수료 확인")
        print("   3. 중구청 홈페이지에서 대형폐기물 수수료표 다운로드")
        
    except Exception as e:
        print(f"❌ JSON 파일 읽기 오류: {e}")

if __name__ == "__main__":
    check_junggu_actual_info() 