import os
import pickle
import PyPDF2
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Generator
import time
import gc

def extract_text_from_pdf_chunked(pdf_path: str, chunk_size: int = 10000) -> Generator[str, None, None]:
    """PDF 파일에서 텍스트를 청크 단위로 추출 (메모리 효율적)"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_buffer = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                print(f"페이지 {page_num + 1}/{len(pdf_reader.pages)} 처리 중...")
                
                page_text = page.extract_text() + "\n"
                text_buffer += page_text
                
                # 버퍼가 일정 크기를 넘으면 yield
                if len(text_buffer) >= chunk_size:
                    yield text_buffer
                    text_buffer = ""
                    gc.collect()  # 가비지 컬렉션
            
            # 남은 텍스트 반환
            if text_buffer:
                yield text_buffer
                
    except Exception as e:
        print(f"PDF 텍스트 추출 오류: {e}")
        yield ""

def clean_text_chunked(text_chunk: str) -> str:
    """텍스트 청크 정리 (메모리 효율적)"""
    # 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text_chunk)
    # 특수 문자 정리 (한글, 영문, 숫자, 기본 문장부호만 유지)
    text = re.sub(r'[^\w\s가-힣.,!?;:()[\]{}"\'-]', '', text)
    return text.strip()

def split_text_into_chunks_efficient(text: str, chunk_size: int = 300, overlap: int = 30) -> List[str]:
    """텍스트를 효율적으로 청크로 분할 (메모리 절약)"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 문장 경계에서 자르기
        if end < len(text):
            # 마침표, 느낌표, 물음표, 줄바꿈 뒤에서 자르기
            for punct in ['.', '!', '?', '\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start:
                    end = last_punct + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk and len(chunk) > 50:  # 너무 짧은 청크 제외
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def create_vector_database_efficient(chunks: List[str], model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2') -> Dict[str, Any]:
    """메모리 효율적인 벡터 데이터베이스 생성"""
    print(f"모델 '{model_name}' 로딩 중...")
    model = SentenceTransformer(model_name)
    
    print("텍스트 임베딩 생성 중...")
    
    # 배치 단위로 임베딩 생성 (메모리 절약)
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        print(f"배치 처리 중: {i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}")
        
        batch_embeddings = model.encode(batch_chunks, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)
        
        # 메모리 정리
        gc.collect()
    
    # 모든 임베딩을 하나로 합치기
    embeddings = np.vstack(all_embeddings)
    
    # 벡터 데이터베이스 구성
    vector_db = {
        'chunks': chunks,
        'embeddings': embeddings,
        'model_name': model_name,
        'created_at': time.time(),
        'total_chunks': len(chunks)
    }
    
    return vector_db

def save_vector_database(vector_db: Dict[str, Any], output_path: str):
    """벡터 데이터베이스를 파일로 저장"""
    try:
        with open(output_path, 'wb') as f:
            pickle.dump(vector_db, f)
        print(f"벡터 데이터베이스가 '{output_path}'에 저장되었습니다.")
        print(f"총 청크 수: {vector_db['total_chunks']}")
        print(f"파일 크기: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"벡터 데이터베이스 저장 오류: {e}")

def main():
    # 파일 경로 설정
    pdf_path = "2025부산의맛(국영)_최종_저용량.pdf"
    output_path = "부산의맛.pkl"
    
    # PDF 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    print("=== 부산의맛 PDF 벡터 데이터베이스 생성 (메모리 효율적) ===")
    print(f"입력 파일: {pdf_path}")
    print(f"출력 파일: {output_path}")
    print()
    
    # 1. PDF에서 텍스트를 청크 단위로 추출
    print("1. PDF 텍스트 추출 중...")
    all_text = ""
    total_chars = 0
    
    for text_chunk in extract_text_from_pdf_chunked(pdf_path, chunk_size=5000):
        cleaned_chunk = clean_text_chunked(text_chunk)
        all_text += cleaned_chunk + " "
        total_chars += len(cleaned_chunk)
        
        # 메모리 정리
        gc.collect()
    
    print(f"추출된 텍스트 길이: {total_chars} 문자")
    
    # 2. 텍스트를 청크로 분할 (더 작은 크기로)
    print("2. 텍스트 청크 분할 중...")
    chunks = split_text_into_chunks_efficient(all_text, chunk_size=300, overlap=30)
    print(f"생성된 청크 수: {len(chunks)}")
    
    # 메모리에서 원본 텍스트 제거
    del all_text
    gc.collect()
    
    # 3. 벡터 데이터베이스 생성 (무료 모델 사용)
    print("3. 벡터 데이터베이스 생성 중...")
    vector_db = create_vector_database_efficient(chunks)
    
    # 4. 파일로 저장
    print("4. 파일 저장 중...")
    save_vector_database(vector_db, output_path)
    
    print("\n=== 완료 ===")
    print(f"부산의맛 벡터 데이터베이스가 성공적으로 생성되었습니다: {output_path}")
    print("사용된 모델: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (무료)")

if __name__ == "__main__":
    main() 