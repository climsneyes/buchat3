import pickle
import os
from config import GEMINI_API_KEY
from rag_utils import answer_with_rag, extract_district_from_query, is_waste_related_query

def test_rag_answer():
    """실제 RAG 답변을 테스트합니다."""
    
    # 다문화.pkl 파일 로드
    if not os.path.exists('다문화.pkl'):
        print("❌ 다문화.pkl 파일이 없습니다.")
        return
    
    print("✅ 다문화.pkl 파일 로드 중...")
    with open('다문화.pkl', 'rb') as f:
        vector_db = pickle.load(f)
    
    print(f"📊 총 문서 수: {len(vector_db.documents)}")
    
    # 테스트 질문들
    test_queries = [
        "해운대구에서 대형폐기물 버리는 방법",
        "해운대에서 쓰레기 버리는 방법",
        "쓰레기 버리는 방법",  # 구군명 없는 경우
        "해운대구 정화조 청소업체",
        "해운대구 종량제 봉투 가격"
    ]
    
    conversation_context = {}
    
    for i, query in enumerate(test_queries):
        print(f"\n{'='*50}")
        print(f"테스트 {i+1}: {query}")
        print(f"{'='*50}")
        
        # 구군명 추출 테스트
        district = extract_district_from_query(query)
        is_waste = is_waste_related_query(query)
        print(f"구군명: {district}")
        print(f"쓰레기 관련: {is_waste}")
        
        # RAG 답변 생성
        try:
            answer = answer_with_rag(query, vector_db, GEMINI_API_KEY, target_lang='ko', conversation_context=conversation_context)
            print(f"\n답변:\n{answer}")
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n대화 컨텍스트: {conversation_context}")

if __name__ == "__main__":
    test_rag_answer() 