import pickle
import os
from rag_utils import SimpleVectorDB

def check_pkl_content(file_path):
    """PKL 파일의 내용을 확인합니다."""
    print(f"=== {file_path} 파일 분석 ===")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return
    
    print(f"파일 크기: {os.path.getsize(file_path)} bytes")
    
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        print(f"✅ 파일 로드 성공!")
        print(f"데이터 타입: {type(data)}")
        
        # SimpleVectorDB 객체인지 확인
        if hasattr(data, 'documents'):
            print(f"📚 문서 수: {len(data.documents)}")
            print(f"📊 임베딩 수: {len(data.doc_embeddings) if hasattr(data, 'doc_embeddings') else '알 수 없음'}")
            
            # 처음 3개 문서 미리보기
            print("\n=== 처음 3개 문서 미리보기 ===")
            for i, doc in enumerate(data.documents[:3]):
                print(f"\n--- 문서 {i+1} ---")
                print(f"내용 길이: {len(doc['page_content'])} 문자")
                print(f"메타데이터: {doc.get('metadata', '없음')}")
                print(f"내용 미리보기: {doc['page_content'][:200]}...")
        
        # ChromaDB 형식인지 확인
        elif hasattr(data, 'docstore') and hasattr(data.docstore, '_dict'):
            print(f"📚 ChromaDB 형식 - 문서 수: {len(data.docstore._dict)}")
            
            # 처음 3개 문서 미리보기
            print("\n=== 처음 3개 문서 미리보기 ===")
            for i, (doc_id, doc) in enumerate(list(data.docstore._dict.items())[:3]):
                print(f"\n--- 문서 {i+1} (ID: {doc_id}) ---")
                if hasattr(doc, 'page_content'):
                    print(f"내용 길이: {len(doc.page_content)} 문자")
                    print(f"메타데이터: {getattr(doc, 'metadata', '없음')}")
                    print(f"내용 미리보기: {doc.page_content[:200]}...")
        
        # 기타 형식
        else:
            print(f"📋 알 수 없는 형식의 데이터")
            print(f"속성들: {dir(data)}")
            
            # 데이터가 리스트인 경우
            if isinstance(data, list):
                print(f"리스트 길이: {len(data)}")
                if len(data) > 0:
                    print(f"첫 번째 항목 타입: {type(data[0])}")
                    print(f"첫 번째 항목 미리보기: {str(data[0])[:200]}...")
            
            # 데이터가 딕셔너리인 경우
            elif isinstance(data, dict):
                print(f"딕셔너리 키들: {list(data.keys())}")
                for key, value in list(data.items())[:3]:
                    print(f"키 '{key}': {type(value)} - {str(value)[:100]}...")
        
    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """모든 벡터DB 파일들을 확인합니다."""
    pkl_files = [
        "다문화.pkl",
        "vector_db_multi.pkl", 
        "외국인근로자.pkl",
        "vector_db_64multi.pkl"
    ]
    
    for file_path in pkl_files:
        if os.path.exists(file_path):
            check_pkl_content(file_path)
            print("\n" + "="*50 + "\n")
        else:
            print(f"⚠️ 파일이 없습니다: {file_path}")

if __name__ == "__main__":
    main() 