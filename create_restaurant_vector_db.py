import json
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import re
import gc
from datetime import datetime

def clean_text(text):
    """텍스트 정리"""
    if not text:
        return ""
    
    # 특수문자 제거 및 정리
    text = re.sub(r'[^\w\s가-힣]', ' ', str(text))
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, chunk_size=300, overlap=50):
    """텍스트를 청크로 분할"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 문장 경계에서 자르기
        if end < len(text):
            # 마침표, 느낌표, 물음표 뒤에서 자르기
            last_period = text.rfind('.', start, end)
            last_exclamation = text.rfind('!', start, end)
            last_question = text.rfind('?', start, end)
            
            # 가장 마지막 문장 부호 찾기
            last_sentence_end = max(last_period, last_exclamation, last_question)
            
            if last_sentence_end > start:
                end = last_sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 오버랩을 고려한 다음 시작점
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def normalize_restaurant_data(busan_food: Dict, taxi_ranking: Dict) -> List[Dict]:
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
                        
                        # 지역 정보를 강조하여 검색용 텍스트 조합
                        search_text_parts.insert(0, f"지역: {district}")
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
                
                # 지역 정보를 강조하여 검색용 텍스트 조합
                search_text_parts.insert(0, f"지역: {district}")
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

def create_restaurant_vector_db():
    """맛집 JSON 데이터로 벡터DB 생성"""
    print("=== 부산 맛집 JSON 벡터 데이터베이스 생성 ===")
    print("입력 파일: 부산의맛(2025).json, 택슐랭(2025).json")
    print("출력 파일: 부산의맛.pkl")
    print()
    
    # 1. JSON 데이터 로드
    print("1. JSON 데이터 로드 중...")
    try:
        with open('부산의맛(2025).json', 'r', encoding='utf-8') as f:
            busan_food = json.load(f)
        print(f"   부산의맛 데이터: {len(busan_food)}개 항목")
        
        with open('택슐랭(2025).json', 'r', encoding='utf-8') as f:
            taxi_ranking = json.load(f)
        print(f"   택슐랭 데이터: {len(taxi_ranking)}개 항목")
        
    except Exception as e:
        print(f"❌ JSON 파일 로드 오류: {e}")
        return
    
    # 2. 데이터 정규화
    print("\n2. 데이터 정규화 중...")
    normalized_data = normalize_restaurant_data(busan_food, taxi_ranking)
    print(f"   정규화된 데이터: {len(normalized_data)}개 맛집")
    
    # 3. 텍스트 청크 생성
    print("\n3. 텍스트 청크 생성 중...")
    chunks = []
    chunk_metadata = []
    
    for i, restaurant in enumerate(normalized_data):
        search_text = restaurant['search_text']
        if not search_text.strip():
            continue
        
        # 텍스트 정리
        cleaned_text = clean_text(search_text)
        if not cleaned_text:
            continue
        
        # 청크 분할
        text_chunks = chunk_text(cleaned_text, chunk_size=300, overlap=50)
        
        for j, chunk in enumerate(text_chunks):
            if len(chunk.strip()) > 50:  # 너무 짧은 청크 제외
                chunks.append(chunk)
                chunk_metadata.append({
                    'restaurant_index': i,
                    'chunk_index': j,
                    'restaurant_name': restaurant['name'],
                    'category': restaurant['category'],
                    'location': restaurant['location'],
                    'source': restaurant['source']
                })
    
    print(f"   생성된 청크: {len(chunks)}개")
    
    if not chunks:
        print("❌ 생성된 청크가 없습니다.")
        return
    
    # 4. 임베딩 모델 로드
    print("\n4. 임베딩 모델 로드 중...")
    try:
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("   모델 로드 완료")
    except Exception as e:
        print(f"❌ 모델 로드 오류: {e}")
        return
    
    # 5. 임베딩 생성 (배치 처리)
    print("\n5. 임베딩 생성 중...")
    batch_size = 32
    embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        print(f"   배치 {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size} 처리 중...")
        
        try:
            batch_embeddings = model.encode(batch_chunks, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
            
            # 메모리 정리
            gc.collect()
            
        except Exception as e:
            print(f"❌ 배치 {i//batch_size + 1} 임베딩 오류: {e}")
            continue
    
    if not embeddings:
        print("❌ 생성된 임베딩이 없습니다.")
        return
    
    # 6. 벡터DB 저장
    print("\n6. 벡터DB 저장 중...")
    vector_db = {
        'chunks': chunks,
        'embeddings': np.array(embeddings),
        'metadata': chunk_metadata,
        'restaurant_data': normalized_data,
        'created_at': datetime.now().isoformat(),
        'total_restaurants': len(normalized_data),
        'total_chunks': len(chunks)
    }
    
    try:
        with open('부산의맛.pkl', 'wb') as f:
            pickle.dump(vector_db, f)
        
        print(f"✅ 벡터DB 저장 완료!")
        print(f"   파일: 부산의맛.pkl")
        print(f"   맛집 수: {len(normalized_data)}개")
        print(f"   청크 수: {len(chunks)}개")
        print(f"   임베딩 차원: {embeddings[0].shape[0]}")
        
    except Exception as e:
        print(f"❌ 벡터DB 저장 오류: {e}")
        return
    
    print("\n=== 벡터DB 생성 완료 ===")

if __name__ == "__main__":
    create_restaurant_vector_db() 