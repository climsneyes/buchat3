import pickle
import os
from config import GEMINI_API_KEY
from rag_utils import GeminiEmbeddings, extract_district_from_query, is_waste_related_query

def test_waste_search():
    """해운대구 쓰레기 처리 정보 검색을 테스트합니다."""
    
    # 다문화.pkl 파일 로드
    if not os.path.exists('다문화.pkl'):
        print("❌ 다문화.pkl 파일이 없습니다.")
        return
    
    print("✅ 다문화.pkl 파일 로드 중...")
    with open('다문화.pkl', 'rb') as f:
        vector_db = pickle.load(f)
    
    print(f"📊 총 문서 수: {len(vector_db.documents)}")
    
    # 해운대구 관련 문서 찾기
    haeundae_docs = []
    for i, doc in enumerate(vector_db.documents):
        if isinstance(doc, dict) and 'metadata' in doc:
            metadata = doc['metadata']
            if 'gu_name' in metadata and metadata['gu_name'] == '해운대구':
                haeundae_docs.append(doc)
                print(f"📄 해운대구 문서 {len(haeundae_docs)}: {metadata.get('title', '제목 없음')}")
    
    print(f"\n🎯 해운대구 관련 문서 {len(haeundae_docs)}개 발견")
    
    # 해운대구 문서 내용 확인
    for i, doc in enumerate(haeundae_docs):
        print(f"\n--- 해운대구 문서 {i+1} ---")
        print(f"제목: {doc['metadata'].get('title', '제목 없음')}")
        print(f"카테고리: {doc['metadata'].get('category', '카테고리 없음')}")
        print(f"타입: {doc['metadata'].get('type', '타입 없음')}")
        print(f"내용: {doc['page_content'][:200]}...")
    
    # 구군명 추출 테스트
    test_queries = [
        "해운대구에서 대형폐기물 버리는 방법",
        "해운대에서 쓰레기 버리는 방법",
        "haeundae-gu waste disposal",
        "해운대구 정화조 청소",
        "해운대 대형폐기물 수거업체"
    ]
    
    print(f"\n🔍 구군명 추출 테스트:")
    for query in test_queries:
        district = extract_district_from_query(query)
        is_waste = is_waste_related_query(query)
        print(f"질문: '{query}'")
        print(f"  - 구군명: {district}")
        print(f"  - 쓰레기 관련: {is_waste}")
        print()

if __name__ == "__main__":
    test_waste_search() 