import os
import pickle
import shutil
from datetime import datetime

# 환경변수에서 firebase_key.json 내용을 읽어서 파일로 저장
firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
if firebase_key_json:
    with open("firebase_key.json", "w", encoding="utf-8") as f:
        f.write(firebase_key_json)

# config.py가 없으면 환경변수로 자동 생성
if not os.path.exists("config.py"):
    with open("config.py", "w", encoding="utf-8") as f:
        f.write(f'''
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash-lite")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "https://pychat-25c45-default-rtdb.asia-southeast1.firebasedatabase.app/")
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")
''')

import flet as ft
from flet_webview import WebView
from pages.nationality_select import NationalitySelectPage
from pages.home import HomePage
from pages.create_room import CreateRoomPage
from pages.room_list import RoomListPage
from pages.chat_room import ChatRoomPage
from pages.foreign_country_select import ForeignCountrySelectPage
import openai
from config import GEMINI_API_KEY, MODEL_NAME, FIREBASE_DB_URL, FIREBASE_KEY_PATH
import uuid
import qrcode
import io
import base64
import geocoder
import time
import firebase_admin
from firebase_admin import credentials, db
from rag_utils import get_or_create_vector_db, answer_with_rag, answer_with_rag_foreign_worker
from rag_utils import SimpleVectorDB, GeminiEmbeddings
from restaurant_search_system import search_restaurants


IS_SERVER = os.environ.get("CLOUDTYPE") == "1"  # Cloudtype 환경변수 등으로 구분

# Cloudtype 배포 주소를 동적으로 설정
def get_base_url():
    """실제 배포된 URL을 동적으로 가져오는 함수"""
    # 환경변수에서 URL 가져오기
    env_url = os.getenv("BASE_URL")
    if env_url:
        return env_url
    
    # Cloudtype 환경변수 확인
    cloudtype_url = os.getenv("CLOUDTYPE_URL")
    if cloudtype_url:
        return cloudtype_url
    
    # 기본값 (개발 환경)
    return "https://port-0-buchat-m0t1itev3f2879ad.sel4.cloudtype.app"

BASE_URL = get_base_url()
print(f"사용 중인 BASE_URL: {BASE_URL}")

# RAG 채팅방 상수
RAG_ROOM_ID = "rag_korean_guide"
RAG_ROOM_TITLE = "다문화가족 한국생활안내"

# --- Firebase 초기화 ---
FIREBASE_AVAILABLE = False
try:
    print(f"Firebase 초기화 시도...")
    print(f"FIREBASE_DB_URL: {FIREBASE_DB_URL}")
    print(f"FIREBASE_KEY_PATH: {FIREBASE_KEY_PATH}")
    
    if not FIREBASE_DB_URL or FIREBASE_DB_URL == "None":
        print("❌ FIREBASE_DB_URL이 설정되지 않았습니다.")
        raise Exception("FIREBASE_DB_URL is not set")
    
    if not os.path.exists(FIREBASE_KEY_PATH):
        print(f"❌ Firebase 키 파일이 존재하지 않습니다: {FIREBASE_KEY_PATH}")
        raise Exception(f"Firebase key file not found: {FIREBASE_KEY_PATH}")
    
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })
    FIREBASE_AVAILABLE = True
    print("✅ Firebase 초기화 성공")
except Exception as e:
    print(f"❌ Firebase 초기화 실패: {e}")
    print("⚠️ Firebase 기능이 비활성화됩니다. 채팅방 생성 및 메시지 저장이 불가능합니다.")
    FIREBASE_AVAILABLE = False

# OpenAI 관련 client = openai.OpenAI(api_key=OPENAI_API_KEY) 제거

# RAG용 벡터DB 준비 (무조건 병합본만 사용)
print("RAG 벡터DB 준비 중...")
VECTOR_DB_MERGED_PATH = "다문화.pkl"
VECTOR_DB_FOREIGN_WORKER_PATH = "외국인근로자.pkl"
VECTOR_DB_RESTAURANT_PATH = "부산의맛.pkl"
vector_db_multicultural = None
vector_db_foreign_worker = None

# 다문화가족 한국생활안내 벡터DB 로드
try:
    if os.path.exists(VECTOR_DB_MERGED_PATH):
        print("다문화가족 벡터DB 파일을 로드합니다...")
        print(f"벡터DB 파일 크기: {os.path.getsize(VECTOR_DB_MERGED_PATH)} bytes")
        with open(VECTOR_DB_MERGED_PATH, "rb") as f:
            vector_db_multicultural = pickle.load(f)
        print(f"벡터DB 로드 완료. 문서 수: {len(vector_db_multicultural.documents) if hasattr(vector_db_multicultural, 'documents') else '알 수 없음'}")
        vector_db_multicultural.embeddings = GeminiEmbeddings(
            gemini_api_key=GEMINI_API_KEY
        )
        print("다문화가족 벡터DB 로드 완료!")
    else:
        print("다문화가족 벡터DB 파일이 없습니다.")
except Exception as e:
    print(f"다문화가족 벡터DB 로드 중 오류 발생: {e}")
    vector_db_multicultural = None

# 외국인 권리구제 벡터DB 로드
try:
    if os.path.exists(VECTOR_DB_FOREIGN_WORKER_PATH):
        print("외국인 권리구제 벡터DB 파일을 로드합니다...")
        print(f"벡터DB 파일 크기: {os.path.getsize(VECTOR_DB_FOREIGN_WORKER_PATH)} bytes")
        with open(VECTOR_DB_FOREIGN_WORKER_PATH, "rb") as f:
            vector_db_foreign_worker = pickle.load(f)
        print(f"벡터DB 로드 완료. 문서 수: {len(vector_db_foreign_worker.documents) if hasattr(vector_db_foreign_worker, 'documents') else '알 수 없음'}")
        vector_db_foreign_worker.embeddings = GeminiEmbeddings(
            gemini_api_key=GEMINI_API_KEY
        )
        print("외국인 권리구제 벡터DB 로드 완료!")
    else:
        print("외국인 권리구제 벡터DB 파일이 없습니다.")
except Exception as e:
    print(f"외국인 권리구제 벡터DB 로드 중 오류 발생: {e}")
    vector_db_foreign_worker = None

# 부산맛집 벡터DB 로드
try:
    if os.path.exists(VECTOR_DB_RESTAURANT_PATH):
        print("부산맛집 벡터DB 파일을 로드합니다...")
        print(f"벡터DB 파일 크기: {os.path.getsize(VECTOR_DB_RESTAURANT_PATH)} bytes")
        with open(VECTOR_DB_RESTAURANT_PATH, "rb") as f:
            restaurant_vector_db = pickle.load(f)
        print(f"부산맛집 벡터DB 로드 완료. 문서 수: {len(restaurant_vector_db['chunks']) if isinstance(restaurant_vector_db, dict) and 'chunks' in restaurant_vector_db else '알 수 없음'}")
        print("부산맛집 벡터DB 로드 완료!")
    else:
        print("부산맛집 벡터DB 파일이 없습니다.")
except Exception as e:
    print(f"부산맛집 벡터DB 로드 중 오류 발생: {e}")
    restaurant_vector_db = None

# RAG 기능 사용 가능 여부 설정 (vector_db 정의 후)
RAG_AVAILABLE = vector_db_multicultural is not None and vector_db_foreign_worker is not None

print("RAG 벡터DB 준비 완료!")

FIND_ROOM_TEXTS = {
    "ko": {
        "title": "채팅방 찾기 방법을 선택하세요",
        "qr": "QR코드로 찾기",
        "qr_desc": "QR코드를 스캔하여 채팅방 참여",
        "id": "ID로 찾기",
        "id_desc": "채팅방 ID를 입력하여 참여",
        "rag": "다문화가족 한국생활안내",
        "rag_desc": "다누리 포털 기반 한국생활 안내 챗봇",
        "restaurant": "부산 맛집검색",
        "restaurant_desc": "부산의맛 & 택슐랭 기반 맛집 검색 챗봇"
    },
    "en": {
        "title": "Select a way to find a chat room",
        "qr": "Find by QR Code",
        "qr_desc": "Scan QR code to join chat room",
        "id": "Find by ID",
        "id_desc": "Join by entering chat room ID",
        "rag": "Korean Life Guide for Multicultural Families",
        "rag_desc": "Chatbot based on Danuri - Korean Life Guide for Multicultural Families Portal materials",
        "restaurant": "Busan Restaurant Search",
        "restaurant_desc": "Restaurant search chatbot based on Busan Food Guide & Taxi Ranking"
    },
    "vi": {
        "title": "Chọn cách tìm phòng chat",
        "qr": "Tìm bằng mã QR",
        "qr_desc": "Quét mã QR để tham gia phòng chat",
        "id": "Tìm bằng ID",
        "id_desc": "Tham gia bằng cách nhập ID phòng chat",
        "rag": "Hướng dẫn cuộc sống Hàn Quốc cho gia đình đa văn hóa",
        "rag_desc": "Chatbot dựa trên tài liệu Hướng dẫn cuộc sống Hàn Quốc của cổng thông tin Danuri cho gia đình đa văn hóa",
        "restaurant": "Tìm kiếm nhà hàng Busan",
        "restaurant_desc": "Chatbot tìm kiếm nhà hàng dựa trên Hướng dẫn ẩm thực Busan & Xếp hạng Taxi"
    },
    "ja": {
        "title": "チャットルームの探し方を選択してください",
        "qr": "QRコードで探す",
        "qr_desc": "QRコードをスキャンしてチャットルームに参加",
        "id": "IDで探す",
        "id_desc": "IDでチャットルームに参加",
        "rag": "多文化家族のための韓国生活ガイド",
        "rag_desc": "多文化家族支援ポータル「ダヌリ」- 韓国生活案内資料に基づくチャットボット",
        "restaurant": "釜山レストラン検索",
        "restaurant_desc": "釜山グルメガイド＆タクシーランキングに基づくレストラン検索チャットボット"
    },
    "zh": {
        "title": "请选择查找聊天室的方法",
        "qr": "通过二维码查找",
        "qr_desc": "扫描二维码加入聊天室",
        "id": "通过ID查找",
        "id_desc": "通过输入聊天室ID加入",
        "rag": "多文化家庭韩国生活指南",
        "rag_desc": "基于多文化家庭支援门户Danuri-韩国生活指南资料的聊天机器人",
        "restaurant": "釜山餐厅搜索",
        "restaurant_desc": "基于釜山美食指南和出租车排名的餐厅搜索聊天机器人"
    },
    "fr": {
        "title": "Sélectionnez une méthode pour trouver un salon de discussion",
        "qr": "Rechercher par QR Code",
        "qr_desc": "Scanner le QR code pour rejoindre le salon",
        "id": "Rechercher par ID",
        "id_desc": "Rejoindre en entrant l'ID de la salle de discussion",
        "rag": "Guide de la vie en Corée pour les familles multiculturelles",
        "rag_desc": "Chatbot basé sur le portail Danuri - Guide de la vie en Corée pour les familles multiculturelles",
        "restaurant": "Recherche de restaurants à Busan",
        "restaurant_desc": "Chatbot de recherche de restaurants basé sur le Guide gastronomique de Busan et le Classement des taxis"
    },
    "de": {
        "title": "Wählen Sie eine Methode, um einen Chatraum zu finden",
        "qr": "Nach QR-Code suchen",
        "qr_desc": "QR-Code scannen, um Chatraum beizutreten",
        "id": "Nach ID suchen",
        "id_desc": "Beitreten, indem Sie die Chatraum-ID eingeben",
        "rag": "Koreanischer Lebensratgeber für multikulturelle Familien",
        "rag_desc": "Chatbot basierend auf dem Danuri-Portal - Koreanischer Lebensratgeber für multikulturelle Familien",
        "restaurant": "Busan Restaurant-Suche",
        "restaurant_desc": "Restaurant-Such-Chatbot basierend auf Busan Food Guide & Taxi-Ranking"
    },
    "th": {
        "title": "เลือกวิธีค้นหาห้องแชท",
        "qr": "ค้นหาด้วย QR Code",
        "qr_desc": "สแกน QR Code เพื่อเข้าร่วมห้องแชท",
        "id": "ค้นหาด้วย ID",
        "id_desc": "เข้าร่วมโดยการป้อน IDห้องแชท",
        "rag": "คู่มือการใช้ชีวิตในเกาหลีสำหรับครอบครัวพหุวัฒนธรรม",
        "rag_desc": "แชทบอทอ้างอิงจากข้อมูลคู่มือการใช้ชีวิตในเกาหลีของพอร์ทัล Danuri สำหรับครอบครัวพหุวัฒนธรรม",
        "restaurant": "ค้นหาร้านอาหารปูซาน",
        "restaurant_desc": "แชทบอทค้นหาร้านอาหารอ้างอิงจากคู่มืออาหารปูซานและอันดับแท็กซี่"
    },
    "zh-TW": {
        "title": "請選擇查找聊天室的方法",
        "qr": "通過QR碼查找",
        "qr_desc": "掃描QR碼加入聊天室",
        "id": "通過ID查找",
        "id_desc": "輸入聊天室ID參加",
        "rag": "多元文化家庭韓國生活指南",
        "rag_desc": "基於多元文化家庭支援門戶Danuri-韓國生活指南資料的聊天機器人",
        "restaurant": "釜山餐廳搜尋",
        "restaurant_desc": "基於釜山美食指南和計程車排名的餐廳搜尋聊天機器人"
    },
    "id": {
        "title": "Pilih cara menemukan ruang obrolan",
        "qr": "Cari dengan QR Code",
        "qr_desc": "Pindai QR code untuk bergabung dengan ruang obrolan",
        "id": "Cari dengan ID",
        "id_desc": "Gabung dengan memasukkan ID ruang obrolan",
        "rag": "Panduan Hidup di Korea untuk Keluarga Multikultural",
        "rag_desc": "Chatbot berdasarkan portal Danuri - Panduan Hidup di Korea untuk Keluarga Multikultural",
        "restaurant": "Pencarian Restoran Busan",
        "restaurant_desc": "Chatbot pencarian restoran berdasarkan Panduan Kuliner Busan & Peringkat Taksi"
    },
}

# 닉네임 입력 화면 다국어 지원
NICKNAME_TEXTS = {
    "ko": {"title": "닉네임 설정", "desc": "다른 사용자들에게 보여질 이름을 설정해주세요", "label": "닉네임", "hint": "닉네임을 입력하세요", "enter": "채팅방 입장", "back": "뒤로가기"},
    "en": {"title": "Set Nickname", "desc": "Set a name to show to other users", "label": "Nickname", "hint": "Enter your nickname", "enter": "Enter Chat Room", "back": "Back"},
    "ja": {"title": "ニックネーム設定", "desc": "他のユーザーに表示される名前を設定してください", "label": "ニックネーム", "hint": "ニックネームを入力してください", "enter": "チャットルーム入室", "back": "戻る"},
    "zh": {"title": "设置昵称", "desc": "请设置将显示给其他用户的名称", "label": "昵称", "hint": "请输入昵称", "enter": "进入聊天室", "back": "返回"},
    "vi": {"title": "Đặt biệt danh", "desc": "Hãy đặt tên sẽ hiển thị cho người khác", "label": "Biệt danh", "hint": "Nhập biệt danh", "enter": "Vào phòng chat", "back": "Quay lại"},
    "fr": {"title": "Définir un pseudo", "desc": "Définissez un nom à afficher aux autres utilisateurs", "label": "Pseudo", "hint": "Entrez votre pseudo", "enter": "Entrer dans le salon", "back": "Retour"},
    "de": {"title": "Spitznamen festlegen", "desc": "Legen Sie einen Namen fest, der anderen angezeigt wird", "label": "Spitzname", "hint": "Spitznamen eingeben", "enter": "Chatraum betreten", "back": "Zurück"},
    "th": {"title": "ตั้งชื่อเล่น", "desc": "ตั้งชื่อที่จะแสดงให้ผู้อื่นเห็น", "label": "ชื่อเล่น", "hint": "กรอกชื่อเล่น", "enter": "เข้าสู่ห้องแชท", "back": "ย้อนกลับ"},
    "zh-TW": {
        "title": "設定暱稱",
        "desc": "請設定將顯示給其他用戶的名稱",
        "label": "暱稱",
        "hint": "請輸入暱稱",
        "enter": "進入聊天室",
        "back": "返回"
    },
    "id": {
        "title": "Atur Nama Panggilan",
        "desc": "Atur nama yang akan ditampilkan ke pengguna lain",
        "label": "Nama Panggilan",
        "hint": "Masukkan nama panggilan",
        "enter": "Masuk ke Ruang Obrolan",
        "back": "Kembali"
    },
}

# --- 외국인 근로자 권리구제 방 카드/버튼 다국어 사전 ---
FOREIGN_WORKER_ROOM_CARD_TEXTS = {
    "ko": {"title": "외국인 근로자 권리구제", "desc": "외국인노동자권리구제안내수첩 기반 RAG 챗봇"},
    "en": {"title": "Foreign Worker Rights Protection", "desc": "RAG chatbot based on the Foreign Worker Rights Guidebook"},
    "vi": {"title": "Bảo vệ quyền lợi người lao động nước ngoài", "desc": "Chatbot RAG dựa trên Sổ tay bảo vệ quyền lợi lao động nước ngoài"},
    "ja": {"title": "外国人労働者権利保護", "desc": "外国人労働者権利保護ガイドブックに基づくRAGチャットボット"},
    "zh": {"title": "外籍劳工权益保护", "desc": "基于外籍劳工权益指南的RAG聊天机器人"},
    "zh-TW": {"title": "外籍勞工權益保護", "desc": "基於外籍勞工權益指南的RAG聊天機器人"},
    "id": {"title": "Perlindungan Hak Pekerja Asing", "desc": "Chatbot RAG berbasis Panduan Hak Pekerja Asing"},
    "th": {"title": "การคุ้มครองสิทธิแรงงานต่างชาติ", "desc": "แชทบอท RAG ตามคู่มือสิทธิแรงงานต่างชาติ"},
    "fr": {"title": "Protection des droits des travailleurs étrangers", "desc": "Chatbot RAG basé sur le guide des droits des travailleurs étrangers"},
    "de": {"title": "Schutz der Rechte ausländischer Arbeitnehmer", "desc": "RAG-Chatbot basierend auf dem Leitfaden für ausländische Arbeitnehmer"},
    "uz": {"title": "Чет эл ишчилари ҳуқуқларини ҳимоя қилиш", "desc": "Чет эл ишчилари ҳуқуқлари бўйича йўриқнома асосидаги RAG чатбот"},
    "ne": {"title": "विदेशी श्रमिक अधिकार संरक्षण", "desc": "विदेशी श्रमिक अधिकार गाइडबुकमा आधारित RAG च्याटबोट"},
    "tet": {"title": "Proteksaun Direitu Trabalhador Estranjeiru", "desc": "Chatbot RAG baseia ba livru guia direitu trabalhador estranjeiru"},
    "lo": {"title": "ການປົກປ້ອງສິດຄົນງານຕ່າງປະເທດ", "desc": "RAG chatbot ອີງຕາມຄູ່ມືສິດຄົນງານຕ່າງປະເທດ"},
    "mn": {"title": "Гадаад хөдөлмөрчдийн эрхийн хамгаалалт", "desc": "Гадаад хөдөлмөрчдийн эрхийн гарын авлагад суурилсан RAG чатбот"},
    "my": {"title": "နိုင်ငံခြားလုပ်သား အခွင့်အရေး ကာကွယ်မှု", "desc": "နိုင်ငံခြားလုပ်သားအခွင့်အရေးလမ်းညွှန်အပေါ်အခြေခံသော RAG chatbot"},
    "bn": {"title": "বিদেশি শ্রমিক অধিকার সুরক্ষা", "desc": "বিদেশি শ্রমিক অধিকার গাইডবুক ভিত্তিক RAG চ্যাটবট"},
    "si": {"title": "විදේශීය කම්කරුවන්ගේ අයිතිවාසිකම් ආරක්ෂාව", "desc": "විදේශීය කම්කරුවන්ගේ අයිතිවාසිකම් මාර්ගෝපදේශය මත පදනම් වූ RAG චැට්බොට්"},
    "km": {"title": "ការការពារសិទ្ធិកម្មករជាតិផ្សេង", "desc": "RAG chatbot ផ្អែកលើមគ្គុទ្ទេសក៍សិទ្ធិកម្មករជាតិផ្សេង"},
    "ky": {"title": "Чет эл жумушчуларынын укуктарын коргоо", "desc": "Чет эл жумушчуларынын укук колдонмосуна негизделген RAG чатбот"},
    "ur": {"title": "غیر ملکی مزدوروں کے حقوق کا تحفظ", "desc": "غیر ملکی مزدوروں کے حقوق کی گائیڈ بک پر مبنی RAG چیٹ بوٹ"}
}

def get_text_color(page):
    # 다크모드에서 더 명확한 대비를 위해 완전한 흰색 사용
    if page.theme_mode == ft.ThemeMode.DARK:
        return "#FFFFFF"
    elif page.theme_mode == ft.ThemeMode.LIGHT:
        return "#000000"
    else:  # SYSTEM 모드인 경우
        # 브라우저의 다크모드 감지를 위한 fallback
        return "#FFFFFF" if hasattr(page, '_dark_mode_detected') and page._dark_mode_detected else "#000000"

def get_header_text_color(page):
    # 헤더용 더 강한 대비 색상
    if page.theme_mode == ft.ThemeMode.DARK:
        return "#FFFFFF"
    else:
        return "#1F2937"  # 더 진한 검은색

def get_sub_text_color(page):
    return ft.Colors.GREY_300 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_600

def get_bg_color(page):
    return ft.Colors.BLACK if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.WHITE

def get_card_bg_color(page):
    return "#23272F" if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.WHITE

# --- QR 코드 공유 다국어 텍스트 복구 ---
QR_SHARE_TEXTS = {
    "ko": {
        "title": "채팅방 공유하기: {room}",
        "desc": "아래 QR코드를 스캔하거나 ID를 복사해 친구에게 공유하세요!",
        "room_id": "채팅방 ID: {id}",
        "close": "닫기"
    },
    "en": {
        "title": "Share Chat Room: {room}",
        "desc": "Scan the QR code below or copy the ID to share with friends!",
        "room_id": "Room ID: {id}",
        "close": "Close"
    },
    "ja": {
        "title": "チャットルームを共有: {room}",
        "desc": "下のQRコードをスキャンするかIDをコピーして友達に共有しましょう！",
        "room_id": "チャットルームID: {id}",
        "close": "閉じる"
    },
    "zh": {
        "title": "分享聊天室: {room}",
        "desc": "扫描下方二维码或复制ID与朋友分享！",
        "room_id": "聊天室ID: {id}",
        "close": "关闭"
    },
    "vi": {
        "title": "Chia sẻ phòng chat: {room}",
        "desc": "Quét mã QR bên dưới hoặc sao chép ID để chia sẻ với bạn bè!",
        "room_id": "ID phòng: {id}",
        "close": "Đóng"
    },
    "fr": {
        "title": "Partager le salon: {room}",
        "desc": "Scannez le QR code ci-dessous ou copiez l'ID pour le partager!",
        "room_id": "ID du salon: {id}",
        "close": "Fermer"
    },
    "de": {
        "title": "Chatraum teilen: {room}",
        "desc": "Scannen Sie den QR-Code unten oder kopieren Sie die ID zum Teilen!",
        "room_id": "Chatraum-ID: {id}",
        "close": "Schließen"
    },
    "th": {
        "title": "แชร์ห้องแชท: {room}",
        "desc": "สแกน QR ด้านล่างหรือคัดลอก ID เพื่อแชร์กับเพื่อน!",
        "room_id": "รหัสห้อง: {id}",
        "close": "ปิด"
    },
    "zh-TW": {
        "title": "分享聊天室: {room}",
        "desc": "掃描下方 QR 碼或複製 ID 與朋友分享！",
        "room_id": "聊天室 ID: {id}",
        "close": "關閉"
    },
    "id": {
        "title": "Bagikan Ruang Obrolan: {room}",
        "desc": "Pindai kode QR di bawah atau salin ID untuk dibagikan!",
        "room_id": "ID Ruang: {id}",
        "close": "Tutup"
    },
}

def main(page: ft.Page):
    print("=== BuChat 앱 시작 ===")
    print(f"현재 시간: {datetime.now()}")
    
    # 시스템 다크모드 감지(또는 강제 다크/라이트)
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(
        color_scheme_seed="deepPurple",
        use_material3=True,
    )
    
    # 다크모드 감지 플래그 설정 (향후 JavaScript 연동 가능)
    page._dark_mode_detected = False
    # 구글 폰트 링크 및 CSS 추가 (웹 환경에서 특수문자 깨짐 방지)
    page.html = """
    <link href='https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap' rel='stylesheet'>
    <style>
      body, * {
        font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif !important;
      }
      /* 모바일 입력 필드 최적화 */
      input, textarea {
        -webkit-appearance: none;
        -moz-appearance: none;
        appearance: none;
        border-radius: 8px;
        font-size: 16px !important; /* iOS에서 확대 방지 */
        /* 자동완성 및 제안 비활성화 */
        -webkit-autocomplete: off;
        -moz-autocomplete: off;
        autocomplete: off;
        -webkit-spellcheck: false;
        spellcheck: false;
      }
      /* 입력 필드 포커스 최적화 */
      input:focus, textarea:focus {
        outline: none;
        border-color: #3B82F6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
      }
      /* 자동완성 스타일 제거 */
      input:-webkit-autofill,
      input:-webkit-autofill:hover,
      input:-webkit-autofill:focus,
      input:-webkit-autofill:active {
        -webkit-box-shadow: 0 0 0 30px white inset !important;
        -webkit-text-fill-color: #000 !important;
      }
      /* 모바일 터치 최적화 */
      * {
        -webkit-tap-highlight-color: transparent;
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
      }
      /* 텍스트 입력 필드만 선택 가능 */
      input, textarea {
        -webkit-user-select: text;
        -khtml-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text;
        user-select: text;
      }
    </style>
    """
    page.font_family = "Noto Sans KR, Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif"
    print("페이지 설정 완료")
    lang = "ko"
    country = None
    
    # 폰트 설정 제거 (기본값 사용)
    pass
    
    # --- QR 코드 관련 함수 (Container를 직접 오버레이) ---
    def copy_room_id(room_id):
        """채팅방 ID를 클립보드에 복사하고 사용자에게 피드백 제공"""
        try:
            page.set_clipboard(room_id)
            # 복사 성공 메시지 표시
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"채팅방 ID가 복사되었습니다: {room_id}"),
                action="확인",
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            print(f"클립보드 복사 실패: {e}")
            # 복사 실패 시 수동 복사 안내
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"복사 실패. ID를 수동으로 복사하세요: {room_id}"),
                action="확인",
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
    
    def show_qr_dialog(room_id, room_title):
        print(f"--- DEBUG: QR 코드 다이얼로그 생성 (Container 방식) ---")
        # 다국어 텍스트 적용
        texts = QR_SHARE_TEXTS.get(lang, QR_SHARE_TEXTS["ko"])
        def close_dialog(e):
            if page.overlay:
                page.overlay.pop()
                page.update()
        # QR코드에 전체 URL이 들어가도록 수정 (영속적 채팅방 정보 포함)
        # buchat2와 호환성을 위해 /join_room/ 경로 사용
        qr_data = f"{BASE_URL}/join_room/{room_id}"
        print(f"=== QR코드 생성 디버그 ===")
        print(f"생성된 QR코드 URL: {qr_data}")
        print(f"BASE_URL: {BASE_URL}")
        print(f"room_id: {room_id}")
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_code_image = ft.Image(src_base64=img_str, width=250, height=250)
        # 고정 채팅방인지 확인
        is_persistent = False
        try:
            room_ref = db.reference(f'/rooms/{room_id}')
            room_data = room_ref.get()
            if room_data and room_data.get('is_persistent'):
                is_persistent = True
        except:
            pass
        
        # 고정 채팅방인 경우 인쇄 안내 추가
        persistent_info = ""
        if is_persistent:
            persistent_info = ft.Text(
                "🖨️ 이 QR코드를 인쇄하여 카메라로 찍으면 언제든지 같은 방에 접속할 수 있습니다!",
                size=12,
                color=ft.Colors.GREEN_600,
                text_align="center",
                max_lines=3
            )
        
        popup_content = ft.Container(
            content=ft.Column([
                ft.Text(texts["title"].format(room=room_title), size=20, weight=ft.FontWeight.BOLD, color=get_header_text_color(page)),
                ft.Text(texts["desc"], text_align="center"),
                qr_code_image,
                # ID 부분을 드래그 가능하고 복사 버튼이 있는 형태로 수정
                ft.Container(
                    content=ft.Column([
                        ft.Text(texts["room_id"].format(id=""), size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Text(
                                        room_id,
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_600,
                                        selectable=True,
                                        font_family="monospace"
                                    ),
                                    bgcolor=ft.Colors.GREY_100,
                                    padding=12,
                                    border_radius=8,
                                    border=ft.border.all(1, ft.Colors.GREY_300),
                                    expand=True
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.COPY,
                                    icon_color=ft.Colors.BLUE_600,
                                    tooltip="ID 복사",
                                    on_click=lambda e: copy_room_id(room_id)
                                )
                            ], alignment=ft.MainAxisAlignment.START, spacing=8),
                            width=300
                        )
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=350
                ),
                persistent_info if is_persistent else ft.Container(),
                ft.ElevatedButton(texts["close"], on_click=close_dialog, width=300)
            ], tight=True, spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=350,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK26)
        )
        page.overlay.append(
            ft.Container(
                content=popup_content,
                alignment=ft.alignment.center,
                expand=True
            )
        )
        page.update()

    def handle_create_room(room_title, target_lang, is_persistent=False):
        if not room_title:
            room_title = "새로운 채팅방"
        if not target_lang:
            target_lang = "en"
            print("상대방 언어가 선택되지 않아 기본값(en)으로 설정합니다.")

        # 고정 채팅방인 경우 고정된 ID 생성 (방 제목 기반)
        if is_persistent:
            import hashlib
            # 방 제목을 기반으로 고정된 ID 생성
            room_id_base = hashlib.md5(room_title.encode()).hexdigest()[:8]
            new_room_id = f"persistent_{room_id_base}"
            print(f"고정 채팅방 ID 생성: {new_room_id}")
        else:
            new_room_id = uuid.uuid4().hex[:8]
        
        # Firebase 사용 가능 여부 확인
        if not FIREBASE_AVAILABLE:
            print("❌ Firebase가 초기화되지 않아 방을 생성할 수 없습니다.")
            # 사용자에게 오류 메시지 표시 (간단한 팝업)
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Firebase 연결 오류로 방을 생성할 수 없습니다. 설정을 확인해주세요."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Firebase에 방 정보 저장
        try:
            rooms_ref = db.reference('/rooms')
            room_data = {
                'id': new_room_id,
                'title': room_title,
                'user_lang': lang,
                'target_lang': target_lang,
                'created_at': int(time.time() * 1000),
                'is_persistent': is_persistent,
                'created_by': page.session.get('nickname') or '익명',  # 방 생성자 정보 추가
                'creator_id': page.session.get('user_id') or str(uuid.uuid4())  # 생성자 고유 ID 추가
            }
            rooms_ref.child(new_room_id).set(room_data)
            print(f"✅ Firebase에 방 '{room_title}' 정보 저장 성공 (고정: {is_persistent}, 생성자: {room_data['created_by']})")
        except Exception as e:
            print(f"❌ Firebase 방 정보 저장 실패: {e}")
            # 사용자에게 오류 메시지 표시 (간단한 팝업)
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Firebase 연결 오류로 방을 생성할 수 없습니다. 설정을 확인해주세요."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            return

        print(f"방 '{room_title}' 생성됨 (ID: {new_room_id}, 내 언어: {lang}, 상대 언어: {target_lang}, 고정: {is_persistent})")
        go_chat(lang, target_lang, new_room_id, room_title)

    # --- 화면 이동 함수 ---
    def go_home(selected_lang=None):
        nonlocal lang
        if selected_lang:
            lang = selected_lang
        page.views.clear()
        page.views.append(HomePage(page, lang,
            on_create=lambda e: go_create(lang),
            on_find=lambda e: go_room_list(lang, e),
            on_quick=lambda e: handle_create_room("빠른 채팅방", lang),
            on_change_lang=go_nationality, on_back=go_nationality))
        page.go("/home")

    def go_nationality(e=None):
        page.views.clear()
        page.views.append(NationalitySelectPage(page, on_select=go_home, on_foreign_select=go_foreign_country_select))
        page.go("/")

    def go_foreign_country_select(e=None):
        page.views.clear()
        page.views.append(ForeignCountrySelectPage(page, on_select=on_country_selected, on_back=go_nationality))
        page.go("/foreign_country_select")

    def on_country_selected(country_code, lang_code):
        nonlocal lang
        lang = lang_code
        go_home(lang)

    def go_create(lang):
        page.views.clear()
        page.views.append(CreateRoomPage(page, lang, on_create=handle_create_room, on_back=lambda e: go_home(lang)))
        page.go("/create_room")

    def go_room_list(lang, e=None):
        def on_find_by_id(e):
            go_find_by_id(lang)
        
        def on_scan_qr(e):
            go_scan_qr(lang)
            
        texts = FIND_ROOM_TEXTS.get(lang, FIND_ROOM_TEXTS["ko"])
        page.views.clear()
        # 사용자별 고유 RAG 방 ID 생성 (UUID 사용)
        user_id = page.session.get("user_id")
        if not user_id:
            user_id = str(uuid.uuid4())
            page.session.set("user_id", user_id)
        user_rag_room_id = f"{RAG_ROOM_ID}_{user_id}"
        page.views.append(
            ft.View(
                "/find_room_method",
                controls=[
                    # 헤더 (뒤로가기 + 타이틀)
                    ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: go_home(lang)),
                        ft.Text(texts["title"], size=24, weight=ft.FontWeight.BOLD, color=get_header_text_color(page)),
                    ], alignment=ft.MainAxisAlignment.START, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    # 카드형 버튼들
                    ft.Container(
                        content=ft.Column([
                            # QR코드 스캔 버튼 (새로 추가)
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.QR_CODE_SCANNER, color="#8B5CF6", size=28),
                                        bgcolor="#F3E8FF", border_radius=12, padding=10, margin=ft.margin.only(right=12)
                                    ),
                                    ft.Column([
                                        ft.Text(texts["qr"], size=16, weight=ft.FontWeight.BOLD, color=get_text_color(page)),
                                        ft.Text(texts["qr_desc"], size=12, color=get_sub_text_color(page), text_align=ft.TextAlign.START, max_lines=3)
                                    ], spacing=2, expand=True)
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=get_card_bg_color(page),
                                border_radius=12,
                                shadow=ft.BoxShadow(blur_radius=8, color="#B0BEC544"),
                                padding=16,
                                margin=ft.margin.only(bottom=16),
                                on_click=on_scan_qr
                            ),
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.TAG, color="#2563EB", size=28),
                                        bgcolor="#E0E7FF", border_radius=12, padding=10, margin=ft.margin.only(right=12)
                                    ),
                                    ft.Column([
                                        ft.Text(texts["id"], size=16, weight=ft.FontWeight.BOLD, color=get_text_color(page)),
                                        ft.Text(texts["id_desc"], size=12, color=get_sub_text_color(page), text_align=ft.TextAlign.START, max_lines=3)
                                    ], spacing=2, expand=True)
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=get_card_bg_color(page),
                                border_radius=12,
                                shadow=ft.BoxShadow(blur_radius=8, color="#B0BEC544"),
                                padding=16,
                                margin=ft.margin.only(bottom=16),
                                on_click=on_find_by_id
                            ),
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.TABLE_CHART, color="#22C55E", size=28),
                                        bgcolor="#DCFCE7", border_radius=12, padding=10, margin=ft.margin.only(right=12)
                                    ),
                                    ft.Column([
                                        ft.Text(texts["rag"], size=16, weight=ft.FontWeight.BOLD, color=get_text_color(page)),
                                        ft.Text(texts["rag_desc"], size=12, color=get_sub_text_color(page), text_align=ft.TextAlign.START, max_lines=3)
                                    ], spacing=2, expand=True)
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=get_card_bg_color(page),
                                border_radius=12,
                                shadow=ft.BoxShadow(blur_radius=8, color="#B0BEC544"),
                                padding=16,
                                margin=ft.margin.only(bottom=16),
                                on_click=lambda e: (print(f"다문화가족 RAG 방 클릭됨 - lang: {lang}, room_id: {user_rag_room_id}"), go_chat(lang, lang, user_rag_room_id, RAG_ROOM_TITLE, is_rag=True))
                            ),
                            # --- 외국인 근로자 권리구제 버튼 추가 ---
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.GAVEL, color="#F59E42", size=28),
                                        bgcolor="#FFF7E6", border_radius=12, padding=10, margin=ft.margin.only(right=12)
                                    ),
                                    ft.Column([
                                        ft.Text(FOREIGN_WORKER_ROOM_CARD_TEXTS.get(lang, FOREIGN_WORKER_ROOM_CARD_TEXTS["ko"])["title"], size=16, weight=ft.FontWeight.BOLD, color=get_text_color(page)),
                                        ft.Text(FOREIGN_WORKER_ROOM_CARD_TEXTS.get(lang, FOREIGN_WORKER_ROOM_CARD_TEXTS["ko"])["desc"], size=12, color=get_sub_text_color(page), text_align=ft.TextAlign.START, max_lines=3)
                                    ], spacing=2, expand=True)
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=get_card_bg_color(page),
                                border_radius=12,
                                shadow=ft.BoxShadow(blur_radius=8, color="#B0BEC544"),
                                padding=16,
                                margin=ft.margin.only(bottom=16),
                                on_click=lambda e: (print(f"외국인 근로자 권리구제 방 클릭됨 - lang: {lang}"), go_foreign_worker_rag_chat(lang))
                            ),
                            # --- 맛집검색 버튼 추가 ---
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.FOOD_BANK, color="#FF6B6B", size=28),
                                        bgcolor="#FFE0E0", border_radius=12, padding=10, margin=ft.margin.only(right=12)
                                    ),
                                    ft.Column([
                                        ft.Text(texts["restaurant"], size=16, weight=ft.FontWeight.BOLD, color=get_text_color(page)),
                                        ft.Text(texts["restaurant_desc"], size=12, color=get_sub_text_color(page), text_align=ft.TextAlign.START, max_lines=3)
                                    ], spacing=2, expand=True)
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=get_card_bg_color(page),
                                border_radius=12,
                                shadow=ft.BoxShadow(blur_radius=8, color="#B0BEC544"),
                                padding=16,
                                margin=ft.margin.only(bottom=16),
                                on_click=lambda e: (print(f"맛집검색 방 클릭됨 - lang: {lang}"), go_restaurant_search_chat(lang))
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.only(top=32),
                        alignment=ft.alignment.center,
                    ),
                ],
                bgcolor=ft.LinearGradient(["#F1F5FF", "#E0E7FF"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right)
            )
        )
        page.go("/find_room_method")

    def go_scan_qr(lang):
        """QR코드 스캔 화면으로 이동 (예시.py 참조)"""
        print(f"=== QR코드 스캔 화면 진입 - lang: {lang} ===")
        
        def on_message(e):
            qr_text = e.data  # JS에서 전달된 QR코드 텍스트
            print(f"=== JavaScript에서 QR코드 데이터 수신 ===")
            print(f"받은 qr_text: {qr_text}")
            print(f"qr_text 타입: {type(qr_text)}")
            print(f"qr_text 길이: {len(qr_text) if qr_text else 0}")
            
            # QR코드에서 방 ID 추출
            room_id = None
            if qr_text and "/join_room/" in qr_text:
                room_id = qr_text.split("/join_room/")[-1].split("/")[0]
                print(f"/join_room/ URL에서 추출된 room_id: {room_id}")
            elif qr_text and "/chat/" in qr_text:
                room_id = qr_text.split("/chat/")[-1].split("/")[0]
                print(f"/chat/ URL에서 추출된 room_id: {room_id}")
            elif qr_text:
                room_id = qr_text.strip()
                print(f"직접 추출된 room_id: {room_id}")
            else:
                print("qr_text가 비어있거나 None입니다.")
            
            if room_id:
                print(f"최종 추출된 room_id: {room_id}")
                print(f"go_chat_from_list 호출 시작")
                go_chat_from_list(room_id)
            else:
                print("QR코드에서 room_id를 추출할 수 없습니다.")
                # 사용자에게 오류 메시지 표시
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("올바르지 않은 QR코드입니다."),
                    action="확인"
                )
                page.snack_bar.open = True
                page.update()

        def on_manual_input(e):
            manual_room_id = manual_input_field.value.strip()
            if manual_room_id:
                print(f"=== 수동 입력 처리 ===")
                print(f"수동 입력된 데이터: {manual_room_id}")
                print(f"입력 데이터 타입: {type(manual_room_id)}")
                print(f"입력 데이터 길이: {len(manual_room_id)}")
                
                # URL에서 방 ID 추출
                room_id = None
                if "/join_room/" in manual_room_id:
                    room_id = manual_room_id.split("/join_room/")[-1].split("/")[0]
                    print(f"/join_room/ URL에서 추출된 room_id: {room_id}")
                elif "/chat/" in manual_room_id:
                    room_id = manual_room_id.split("/chat/")[-1].split("/")[0]
                    print(f"/chat/ URL에서 추출된 room_id: {room_id}")
                else:
                    room_id = manual_room_id
                    print(f"직접 사용된 room_id: {room_id}")
                
                if room_id:
                    print(f"최종 사용할 room_id: {room_id}")
                    go_chat_from_list(room_id)
                else:
                    print("수동 입력에서 room_id를 추출할 수 없습니다.")
                    # 사용자에게 오류 메시지 표시
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("올바르지 않은 입력입니다."),
                        action="확인"
                    )
                    page.snack_bar.open = True
                    page.update()
            else:
                print("수동 입력이 비어있습니다.")
                # 사용자에게 안내
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("QR코드 내용을 입력해주세요."),
                    action="확인"
                )
                page.snack_bar.open = True
                page.update()

        # 다국어 텍스트 사전
        FIND_BY_QR_TEXTS = {
            "ko": {"title": "QR 코드 스캔", "desc": "QR 코드를 스캔하거나 내용을 직접 입력하세요", "label": "QR 코드 내용을 직접 입력하세요", "enter": "입력한 내용으로 입장", "tip": "💡 팁: QR 코드를 스캔할 수 없는 경우,\n위 입력창에 QR 코드 내용을 복사해서 붙여넣으세요.", "back": "뒤로가기"},
            "en": {"title": "Scan QR Code", "desc": "Scan the QR code or enter the content manually", "label": "Enter QR code content", "enter": "Enter with input", "tip": "💡 Tip: If you can't scan the QR code,\npaste the QR code content into the input box above.", "back": "Back"},
            "ja": {"title": "QRコードスキャン", "desc": "QRコードをスキャンするか内容を直接入力してください", "label": "QRコード内容を直接入力してください", "enter": "入力内容で入室", "tip": "💡 ヒント: QRコードをスキャンできない場合、\n上の入力欄にQRコード内容を貼り付けてください。", "back": "戻る"},
            "zh": {"title": "扫描二维码", "desc": "扫描二维码或手动输入内容", "label": "请直接输入二维码内容", "enter": "用输入内容进入", "tip": "💡 提示：如果无法扫描二维码，\n请将二维码内容粘贴到上方输入框。", "back": "返回"},
            "zh-TW": {"title": "掃描二維碼", "desc": "掃描二維碼或手動輸入內容", "label": "請直接輸入二維碼內容", "enter": "用輸入內容進入", "tip": "💡 提示：若無法掃描二維碼，\n請將二維碼內容貼到上方輸入框。", "back": "返回"},
            "id": {"title": "Pindai Kode QR", "desc": "Pindai kode QR atau masukkan isinya secara manual", "label": "Masukkan isi kode QR", "enter": "Masuk dengan input", "tip": "💡 Tips: Jika tidak dapat memindai kode QR,\ntempelkan isi kode QR ke kotak input di atas.", "back": "Kembali"},
            "vi": {"title": "Quét mã QR", "desc": "Quét mã QR hoặc nhập nội dung thủ công", "label": "Nhập nội dung mã QR", "enter": "Vào bằng nội dung nhập", "tip": "💡 Mẹo: Nếu không quét được mã QR,\ndán nội dung mã QR vào ô nhập phía trên.", "back": "Quay lại"},
            "fr": {"title": "Scanner le code QR", "desc": "Scannez le code QR ou saisissez le contenu manuellement", "label": "Saisissez le contenu du code QR", "enter": "Entrer avec le contenu saisi", "tip": "💡 Astuce : Si vous ne pouvez pas scanner le code QR,\ncollez le contenu du code QR dans la zone de saisie ci-dessus.", "back": "Retour"},
            "de": {"title": "QR-Code scannen", "desc": "Scannen Sie den QR-Code oder geben Sie den Inhalt manuell ein", "label": "Geben Sie den QR-Code-Inhalt ein", "enter": "Mit Eingabe beitreten", "tip": "💡 Tipp: Wenn Sie den QR-Code nicht scannen können,\nfügen Sie den QR-Code-Inhalt in das obige Eingabefeld ein.", "back": "Zurück"},
            "th": {"title": "สแกนคิวอาร์โค้ด", "desc": "สแกนคิวอาร์โค้ดหรือกรอกเนื้อหาด้วยตนเอง", "label": "กรอกเนื้อหาคิวอาร์โค้ด", "enter": "เข้าร่วมด้วยเนื้อหาที่กรอก", "tip": "💡 เคล็ดลับ: หากสแกนคิวอาร์โค้ดไม่ได้\nให้นำเนื้อหาคิวอาร์โค้ดไปวางในช่องกรอกด้านบน", "back": "ย้อนกลับ"},
        }
        t = FIND_BY_QR_TEXTS.get(lang, FIND_BY_QR_TEXTS["en"])
        manual_input_field = ft.TextField(
            label=t["label"],
            hint_text=t["label"],
            width=350,
            on_submit=on_manual_input
        )

        # 안내 메시지와 수동 입력 옵션 제공
        page.views.clear()
        page.views.append(
            ft.View(
                "/scan_qr",
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(
                                name=ft.Icons.QR_CODE,
                                size=64,
                                color=ft.Colors.BLUE_500
                            ),
                            ft.Text(
                                t["title"],
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Text(
                                t["desc"],
                                size=14,
                                color=get_sub_text_color(page),
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Container(height=20),
                            manual_input_field,
                            ft.ElevatedButton(
                                t["enter"],
                                on_click=on_manual_input,
                                width=350
                            ),
                            ft.Container(height=20),
                            ft.Text(
                                t["tip"],
                                size=12,
                                color=ft.Colors.GREY_500,
                                text_align=ft.TextAlign.CENTER
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=32,
                        bgcolor=get_card_bg_color(page),
                        border_radius=20,
                        shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK12),
                    ),
                    ft.ElevatedButton(t["back"], on_click=lambda e: go_room_list(lang), width=350)
                ],
                bgcolor=get_bg_color(page),
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                vertical_alignment=ft.MainAxisAlignment.CENTER
            )
        )
        page.go("/scan_qr")

    def start_qr_scan(callback):
        """QR코드 스캔 시작 - 실제 카메라 접근 및 QR코드 인식 (예시.py 참조)"""
        print(f"=== start_qr_scan 함수 시작 ===")
        print(f"콜백 함수: {callback}")
        print(f"콜백 함수 타입: {type(callback)}")
        
        try:
            # 실제 QR코드 스캔을 위한 JavaScript 코드
            js_code = """
            // QR코드 스캔을 위한 JavaScript 코드
            async function startQRScan() {
                try {
                    // 카메라 접근
                    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                    const video = document.createElement('video');
                    video.srcObject = stream;
                    video.play();
                    
                    // jsQR 라이브러리 로드 (CDN 사용)
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
                    document.head.appendChild(script);
                    
                    script.onload = function() {
                        const canvas = document.createElement('canvas');
                        const context = canvas.getContext('2d');
                        
                        function scanQR() {
                            canvas.width = video.videoWidth;
                            canvas.height = video.videoHeight;
                            context.drawImage(video, 0, 0, canvas.width, canvas.height);
                            
                            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                            const code = jsQR(imageData.data, imageData.width, imageData.height);
                            
                            if (code) {
                                console.log('QR코드 감지됨:', code.data);
                                // Flet으로 데이터 전송
                                window.flutter_inappwebview.callHandler('onQRScanned', code.data);
                                stream.getTracks().forEach(track => track.stop());
                                return;
                            }
                            
                            requestAnimationFrame(scanQR);
                        }
                        
                        scanQR();
                    };
                    
                } catch (error) {
                    console.error('QR코드 스캔 오류:', error);
                    // 오류 발생 시 시뮬레이션 데이터 반환
                    setTimeout(() => {
                        const testData = 'https://port-0-buchat-m0t1itev3f2879ad.sel4.cloudtype.app/join_room/03558704';
                        window.flutter_inappwebview.callHandler('onQRScanned', testData);
                    }, 3000);
                }
            }
            
            startQRScan();
            """
            
            print(f"JavaScript 코드 실행 시작")
            # Flet에서는 JavaScript 실행이 제한적이므로 시뮬레이션 방식 사용
            print(f"JavaScript 실행 대신 시뮬레이션 방식 사용")
            
            # 사용자에게 안내
            page.snack_bar = ft.SnackBar(
                content=ft.Text("QR코드 스캔을 시작합니다. 3초 후 테스트 URL이 반환됩니다. (실제 QR코드 스캔 시에는 채팅방 공유 QR코드를 스캔하세요)"),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            
            # 시뮬레이션을 위한 스레드 시작
            import threading
            import time
            import random
            
            def simulate_qr_scan():
                time.sleep(3)
                # 실제 Firebase에 존재하는 일반 사용자 채팅방 ID들만 사용 (RAG 방 제외)
                room_id = random.choice([
                    "03558704",  # 실제 존재하는 방
                    "f8ae1de0",  # 실제 존재하는 방
                    "persistent_0e12de26",  # 실제 존재하는 영속적 방
                    "persistent_f2da8888"  # 실제 존재하는 영속적 방
                ])
                
                # 실제 QR코드 스캔과 동일한 URL 형태로 반환 (/join_room/ 경로 사용)
                test_data = f"{BASE_URL}/join_room/{room_id}"
                print(f"시뮬레이션 QR코드 데이터: {test_data}")
                callback(test_data)
            
            # 백그라운드에서 시뮬레이션 실행
            thread = threading.Thread(target=simulate_qr_scan)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"QR코드 스캔 시작 중 오류 발생: {e}")
            # 오류 발생 시 사용자에게 알림
            page.snack_bar = ft.SnackBar(
                content=ft.Text("QR코드 스캔을 시작할 수 없습니다. 수동으로 QR코드 내용을 입력해주세요."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()

    def go_find_by_id(lang):
        def on_submit(e=None):
            room_id = id_field.value.strip()
            if room_id:
                go_chat_from_list(room_id)
        # 다국어 텍스트 사전
        FIND_BY_ID_TEXTS = {
            "ko": {"title": "방 ID로 채팅방 찾기", "label": "방 ID를 입력하세요", "enter": "입장", "back": "뒤로가기"},
            "en": {"title": "Find Chat Room by ID", "label": "Enter chat room ID", "enter": "Enter", "back": "Back"},
            "ja": {"title": "IDでチャットルームを探す", "label": "ルームIDを入力してください", "enter": "入室", "back": "戻る"},
            "zh": {"title": "通过ID查找聊天室", "label": "请输入房间ID", "enter": "进入", "back": "返回"},
            "zh-TW": {"title": "通過ID查找聊天室", "label": "請輸入房間ID", "enter": "進入", "back": "返回"},
            "id": {"title": "Cari Ruang Obrolan dengan ID", "label": "Masukkan ID ruang obrolan", "enter": "Masuk", "back": "Kembali"},
            "vi": {"title": "Tìm phòng chat bằng ID", "label": "Nhập ID phòng chat", "enter": "Vào phòng", "back": "Quay lại"},
            "fr": {"title": "Trouver une salle par ID", "label": "Entrez l'ID de la salle", "enter": "Entrer", "back": "Retour"},
            "de": {"title": "Chatraum per ID finden", "label": "Geben Sie die Raum-ID ein", "enter": "Betreten", "back": "Zurück"},
            "th": {"title": "ค้นหาห้องแชทด้วย ID", "label": "กรอก ID ห้องแชท", "enter": "เข้าร่วม", "back": "ย้อนกลับ"},
        }
        t = FIND_BY_ID_TEXTS.get(lang, FIND_BY_ID_TEXTS["en"])
        id_field = ft.TextField(label=t["label"], width=300, on_submit=on_submit)
        page.views.clear()
        page.views.append(
            ft.View(
                "/find_by_id",
                controls=[
                    ft.Text(t["title"], size=20, weight=ft.FontWeight.BOLD, color=get_header_text_color(page)),
                    id_field,
                    ft.ElevatedButton(t["enter"], on_click=on_submit, width=300),
                    ft.ElevatedButton(t["back"], on_click=lambda e: go_room_list(lang), width=300)
                ],
                bgcolor=get_bg_color(page),
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                vertical_alignment=ft.MainAxisAlignment.CENTER
            )
        )
        page.go("/find_by_id")

    def go_chat_from_list(room_id):
        print(f"=== go_chat_from_list 함수 시작 ===")
        print(f"받은 room_id: {room_id}")
        print(f"room_id 타입: {type(room_id)}")
        print(f"room_id 길이: {len(room_id) if room_id else 0}")
        
        # RAG 방 ID 목록 (QR코드 스캔으로 입장 차단)
        rag_room_ids = [
            "rag_korean_guide",  # 다문화가족 RAG
            "foreign_worker_rights_rag",  # 외국인 권리구제 RAG
            "restaurant_search_rag"  # 맛집검색 RAG
        ]
        
        # RAG 방인지 확인 (QR코드 스캔으로 RAG 방 입장 차단)
        print(f"RAG_ROOM_ID: {RAG_ROOM_ID}")
        print(f"room_id.startswith(RAG_ROOM_ID): {room_id.startswith(RAG_ROOM_ID) if room_id else False}")
        
        # RAG 방인지 확인
        is_rag_room = (room_id == RAG_ROOM_ID or 
                       room_id.startswith(RAG_ROOM_ID) or
                       room_id in rag_room_ids or
                       "rag_korean_guide" in room_id)
        
        if is_rag_room:
            print(f"RAG 방 QR코드 스캔 차단: {room_id}")
            page.snack_bar = ft.SnackBar(
                content=ft.Text("RAG 채팅방은 QR코드로 입장할 수 없습니다. 메인 화면에서 직접 선택해주세요."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            print(f"RAG 방 차단 메시지 표시 완료")
            print(f"go_home 호출 시작")
            go_home(lang)
            print(f"go_home 호출 완료")
            return
        
        # 기존 RAG 방 처리 로직 (QR코드가 아닌 직접 접근 시에만)
        if room_id == RAG_ROOM_ID or room_id.startswith(RAG_ROOM_ID):
            print(f"RAG 채팅방으로 인식됨")
            user_id = page.session.get("user_id")
            print(f"현재 user_id: {user_id}")
            if not user_id:
                user_id = str(uuid.uuid4())
                page.session.set("user_id", user_id)
                print(f"새로 생성된 user_id: {user_id}")
            user_rag_room_id = f"{RAG_ROOM_ID}_{user_id}"
            print(f"생성된 user_rag_room_id: {user_rag_room_id}")
            print(f"go_chat 호출 시작 (RAG)")
            go_chat(lang, lang, user_rag_room_id, RAG_ROOM_TITLE, is_rag=True)
            print(f"go_chat 호출 완료 (RAG)")
            return
        
        # Firebase 사용 가능 여부 확인
        print(f"FIREBASE_AVAILABLE: {FIREBASE_AVAILABLE}")
        if not FIREBASE_AVAILABLE:
            print(f"Firebase가 사용 불가능하여 방 정보를 가져올 수 없습니다: {room_id}")
            # 사용자에게 오류 메시지 표시
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Firebase 연결 오류로 채팅방에 접속할 수 없습니다."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            print(f"Firebase 오류 메시지 표시 완료")
            print(f"go_home 호출 시작")
            go_home(lang)
            print(f"go_home 호출 완료")
            return
        
        try:
            print(f"Firebase에서 방 정보 조회 시작")
            room_ref = db.reference(f'/rooms/{room_id}')
            print(f"Firebase 참조 생성: {room_ref}")
            room_data = room_ref.get()
            print(f"Firebase에서 가져온 room_data: {room_data}")
            
            if room_data:
                print(f"방 정보 찾음: {room_data}")
                print(f"go_chat 호출 시작 (일반 채팅방)")
                go_chat(
                    user_lang=room_data.get('user_lang', 'ko'),
                    target_lang=room_data.get('target_lang', 'en'),
                    room_id=room_id,
                    room_title=room_data.get('title', '채팅방'),
                    is_rag=room_data.get('is_rag', False)
                )
                print(f"go_chat 호출 완료 (일반 채팅방)")
            else:
                print(f"오류: ID가 {room_id}인 방을 찾을 수 없습니다.")
                # 사용자에게 오류 메시지 표시
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"채팅방을 찾을 수 없습니다. (ID: {room_id})"),
                    action="확인"
                )
                page.snack_bar.open = True
                page.update()
                print(f"채팅방 없음 오류 메시지 표시 완료")
                print(f"go_home 호출 시작")
                go_home(lang)
                print(f"go_home 호출 완료")
        except Exception as e:
            print(f"Firebase에서 방 정보 가져오기 실패: {e}")
            import traceback
            traceback.print_exc()
            # 사용자에게 오류 메시지 표시
            page.snack_bar = ft.SnackBar(
                content=ft.Text("채팅방 정보를 가져오는 중 오류가 발생했습니다."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            print(f"Firebase 예외 오류 메시지 표시 완료")
            print(f"go_home 호출 시작")
            go_home(lang)
            print(f"go_home 호출 완료")

    def go_chat(user_lang, target_lang, room_id, room_title="채팅방", is_rag=False, is_foreign_worker_rag=False, is_restaurant_search_rag=False):
        def after_nickname(nickname):
            page.session.set("nickname", nickname)
            page.views.clear()
            
            # 맛집검색 RAG 채팅방인지 확인
            if is_restaurant_search_rag:
                def restaurant_search_answer(query, target_lang):
                    try:
                        print(f"맛집검색 질문: {query}")
                        print(f"타겟 언어: {target_lang}")
                        print(f"전달할 target_lang: {target_lang}")
                        
                        # 맛집검색 시스템 사용
                        result = search_restaurants(query, GEMINI_API_KEY)
                        print(f"맛집검색 답변 생성 완료: {len(result)} 문자")
                        # 한국어가 아니면 번역 적용
                        if target_lang != "ko":
                            from pages.chat_room import translate_message
                            result = translate_message(result, target_lang)
                        return result
                    except Exception as e:
                        print(f"맛집검색 오류: {e}")
                        import traceback
                        traceback.print_exc()
                        return "죄송합니다. 맛집 정보를 찾을 수 없습니다."
                
                page.views.append(ChatRoomPage(
                    page,
                    room_id=room_id,
                    room_title=room_title,
                    user_lang=user_lang,
                    target_lang=target_lang,
                    on_back=lambda e: go_room_list(lang),
                    on_share=on_share_clicked,
                    custom_translate_message=restaurant_search_answer,
                    firebase_available=FIREBASE_AVAILABLE,
                    is_restaurant_search_rag=True
                ))
            # 외국인 근로자 RAG 채팅방인지 확인
            elif is_foreign_worker_rag:
                # 대화 컨텍스트를 저장할 변수
                conversation_context = {}
                
                def foreign_worker_rag_answer(query, target_lang):
                    try:
                        print(f"외국인 권리구제 RAG 질문: {query}")
                        print(f"타겟 언어: {target_lang}")
                        print(f"전달할 target_lang: {target_lang}")
                        
                        # 쓰레기 처리 관련 질문인지 확인
                        from rag_utils import is_waste_related_query
                        if is_waste_related_query(query):
                            # 쓰레기 처리 관련 질문이면 다문화가족 벡터DB 사용
                            if vector_db_multicultural is None:
                                print("다문화가족 벡터DB가 None입니다.")
                                return "죄송합니다. RAG 기능이 현재 사용할 수 없습니다. (다문화가족 벡터DB가 로드되지 않았습니다.)"
                            print(f"쓰레기 처리 질문 - 다문화가족 벡터DB 사용")
                            result = answer_with_rag_foreign_worker(query, vector_db_multicultural, GEMINI_API_KEY, target_lang=target_lang, conversation_context=conversation_context)
                        else:
                            # 일반 외국인 근로자 관련 질문이면 외국인 근로자 벡터DB 사용
                            if vector_db_foreign_worker is None:
                                print("외국인 권리구제 벡터DB가 None입니다.")
                                return "죄송합니다. RAG 기능이 현재 사용할 수 없습니다. (외국인 권리구제 벡터DB가 로드되지 않았습니다.)"
                            print(f"외국인 근로자 질문 - 외국인 근로자 벡터DB 사용")
                            result = answer_with_rag_foreign_worker(query, vector_db_foreign_worker, GEMINI_API_KEY, target_lang=target_lang, conversation_context=conversation_context)
                        
                        print(f"RAG 답변 생성 완료: {len(result)} 문자")
                        return result
                    except Exception as e:
                        print(f"외국인 근로자 RAG 오류: {e}")
                        import traceback
                        traceback.print_exc()
                        return "죄송합니다. 외국인 근로자 권리구제 정보를 찾을 수 없습니다."
                
                page.views.append(ChatRoomPage(
                    page,
                    room_id=room_id,
                    room_title=room_title,
                    user_lang=user_lang,
                    target_lang=target_lang,
                    on_back=lambda e: go_room_list(lang),
                    on_share=on_share_clicked,
                    custom_translate_message=foreign_worker_rag_answer,
                    firebase_available=FIREBASE_AVAILABLE,
                    is_foreign_worker_rag=True
                ))
            # 기존 다문화 가족 RAG 채팅방인지 확인
            elif is_rag:
                # 대화 컨텍스트를 저장할 변수
                conversation_context = {}
                
                def multicultural_rag_answer(query, target_lang):
                    try:
                        print(f"다문화 가족 RAG 질문: {query}")
                        print(f"타겟 언어: {target_lang}")
                        print(f"전달할 target_lang: {target_lang}")
                        if vector_db_multicultural is None:
                            print("다문화가족 벡터DB가 None입니다.")
                            return "죄송합니다. RAG 기능이 현재 사용할 수 없습니다. (다문화가족 벡터DB가 로드되지 않았습니다.)"
                        print(f"다문화가족 벡터DB 문서 수: {len(vector_db_multicultural.documents) if hasattr(vector_db_multicultural, 'documents') else '알 수 없음'}")
                        result = answer_with_rag(query, vector_db_multicultural, GEMINI_API_KEY, target_lang=target_lang, conversation_context=conversation_context)
                        print(f"RAG 답변 생성 완료: {len(result)} 문자")
                        return result
                    except Exception as e:
                        print(f"다문화 가족 RAG 오류: {e}")
                        import traceback
                        traceback.print_exc()
                        return "죄송합니다. 다문화 가족 한국생활 안내 정보를 찾을 수 없습니다."
                
                page.views.append(ChatRoomPage(
                    page,
                    room_id=room_id,
                    room_title=room_title,
                    user_lang=user_lang,
                    target_lang=target_lang,
                    on_back=lambda e: go_home(lang),
                    on_share=on_share_clicked,
                    custom_translate_message=multicultural_rag_answer,
                    firebase_available=FIREBASE_AVAILABLE
                ))
            else:
                page.views.append(ChatRoomPage(
                    page, 
                    room_id=room_id, 
                    room_title=room_title, 
                    user_lang=user_lang, 
                    target_lang=target_lang,
                    on_back=lambda e: go_home(lang),
                    on_share=on_share_clicked,
                    firebase_available=FIREBASE_AVAILABLE
                ))
            # 라우팅 중복 방지를 위해 직접 페이지 업데이트
            print(f"채팅방 페이지 설정 완료 - room_id: {room_id}")
            page.update()
        def on_share_clicked(e):
            print(f"--- DEBUG: 공유 버튼 클릭됨 ---")
            show_qr_dialog(room_id, room_title)
        if not page.session.get("nickname"):
            # 닉네임 입력 화면 다국어 지원
            texts = NICKNAME_TEXTS.get(lang, NICKNAME_TEXTS["ko"])
            nickname_value = ""
            char_count = ft.Text(f"0/12", size=12, color=get_sub_text_color(page))
            nickname_field = ft.TextField(label=texts["label"], hint_text=texts["hint"], on_change=None, max_length=12, width=320)
            enter_button = ft.ElevatedButton(texts["enter"], disabled=True, width=320)
            def on_nickname_change(e):
                value = nickname_field.value.strip()
                char_count.value = f"{len(value)}/12"
                enter_button.disabled = not (2 <= len(value) <= 12)
                page.update()
            nickname_field.on_change = on_nickname_change
            def on_nickname_submit(e=None):
                nickname = nickname_field.value.strip()
                if 2 <= len(nickname) <= 12:
                    after_nickname(nickname)
            enter_button.on_click = on_nickname_submit
            page.views.clear()
            page.views.append(
                ft.View(
                    "/nickname",
                    controls=[
                        ft.Row([
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: go_home(lang)),
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(name=ft.Icons.PERSON, color="#22C55E", size=28),
                                        bgcolor="#22C55E22", border_radius=12, padding=8, margin=ft.margin.only(right=8)
                                    ),
                                    ft.Text(texts["title"], size=22, weight=ft.FontWeight.BOLD, color=get_header_text_color(page)),
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ),
                        ], alignment=ft.MainAxisAlignment.START, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(texts["desc"], size=14, color=get_sub_text_color(page), text_align="center"),
                                ft.Container(height=8),
                                ft.Text(texts["label"], size=14, weight=ft.FontWeight.W_500),
                        nickname_field,
                                ft.Row([
                                    char_count
                                ], alignment=ft.MainAxisAlignment.END),
                                ft.Container(height=8),
                                enter_button,
                                ft.Container(height=8),
                                ft.ElevatedButton(texts["back"], on_click=lambda e: go_home(lang), width=320, style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200, color=ft.Colors.BLACK)),
                            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=40,
                            bgcolor=get_card_bg_color(page),
                            border_radius=20,
                            shadow=ft.BoxShadow(blur_radius=24, color="#B0BEC544"),
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(top=32),
                            width=400,
                        ),
                    ],
                    bgcolor=ft.LinearGradient(["#F1F5FF", "#E0E7FF"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right),
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    vertical_alignment=ft.MainAxisAlignment.CENTER
                )
            )
            page.update()
            return
        else:
            after_nickname(page.session.get("nickname") or "")

    # --- 외국인 근로자 권리구제 RAG 채팅방 진입 함수 ---
    def go_foreign_worker_rag_chat(lang):
        # 고유 방 ID 및 타이틀
        room_id = "foreign_worker_rights_rag"
        room_title = "외국인 근로자 권리구제"
        print(f"외국인 근로자 권리구제 방 진입 - lang: {lang}, room_id: {room_id}")
        # 채팅방 진입 (is_foreign_worker_rag=True로 설정)
        go_chat(lang, lang, room_id, room_title, is_rag=False, is_foreign_worker_rag=True)

    # --- 맛집검색 RAG 채팅방 진입 함수 ---
    def go_restaurant_search_chat(lang):
        # 고유 방 ID 및 타이틀
        room_id = "restaurant_search_rag"
        room_title = "맛집검색"
        print(f"맛집검색 방 진입 - lang: {lang}, room_id: {room_id}")
        # 채팅방 진입 (is_restaurant_search_rag=True로 설정)
        go_chat(lang, lang, room_id, room_title, is_rag=False, is_foreign_worker_rag=False, is_restaurant_search_rag=True)

    # --- 라우팅 처리 ---
    def route_change(route):
        print(f"Route: {page.route}")
        parts = page.route.split('/')
        
        if page.route == "/":
            go_nationality()
        elif page.route == "/home":
            go_home(lang)
        elif page.route == "/create_room":
            go_create(lang)
        elif page.route == "/scan_qr":
            go_scan_qr(lang)
        elif page.route.startswith("/join_room/"):
            room_id = parts[2]
            print(f"=== /join_room/ 경로 라우팅 처리 ===")
            print(f"추출된 room_id: {room_id}")
            # QR코드로 참여 시, Firebase에서 방 정보를 가져옵니다.
            # 중복 호출 방지를 위해 현재 페이지가 이미 채팅방인지 확인
            current_route = page.route
            if current_route == f"/join_room/{room_id}":
                print(f"이미 해당 채팅방 페이지에 있음: {current_route}")
                return
            go_chat_from_list(room_id)
        elif page.route.startswith("/chat/"):
            room_id = parts[2]
            print(f"=== /chat/ 경로 라우팅 처리 ===")
            print(f"추출된 room_id: {room_id}")
            # 직접 채팅방 URL로 접속 시, Firebase에서 방 정보를 가져옵니다.
            # 중복 호출 방지를 위해 현재 페이지가 이미 채팅방인지 확인
            current_route = page.route
            if current_route == f"/chat/{room_id}":
                print(f"이미 해당 채팅방 페이지에 있음: {current_route}")
                return
            go_chat_from_list(room_id)
        # 다른 라우트 핸들링...
        page.update()

    page.on_route_change = route_change
    page.go("/")

if __name__ == "__main__":
    ft.app(target=main, port=8000)
