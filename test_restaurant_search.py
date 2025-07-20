import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from restaurant_search_system import get_restaurant_search

def test_restaurant_search():
    print("=== 맛집검색 시스템 테스트 ===")
    
    # 검색 시스템 초기화
    search_system = get_restaurant_search()
    
    # 테스트 쿼리들
    test_queries = [
        "해운대 해산물 맛집",
        "서면 고기집", 
        "부산 피자집",
        "남포동 맛집",
        "카페 추천",
        "한식집",
        "중식집",
        "일식집",
        "양식집"
    ]
    
    for query in test_queries:
        print(f"\n--- 검색: '{query}' ---")
        result = search_system.hybrid_search(query)
        
        print(f"검색 쿼리: {result['query']}")
        print(f"키워드 검색 결과: {len(result['keyword_results'])}개")
        print(f"의미적 검색 결과: {len(result['semantic_results'])}개")
        print(f"통합 결과: {len(result['combined_results'])}개")
        
        # 실제 답변 출력
        print("\n=== 실제 답변 ===")
        print(result['answer'])
        print("=" * 50)

if __name__ == "__main__":
    test_restaurant_search() 