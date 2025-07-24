import json
import pickle
import numpy as np
from rag_utils import GeminiEmbeddings
from typing import List, Dict, Any, Tuple
import re
from datetime import datetime

class HybridRestaurantSearch:
    def __init__(self, gemini_api_key):
        self.gemini_api_key = gemini_api_key
        self.restaurant_data = {}
        self.vector_db = None
        self.embeddings = GeminiEmbeddings(gemini_api_key)
        self.load_data()
    
    def load_data(self):
        """JSON 데이터와 벡터DB 로드"""
        print("맛집 데이터 로딩 중...")
        
        # 1. JSON 데이터 로드
        try:
            with open('부산의맛(2025).json', 'r', encoding='utf-8') as f:
                busan_food = json.load(f)
            
            with open('택슐랭(2025).json', 'r', encoding='utf-8') as f:
                taxi_ranking = json.load(f)
            
            # 데이터 통합 및 정규화
            self.restaurant_data = self.normalize_restaurant_data(busan_food, taxi_ranking)
            print(f"JSON 데이터 로드 완료: {len(self.restaurant_data)}개 맛집")
            
        except Exception as e:
            print(f"JSON 데이터 로드 오류: {e}")
            self.restaurant_data = {}
        
        # 2. 벡터DB 로드 (부산의맛.pkl이 있다면)
        try:
            with open('부산의맛.pkl', 'rb') as f:
                self.vector_db = pickle.load(f)
            print("벡터DB 로드 완료")
            
        except FileNotFoundError:
            print("벡터DB 파일이 없습니다. JSON 검색만 사용합니다.")
            self.vector_db = None
        except Exception as e:
            print(f"벡터DB 로드 오류: {e}")
            self.vector_db = None
    
    def normalize_restaurant_data(self, busan_food: Dict, taxi_ranking: Dict) -> List[Dict]:
        """맛집 데이터 정규화"""
        normalized_data = []
        
        # 부산의맛 데이터 처리
        if "부산의 맛 2025" in busan_food:
            busan_food_data = busan_food["부산의 맛 2025"]
            
            for district, restaurants in busan_food_data.items():
                if isinstance(restaurants, list):
                    for restaurant in restaurants:
                        if isinstance(restaurant, dict):
                            # 검색용 텍스트 생성
                            search_text_parts = []
                            
                            # 식당 이름
                            name = ""
                            if "식당이름" in restaurant:
                                name_obj = restaurant["식당이름"]
                                if isinstance(name_obj, dict):
                                    name = name_obj.get("한글", name_obj.get("영어", ""))
                                else:
                                    name = str(name_obj)
                            
                            if name:
                                search_text_parts.append(f"맛집 이름: {name}")
                            
                            # 개요
                            overview = ""
                            if "개요" in restaurant:
                                overview_obj = restaurant["개요"]
                                if isinstance(overview_obj, dict):
                                    overview = overview_obj.get("한글", overview_obj.get("영어", ""))
                                else:
                                    overview = str(overview_obj)
                            
                            if overview:
                                search_text_parts.append(f"개요: {overview}")
                            
                            # 메뉴
                            menu = ""
                            if "메뉴" in restaurant:
                                menu_obj = restaurant["메뉴"]
                                if isinstance(menu_obj, dict):
                                    menu = menu_obj.get("한글", menu_obj.get("영어", ""))
                                else:
                                    menu = str(menu_obj)
                            
                            if menu:
                                search_text_parts.append(f"메뉴: {menu}")
                            
                            # 기타 정보들
                            address = restaurant.get("주소", "")
                            if address:
                                search_text_parts.append(f"주소: {address}")
                            
                            phone = restaurant.get("전화번호", "")
                            if phone:
                                search_text_parts.append(f"전화번호: {phone}")
                            
                            hours = restaurant.get("영업시간", "")
                            if hours:
                                search_text_parts.append(f"영업시간: {hours}")
                            
                            closed = restaurant.get("휴무일", "")
                            if closed:
                                search_text_parts.append(f"휴무일: {closed}")
                            
                            # 검색용 텍스트 조합
                            search_text = " ".join(search_text_parts)
                            
                            normalized_item = {
                                'name': name,
                                'category': '',  # 부산의맛에는 카테고리가 없음
                                'location': district,
                                'address': address,
                                'phone': phone,
                                'rating': 0,  # 부산의맛에는 평점이 없음
                                'description': overview,
                                'menu': menu,
                                'hours': hours,
                                'closed': closed,
                                'source': '부산의맛',
                                'search_text': search_text,
                                'original_data': restaurant
                            }
                            normalized_data.append(normalized_item)
        
        # 택슐랭 데이터 처리
        if "restaurants" in taxi_ranking:
            restaurants = taxi_ranking["restaurants"]
            
            for restaurant in restaurants:
                if isinstance(restaurant, dict):
                    # 검색용 텍스트 생성
                    search_text_parts = []
                    
                    name = restaurant.get("name", "")
                    if name:
                        search_text_parts.append(f"맛집 이름: {name}")
                    
                    overview = restaurant.get("overview", "")
                    if overview:
                        search_text_parts.append(f"개요: {overview}")
                    
                    district = restaurant.get("district", "")
                    if district:
                        search_text_parts.append(f"지역: {district}")
                    
                    address = restaurant.get("address", "")
                    if address:
                        search_text_parts.append(f"주소: {address}")
                    
                    phone = restaurant.get("phoneNumber", "")
                    if phone:
                        search_text_parts.append(f"전화번호: {phone}")
                    
                    hours = restaurant.get("businessHours", "")
                    if hours:
                        search_text_parts.append(f"영업시간: {hours}")
                    
                    closed = restaurant.get("closedDays", "")
                    if closed:
                        search_text_parts.append(f"휴무일: {closed}")
                    
                    # 추천 메뉴
                    recommended_menu = restaurant.get("recommendedMenu", [])
                    if recommended_menu:
                        menu_texts = []
                        for menu_item in recommended_menu:
                            if isinstance(menu_item, dict):
                                menu_name = menu_item.get("name", "")
                                menu_price = menu_item.get("price", "")
                                if menu_name and menu_price:
                                    menu_texts.append(f"{menu_name} {menu_price}")
                        if menu_texts:
                            search_text_parts.append(f"추천메뉴: {', '.join(menu_texts)}")
                    
                    # 추천 이유
                    reason = restaurant.get("recommendationReason", "")
                    if reason:
                        search_text_parts.append(f"추천이유: {reason}")
                    
                    # 검색용 텍스트 조합
                    search_text = " ".join(search_text_parts)
                    
                    normalized_item = {
                        'name': name,
                        'category': '',  # 택슐랭에는 카테고리가 없음
                        'location': district,
                        'address': address,
                        'phone': phone,
                        'rating': 0,  # 택슐랭에는 평점이 없음
                        'description': overview,
                        'menu': ', '.join([f"{item.get('name', '')} {item.get('price', '')}" for item in recommended_menu if isinstance(item, dict)]),
                        'hours': hours,
                        'closed': closed,
                        'reason': reason,
                        'source': '택슐랭',
                        'search_text': search_text,
                        'original_data': restaurant
                    }
                    normalized_data.append(normalized_item)
        
        return normalized_data
    
    def search_by_keywords(self, query: str) -> List[Dict]:
        """키워드 기반 검색 (JSON 데이터)"""
        query_lower = query.lower()
        results = []
        
        # 검색 키워드 분리 (공백으로 구분)
        search_keywords = query_lower.split()
        
        # 음식 종류와 지역명 분리 (더 다양한 표현 포함)
        food_types = ['해산물', '한식', '중식', '일식', '양식', '고기', '카페', '피자', '치킨', '스시', '초밥', '회', '삼겹살', '갈비', '불고기']
        regions = ['서면', '해운대', '남포동', '광안리', '동래', '부산대', '부산시청', '부산역']
        
        # 쿼리에서 음식 종류와 지역명 추출
        query_food_type = None
        query_region = None
        
        # 음식 종류 매칭 (더 정교한 매칭)
        food_patterns = {
            '고기': ['고기', '고기집', '삼겹살', '갈비', '불고기', '돼지고기', '소고기', '갈비살', '고깃집'],
            '해산물': ['해산물', '해산물집', '생선', '회', '조개', '새우', '게', '문어', '오징어', '굴', '전복', '홍합', '바다', '수산물', '해산물 파는 집'],
            '스시': ['스시', '스시집', '초밥', '사시미', '일식', '일본'],
            '양식': ['양식', '양식집', '피자', '파스타', '스테이크', '샐러드', '이탈리안', '양식집'],
            '한식': ['한식', '한식집', '한국', '국밥', '국수', '비빔밥', '김치', '된장', '순대', '떡볶이'],
            '중식': ['중식', '중식집', '중국', '짜장면', '탕수육', '마파두부', '깐풍기', '훠궈'],
            '카페': ['카페', '커피', '베이커리', '디저트', '케이크', '빵'],
            '피자': ['피자', '도미노', '피자헛'],
            '치킨': ['치킨', '닭', '후라이드', '양념']
        }
        
        for food_type, patterns in food_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                query_food_type = food_type
                break
        
        for region in regions:
            if region in query_lower:
                query_region = region
                break
        
        for restaurant in self.restaurant_data:
            score = 0
            search_text = restaurant['search_text'].lower()
            name_lower = restaurant['name'].lower()
            location_lower = restaurant['location'].lower()
            description_lower = restaurant.get('description', '').lower()
            menu_lower = restaurant.get('menu', '').lower()
            
            # 음식 종류 매칭 (높은 우선순위)
            if query_food_type:
                food_keywords = {
                    '고기': ['고기', '고기집', '삼겹살', '갈비', '불고기', '돼지고기', '소고기', '갈비살', '고깃집', '삼겹살집', '갈비집'],
                    '해산물': ['해산물', '해산물집', '생선', '회', '조개', '새우', '게', '문어', '오징어', '굴', '전복', '홍합', '바다', '수산물', '해산물 파는 집', '회집', '생선집'],
                    '스시': ['스시', '스시집', '초밥', '사시미', '일식', '일본', '초밥집'],
                    '양식': ['양식', '양식집', '피자', '파스타', '스테이크', '샐러드', '이탈리안', '양식집', '피자집', '파스타집'],
                    '한식': ['한식', '한식집', '한국', '국밥', '국수', '비빔밥', '김치', '된장', '순대', '떡볶이', '국밥집', '국수집'],
                    '중식': ['중식', '중식집', '중국', '짜장면', '탕수육', '마파두부', '깐풍기', '훠궈', '짜장면집'],
                    '카페': ['카페', '커피', '베이커리', '디저트', '케이크', '빵'],
                    '피자': ['피자', '도미노', '피자헛', '피자집'],
                    '치킨': ['치킨', '닭', '후라이드', '양념', '치킨집']
                }
                
                if query_food_type in food_keywords:
                    keywords = food_keywords[query_food_type]
                    if any(keyword in search_text for keyword in keywords):
                        score += 25  # 음식 종류 매칭은 높은 점수
                    elif any(keyword in name_lower for keyword in keywords):
                        score += 20
                    elif any(keyword in description_lower for keyword in keywords):
                        score += 15
                    elif any(keyword in menu_lower for keyword in keywords):
                        score += 10
            
            # 지역명 매칭
            if query_region:
                region_keywords = {
                    '서면': ['서면', '부전동', '부전', '부산진구'],
                    '해운대': ['해운대', '해운대구'],
                    '남포동': ['남포동', '중구'],
                    '광안리': ['광안리', '광안대교', '수영구'],
                    '동래': ['동래', '동래구'],
                    '부산대': ['부산대', '금정구', '장전동'],
                    '부산시청': ['부산시청', '연제구'],
                    '부산역': ['부산역', '동구']
                }
                
                if query_region in region_keywords:
                    keywords = region_keywords[query_region]
                    if any(keyword in location_lower for keyword in keywords):
                        score += 15  # 지역명 매칭도 높은 점수
                    elif any(keyword in search_text for keyword in keywords):
                        score += 10
            
            # 일반 키워드 매칭 (낮은 우선순위)
            for keyword in search_keywords:
                if len(keyword) >= 2:  # 2글자 이상 키워드만
                    if keyword in name_lower:
                        score += 5
                    if keyword in location_lower:
                        score += 4
                    if keyword in description_lower:
                        score += 3
                    if keyword in menu_lower:
                        score += 2
                    if keyword in search_text:
                        score += 1
            
            # 정확한 매칭 (가장 높은 점수)
            if query_lower in name_lower:
                score += 25
            if query_lower in location_lower:
                score += 20
            if query_lower in description_lower:
                score += 15
            if query_lower in menu_lower:
                score += 12
            
            if score > 0:
                restaurant['match_score'] = score
                results.append(restaurant)
        
        # 음식 종류가 명시된 경우 해당 음식 종류의 맛집만 필터링
        if query_food_type:
            food_filtered_results = []
            food_keywords = {
                '고기': ['고기', '고기집', '삼겹살', '갈비', '불고기', '돼지고기', '소고기', '갈비살', '고깃집', '삼겹살집', '갈비집'],
                '해산물': ['해산물', '해산물집', '생선', '회', '조개', '새우', '게', '문어', '오징어', '굴', '전복', '홍합', '바다', '수산물', '해산물 파는 집', '회집', '생선집'],
                '스시': ['스시', '스시집', '초밥', '사시미', '일식', '일본', '초밥집'],
                '양식': ['양식', '양식집', '피자', '파스타', '스테이크', '샐러드', '이탈리안', '양식집', '피자집', '파스타집'],
                '한식': ['한식', '한식집', '한국', '국밥', '국수', '비빔밥', '김치', '된장', '순대', '떡볶이', '국밥집', '국수집'],
                '중식': ['중식', '중식집', '중국', '짜장면', '탕수육', '마파두부', '깐풍기', '훠궈', '짜장면집'],
                '카페': ['카페', '커피', '베이커리', '디저트', '케이크', '빵'],
                '피자': ['피자', '도미노', '피자헛', '피자집'],
                '치킨': ['치킨', '닭', '후라이드', '양념', '치킨집']
            }
            
            for result in results:
                search_text_lower = result['search_text'].lower()
                name_lower = result['name'].lower()
                description_lower = result.get('description', '').lower()
                menu_lower = result.get('menu', '').lower()
                
                # 음식 종류 키워드가 검색 텍스트, 이름, 설명, 메뉴 중 하나라도 포함되어 있으면 포함
                keywords = food_keywords.get(query_food_type, [])
                if any(keyword in search_text_lower for keyword in keywords) or \
                   any(keyword in name_lower for keyword in keywords) or \
                   any(keyword in description_lower for keyword in keywords) or \
                   any(keyword in menu_lower for keyword in keywords):
                    food_filtered_results.append(result)
            
            # 필터링된 결과가 있으면 사용, 없으면 원본 결과 사용
            if food_filtered_results:
                results = food_filtered_results
                print(f"음식 종류 필터링 적용: {query_food_type} 맛집 {len(results)}개")
        
        # 지역명이 명시된 경우 해당 지역의 맛집만 필터링
        if query_region:
            region_filtered_results = []
            region_keywords = {
                '서면': ['서면', '부전동', '부전', '부산진구'],
                '해운대': ['해운대', '해운대구'],
                '남포동': ['남포동', '중구'],
                '광안리': ['광안리', '광안대교', '수영구'],
                '동래': ['동래', '동래구'],
                '부산대': ['부산대', '금정구', '장전동'],
                '부산시청': ['부산시청', '연제구'],
                '부산역': ['부산역', '동구']
            }
            
            for result in results:
                location_lower = result['location'].lower()
                if any(keyword in location_lower for keyword in region_keywords.get(query_region, [])):
                    region_filtered_results.append(result)
            
            # 필터링된 결과가 있으면 사용, 없으면 원본 결과 사용
            if region_filtered_results:
                results = region_filtered_results
                print(f"지역 필터링 적용: {query_region} 지역 맛집 {len(results)}개")
        
        # 점수순 정렬
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results[:10]  # 상위 10개
    
    def search_by_semantic(self, query: str) -> List[Dict]:
        """의미적 검색 (벡터DB)"""
        if not self.vector_db:
            return []
        
        try:
            # 쿼리 임베딩
            query_embedding = self.embeddings.embed_query(query)
            
            # 유사도 계산
            similarities = np.dot(self.vector_db['embeddings'], query_embedding.T).flatten()
            
            # 상위 결과 인덱스
            top_indices = np.argsort(similarities)[::-1][:5]
            
            results = []
            for idx in top_indices:
                chunk = self.vector_db['chunks'][idx]
                # 청크에서 맛집 정보 추출 시도
                restaurant_info = self.extract_restaurant_from_chunk(chunk)
                if restaurant_info:
                    restaurant_info['similarity_score'] = float(similarities[idx])
                    results.append(restaurant_info)
            
            return results
            
        except Exception as e:
            print(f"의미적 검색 오류: {e}")
            return []
    
    def search_by_rag(self, query: str) -> List[Dict]:
        """RAG 기반 검색"""
        if not self.vector_db:
            print("벡터DB가 없습니다. JSON 키워드 검색을 사용합니다.")
            return self.search_by_keywords(query)
        
        try:
            # 쿼리 임베딩
            query_embedding = self.embeddings.embed_query(query)
            
            # 임베딩 형식 확인 및 변환
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding).reshape(1, -1)
            elif query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # 벡터DB 임베딩 차원 확인
            db_embeddings = self.vector_db['embeddings']
            query_dim = query_embedding.shape[1]
            db_dim = db_embeddings.shape[1]
            
            # 차원이 다르면 JSON 키워드 검색으로 대체
            if query_dim != db_dim:
                print(f"임베딩 차원 불일치: 쿼리({query_dim}) vs DB({db_dim}), JSON 키워드 검색으로 대체")
                return self.search_by_keywords(query)
            
            # 유사도 계산
            similarities = np.dot(db_embeddings, query_embedding.T).flatten()
            
            # 상위 결과 인덱스 (더 많은 결과 검색)
            top_indices = np.argsort(similarities)[::-1][:8]
            
            results = []
            for idx in top_indices:
                chunk = self.vector_db['chunks'][idx]
                # 청크에서 맛집 정보 추출 시도
                restaurant_info = self.extract_restaurant_from_chunk(chunk)
                if restaurant_info:
                    restaurant_info['similarity_score'] = float(similarities[idx])
                    results.append(restaurant_info)
            
            # RAG 결과가 없으면 JSON 키워드 검색으로 대체
            if not results:
                print("RAG 검색 결과가 없습니다. JSON 키워드 검색으로 대체합니다.")
                return self.search_by_keywords(query)
            
            return results
            
        except Exception as e:
            print(f"RAG 검색 오류: {e}, JSON 키워드 검색으로 대체")
            return self.search_by_keywords(query)
    
    def extract_restaurant_from_chunk(self, chunk: str) -> Dict:
        """청크에서 맛집 정보 추출"""
        # 간단한 패턴 매칭으로 맛집 정보 추출
        lines = chunk.split('\n')
        restaurant_info = {
            'name': '',
            'category': '',
            'location': '',
            'description': chunk[:200] + '...' if len(chunk) > 200 else chunk,
            'source': '벡터DB',
            'match_score': 0
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 지역 정보 추출 (가장 중요!)
            if line.startswith('지역:'):
                restaurant_info['location'] = line.replace('지역:', '').strip()
                continue
            
            # 맛집 이름 패턴 (한글 + 숫자/영문)
            if line.startswith('맛집 이름:') or line.startswith('식당이름:'):
                name = line.replace('맛집 이름:', '').replace('식당이름:', '').strip()
                if name and not restaurant_info['name']:
                    restaurant_info['name'] = name
                continue
            
            # 일반적인 맛집 이름 패턴 (한글 + 숫자/영문)
            if re.match(r'^[가-힣\w\s]+$', line) and len(line) > 2 and len(line) < 50:
                if not restaurant_info['name']:
                    restaurant_info['name'] = line
            
            # 카테고리 패턴
            if any(keyword in line for keyword in ['한식', '중식', '일식', '양식', '해산물', '고기', '치킨', '피자', '카페']):
                restaurant_info['category'] = line
        
        return restaurant_info if restaurant_info['name'] else None
    
    def hybrid_search(self, query: str) -> Dict[str, Any]:
        """RAG 기반 검색으로 변경"""
        print(f"검색 쿼리: {query}")
        
        # 지역명 분석 및 구 정보 추가
        enhanced_query = query
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            
            # 지역명 분석 프롬프트
            location_prompt = f"""
다음 검색어에서 부산의 지역명이나 주요 건물이 언급되었는지 확인하고, 해당 지역이 어느 구에 속하는지 알려주세요.

중요: 사용자가 구 이름을 명시하지 않았더라도, 지역명이나 주요 건물이 언급되면 반드시 해당 구를 찾아서 답변하세요.

부산 주요 지역과 구 매핑:
- 서면, 부전동, 부전, 서면역 → 부산진구
- 해운대, 해운대해수욕장, 해운대역 → 해운대구  
- 남포동, 용두산, 광복동, 중구 → 중구
- 광안리, 광안대교, 수영, 광안리역 → 수영구
- 동래, 온천동, 동래역 → 동래구
- 부산대, 장전동, 부산대역 → 금정구
- 사상, 사상구 → 사상구
- 연제, 연산동 → 연제구
- 북구, 구포 → 북구
- 강서, 명지 → 강서구
- 기장, 장안 → 기장군

부산 주요 건물과 구 매핑:
- 부산시청 → 연제구
- 부산역 → 동구
- 부산고속터미널 → 금정구
- 부산항국제여객터미널 → 중구
- 부산국제금융센터(BIFC) → 중구
- 부산타워 → 중구
- 용두산공원 → 중구
- 광복동 → 중구
- 남포동 → 중구
- 서면역 → 부산진구
- 해운대역 → 해운대구
- 광안리역 → 수영구
- 동래역 → 동래구
- 부산대역 → 금정구

검색어: "{query}"

지역명이나 주요 건물이 있으면 "지역명:구명" 형태로, 없으면 "없음"으로만 답변하세요.
예시: 
- "서면 맛집" → "서면:부산진구"
- "해운대 해산물" → "해운대:해운대구" 
- "부산시청 근처 맛집" → "부산시청:연제구"
- "서면 고기집 어디가 좋아" → "서면:부산진구"
- "해운대 근처 맛집" → "해운대:해운대구"
- "피자 맛집" → "없음"
"""
            
            location_response = model.generate_content(location_prompt, generation_config={"max_output_tokens": 128, "temperature": 0.1})
            location_result = location_response.text.strip()
            
            # 지역명이 발견되면 구 정보를 검색어에 추가
            if ":" in location_result and location_result != "없음":
                location_parts = location_result.split(":")
                if len(location_parts) == 2:
                    original_location = location_parts[0].strip()
                    district = location_parts[1].strip()
                    enhanced_query = f"{query} {district}"
                    print(f"지역명 분석: '{query}' -> '{original_location}:{district}' -> '{enhanced_query}'")
            
        except Exception as e:
            print(f"지역명 분석 오류: {e}")
            # API 오류 시에도 기본 검색 진행
            enhanced_query = query
        
        # 외국어 검색어를 한국어로 번역
        translated_query = enhanced_query
        try:
            # 간단한 외국어 감지 (한글이 포함되지 않은 경우)
            if not any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7af' for char in enhanced_query):
                # Gemini API를 사용하여 한국어로 번역
                import google.generativeai as genai
                
                genai.configure(api_key=self.gemini_api_key)
                model = genai.GenerativeModel("gemini-2.0-flash-lite")
                
                prompt = f"Translate the following text to Korean and return only the translation. This is for restaurant search in Busan, so translate food-related terms appropriately.\nText: {enhanced_query}"
                response = model.generate_content(prompt, generation_config={"max_output_tokens": 256, "temperature": 0.1})
                translated_query = response.text.strip()
                print(f"외국어 검색어 번역: '{enhanced_query}' -> '{translated_query}'")
        except Exception as e:
            print(f"검색어 번역 오류: {e}")
            # 번역 실패 시 원본 쿼리 사용
            translated_query = enhanced_query
        
        # RAG 검색만 사용
        rag_results = self.search_by_rag(translated_query)
        print(f"RAG 검색 결과: {len(rag_results)}개")
        
        # 결과 처리
        combined_results = self.combine_results(rag_results)
        
        # 답변 생성
        answer = self.generate_answer(query, combined_results)
        
        return {
            'query': query,
            'combined_results': rag_results,
            'answer': answer
        }

    def combine_results(self, rag_results: List[Dict]) -> List[Dict]:
        """RAG 검색 결과 처리"""
        # 유사도 점수순 정렬
        rag_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        # 중복 제거
        unique_results = []
        seen_names = set()
        
        for result in rag_results:
            name = result.get('name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                unique_results.append(result)
        
        return unique_results[:10]  # 상위 10개

    def generate_answer(self, query: str, results: List[Dict]) -> str:
        """검색 결과를 바탕으로 답변 생성"""
        if not results:
            # DB에 없는 경우 Gemini 검색을 통해 답변 생성
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                model = genai.GenerativeModel("gemini-2.0-flash-lite")
                
                prompt = f"""부산 맛집에 대한 질문에 대해 100자 이내로 간단하고 친근하게 답변해주세요.

질문: {query}

답변은 다음 조건을 만족해야 합니다:
1. 100자 이내로 간단하게
2. 친근하고 도움이 되는 톤
3. 부산 맛집 관련 정보 제공
4. 구체적인 추천이나 조언 포함

예시 답변 스타일:
- "부산에서 {query} 맛집을 찾고 계시는군요! 해운대구의 해산물 맛집이나 서면의 분식집을 추천해드려요."
- "부산 {query} 맛집은 광안리나 남포동에 많이 있어요. 특히 해운대구의 해산물 맛집들이 유명합니다."
"""
                    
                response = model.generate_content(prompt, generation_config={"max_output_tokens": 200, "temperature": 0.7})
                return response.text.strip()
            except Exception as e:
                print(f"Gemini 검색 오류: {e}")
                # API 오류 시 기본 답변 제공
                return f"부산에서 {query} 맛집을 찾고 계시는군요! 해운대구의 해산물 맛집이나 서면의 분식집을 추천해드려요. 더 구체적인 지역이나 음식 종류를 말씀해주시면 더 정확한 추천을 드릴 수 있어요."
        
        answer_parts = []
        
        # 특정 맛집 이름으로 검색한 경우 (첫 번째 결과가 정확히 일치하는 경우)
        if len(results) > 0:
            first_result = results[0]
            first_name = first_result.get('name', '').strip()
            query_lower = query.lower()
            
            # 검색어에 맛집 이름이 포함되어 있고, 첫 번째 결과가 정확히 일치하는 경우
            if first_name and first_name.lower() in query_lower:
                answer_parts.append(f"'{first_name}'에 대한 상세 정보입니다! 🍽️")
                
                # 해당 맛집만 상세히 표시
                restaurant = first_result
                name = restaurant.get('name', '이름 없음')
                category = restaurant.get('category', '')
                location = restaurant.get('location', '')
                rating = restaurant.get('rating', 0)
                address = restaurant.get('address', '')
                phone = restaurant.get('phone', '')
                hours = restaurant.get('hours', '')
                menu = restaurant.get('menu', '')
                description = restaurant.get('description', '')
                
                info = f"\n**{name}**"
                if category:
                    info += f" ({category})"
                if location:
                    info += f" - {location}"
                if rating:
                    info += f" ⭐ {rating}"
                if address:
                    info += f"\n📍 **주소**: {address}"
                if phone:
                    info += f"\n📞 **전화번호**: {phone}"
                if hours:
                    info += f"\n🕒 **영업시간**: {hours}"
                if menu:
                    info += f"\n🍽️ **메뉴**: {menu}"
                if description:
                    info += f"\n📝 **설명**: {description}"
                
                answer_parts.append(info)
                answer_parts.append("\n더 자세한 정보가 필요하시면 말씀해주세요!")
                
                return "".join(answer_parts)
        
        # 일반 검색 결과 표시
        # 쿼리 분석
        if any(keyword in query for keyword in ['추천', '어디', '좋은']):
            answer_parts.append(f"'{query}'에 대한 맛집을 찾아드렸습니다! 🍽️")
        else:
            answer_parts.append(f"'{query}' 검색 결과입니다! 🍽️")
        
        # 결과 요약
        answer_parts.append(f"\n총 {len(results)}개의 맛집을 찾았습니다:")
        
        # 모든 맛집 상세 정보 표시
        for i, restaurant in enumerate(results, 1):
            name = restaurant.get('name', '이름 없음')
            category = restaurant.get('category', '')
            location = restaurant.get('location', '')
            rating = restaurant.get('rating', 0)
            address = restaurant.get('address', '')
            phone = restaurant.get('phone', '')
            hours = restaurant.get('hours', '')
            menu = restaurant.get('menu', '')
            
            info = f"\n{i}. **{name}**"
            if category:
                info += f" ({category})"
            if location:
                info += f" - {location}"
            if rating:
                info += f" ⭐ {rating}"
            if address:
                info += f"\n   📍 {address}"
            if phone:
                info += f"\n   📞 {phone}"
            if hours:
                info += f"\n   🕒 {hours}"
            if menu:
                # 메뉴가 길면 앞부분만 표시
                menu_preview = menu[:100] + "..." if len(menu) > 100 else menu
                info += f"\n   🍽️ {menu_preview}"
            
            answer_parts.append(info)
        
        answer_parts.append("\n더 자세한 정보가 필요하시면 맛집 이름을 말씀해주세요!")
        
        return "".join(answer_parts)

# 전역 인스턴스
restaurant_search = None

def get_restaurant_search(gemini_api_key):
    """맛집 검색 시스템 인스턴스 반환"""
    global restaurant_search
    if restaurant_search is None:
        restaurant_search = HybridRestaurantSearch(gemini_api_key)
    return restaurant_search

def search_restaurants(query: str, gemini_api_key: str) -> str:
    """맛집 검색 함수 (RAG 시스템에서 사용)"""
    search_system = get_restaurant_search(gemini_api_key)
    
    # RAG 검색만 사용
    result = search_system.hybrid_search(query)
    return result['answer'] 