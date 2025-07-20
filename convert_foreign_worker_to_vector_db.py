import os
import pickle
from rag_utils import GeminiEmbeddings, SimpleVectorDB, chunk_pdf_to_text_chunks

def create_foreign_worker_vector_db(pdf_dir, output_path, gemini_api_key):
    """지정한 폴더 내 모든 PDF를 임베딩하여 벡터DB로 저장합니다."""
    pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    all_chunks = []
    for pdf_path in pdf_files:
        print(f"PDF 처리: {pdf_path}")
        chunks = chunk_pdf_to_text_chunks(pdf_path)
        all_chunks.extend(chunks)
        print(f"  - {os.path.basename(pdf_path)}: {len(chunks)}개 청크")
    print(f"총 청크 수: {len(all_chunks)}")
    if not all_chunks:
        print("❌ 임베딩할 청크가 없습니다.")
        return None
    embeddings = GeminiEmbeddings(gemini_api_key)
    doc_embeddings = embeddings.embed_documents([doc['page_content'] for doc in all_chunks])
    vector_db = SimpleVectorDB(all_chunks, embeddings, doc_embeddings)
    with open(output_path, "wb") as f:
        pickle.dump(vector_db, f)
    print(f"✅ 벡터DB 저장 완료: {output_path}")
    return vector_db

if __name__ == "__main__":
    from config import GEMINI_API_KEY
    pdf_dir = "외국 근로자"
    output_path = "외국인근로자.pkl"
    create_foreign_worker_vector_db(pdf_dir, output_path, GEMINI_API_KEY) 