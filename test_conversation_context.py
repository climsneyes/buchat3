import pickle
import os
from config import GEMINI_API_KEY
from rag_utils import answer_with_rag

def test_conversation_context():
    """대화 컨텍스트 연결 로직을 테스트합니다."""
    
    # 다문화.pkl 파일 로드
    if not os.path.exists('다문화.pkl'):
        print("❌ 다문화.pkl 파일이 없습니다.")
        return
    
    print("✅ 다문화.pkl 파일 로드 중...")
    with open('다문화.pkl', 'rb') as f:
        vector_db = pickle.load(f)
    
    print(f"📊 총 문서 수: {len(vector_db.documents)}")
    
    # 테스트 시나리오: 순차적 입력
    test_scenarios = [
        {
            "name": "남구 책상 순차 입력",
            "queries": [
                "책상을 버리고 싶어요",
                "남구에요"
            ]
        },
        {
            "name": "해운대구 소파 순차 입력",
            "queries": [
                "소파 버리는 방법",
                "해운대구"
            ]
        },
        {
            "name": "동구 냉장고 순차 입력",
            "queries": [
                "냉장고 버리는 방법",
                "동구"
            ]
        }
    ]
    
    print("\n🔍 대화 컨텍스트 연결 로직 테스트")
    print("=" * 60)
    
    for scenario in test_scenarios:
        print(f"\n📝 시나리오: {scenario['name']}")
        print("-" * 50)
        
        # 대화 컨텍스트 초기화
        conversation_context = {}
        
        for i, query in enumerate(scenario['queries'], 1):
            print(f"\n  🔄 단계 {i}: {query}")
            print(f"  컨텍스트: {conversation_context}")
            
            try:
                # RAG 답변 생성
                answer = answer_with_rag(query, vector_db, GEMINI_API_KEY, target_lang='ko', conversation_context=conversation_context)
                
                print(f"  답변: {answer[:200]}...")
                
            except Exception as e:
                print(f"  ❌ 오류 발생: {e}")
            
            print("  " + "-" * 30)
        
        print(f"  ✅ 시나리오 완료: {scenario['name']}")

if __name__ == "__main__":
    test_conversation_context() 