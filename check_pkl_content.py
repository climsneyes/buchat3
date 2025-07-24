import pickle
import os

def check_pkl_content(file_path):
    """pickle 파일의 내용을 확인하는 함수"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ 파일이 존재하지 않습니다: {file_path}")
            return
        
        print(f"📁 파일 크기: {os.path.getsize(file_path)} bytes")
        
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        print(f"✅ 파일 로드 성공!")
        print(f"📊 데이터 타입: {type(data)}")
        
        # 데이터 구조 확인
        if hasattr(data, '__dict__'):
            print(f"🔍 객체 속성들:")
            for attr_name, attr_value in data.__dict__.items():
                if isinstance(attr_value, (list, dict)):
                    print(f"  - {attr_name}: {type(attr_value)} (길이: {len(attr_value)})")
                else:
                    print(f"  - {attr_name}: {type(attr_value)} = {attr_value}")
        
        # 특정 속성들 확인
        if hasattr(data, 'documents'):
            print(f"\n📄 documents 정보:")
            print(f"  - 문서 수: {len(data.documents)}")
            if len(data.documents) > 0:
                print(f"  - 첫 번째 문서 타입: {type(data.documents[0])}")
                if isinstance(data.documents[0], dict):
                    print(f"  - 첫 번째 문서 키들: {list(data.documents[0].keys())}")
                    if 'page_content' in data.documents[0]:
                        content = data.documents[0]['page_content']
                        print(f"  - 첫 번째 문서 내용 (처음 200자): {content[:200]}...")
                    elif 'text' in data.documents[0]:
                        content = data.documents[0]['text']
                        print(f"  - 첫 번째 문서 내용 (처음 200자): {content[:200]}...")
                else:
                    print(f"  - 첫 번째 문서 내용: {str(data.documents[0])[:200]}...")
                
                # 처음 3개 문서 미리보기
                print(f"\n📖 처음 3개 문서 미리보기:")
                for i, doc in enumerate(data.documents[:3]):
                    print(f"\n--- 문서 {i+1} ---")
                    if isinstance(doc, dict):
                        if 'page_content' in doc:
                            content = doc['page_content']
                            print(f"내용 길이: {len(content)} 문자")
                            print(f"내용 (처음 300자): {content[:300]}...")
                        if 'metadata' in doc:
                            print(f"메타데이터: {doc['metadata']}")
                    else:
                        print(f"내용: {str(doc)[:300]}...")
        
        if hasattr(data, 'embeddings'):
            print(f"\n🧠 embeddings 정보:")
            print(f"  - 타입: {type(data.embeddings)}")
        
        if hasattr(data, 'doc_embeddings'):
            print(f"\n📊 doc_embeddings 정보:")
            print(f"  - 타입: {type(data.doc_embeddings)}")
            print(f"  - 길이: {len(data.doc_embeddings)}")
            if len(data.doc_embeddings) > 0:
                print(f"  - 첫 번째 임베딩 타입: {type(data.doc_embeddings[0])}")
                if hasattr(data.doc_embeddings[0], 'shape'):
                    print(f"  - 첫 번째 임베딩 크기: {data.doc_embeddings[0].shape}")
        
        # dict 타입인 경우
        if isinstance(data, dict):
            print(f"\n📋 딕셔너리 키들:")
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    print(f"  - {key}: {type(value)} (길이: {len(value)})")
                    if isinstance(value, list) and len(value) > 0:
                        print(f"    첫 번째 항목 타입: {type(value[0])}")
                        if isinstance(value[0], dict):
                            print(f"    첫 번째 항목 키들: {list(value[0].keys())}")
                        elif isinstance(value[0], str):
                            print(f"    첫 번째 항목 내용 (처음 200자): {value[0][:200]}...")
                else:
                    print(f"  - {key}: {type(value)} = {value}")
        
        # list 타입인 경우
        if isinstance(data, list):
            print(f"\n📋 리스트 정보:")
            print(f"  - 길이: {len(data)}")
            if len(data) > 0:
                print(f"  - 첫 번째 항목: {type(data[0])}")
                print(f"  - 첫 번째 항목 내용: {str(data[0])[:200]}...")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 다문화.pkl 파일 확인
    print("=== 다문화.pkl 파일 내용 확인 ===")
    check_pkl_content("다문화.pkl")
    
    print("\n" + "="*50 + "\n")
    
    # 다른 pkl 파일들도 확인
    other_files = ["외국인근로자.pkl", "부산의맛.pkl"]
    for file_name in other_files:
        if os.path.exists(file_name):
            print(f"=== {file_name} 파일 내용 확인 ===")
            check_pkl_content(file_name)
            print("\n" + "="*50 + "\n") 