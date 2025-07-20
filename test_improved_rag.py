import pickle
import os
from config import GEMINI_API_KEY
from rag_utils import answer_with_rag

def test_improved_rag():
    """개선된 RAG 시스템을 테스트합니다."""
    
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
        "중구에서 책상 버리는 방법",
        "해운대구에서 소파 버리는 방법",
        "동구에서 냉장고 버리는 방법",
        "서구에서 TV 버리는 방법",
        "영도구에서 자전거 버리는 방법"
    ]
    
    print("\n🔍 개선된 RAG 시스템 테스트")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 테스트 {i}: {query}")
        print("-" * 40)
        
        try:
            # 대화 컨텍스트 초기화
            conversation_context = {}
            
            # RAG 답변 생성
            answer = answer_with_rag(query, vector_db, GEMINI_API_KEY, target_lang='ko', conversation_context=conversation_context)
            
            print(f"답변: {answer}")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_improved_rag() 