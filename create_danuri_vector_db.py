import os
import pickle
import glob
from datetime import datetime
from config import GEMINI_API_KEY
from rag_utils import GeminiEmbeddings, SimpleVectorDB, chunk_pdf_to_text_chunks

def create_danuri_vector_db():
    """다누리 폴더의 모든 PDF 파일들을 처리하여 벡터DB를 생성합니다."""
    print("=== 다누리 PDF 파일들을 처리하여 벡터DB 생성 ===")
    
    # 다누리 폴더 경로
    danuri_folder = "다누리"
    
    # PDF 파일들 찾기
    pdf_files = glob.glob(os.path.join(danuri_folder, "*.pdf"))
    pdf_files.sort()  # 파일명 순으로 정렬
    
    print(f"📁 발견된 PDF 파일 수: {len(pdf_files)}")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {os.path.basename(pdf_file)}")
    
    # Gemini 임베딩 모델 초기화
    print("\n🔧 Gemini 임베딩 모델 초기화 중...")
    embeddings_model = GeminiEmbeddings(GEMINI_API_KEY)
    
    # 문서와 임베딩을 저장할 리스트
    all_documents = []
    all_embeddings = []
    
    total_chunks = 0
    
    # 각 PDF 파일 처리
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n📄 처리 중 ({i}/{len(pdf_files)}): {os.path.basename(pdf_path)}")
        
        try:
            # PDF를 텍스트 청크로 분할
            chunks = chunk_pdf_to_text_chunks(pdf_path, chunk_size=1000, chunk_overlap=100)
            print(f"  - 생성된 청크 수: {len(chunks)}")
            
            # 각 청크에 대해 임베딩 생성
            for j, chunk in enumerate(chunks):
                print(f"    청크 {j+1}/{len(chunks)} 처리 중...")
                
                # 문서 객체 생성 (chunk는 이미 page_content와 metadata를 포함)
                document_obj = {
                    'page_content': chunk['page_content'],
                    'metadata': {
                        'source': os.path.basename(pdf_path),
                        'chunk_index': j,
                        'total_chunks': len(chunks),
                        'file_index': i,
                        'created_at': datetime.now().isoformat(),
                        'category': '다누리_한국생활안내',
                        'page': chunk['metadata'].get('page', 1)
                    }
                }
                
                # 임베딩 생성
                embedding = embeddings_model.embed_query(chunk['page_content'])
                
                # 리스트에 추가
                all_documents.append(document_obj)
                all_embeddings.append(embedding)
                total_chunks += 1
                
                # 진행상황 표시 (10개마다)
                if (j + 1) % 10 == 0:
                    print(f"      {j+1}/{len(chunks)} 완료")
            
            print(f"  ✅ {os.path.basename(pdf_path)} 처리 완료")
            
        except Exception as e:
            print(f"  ❌ {os.path.basename(pdf_path)} 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 벡터DB 생성
    print(f"\n🔧 벡터DB 생성 중...")
    print(f"📊 총 문서 수: {len(all_documents)}")
    print(f"📊 총 임베딩 수: {len(all_embeddings)}")
    
    vector_db = SimpleVectorDB(
        documents=all_documents,
        embeddings=embeddings_model,
        doc_embeddings=all_embeddings
    )
    
    # 벡터DB 저장
    output_path = "다문화_다누리.pkl"
    print(f"\n💾 벡터DB 저장 중: {output_path}")
    
    with open(output_path, 'wb') as f:
        pickle.dump(vector_db, f)
    
    print(f"✅ 벡터DB 저장 완료!")
    print(f"📁 파일 크기: {os.path.getsize(output_path)} bytes")
    
    # 기존 다문화.pkl 백업
    if os.path.exists("다문화.pkl"):
        backup_path = f"다문화_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        print(f"\n🔄 기존 다문화.pkl 백업 중: {backup_path}")
        os.rename("다문화.pkl", backup_path)
        print(f"✅ 백업 완료: {backup_path}")
    
    # 새 벡터DB를 다문화.pkl로 복사
    print(f"\n🔄 새 벡터DB를 다문화.pkl로 복사 중...")
    import shutil
    shutil.copy2(output_path, "다문화.pkl")
    print(f"✅ 다문화.pkl 업데이트 완료!")
    
    # 통계 정보 출력
    print(f"\n📈 최종 통계:")
    print(f"  - 처리된 PDF 파일 수: {len(pdf_files)}")
    print(f"  - 총 텍스트 청크 수: {total_chunks}")
    print(f"  - 벡터DB 파일: 다문화.pkl")
    print(f"  - 백업 파일: {backup_path if 'backup_path' in locals() else '없음'}")
    
    return vector_db

if __name__ == "__main__":
    create_danuri_vector_db() 