import pickle
import os
from config import GEMINI_API_KEY
from rag_utils import extract_district_from_query, is_waste_related_query

def debug_rag_search():
    """RAG 검색 과정을 디버깅합니다."""
    
    # 다문화.pkl 파일 로드
    if not os.path.exists('다문화.pkl'):
        print("❌ 다문화.pkl 파일이 없습니다.")
        return
    
    print("✅ 다문화.pkl 파일 로드 중...")
    with open('다문화.pkl', 'rb') as f:
        vector_db = pickle.load(f)
    
    print(f"📊 총 문서 수: {len(vector_db.documents)}")
    
    # 테스트 질문
    query = "해운대구에서 침대 버리는 방법"
    
    print(f"\n🔍 테스트 질문: {query}")
    
    # 1. 구군명 추출 테스트
    district = extract_district_from_query(query)
    is_waste = is_waste_related_query(query)
    print(f"구군명: {district}")
    print(f"쓰레기 관련: {is_waste}")
    
    # 2. 해운대구 관련 문서 찾기
    print(f"\n📄 해운대구 관련 문서 검색:")
    waste_docs = []
    for i, doc in enumerate(vector_db.documents):
        if isinstance(doc, dict) and 'metadata' in doc:
            metadata = doc['metadata']
            if 'category' in metadata and metadata['category'] == '쓰레기처리':
                if 'gu_name' in metadata and metadata['gu_name'] == '해운대구':
                    waste_docs.append(doc)
                    print(f"  - 문서 {i+1}: {metadata.get('title', '제목 없음')} (타입: {metadata.get('type', '타입 없음')})")
    
    print(f"\n🎯 해운대구 쓰레기 처리 문서 {len(waste_docs)}개 발견")
    
    # 3. 문서 내용 확인
    for i, doc in enumerate(waste_docs):
        print(f"\n--- 문서 {i+1} ---")
        print(f"제목: {doc['metadata'].get('title', '제목 없음')}")
        print(f"타입: {doc['metadata'].get('type', '타입 없음')}")
        print(f"내용: {doc['page_content'][:300]}...")
    
    # 4. 침대 관련 내용이 있는지 확인
    print(f"\n🛏️ 침대 관련 내용 검색:")
    bed_related_docs = []
    for doc in waste_docs:
        if '침대' in doc['page_content']:
            bed_related_docs.append(doc)
            print(f"  - {doc['metadata'].get('title', '제목 없음')}: 침대 관련 내용 포함")
    
    if not bed_related_docs:
        print("  - 침대 관련 내용이 포함된 문서가 없습니다.")
        # 대형폐기물 관련 문서 확인
        print(f"\n📦 대형폐기물 관련 문서 확인:")
        for doc in waste_docs:
            if doc['metadata'].get('type') == 'large_waste_info':
                print(f"  - {doc['metadata'].get('title', '제목 없음')}")
                print(f"    내용: {doc['page_content'][:200]}...")

if __name__ == "__main__":
    debug_rag_search() 