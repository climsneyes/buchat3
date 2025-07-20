import os
import pickle
import hashlib
import time
from typing import List, Dict, Any
import PyPDF2
import chromadb
from chromadb.config import Settings
from config import GEMINI_API_KEY
from rag_utils import GeminiEmbeddings

class ChromaDBWrapper:
    def __init__(self, db_name: str, persist_directory: str = "./chroma_db"):
        self.db_name = db_name
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        embedding_function = GeminiEmbeddings(GEMINI_API_KEY)
        self.collection = self.client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
    def add_documents(self, documents: List[Dict[str, Any]]):
        ids = []
        texts = []
        metadatas = []
        for i, doc in enumerate(documents):
            doc_id = f"doc_{i}_{hashlib.md5(doc['page_content'].encode()).hexdigest()[:8]}"
            ids.append(doc_id)
            texts.append(doc['page_content'])
            metadatas.append(doc['metadata'])
        print(f"📝 ChromaDB에 {len(documents)}개 문서를 추가하는 중...")
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            try:
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                print(f"   ✅ 배치 {i//batch_size + 1} 완료 ({len(batch_texts)}개 문서)")
            except Exception as e:
                print(f"   ❌ 배치 {i//batch_size + 1} 오류: {e}")
        print(f"✅ 총 {len(documents)}개 문서를 ChromaDB '{self.db_name}'에 추가했습니다.")
    def similarity_search(self, query: str, k: int = 3):
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )
        return results

def chunk_pdf_to_text_chunks(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """PDF를 텍스트 청크로 분할"""
    chunks = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if not text.strip():
                    continue
                
                # 페이지별로 청크 분할
                words = text.split()
                for i in range(0, len(words), chunk_size - chunk_overlap):
                    chunk_words = words[i:i + chunk_size]
                    chunk_text = ' '.join(chunk_words)
                    
                    if chunk_text.strip():
                        chunks.append({
                            'page_content': chunk_text,
                            'metadata': {
                                'source': pdf_path,
                                'page': page_num + 1,
                                'chunk_id': len(chunks)
                            }
                        })
    
    except Exception as e:
        print(f"❌ PDF 처리 오류 ({pdf_path}): {e}")
        return []
    
    return chunks

def create_foreign_worker_db():
    """외국인노동자권리구제안내수첩 PDF들을 임베딩해서 ChromaDB로 저장"""
    
    # PDF 파일 목록
    pdf_files = [
        "외국인노동자권리구제안내수첩_(국문용).pdf",
        "외국인노동자권리구제안내용수첩_우즈백.pdf",
        "외국인노동자권리구제안내용수첩_최종_네팔어.pdf",
        "외국인노동자권리구제안내용수첩_최종_동티모르.pdf",
        "외국인노동자권리구제안내용수첩_최종_라오스.pdf",
        "외국인노동자권리구제안내용수첩_최종_몽골어.pdf",
        "외국인노동자권리구제안내용수첩_최종_미얀마.pdf",
        "외국인노동자권리구제안내용수첩_최종_방글라데시.pdf",
        "외국인노동자권리구제안내용수첩_최종_베트남.pdf",
        "외국인노동자권리구제안내용수첩_최종_스리랑카.pdf",
        "외국인노동자권리구제안내용수첩_최종_인도네시아.pdf",
        "외국인노동자권리구제안내용수첩_최종_캄보디아.pdf",
        "외국인노동자권리구제안내용수첩_최종_키르기스.pdf",
        "외국인노동자권리구제안내용수첩_최종_태국어.pdf",
        "외국인노동자권리구제안내용수첩_최종_파키스탄.pdf",
        "외국인노동자권리구제안내용수첩_최종_필리핀.pdf"
    ]
    
    # ChromaDB 생성 (기존 DB와 겹치지 않는 이름)
    db_name = "foreign_worker_rights_guide_openai"
    chroma_db = ChromaDBWrapper(db_name)
    
    all_chunks = []
    
    print("🔍 PDF 파일들을 처리하고 있습니다...")
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"⚠️ 파일이 존재하지 않습니다: {pdf_file}")
            continue
        
        print(f"📄 처리 중: {pdf_file}")
        chunks = chunk_pdf_to_text_chunks(pdf_file)
        all_chunks.extend(chunks)
        print(f"   → {len(chunks)}개 청크 생성")
    
    if not all_chunks:
        print("❌ 처리할 청크가 없습니다.")
        return None
    
    print(f"\n📊 총 {len(all_chunks)}개 청크를 ChromaDB에 저장합니다...")
    
    # ChromaDB에 문서 추가
    chroma_db.add_documents(all_chunks)
    
    # DB 정보 저장
    db_info = {
        'db_name': db_name,
        'total_chunks': len(all_chunks),
        'pdf_files': pdf_files,
        'created_at': time.time()
    }
    
    with open(f"{db_name}_info.pkl", "wb") as f:
        pickle.dump(db_info, f)
    
    print(f"✅ 외국인노동자권리구제안내수첩 ChromaDB 생성 완료!")
    print(f"   - DB 이름: {db_name}")
    print(f"   - 총 청크 수: {len(all_chunks)}")
    print(f"   - 저장 위치: ./chroma_db/{db_name}")
    print(f"   - 정보 파일: {db_name}_info.pkl")
    
    return chroma_db

if __name__ == "__main__":
    create_foreign_worker_db() 