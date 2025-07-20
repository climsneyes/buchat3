import json
import pickle
from rag_utils import SimpleVectorDB, GeminiEmbeddings
import os
from config import GEMINI_API_KEY

def load_waste_data():
    """부산광역시 쓰레기 처리 정보 JSON 파일을 로드합니다."""
    with open('부산광역시_쓰레기처리정보.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def format_waste_info_for_vector_db(waste_data):
    """쓰레기 처리 정보를 벡터 데이터베이스에 적합한 형태로 포맷팅합니다."""
    formatted_docs = []
    
    # 전체 개요 정보
    overview_text = f"""
부산광역시 쓰레기 처리 정보
총 {len(waste_data)}개 구군의 쓰레기 처리 정보를 제공합니다.

공통 정보:
- 대형폐기물: 원형이 훼손된 가구류, 사무용기자재 등 종량제 봉투에 넣을 수 없는 폐기물
- 소형폐가전: 1m 미만의 가전제품으로 매주 수요일 무상수거
- 재활용품: 종이류, 플라스틱류, 캔류, 유리병류, 의류, 스티로폼, 비닐류 등
- 음식물쓰레기: 물기 제거 후 전용용기에 배출
- 특수폐기물: 폐형광등, 폐건전지, 폐의약품 등
- 과태료: 무단투기 시 100만원 이하
"""
    formatted_docs.append({
        'content': overview_text,
        'metadata': {
            'title': '부산광역시 쓰레기 처리 정보 개요',
            'category': '쓰레기처리',
            'type': 'overview'
        }
    })
    
    # 구군별 상세 정보
    for gu_name, gu_info in waste_data.items():
        # 기본 정보
        basic_info = f"""
{gu_name} 쓰레기 처리 정보

담당부서: {gu_info.get('담당부서', '정보 없음')}
연락처: {gu_info.get('연락처', '정보 없음')}
"""
        
        # 배출요일 정보가 있는 경우
        if '배출요일' in gu_info:
            basic_info += "\n배출요일:\n"
            for day, items in gu_info['배출요일'].items():
                if isinstance(items, list):
                    basic_info += f"- {day}: {', '.join(items)}\n"
                else:
                    basic_info += f"- {day}: {items}\n"
        
        formatted_docs.append({
            'content': basic_info,
            'metadata': {
                'title': f'{gu_name} 쓰레기 처리 기본 정보',
                'category': '쓰레기처리',
                'type': 'basic_info',
                'gu_name': gu_name
            }
        })
        
        # 종량제 봉투 가격 정보
        if '종량제봉투_가격' in gu_info:
            price_info = f"{gu_name} 종량제 봉투 가격:\n"
            for size, price in gu_info['종량제봉투_가격'].items():
                if isinstance(price, (int, float)):
                    price_info += f"- {size}: {price:,}원\n"
                else:
                    price_info += f"- {size}: {price}원\n"
            
            formatted_docs.append({
                'content': price_info,
                'metadata': {
                    'title': f'{gu_name} 종량제 봉투 가격',
                    'category': '쓰레기처리',
                    'type': 'price_info',
                    'gu_name': gu_name
                }
            })
        
        # 음식물쓰레기 전용용기 가격 정보
        if '음식물쓰레기_전용용기_가격' in gu_info:
            food_waste_info = f"{gu_name} 음식물쓰레기 전용용기 가격:\n"
            for size, price in gu_info['음식물쓰레기_전용용기_가격'].items():
                if isinstance(price, (int, float)):
                    food_waste_info += f"- {size}: {price:,}원\n"
                else:
                    food_waste_info += f"- {size}: {price}원\n"
            
            formatted_docs.append({
                'content': food_waste_info,
                'metadata': {
                    'title': f'{gu_name} 음식물쓰레기 전용용기 가격',
                    'category': '쓰레기처리',
                    'type': 'food_waste_price',
                    'gu_name': gu_name
                }
            })
        
        # 수거업체 정보
        if '수거업체' in gu_info:
            company_info = f"{gu_name} 수거업체 정보:\n"
            for company in gu_info['수거업체']:
                company_info += f"- {company['업체명']}: {company['연락처']} (담당구역: {company['담당구역']})\n"
            
            formatted_docs.append({
                'content': company_info,
                'metadata': {
                    'title': f'{gu_name} 수거업체 정보',
                    'category': '쓰레기처리',
                    'type': 'company_info',
                    'gu_name': gu_name
                }
            })
        
        # 특이사항
        if '특이사항' in gu_info:
            special_info = f"{gu_name} 특이사항:\n"
            for item in gu_info['특이사항']:
                special_info += f"- {item}\n"
            
            formatted_docs.append({
                'content': special_info,
                'metadata': {
                    'title': f'{gu_name} 특이사항',
                    'category': '쓰레기처리',
                    'type': 'special_info',
                    'gu_name': gu_name
                }
            })
        
        # 대형폐기물 정보 (새로운 구조)
        if '대형폐기물_수거업체' in gu_info:
            large_waste_info = f"{gu_name} 대형폐기물 처리:\n"
            
            # 수거업체 정보
            large_waste_info += "수거업체:\n"
            for company in gu_info['대형폐기물_수거업체']:
                large_waste_info += f"- {company['업체명']}: {company['연락처']}\n"
                if '신고방법' in company:
                    large_waste_info += f"  신고방법: {company['신고방법']}\n"
                large_waste_info += f"  담당구역: {company['담당구역']}\n"
            
            # 신고방법
            if '대형폐기물_신고방법' in gu_info:
                large_waste_info += "\n신고방법:\n"
                for method in gu_info['대형폐기물_신고방법']:
                    large_waste_info += f"- {method}\n"
            
            # 수수료 예시
            if '대형폐기물_수수료_예시' in gu_info:
                large_waste_info += "\n수수료 예시:\n"
                for item in gu_info['대형폐기물_수수료_예시']:
                    large_waste_info += f"- {item}\n"
            
            # 특이사항
            if '대형폐기물_특이사항' in gu_info:
                large_waste_info += "\n특이사항:\n"
                for item in gu_info['대형폐기물_특이사항']:
                    large_waste_info += f"- {item}\n"
            
            formatted_docs.append({
                'content': large_waste_info,
                'metadata': {
                    'title': f'{gu_name} 대형폐기물 처리',
                    'category': '쓰레기처리',
                    'type': 'large_waste_info',
                    'gu_name': gu_name
                }
            })
        
        # 정화조 청소 정보 (새로 추가)
        if '정화조_청소업체' in gu_info:
            septic_info = f"{gu_name} 정화조 청소 정보:\n"
            
            # 청소업체 정보
            septic_info += "청소업체:\n"
            for company in gu_info['정화조_청소업체']:
                septic_info += f"- {company['업체명']}: {company['연락처']}\n"
                if '담당구역' in company:
                    septic_info += f"  담당구역: {company['담당구역']}\n"
            
            # 청소수수료
            if '정화조_청소수수료' in gu_info:
                septic_info += "\n청소수수료:\n"
                for item in gu_info['정화조_청소수수료']:
                    septic_info += f"- {item}\n"
            
            formatted_docs.append({
                'content': septic_info,
                'metadata': {
                    'title': f'{gu_name} 정화조 청소 정보',
                    'category': '쓰레기처리',
                    'type': 'septic_info',
                    'gu_name': gu_name
                }
            })
    
    # 공통 정보 상세 (기존 구조가 있는 경우)
    if '부산광역시_쓰레기처리정보' in waste_data and '공통_정보' in waste_data['부산광역시_쓰레기처리정보']:
        common_info = waste_data['부산광역시_쓰레기처리정보']['공통_정보']
        
        # 대형폐기물 처리 상세
        if '대형폐기물_처리' in common_info:
            large_waste_detail = f"""
대형폐기물 처리 방법:

정의: {common_info['대형폐기물_처리']['정의']}

신고방법:
"""
            for method in common_info['대형폐기물_처리']['신고방법']:
                large_waste_detail += f"- {method}\n"
            
            large_waste_detail += "\n무상수거 대상:\n"
            for item in common_info['대형폐기물_처리']['무상수거_대상']:
                large_waste_detail += f"- {item}\n"
            
            large_waste_detail += "\n유상수거 대상:\n"
            for item in common_info['대형폐기물_처리']['유상수거_대상']:
                large_waste_detail += f"- {item}\n"
            
            formatted_docs.append({
                'content': large_waste_detail,
                'metadata': {
                    'title': '대형폐기물 처리 방법',
                    'category': '쓰레기처리',
                    'type': 'large_waste_detail'
                }
            })
        
        # 소형폐가전 처리 상세
        if '소형폐가전_처리' in common_info:
            small_appliance_detail = f"""
소형폐가전 처리 방법:

정의: {common_info['소형폐가전_처리']['정의']}
배출방법: {common_info['소형폐가전_처리']['배출방법']}

대상품목:
"""
            for item in common_info['소형폐가전_처리']['대상품목']:
                small_appliance_detail += f"- {item}\n"
            
            formatted_docs.append({
                'content': small_appliance_detail,
                'metadata': {
                    'title': '소형폐가전 처리 방법',
                    'category': '쓰레기처리',
                    'type': 'small_appliance_detail'
                }
            })
        
        # 재활용품 배출요령
        if '재활용품_배출요령' in common_info:
            recycling_info = "재활용품 배출요령:\n"
            for category, method in common_info['재활용품_배출요령'].items():
                recycling_info += f"- {category}: {method}\n"
            
            formatted_docs.append({
                'content': recycling_info,
                'metadata': {
                    'title': '재활용품 배출요령',
                    'category': '쓰레기처리',
                    'type': 'recycling_info'
                }
            })
        
        # 음식물쓰레기 배출요령
        if '음식물쓰레기_배출요령' in common_info:
            food_waste_detail = f"""
음식물쓰레기 배출요령:

배출방법: {common_info['음식물쓰레기_배출요령']['배출방법']}

제거해야 할 물질:
"""
            for item in common_info['음식물쓰레기_배출요령']['제거해야_할_물질']:
                food_waste_detail += f"- {item}\n"
            
            food_waste_detail += "\n주의사항:\n"
            for item in common_info['음식물쓰레기_배출요령']['주의사항']:
                food_waste_detail += f"- {item}\n"
            
            formatted_docs.append({
                'content': food_waste_detail,
                'metadata': {
                    'title': '음식물쓰레기 배출요령',
                    'category': '쓰레기처리',
                    'type': 'food_waste_detail'
                }
            })
        
        # 특수폐기물 처리
        if '특수폐기물_처리' in common_info:
            special_waste_info = "특수폐기물 처리 방법:\n"
            for category, method in common_info['특수폐기물_처리'].items():
                special_waste_info += f"- {category}: {method}\n"
            
            formatted_docs.append({
                'content': special_waste_info,
                'metadata': {
                    'title': '특수폐기물 처리 방법',
                    'category': '쓰레기처리',
                    'type': 'special_waste_info'
                }
            })
    
    return formatted_docs

def add_waste_info_to_multicultural_db():
    """쓰레기 처리 정보를 다문화.pkl 벡터 데이터베이스에 추가합니다."""
    print("부산광역시 쓰레기 처리 정보를 다문화.pkl에 추가하는 중...")
    
    # Gemini 임베딩 모델 초기화
    embeddings_model = GeminiEmbeddings(GEMINI_API_KEY)
    
    # 기존 다문화.pkl 로드
    if os.path.exists('다문화.pkl'):
        print("기존 다문화.pkl 파일을 로드하는 중...")
        with open('다문화.pkl', 'rb') as f:
            vector_db = pickle.load(f)
        print(f"기존 문서 수: {len(vector_db.documents)}")
    else:
        print("다문화.pkl 파일이 없습니다. 새로운 벡터 데이터베이스를 생성합니다.")
        vector_db = SimpleVectorDB()
    
    # 쓰레기 처리 정보 로드 및 포맷팅
    waste_data = load_waste_data()
    formatted_docs = format_waste_info_for_vector_db(waste_data)
    
    print(f"추가할 문서 수: {len(formatted_docs)}")
    
    # 문서들을 벡터 데이터베이스에 추가
    new_documents = []
    new_embeddings = []
    
    for i, doc in enumerate(formatted_docs):
        print(f"문서 {i+1}/{len(formatted_docs)} 추가 중: {doc['metadata']['title']}")
        
        # 임베딩 생성
        embedding = embeddings_model.embed_query(doc['content'])
        
        # 문서 객체 생성
        document_obj = {
            'page_content': doc['content'],
            'metadata': doc['metadata']
        }
        
        new_documents.append(document_obj)
        new_embeddings.append(embedding)
    
    # 기존 문서와 새 문서 합치기
    if vector_db.documents is None:
        vector_db.documents = []
    if vector_db.doc_embeddings is None:
        vector_db.doc_embeddings = []
    
    vector_db.documents.extend(new_documents)
    vector_db.doc_embeddings.extend(new_embeddings)
    vector_db.embeddings = embeddings_model
    
    # 백업 파일 생성
    backup_filename = '다문화_backup_with_waste.pkl'
    print(f"백업 파일 생성 중: {backup_filename}")
    with open(backup_filename, 'wb') as f:
        pickle.dump(vector_db, f)
    
    # 업데이트된 파일 저장
    print("업데이트된 다문화.pkl 파일 저장 중...")
    with open('다문화.pkl', 'wb') as f:
        pickle.dump(vector_db, f)
    
    print(f"완료! 총 문서 수: {len(vector_db.documents)}")
    print(f"백업 파일: {backup_filename}")
    print("이제 다문화가족 한국생활안내에서 부산광역시 쓰레기 처리 정보를 조회할 수 있습니다.")

if __name__ == "__main__":
    add_waste_info_to_multicultural_db() 