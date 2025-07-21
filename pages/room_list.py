import flet as ft
from firebase_admin import db
import time

def RoomListPage(page, lang="ko", on_select=None, on_back=None):
    # 화면 크기에 따른 반응형 설정
    is_mobile = page.width < 600
    is_tablet = 600 <= page.width < 1024
    
    # 반응형 크기 계산
    container_width = min(page.width * 0.95, 600) if not is_mobile else page.width * 0.98
    card_width = min(400, page.width * 0.9)
    title_size = 20 if is_mobile else 24
    subtitle_size = 16 if is_mobile else 18
    text_size = 14 if is_mobile else 16
    
    # 언어별 텍스트 사전
    texts = {
        "ko": {
            "title": "📋 채팅방 목록",
            "subtitle": "현재 활성화된 채팅방들",
            "no_rooms": "현재 활성화된 채팅방이 없습니다.",
            "create_new": "새로운 채팅방 만들기",
            "persistent_rooms": "영속적 채팅방",
            "temporary_rooms": "임시 채팅방",
            "room_id": "방 ID: {id}",
            "created_at": "생성: {time}",
            "join": "입장",
            "back": "뒤로가기"
        },
        "en": {
            "title": "📋 Chat Room List",
            "subtitle": "Currently active chat rooms",
            "no_rooms": "No active chat rooms found.",
            "create_new": "Create New Chat Room",
            "persistent_rooms": "Persistent Rooms",
            "temporary_rooms": "Temporary Rooms",
            "room_id": "Room ID: {id}",
            "created_at": "Created: {time}",
            "join": "Join",
            "back": "Back"
        },
        "ja": {
            "title": "📋 チャットルーム一覧",
            "subtitle": "現在アクティブなチャットルーム",
            "no_rooms": "アクティブなチャットルームが見つかりません。",
            "create_new": "新しいチャットルームを作成",
            "persistent_rooms": "永続的ルーム",
            "temporary_rooms": "一時的ルーム",
            "room_id": "ルームID: {id}",
            "created_at": "作成: {time}",
            "join": "参加",
            "back": "戻る"
        },
        "zh": {
            "title": "📋 聊天室列表",
            "subtitle": "当前活跃的聊天室",
            "no_rooms": "没有找到活跃的聊天室。",
            "create_new": "创建新聊天室",
            "persistent_rooms": "持久聊天室",
            "temporary_rooms": "临时聊天室",
            "room_id": "房间ID: {id}",
            "created_at": "创建: {time}",
            "join": "加入",
            "back": "返回"
        },
        "zh-TW": {
            "title": "📋 聊天室列表",
            "subtitle": "當前活躍的聊天室",
            "no_rooms": "沒有找到活躍的聊天室。",
            "create_new": "建立新聊天室",
            "persistent_rooms": "持久聊天室",
            "temporary_rooms": "臨時聊天室",
            "room_id": "房間ID: {id}",
            "created_at": "建立: {time}",
            "join": "加入",
            "back": "返回"
        },
        "id": {
            "title": "📋 Daftar Ruang Obrolan",
            "subtitle": "Ruang obrolan yang aktif saat ini",
            "no_rooms": "Tidak ada ruang obrolan aktif yang ditemukan.",
            "create_new": "Buat Ruang Obrolan Baru",
            "persistent_rooms": "Ruang Persisten",
            "temporary_rooms": "Ruang Sementara",
            "room_id": "ID Ruang: {id}",
            "created_at": "Dibuat: {time}",
            "join": "Bergabung",
            "back": "Kembali"
        },
        "fr": {
            "title": "📋 Liste des salles de chat",
            "subtitle": "Salles de chat actuellement actives",
            "no_rooms": "Aucune salle de chat active trouvée.",
            "create_new": "Créer une nouvelle salle",
            "persistent_rooms": "Salles persistantes",
            "temporary_rooms": "Salles temporaires",
            "room_id": "ID de salle: {id}",
            "created_at": "Créé: {time}",
            "join": "Rejoindre",
            "back": "Retour"
        },
        "de": {
            "title": "📋 Chatraum-Liste",
            "subtitle": "Aktuell aktive Chaträume",
            "no_rooms": "Keine aktiven Chaträume gefunden.",
            "create_new": "Neuen Chatraum erstellen",
            "persistent_rooms": "Persistente Räume",
            "temporary_rooms": "Temporäre Räume",
            "room_id": "Raum-ID: {id}",
            "created_at": "Erstellt: {time}",
            "join": "Beitreten",
            "back": "Zurück"
        },
        "th": {
            "title": "📋 รายการห้องแชท",
            "subtitle": "ห้องแชทที่ใช้งานอยู่ปัจจุบัน",
            "no_rooms": "ไม่พบห้องแชทที่ใช้งานอยู่",
            "create_new": "สร้างห้องแชทใหม่",
            "persistent_rooms": "ห้องถาวร",
            "temporary_rooms": "ห้องชั่วคราว",
            "room_id": "รหัสห้อง: {id}",
            "created_at": "สร้าง: {time}",
            "join": "เข้าร่วม",
            "back": "ย้อนกลับ"
        },
        "vi": {
            "title": "📋 Danh sách phòng trò chuyện",
            "subtitle": "Các phòng trò chuyện đang hoạt động",
            "no_rooms": "Không tìm thấy phòng trò chuyện nào đang hoạt động.",
            "create_new": "Tạo phòng trò chuyện mới",
            "persistent_rooms": "Phòng bền vững",
            "temporary_rooms": "Phòng tạm thời",
            "room_id": "ID phòng: {id}",
            "created_at": "Tạo: {time}",
            "join": "Tham gia",
            "back": "Quay lại"
        }
    }
    t = texts.get(lang, texts["en"])
    
    def format_time(timestamp):
        """타임스탬프를 읽기 쉬운 시간으로 변환"""
        try:
            # 밀리초를 초로 변환
            seconds = timestamp / 1000
            from datetime import datetime
            dt = datetime.fromtimestamp(seconds)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return "알 수 없음"

    def load_rooms():
        """Firebase에서 채팅방 목록을 로드"""
        try:
            rooms_ref = db.reference('/rooms')
            rooms_data = rooms_ref.get()
    
            if not rooms_data:
                return [], []
            
            persistent_rooms = []
            temporary_rooms = []
            
            for room_id, room_data in rooms_data.items():
                if isinstance(room_data, dict):
                    room_info = {
                        'id': room_id,
                        'title': room_data.get('title', '제목 없음'),
                        'created_at': room_data.get('created_at', 0),
                        'is_persistent': room_data.get('is_persistent', False)
                    }
                    
                    if room_info['is_persistent']:
                        persistent_rooms.append(room_info)
                    else:
                        temporary_rooms.append(room_info)
            
            # 생성 시간순으로 정렬 (최신순)
            persistent_rooms.sort(key=lambda x: x['created_at'], reverse=True)
            temporary_rooms.sort(key=lambda x: x['created_at'], reverse=True)
            
            return persistent_rooms, temporary_rooms
            
        except Exception as e:
            print(f"채팅방 목록 로드 오류: {e}")
            return [], []

    def create_room_card(room):
        """채팅방 카드 생성"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(
                        name=ft.Icons.LOCK if room['is_persistent'] else ft.Icons.PUBLIC,
                        color=ft.colors.GREEN_600 if room['is_persistent'] else ft.colors.BLUE_600,
                        size=20
                    ),
                    ft.Text(
                        room['title'],
                        size=text_size,
                        weight=ft.FontWeight.BOLD,
                        expand=True
                    ),
                    ft.ElevatedButton(
                        t["join"],
                        on_click=lambda e, room_id=room['id']: on_select(room_id) if on_select else None,
                        style=ft.ButtonStyle(
                            bgcolor=ft.colors.GREEN_600,
                            color=ft.colors.WHITE
                        )
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(
                    t["room_id"].format(id=room['id']),
                    size=12,
                    color=ft.colors.GREY_600
                ),
                ft.Text(
                    t["created_at"].format(time=format_time(room['created_at'])),
                    size=12,
                    color=ft.colors.GREY_500
                )
            ], spacing=8),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            padding=16,
            shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK12),
            margin=ft.margin.only(bottom=12),
            width=card_width
        )

    def get_text_color(page):
        if page.theme_mode == ft.ThemeMode.DARK:
            return "#FFFFFF"
        elif page.theme_mode == ft.ThemeMode.LIGHT:
            return "#000000"
        else:  # SYSTEM 모드인 경우
            return "#FFFFFF" if hasattr(page, '_dark_mode_detected') and page._dark_mode_detected else "#000000"

    def get_header_text_color(page):
        # 헤더용 더 강한 대비 색상
        if page.theme_mode == ft.ThemeMode.DARK:
            return "#FFFFFF"
        else:
            return "#1F2937"  # 더 진한 검은색

    # 초기 채팅방 목록 로드
    persistent_rooms, temporary_rooms = load_rooms()
    
    # 영속적 채팅방 섹션
    persistent_section = ft.Column([
        ft.Text(
            t["persistent_rooms"],
            size=subtitle_size,
            weight=ft.FontWeight.BOLD,
            color=ft.colors.GREEN_700
        ),
        *[create_room_card(room) for room in persistent_rooms]
    ], spacing=12) if persistent_rooms else ft.Container()
    
    # 임시 채팅방 섹션
    temporary_section = ft.Column([
        ft.Text(
            t["temporary_rooms"],
            size=subtitle_size,
            weight=ft.FontWeight.BOLD,
            color=ft.colors.BLUE_700
        ),
        *[create_room_card(room) for room in temporary_rooms]
    ], spacing=12) if temporary_rooms else ft.Container()
    
    # 빈 상태 메시지
    empty_message = ft.Container(
        content=ft.Column([
            ft.Icon(
                name=ft.Icons.CHAT_BUBBLE_OUTLINE,
                size=64,
                color=ft.colors.GREY_400
            ),
            ft.Text(
                t["no_rooms"],
                size=16,
                color=ft.colors.GREY_600,
                text_align="center"
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
        padding=40
    ) if not persistent_rooms and not temporary_rooms else ft.Container()

    return ft.View(
        "/room_list",
        controls=[
            # 헤더
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=on_back) if on_back else ft.Container(),
                ft.Text(t["title"], size=title_size, weight=ft.FontWeight.BOLD, color=get_header_text_color(page)),
            ], alignment=ft.MainAxisAlignment.START, spacing=8),

            # 채팅방 목록
            ft.Container(
                content=ft.Column([
                    ft.Text(t["subtitle"], size=subtitle_size, color=ft.colors.GREY_600),
                    persistent_section,
                    temporary_section,
                    empty_message
                ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=container_width,
                padding=20
            )
        ],
        bgcolor=ft.LinearGradient(["#F1F5FF", "#E0E7FF"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right),
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
