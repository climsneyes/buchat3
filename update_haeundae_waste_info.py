import json
import os

def update_haeundae_waste_info():
    """해운대구 대형폐기물 수수료 예시에 침대 정보를 추가합니다."""
    
    # 기존 JSON 파일 로드
    with open('부산광역시_쓰레기처리정보.json', 'r', encoding='utf-8') as f:
        waste_data = json.load(f)
    
    # 해운대구 대형폐기물 수수료 예시 업데이트
    haeundae_large_waste_fees = [
        "가구류: 거실장식장 7,000~11,000원, 서랍장 6,000~11,000원, 소파 2,000~10,000원, 침대 5,000~18,000원",
        "가전제품: 냉장고 10,000~30,000원, 세탁기 5,000~7,000원, 에어컨 5,000~20,000원",
        "상세한 품목별 수수료는 해운대구청 홈페이지 참조"
    ]
    
    # 해운대구 정보 업데이트
    if "해운대구" in waste_data:
        waste_data["해운대구"]["대형폐기물_수수료_예시"] = haeundae_large_waste_fees
        print("✅ 해운대구 대형폐기물 수수료 예시 업데이트 완료")
    else:
        print("❌ 해운대구 정보를 찾을 수 없습니다.")
        return
    
    # 백업 파일 생성
    backup_filename = f'부산광역시_쓰레기처리정보.json.backup6'
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(waste_data, f, ensure_ascii=False, indent=2)
    
    # 업데이트된 JSON 파일 저장
    with open('부산광역시_쓰레기처리정보.json', 'w', encoding='utf-8') as f:
        json.dump(waste_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON 파일이 성공적으로 업데이트되었습니다!")
    print(f"📁 백업 파일: {backup_filename}")

if __name__ == "__main__":
    update_haeundae_waste_info() 