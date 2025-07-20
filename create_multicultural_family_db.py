import chromadb
import os
from rag_utils import GeminiEmbeddings
from typing import List, Dict
import json
from config import GEMINI_API_KEY

def create_multicultural_family_database():
    """다문화 가족 한국생활 안내 자료를 위한 ChromaDB 생성"""
    
    # ChromaDB 클라이언트 설정
    persist_directory = "./chroma_db"
    db_name = "multicultural_family_guide_openai"
    
    # ChromaDB 클라이언트 생성
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    
    # OpenAI 임베딩 함수 생성
    embedding_function = GeminiEmbeddings(GEMINI_API_KEY)
    
    # 컬렉션 생성 또는 가져오기
    collection = chroma_client.get_or_create_collection(
        name=db_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 다문화 가족 한국생활 안내 자료 (예시 데이터)
    # 실제로는 PDF 파일들을 로드하여 사용해야 합니다
    multicultural_guide_data = [
        {
            "content": "다문화 가족을 위한 한국생활 안내서입니다. 한국에서의 기본적인 생활 방법과 문화를 안내합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "기본안내"}
        },
        {
            "content": "한국의 교육 제도와 학교 생활에 대한 안내입니다. 자녀 교육과 관련된 정보를 제공합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "교육"}
        },
        {
            "content": "한국의 의료 제도와 건강보험에 대한 안내입니다. 병원 이용 방법과 보험 혜택을 설명합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "의료"}
        },
        {
            "content": "한국의 교통수단 이용 방법과 대중교통 안내입니다. 버스, 지하철, 택시 이용법을 설명합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "교통"}
        },
        {
            "content": "한국의 음식 문화와 식사 예절에 대한 안내입니다. 한국 음식과 식사 방법을 소개합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "문화"}
        },
        {
            "content": "한국의 법률 제도와 권리 보호에 대한 안내입니다. 다문화 가족의 법적 권리와 의무를 설명합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "법률"}
        },
        {
            "content": "한국의 주거 문화와 집 구하기 안내입니다. 월세, 전세, 매매 등 주택 관련 정보를 제공합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "주거"}
        },
        {
            "content": "한국의 취업과 직장 생활 안내입니다. 일자리 찾기와 직장에서의 예절을 설명합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "취업"}
        },
        {
            "content": "한국의 계절과 날씨에 대한 안내입니다. 사계절의 특징과 준비해야 할 사항을 설명합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "생활"}
        },
        {
            "content": "한국의 전통 문화와 명절에 대한 안내입니다. 설날, 추석 등 주요 명절의 의미와 풍습을 소개합니다.",
            "metadata": {"source": "다문화가족지원포털", "category": "문화"}
        }
    ]
    
    # 문서와 메타데이터 분리
    documents = [item["content"] for item in multicultural_guide_data]
    metadatas = [item["metadata"] for item in multicultural_guide_data]
    ids = [f"multicultural_{i}" for i in range(len(documents))]
    
    # 컬렉션에 문서 추가
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"다문화 가족 안내 자료 {len(documents)}개가 ChromaDB에 추가되었습니다.")
    print(f"데이터베이스 이름: {db_name}")
    print(f"저장 위치: {persist_directory}")
    
    # 컬렉션 정보 확인
    print(f"\n컬렉션 정보:")
    print(f"총 문서 수: {collection.count()}")
    
    return collection

if __name__ == "__main__":
    try:
        collection = create_multicultural_family_database()
        print("\n다문화 가족 ChromaDB 생성이 완료되었습니다!")
    except Exception as e:
        print(f"오류 발생: {e}")
        print("Gemini API 키가 올바르게 설정되었는지 확인해주세요.") 