import flet as ft
import os
from config import GEMINI_API_KEY, MODEL_NAME
from flet import Column, Switch
import time
from firebase_admin import db
import uuid
import threading
import google.generativeai as genai
import atexit
import re

IS_SERVER = os.environ.get("CLOUDTYPE") == "1"

# 부적절한 단어 필터링 (욕설, 스팸 등)
INAPPROPRIATE_WORDS = [
    # 한국어 욕설
    "씨발", "개새끼", "병신", "미친", "바보", "멍청이", "등신", "개자식", "새끼", "좆", "보지", "자지",
    # 영어 욕설
    "fuck", "shit", "bitch", "asshole", "dick", "pussy", "cock", "cunt", "whore", "slut",
    # 스팸 단어
    "광고", "홍보", "판매", "구매", "돈", "돈벌이", "수익", "투자", "부업", "부자", "돈많은",
    # 반복 스팸
    "ㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋ", "ㅎㅎㅎㅎㅎㅎㅎㅎㅎㅎ", "!!!!!", "?????", "ㅠㅠㅠㅠㅠㅠㅠㅠㅠㅠ"
]

def is_inappropriate_message(message):
    """부적절한 메시지인지 확인"""
    message_lower = message.lower()
    
    # 부적절한 단어 포함 여부 확인
    for word in INAPPROPRIATE_WORDS:
        if word in message_lower:
            return True, f"부적절한 단어가 포함되어 있습니다: {word}"
    
    # 반복 문자 체크 (같은 문자 5번 이상 반복)
    repeated_chars = re.findall(r'(.)\1{4,}', message)
    if repeated_chars:
        return True, "반복되는 문자가 너무 많습니다"
    
    # 메시지 길이 체크 (너무 긴 메시지)
    if len(message) > 500:
        return True, "메시지가 너무 깁니다 (500자 제한)"
    
    # URL 스팸 체크
    url_count = message.count('http') + message.count('www')
    if url_count > 2:
        return True, "URL이 너무 많습니다"
    
    return False, ""

def filter_message(message):
    """메시지 필터링 (부적절한 단어 마스킹)"""
    filtered_message = message
    for word in INAPPROPRIATE_WORDS:
        if word.lower() in filtered_message.lower():
            # 부적절한 단어를 *로 마스킹
            import re
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            filtered_message = pattern.sub('*' * len(word), filtered_message)
    
    return filtered_message

# Gemini 기반 번역 함수 (예시: 실제 구현 필요)
def translate_message(text, target_lang):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        # 언어 코드 → 영어 언어명 매핑
        lang_map = {
            "en": "English", "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "zh-TW": "Traditional Chinese", "id": "Indonesian", "vi": "Vietnamese", "fr": "French", "de": "German", "th": "Thai", "uz": "Uzbek", "ne": "Nepali", "tet": "Tetum", "lo": "Lao", "mn": "Mongolian", "my": "Burmese", "bn": "Bengali", "si": "Sinhala", "km": "Khmer", "ky": "Kyrgyz", "ur": "Urdu"
        }
        target_lang_name = lang_map.get(target_lang, target_lang)
        prompt = f"Translate the following text to {target_lang_name} and return only the translation.\n{text}"
        response = model.generate_content(prompt, generation_config={"max_output_tokens": 512, "temperature": 0.2})
        return response.text.strip()
    except Exception as e:
        return f"[번역 오류] {e}"

# 언어 코드에 따른 전체 언어 이름 매핑
LANG_NAME_MAP = {
    "ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어",
    "fr": "프랑스어", "de": "독일어", "th": "태국어", "vi": "베트남어",
    "zh-TW": "대만어", "zh-HK": "홍콩어", "id": "인도네시아어",
    "zh-SG": "싱가포르 중국어", "en-SG": "싱가포르 영어", "ms-SG": "싱가포르 말레이어", "ta-SG": "싱가포르 타밀어",
    "uz": "우즈베키스탄어", "ne": "네팔어", "tet": "동티모르어", "lo": "라오스어",
    "mn": "몽골어", "my": "미얀마어", "bn": "방글라데시어", "si": "스리랑카어",
    "km": "캄보디아어", "ky": "키르기스스탄어", "ur": "파키스탄어"
}

# RAG 가이드 텍스트 다국어 사전 (상세 구조)
RAG_GUIDE_TEXTS = {
    "ko": {
        "title": "다문화가족 한국생활안내",
        "info": "다음과 같은 정보를 질문할 수 있습니다:",
        "items": [
            "🏥 병원, 약국 이용 방법",
            "🏦 은행, 우체국, 관공서 이용",
            "🚌 교통수단 이용 (버스, 지하철, 기차)",
            "🚗 운전면허, 자가용, 택시 이용",
            "🏠 집 구하기",
            "📱 핸드폰 사용하기",
            "🗑️ 쓰레기 버리기 (종량제, 분리배출)",
            "🆔 외국인등록증 신청, 체류기간 연장"
        ],
        "example_title": "질문 예시:",
        "examples": [
            "• 외국인등록을 하려면 어디로 가요?",
            "• 체류기간이 3개월 남았는데 연장하려면 어떻게 해요?",
            "• 외국인은 핸드폰을 어떻게 사용하나요?",
            "• 전셋집이 뭐예요?",
            "• 공인중개사무소가 뭐죠?",
            "• 집 계약서는 어떻게 쓰면 되나요?",
            "• 대한민국 운전면허증을 받는 과정은?",
            "• 쓰레기 봉투는 어디서 사나요?",
            "• 쓰레기 버리는 방법은요?",
            "• 몸이 아픈데 어떡하죠?",
            "• 병원에 갈 때 필요한 건강보험증이 뭐죠?",
            "• 한의원은 일반병원과 다른가요?",
            "• 처방전이 없는데 어떻게 하나요?",
            "• 은행계좌는 어떻게 만들어요?",
            "• 외국에 물건을 보내고 싶은데 어떻게 하죠?",
            "• 24시간 콜센터 번호는 어떻게 되죠?",
            "• 긴급전화 번호는 뭐에요?",
            "• 한국어를 배울 수 있는 방법은요?"
        ],
        "input_hint": "아래에 질문을 입력해보세요! 💬"
    },
    "en": {
        "title": "Korean Life Guide for Multicultural Families",
        "info": "You can ask about the following topics:",
        "items": [
            "🏥 How to use hospitals and pharmacies",
            "🏦 How to use banks, post offices, government offices",
            "🚌 How to use public transport (bus, subway, train)",
            "🚗 Driver's license, private car, taxi",
            "🏠 Finding a house",
            "📱 Using a mobile phone",
            "🗑️ How to dispose of trash (volume-based, recycling)",
            "🆔 Alien registration, extension of stay"
        ],
        "example_title": "Example questions:",
        "examples": [
            "• Where do I go to register as a foreigner?",
            "• My stay period expires in 3 months, how do I extend it?",
            "• How do foreigners use mobile phones?",
            "• What is jeonse (deposit-based housing)?",
            "• What is a real estate agency?",
            "• How do I write a housing contract?",
            "• What is the process for getting a Korean driver's license?",
            "• Where do I buy trash bags?",
            "• How do I dispose of trash?",
            "• I'm sick, what should I do?",
            "• What is health insurance card needed for hospitals?",
            "• Is oriental medicine different from regular hospitals?",
            "• What if I don't have a prescription?",
            "• How do I open a bank account?",
            "• How do I send things abroad?",
            "• What are the 24-hour call center numbers?",
            "• What are the emergency numbers?",
            "• How can I learn Korean?"
        ],
        "input_hint": "Type your question below! 💬"
    },
    "ja": {
        "title": "多文化家族のための韓国生活ガイド",
        "info": "以下のトピックについて質問できます:",
        "items": [
            "🏥 病院、薬局の利用方法",
            "🏦 銀行、郵便局、政府機関の利用",
            "🚌 公共交通機関の利用（バス、地下鉄、電車）",
            "🚗 運転免許、自家用車、タクシー",
            "🏠 家探し",
            "📱 携帯電話の使用",
            "🗑️ ゴミの捨て方（従量制、リサイクル）",
            "🆔 外国人登録、滞在期間延長"
        ],
        "example_title": "質問例:",
        "examples": [
            "• 外国人登録はどこで行いますか？",
            "• 滞在期間が3ヶ月残っていますが、延長するにはどうすればいいですか？",
            "• 外国人は携帯電話をどのように使用しますか？",
            "• 全税（保証金ベースの住宅）とは何ですか？",
            "• 不動産会社とは何ですか？",
            "• 住宅契約書はどのように書けばいいですか？",
            "• 韓国の運転免許を取得する手続きは？",
            "• ゴミ袋はどこで買えますか？",
            "• ゴミの捨て方は？",
            "• 体調が悪いのですが、どうすればいいですか？",
            "• 病院に行く際に必要な健康保険証とは？",
            "• 韓医院は一般병원と違いますか？",
            "• 処方箋がない場合はどうすればいいですか？",
            "• 銀行口座はどのように開設しますか？",
            "• 海外に物を送りたいのですが、どうすればいいですか？",
            "• 24時間コールセンターの番号は？",
            "• 緊急전화番号は何ですか？",
            "• 韓国語を学ぶ方法は？"
        ],
        "input_hint": "下に質問を入力してください！💬"
    },
    "zh": {
        "title": "多元文化家庭韩国生活指南",
        "info": "您可以询问以下主题:",
        "items": [
            "🏥 如何使用医院和药房",
            "🏦 如何使用银行、邮局、政府机关",
            "🚌 如何使用公共交通（公交车、地铁、火车）",
            "🚗 驾照、私家车、出租车",
            "🏠 找房子",
            "📱 使用手机",
            "🗑️ 如何丢弃垃圾（按量收费、回收）",
            "🆔 外国人登记、延长停留时间"
        ],
        "example_title": "问题示例:",
        "examples": [
            "• 我要去哪里办理外国人登记？",
            "• 我的停留期限还剩3个月，如何延长？",
            "• 外国人如何使用手机？",
            "• 什么是全租房？",
            "• 什么是房地产中介？",
            "• 我该如何写房屋合约？",
            "• 取得韩国驾照的流程是什么？",
            "• 我在哪里买垃圾袋？",
            "• 我该如何丢垃圾？",
            "• 我生病了该怎么办？",
            "• 去医院需要的健康保险卡是什么？",
            "• 韩医院和一般医院有什么不同？",
            "• 如果没有处方怎么办？",
            "• 我该如何开银行账户？",
            "• 我该如何寄东西到国外？",
            "• 24小时客服电话是多少？",
            "• 紧急电话号码是什么？",
            "• 我该如何学韩文？"
        ],
        "input_hint": "请在下方输入您的问题！💬"
    },
    "zh-TW": {
        "title": "多元文化家庭韓國生活指南",
        "info": "您可以詢問以下主題:",
        "items": [
            "🏥 如何使用醫院和藥局",
            "🏦 如何使用銀行、郵局、政府機關",
            "🚌 如何搭乘大眾運輸（公車、地鐵、火車）",
            "🚗 駕照、私家車、計程車",
            "🏠 找房子",
            "📱 使用手機",
            "🗑️ 如何丟垃圾（按量收費、回收）",
            "🆔 外國人登記、延長停留時間"
        ],
        "example_title": "問題範例:",
        "examples": [
            "• 我要去哪裡辦理外國人登記？",
            "• 我的停留期限還剩3個月，如何延長？",
            "• 外國人如何使用手機？",
            "• 什麽是全租房？",
            "• 什麽是房地產仲介？",
            "• 我該如何寫房屋合約？",
            "• 取得韓國駕照的流程是什麽？",
            "• 我在哪裡買垃圾袋？",
            "• 我該如何丟垃圾？",
            "• 我生病了該怎麽辦？",
            "• 去醫院需要的健康保險卡是什麽？",
            "• 韓醫院和一般醫院有什麽不同？",
            "• 如果沒有處方怎麽辦？",
            "• 我該如何開銀行帳戶？",
            "• 我該如何寄東西到國外？",
            "• 24小時客服電話是多少？",
            "• 緊急電話號碼是什麽？",
            "• 我該如何學韓文？"
        ],
        "input_hint": "請在下方輸入您的問題！💬"
    },
    "id": {
        "title": "Panduan Hidup di Korea untuk Keluarga Multikultural",
        "info": "Anda dapat bertanya tentang topik berikut:",
        "items": [
            "🏥 Cara menggunakan rumah sakit dan apotek",
            "🏦 Cara menggunakan bank, kantor pos, kantor pemerintah",
            "🚌 Cara menggunakan transportasi umum (bus, subway, kereta)",
            "🚗 SIM, mobil pribadi, taksi",
            "🏠 Mencari rumah",
            "📱 Menggunakan ponsel",
            "🗑️ Cara membuang sampah (berdasarkan volume, daur ulang)",
            "🆔 Pendaftaran orang asing, perpanjangan masa tinggal"
        ],
        "example_title": "Contoh pertanyaan:",
        "examples": [
            "• Ke mana saya harus pergi untuk mendaftar sebagai orang asing?",
            "• Masa tinggal saya tersisa 3 bulan, bagaimana cara memperpanjangnya?",
            "• Bagaimana orang asing menggunakan ponsel?",
            "• Apa itu jeonse (rumah sewa deposit)?",
            "• Apa itu agen real estat?",
            "• Bagaimana cara menulis kontrak rumah?",
            "• Apa proses mendapatkan SIM Korea?",
            "• Di mana saya membeli kantong sampah?",
            "• Bagaimana cara membuang sampah?",
            "• Saya sakit, apa yang harus saya lakukan?",
            "• Apa itu kartu asuransi kesehatan untuk rumah sakit?",
            "• Apakah pengobatan oriental berbeda dengan rumah sakit biasa?",
            "• Bagaimana jika saya tidak punya resep?",
            "• Bagaimana cara membuka rekening bank?",
            "• Bagaimana cara mengirim barang ke luar negeri?",
            "• Berapa nomor call center 24 jam?",
            "• Berapa nomor darurat?",
            "• Bagaimana cara belajar bahasa Korea?"
        ],
        "input_hint": "Tulis pertanyaan Anda di bawah ini! 💬"
    },
    "vi": {
        "title": "Hướng dẫn cuộc sống Hàn Quốc cho gia đình đa văn hóa",
        "info": "Bạn có thể hỏi về các chủ đề sau:",
        "items": [
            "🏥 Cách sử dụng bệnh viện và nhà thuốc",
            "🏦 Cách sử dụng ngân hàng, bưu điện, cơ quan chính phủ",
            "🚌 Cách sử dụng phương tiện công cộng (xe buýt, tàu điện ngầm, tàu)",
            "🚗 Bằng lái xe, xe riêng, taxi",
            "🏠 Tìm nhà",
            "📱 Sử dụng điện thoại di động",
            "🗑️ Cách vứt rác (theo thể tích, tái chế)",
            "🆔 Đăng ký người nước ngoài, gia hạn thời gian lưu trú"
        ],
        "example_title": "Ví dụ câu hỏi:",
        "examples": [
            "• Tôi đi đâu để đăng ký người nước ngoài?",
            "• Thời gian lưu trú của tôi còn lại 3 tháng, làm thế nào để gia hạn?",
            "• Người nước ngoài sử dụng điện thoại di động như thế nào?",
            "• Jeonse (nhà ở theo tiền đặt cọc) là gì?",
            "• Công ty bất động sản là gì?",
            "• Tôi viết hợp đồng nhà như thế nào?",
            "• Quy trình lấy bằng lái xe Hàn Quốc là gì?",
            "• Tôi mua túi rác ở đâu?",
            "• Tôi vứt rác như thế nào?",
            "• Tôi bị bệnh, tôi nên làm gì?",
            "• Thẻ bảo hiểm y tế cần thiết cho bệnh viện là gì?",
            "• Y học cổ truyền có khác với bệnh viện thường không?",
            "• Nếu tôi không có đơn thuốc thì sao?",
            "• Tôi mở tài khoản ngân hàng như thế nào?",
            "• Tôi gửi đồ ra nước ngoài như thế nào?",
            "• Số điện thoại trung tâm cuộc gọi 24 giờ là gì?",
            "• Số điện thoại khẩn cấp là gì?",
            "• Tôi có thể học tiếng Hàn như thế nào?"
        ],
        "input_hint": "Nhập câu hỏi của bạn bên dưới! 💬"
    },
    "fr": {
        "title": "Guide de vie en Corée pour familles multiculturelles",
        "info": "Vous pouvez poser des questions sur les sujets suivants :",
        "items": [
            "🏥 Comment utiliser les hôpitaux et pharmacies",
            "🏦 Comment utiliser les banques, bureaux de poste, bureaux gouvernementaux",
            "🚌 Comment utiliser les transports publics (bus, métro, train)",
            "🚗 Permis de conduire, voiture privée, taxi",
            "🏠 Trouver une maison",
            "📱 Utiliser un téléphone portable",
            "🗑️ Comment jeter les déchets (basé sur le volume, recyclage)",
            "🆔 Enregistrement des étrangers, prolongation du séjour"
        ],
        "example_title": "Exemples de questions :",
        "examples": [
            "• Où dois-je aller pour m'enregistrer en tant qu'étranger ?",
            "• Ma période de séjour expire dans 3 mois, comment la prolonger ?",
            "• Comment les étrangers utilisent-ils les téléphones portables ?",
            "• Qu'est-ce que le jeonse (logement basé sur un dépôt) ?",
            "• Qu'est-ce qu'une agence immobilière ?",
            "• Comment rédiger un contrat de logement ?",
            "• Quel est le processus pour obtenir un permis de conduire coréen ?",
            "• Où acheter des sacs poubelle ?",
            "• Comment jeter les déchets ?",
            "• Je suis malade, que dois-je faire ?",
            "• Qu'est-ce que la carte d'assurance maladie pour les hôpitaux ?",
            "• La médecine orientale est-elle différente des hôpitaux ordinaires ?",
            "• Que faire si je n'ai pas d'ordonnance ?",
            "• Comment ouvrir un compte bancaire ?",
            "• Comment envoyer des objets à l'étranger ?",
            "• Quels sont les numéros de centre d'appels 24h ?",
            "• Quels sont les numéros d'urgence ?",
            "• Comment puis-je apprendre le coréen ?"
        ],
        "input_hint": "Tapez votre question ci-dessous ! 💬"
    },
    "de": {
        "title": "Leitfaden für das Leben in Korea für multikulturelle Familien",
        "info": "Sie können Fragen zu folgenden Themen stellen:",
        "items": [
            "🏥 Wie man Krankenhäuser und Apotheken nutzt",
            "🏦 Wie man Banken, Postämter, Regierungsbüros nutzt",
            "🚌 Wie man öffentliche Verkehrsmittel nutzt (Bus, U-Bahn, Zug)",
            "🚗 Führerschein, Privatauto, Taxi",
            "🏠 Haus finden",
            "📱 Mobiltelefon nutzen",
            "🗑️ Wie man Müll entsorgt (volumenbasiert, Recycling)",
            "🆔 Ausländerregistrierung, Aufenthaltsverlängerung"
        ],
        "example_title": "Beispielfragen:",
        "examples": [
            "• Wo muss ich mich als Ausländer registrieren?",
            "• Mein Aufenthalt läuft in 3 Monaten ab, wie verlängere ich ihn?",
            "• Wie nutzen Ausländer Mobiltelefone?",
            "• Was ist Jeonse (Mietwohnung mit Kaution)?",
            "• Was ist eine Immobilienagentur?",
            "• Wie schreibe ich einen Wohnungsvertrag?",
            "• Was ist der Prozess für einen koreanischen Führerschein?",
            "• Wo kaufe ich Müllbeutel?",
            "• Wie entsorge ich Müll?",
            "• Ich bin krank, was soll ich tun?",
            "• Was ist die Krankenversicherungskarte für Krankenhäuser?",
            "• Ist orientalische Medizin anders als normale Krankenhäuser?",
            "• Was, wenn ich kein Rezept habe?",
            "• Wie eröffne ich ein Bankkonto?",
            "• Wie sende ich Dinge ins Ausland?",
            "• Was sind die 24-Stunden-Callcenter-Nummern?",
            "• Was sind die Notrufnummern?",
            "• Wie kann ich Koreanisch lernen?"
        ],
        "input_hint": "Geben Sie Ihre Frage unten ein! 💬"
    },
    "th": {
        "title": "คู่มือการใช้ชีวิตในเกาหลีสำหรับครอบครัวพหุวัฒนธรรม",
        "info": "คุณสามารถถามเกี่ยวกับหัวข้อต่อไปนี้:",
        "items": [
            "🏥 วิธีใช้โรงพยาบาลและร้านขายยา",
            "🏦 วิธีใช้ธนาคาร ที่ทำการไปรษณีย์ สำนักงานรัฐบาล",
            "🚌 วิธีใช้ระบบขนส่งสาธารณะ (รถบัส รถไฟใต้ดิน รถไฟ)",
            "🚗 ใบขับขี่ รถส่วนตัว แท็กซี่",
            "🏠 หาบ้าน",
            "📱 ใช้โทรศัพท์มือถือ",
            "🗑️ วิธีทิ้งขยะ (ตามปริมาณ การรีไซเคิล)",
            "🆔 การลงทะเบียนชาวต่างชาติ การขยายเวลาพำนัก"
        ],
        "example_title": "ตัวอย่างคำถาม:",
        "examples": [
            "• ฉันจะไปลงทะเบียนเป็นชาวต่างชาติที่ไหน?",
            "• ระยะเวลาพำนักของฉันเหลือ 3 เดือน จะขยายอย่างไร?",
            "• ชาวต่างชาติใช้โทรศัพท์มือถืออย่างไร?",
            "• Jeonse (บ้านเช่าตามเงินมัดจำ) คืออะไร?",
            "• บริษัทอสังหาริมทรัพย์คืออะไร?",
            "• ฉันเขียนสัญญาบ้านอย่างไร?",
            "• กระบวนการขอใบขับขี่เกาหลีคืออะไร?",
            "• ฉันซื้อถุงขยะที่ไหน?",
            "• ฉันทิ้งขยะอย่างไร?",
            "• ฉันป่วย ฉันควรทำอย่างไร?",
            "• บัตรประกันสุขภาพที่จำเป็นสำหรับโรงพยาบาลคืออะไร?",
            "• การแพทย์แผนตะวันออกแตกต่างจากโรงพยาบาลทั่วไปหรือไม่?",
            "• ถ้าฉันไม่มีใบสั่งยาล่ะ?",
            "• ฉันเปิดบัญชีธนาคารอย่างไร?",
            "• ฉันส่งของไปต่างประเทศอย่างไร?",
            "• เบอร์ศูนย์บริการ 24 ชั่วโมงคืออะไร?",
            "• เบอร์ฉุกเฉินคืออะไร?",
            "• ฉันจะเรียนภาษาเกาหลีได้อย่างไร?"
        ],
        "input_hint": "พิมพ์คำถามของคุณด้านล่าง! 💬"
    },
    "uz": {
        "title": "Чет эл ишчилари ҳуқуқларини ҳимоя қилиш бўйича йўриқнома",
        "info": "Қуйидаги ҳуқуқ ҳимояси мавзулари ҳақида савол бера оласиз:",
        "items": [
            "💰 Иш ҳақининг қолдирилиши ва тўланиши",
            "🚫 Нодўст ундатиш ва ундатиш огоҳлантириши",
            "🏥 Иш ҳалокати ва иш билан боглиқ жароҳатлар",
            "🚨 Иш жойидаги жинсий таъқиб ва жинсий зўравонлик",
            "📞 Чет элликлар учун алоҳида суғурта ва маслаҳат",
            "📱 Шошилинч алока ва маслаҳат агентликлари",
            "⚖️ Меҳнат қонунлари ва ҳуқуқ ҳимояси жараёни"
        ],
        "example_title": "Савол мисоллари:",
        "examples": [
            "• Менинг иш ҳақим қолдирилган",
            "• Мен нодўст ундатилдим",
            "• Мен ишда жароҳатландим",
            "• Мен иш жойида жинсий таъқибга дуч келдим",
            "• Мен жинсий зўравонлик ёки таъқибга дуч келдим",
            "• Чет элликлар учун қандай суғурта мавжуд?",
            "• Кореяда қайси телефон рақамларини билишим керак?"
        ],
        "input_hint": "Қуйидаги ҳуқуқ ҳимояси саволингизни киритинг! 💬"
    },
    "ne": {
        "title": "विदेशी श्रमिक अधिकार संरक्षण गाइड",
        "info": "तपाईं निम्न अधिकार संरक्षण विषयहरूको बारेमा सोध्न सक्नुहुन्छ:",
        "items": [
            "💰 तलब रोक्ने र भुक्तानी",
            "🚫 अन्यायपूर्ण बर्खास्त र बर्खास्त सूचना",
            "🏥 औद्योगिक दुर्घटना र काम सम्बन्धित चोट",
            "🚨 कार्यस्थलमा यौन उत्पीडन र यौन हमला",
            "📞 विदेशीहरूको लागि विशेष बीमा र परामर्श",
            "📱 आकस्मिक सम्पर्क र परामर्श एजेन्सीहरू",
            "⚖️ श्रम कानून र अधिकार संरक्षण प्रक्रिया"
        ],
        "example_title": "प्रश्नहरूको उदाहरण:",
        "examples": [
            "• मेरो तलब रोकिएको छ",
            "• म अन्यायपूर्ण रूपमा बर्खास्त भएको थिएँ",
            "• म काममा चोट पुगेको थिएँ",
            "• म कार्यस्थलमा यौन उत्पीडनको अनुभव गरेको थिएँ",
            "• म यौन हमला वा उत्पीडनको शिकार भएको थिएँ",
            "• विदेशीहरूको लागि कुन बीमा उपलब्ध छ?",
            "• कोरियामा कुन फोन नम्बरहरू थाहा पाउनु पर्छ?"
        ],
        "input_hint": "तल आफ्नो अधिकार संरक्षण प्रश्न लेख्नुहोस्! 💬"
    },
    "tet": {
        "title": "Gia ba Knaar Direitu Trabalhadór Estranjeiru",
        "info": "Ita bele husu kona-ba topiku protesaun direitu sira ne'e:",
        "items": [
            "💰 Saláriu atrasu no pagamentu saláriu",
            "🚫 Despedida injusta no avizu despedida",
            "🏥 Asidente trabálhu no lesaun relasiona ho servisu",
            "🚨 Asédiu seksuál no atake seksuál iha fatin servisu",
            "📞 Seguru no konsellu espesiál ba estranjeiru",
            "📱 Kontaktu emergénsia no ajénsia konsellu",
            "⚖️ Lei trabálhu no prosedimentu protesaun direitu"
        ],
        "example_title": "Ezemplu pergunta sira:",
        "examples": [
            "• Ha'u-nia saláriu hetan atrasu",
            "• Ha'u hetan despedida injusta",
            "• Ha'u hetan lesaun iha servisu",
            "• Ha'u esperiénsia asédiu seksuál iha fatin servisu",
            "• Ha'u hetan atake ka asédiu seksuál",
            "• Seguru saida mak disponível ba estranjeiru?",
            "• Numeru telefone saida mak ha'u tenke hatene iha Korea?"
        ],
        "input_hint": "Hakerek ita-nia pergunta protesaun direitu iha okos! 💬"
    },
    "lo": {
        "title": "ຄູ່ມືການປົກປ້ອງສິດຂອງຄົນງານຕ່າງປະເທດ",
        "info": "ທ່ານສາມາດຖາມກ່ຽວກັບຫົວຂໍ້ການປົກປ້ອງສິດດັ່ງນີ້:",
        "items": [
            "💰 ຄ່າແຮງງານຄ້າງຊຳແລະການຈ່າຍຄ່າແຮງງານ",
            "🚫 ການໄລ່ອອກທີ່ບໍ່ຍຸດຕິທຳແລະການແຈ້ງໄລ່ອອກ",
            "🏥 ອຸປະຕິເຫດທາງອຸດສາຫະກຳແລະການບາດເຈັບທີ່ກ່ຽວຂ້ອງກັບການເຮັດວຽກ",
            "🚨 ການລະເມີດທາງເພດແລະການຮຸກຮານທາງເພດໃນສະຖານທີ່ເຮັດວຽກ",
            "📞 ການປະກັນໄພແລະການໃຫ້ຄຳປຶກສາສຳລັບຄົນຕ່າງປະເທດ",
            "📱 ການຕິດຕໍ່ສຸກເສີນແລະອົງກອນໃຫ້ຄຳປຶກສາ",
            "⚖️ ກົດໝາຍແຮງງານແລະຂັ້ນຕອນການປົກປ້ອງສິດ"
        ],
        "example_title": "ຕົວຢ່າງຄຳຖາມ:",
        "examples": [
            "• ຄ່າແຮງງານຂອງຂ້ອຍຖືກຄ້າງຊຳ",
            "• ຂ້ອຍຖືກໄລ່ອອກຢ່າງບໍ່ຍຸດຕິທຳ",
            "• ຂ້ອຍບາດເຈັບໃນຂະນະເຮັດວຽກ",
            "• ຂ້ອຍປະສົບກັບການລະເມີດທາງເພດໃນສະຖານທີ່ເຮັດວຽກ",
            "• ຂ້ອຍປະສົບກັບການຮຸກຮານຫຼືການລະເມີດທາງເພດ",
            "• ການປະກັນໄພໃດທີ່ມີສຳລັບຄົນຕ່າງປະເທດ?",
            "• ເບີໂທລະສັບໃດທີ່ຂ້ອຍຄວນຮູ້ໃນເກົາຫຼີ?"
        ],
        "input_hint": "ຂຽນຄຳຖາມການປົກປ້ອງສິດຂອງທ່ານຂ້າງລຸ່ມ! 💬"
    },
    "mn": {
        "title": "Гадаад хөдөлмөрчдийн эрхийн хамгаалалтын заавар",
        "info": "Та дараах эрхийн хамгаалалтын сэдвүүдийн талаар асуулт тавьж болно:",
        "items": [
            "💰 Цалингийн хойшлуулалт ба төлбөр",
            "🚫 Шударга бус халах ба халах мэдэгдэл",
            "🏥 Аж үйлдвэрийн осол ба ажлын холбоотой гэмтэл",
            "🚨 Ажлын байран дээрх хүйсийн хавчлага ба хүйсийн халдлага",
            "📞 Гадаад хүмүүст зориулсан даатгал ба зөвлөгөө",
            "📱 Яаралтын холбоо ба зөвлөгөөний агентлагууд",
            "⚖️ Хөдөлмөрийн хууль ба эрхийн хамгаалалтын журам"
        ],
        "example_title": "Асуултын жишээ:",
        "examples": [
            "• Миний цалин хойшлогдсон",
            "• Би шударга бус байдлаар халсан",
            "• Би ажил дээр гэмтсэн",
            "• Би ажлын байран дээр хүйсийн хавчлагад өртсөн",
            "• Би хүйсийн халдлага эсвэл хавчлагад өртсөн",
            "• Гадаад хүмүүст ямар даатгал боломжтой вэ?",
            "• Солонгос улсад ямар утасны дугаарыг мэдэх ёстой вэ?"
        ],
        "input_hint": "Доорх эрхийн хамгаалалтын асуултаа бичнэ үү! 💬"
    },
    "my": {
        "title": "နိုင်ငံခြားလုပ်သားများ အခွင့်အရေး ကာကွယ်ရေး လမ်းညွှန်",
        "info": "အောက်ပါ အခွင့်အရေး ကာကွယ်ရေး ခေါင်းစဉ်များအကြောင်း မေးခွန်းများ မေးနိုင်ပါသည်:",
        "items": [
            "💰 လုပ်ခ ကြွေးကြော်ခြင်းနှင့် လုပ်ခ ပေးချေခြင်း",
            "🚫 မတရား ထုတ်ပယ်ခြင်းနှင့် ထုတ်ပယ်ခြင်း အကြောင်းကြားချက်",
            "🏥 စက်မှုလုပ်ငန်း မတော်တဆမှုနှင့် အလုပ်နှင့်ဆိုင်သော ဒဏ်ရာ",
            "🚨 အလုပ်ခွင်တွင် လိင်ပိုင်းဆိုင်ရာ နှောင့်ယှက်မှုနှင့် လိင်ပိုင်းဆိုင်ရာ စော်ကားမှု",
            "📞 နိုင်ငံခြားသားများအတွက် အထူး အာမခံနှင့် အကြံပေးခြင်း",
            "📱 အရေးပေါ် ဆက်သွယ်ရေးနှင့် အကြံပေးခြင်း အေဂျင်စီများ",
            "⚖️ အလုပ်သမား ဥပဒေများနှင့် အခွင့်အရေး ကာကွယ်ရေး လုပ်ငန်းစဉ်"
        ],
        "example_title": "မေးခွန်း ဥပမာများ:",
        "examples": [
            "• ကျွန်ုပ်၏ လုပ်ခ ကြွေးကြော်ခံရသည်",
            "• ကျွန်ုပ် မတရားစွာ ထုတ်ပယ်ခံရသည်",
            "• ကျွန်ုပ် အလုပ်တွင် ဒဏ်ရာရခဲ့သည်",
            "• ကျွန်ုပ် အလုပ်ခွင်တွင် လိင်ပိုင်းဆိုင်ရာ နှောင့်ယှက်မှု ကြုံတွေ့ခဲ့သည်",
            "• ကျွန်ုပ် လိင်ပိုင်းဆိုင်ရာ စော်ကားမှု သို့မဟုတ် နှောင့်ယှက်မှု ခံရသည်",
            "• နိုင်ငံခြားသားများအတွက် မည်သည့် အာမခံ ရရှိနိုင်သနည်း?",
            "• ကိုရီးယားတွင် မည်သည့် ဖုန်းနံပါတ်များ သိထားသင့်သနည်း?"
        ],
        "input_hint": "အောက်တွင် သင့် အခွင့်အရေး ကာကွယ်ရေး မေးခွန်းကို ရေးပါ! 💬"
    },
    "bn": {
        "title": "বিদেশি শ্রমিক অধিকার সুরক্ষা গাইড",
        "info": "আপনি নিম্নলিখিত অধিকার সুরক্ষা বিষয়গুলি সম্পর্কে জিজ্ঞাসা করতে পারেন:",
        "items": [
            "💰 মজুরি বকেয়া এবং মজুরি প্রদান",
            "🚫 অন্যায় বরখাস্ত এবং বরখাস্তের নোটিশ",
            "🏥 শিল্প দুর্ঘটনা এবং কাজ সম্পর্কিত আঘাত",
            "🚨 কর্মক্ষেত্রে যৌন হয়রানি এবং যৌন নিপীড়ন",
            "📞 বিদেশিদের জন্য বিশেষ বীমা এবং পরামর্শ",
            "📱 জরুরি যোগাযোগ এবং পরামর্শ সংস্থা",
            "⚖️ শ্রম আইন এবং অধিকার সুরক্ষা প্রক্রিয়া"
        ],
        "example_title": "প্রশ্নের উদাহরণ:",
        "examples": [
            "• আমার মজুরি বকেয়া রয়েছে",
            "• আমি অন্যায়ভাবে বরখাস্ত হয়েছি",
            "• আমি কাজে আহত হয়েছি",
            "• আমি কর্মক্ষেত্রে যৌন হয়রানির শিকার হয়েছি",
            "• আমি যৌন নিপীড়ন বা হয়রানির শিকার হয়েছি",
            "• বিদেশিদের জন্য কী ধরনের বীমা পাওয়া যায়?",
            "• কোরিয়ায় কোন ফোন নম্বরগুলি জানা উচিত?"
        ],
        "input_hint": "নীচে আপনার অধিকার সুরক্ষা প্রশ্ন লিখুন! 💬"
    },
    "si": {
        "title": "විදේශීය කම්කරුවන්ගේ අයිතිවාසිකම් ආරක්ෂා කිරීමේ මාර්ගෝපදේශය",
        "info": "ඔබට පහත අයිතිවාසිකම් ආරක්ෂා කිරීමේ මාතෘකා ගැන ප්‍රශ්න අසන්න පුළුවන්:",
        "items": [
            "💰 වැටුප් ණය සහ වැටුප් ගෙවීම",
            "🚫 අයුතු ඉවත් කිරීම සහ ඉවත් කිරීමේ දැනුම්දීම",
            "🏥 කර්මාන්ත හානි සහ වැඩ සම්බන්ධ තුවාල",
            "🚨 වැඩ ස්ථානයේ ලිංගික හානි සහ ලිංගික පහර",
            "📞 විදේශීයයින් සඳහා විශේෂ රක්ෂණ සහ උපදේශන",
            "📱 හදිසි සම්බන්ධතා සහ උපදේශන ආයතන",
            "⚖️ ශ්‍රම නීති සහ අයිතිවාසිකම් ආරක්ෂා කිරීමේ ක්‍රියාවලිය"
        ],
        "example_title": "ප්‍රශ්න උදාහරණ:",
        "examples": [
            "• මගේ වැටුප් ණය වෙලා තියෙනවා",
            "• මම අයුතු ලෙස ඉවත් කරනවා",
            "• මම වැඩේදී තුවාල වෙනවා",
            "• මම වැඩ ස්ථානයේ ලිංගික හානි අත්විඳිනවා",
            "• මම ලිංගික පහර හෝ හානි අත්විඳිනවා",
            "• විදේශීයයින් සඳහා කුමන රක්ෂණ තියෙනවාද?",
            "• කොරියාවේ කුමන දුරකථන අංක දැනගන්න ඕනෑද?"
        ],
        "input_hint": "පහත ඔබේ අයිතිවාසිකම් ආරක්ෂා කිරීමේ ප්‍රශ්නය ලියන්න! 💬"
    },
    "km": {
        "title": "មគ្គុទ្ទេសក៍ការការពារសិទ្ធិរបស់កម្មករជាតិផ្សេង",
        "info": "អ្នកអាចសួរអំពីប្រធានបទការពារសិទ្ធិដូចខាងក្រោម:",
        "items": [
            "💰 ប្រាក់ខែជំពាក់និងការទូទាត់ប្រាក់ខែ",
            "🚫 ការដកចេញដោយមិនយុត្តិធម៌និងការជូនដំណឹងដកចេញ",
            "🏥 គ្រោះថ្នាក់ការងារនិងការរបួសដែលពាក់ព័ន្ធនឹងការងារ",
            "🚨 ការរំលោភផ្លូវភេទនិងការវាយប្រហារផ្លូវភេទនៅកន្លែងធ្វើការ",
            "📞 ការធានារ៉ាប់រងនិងការណែនាំសម្រាប់ជនជាតិផ្សេង",
            "📱 ការទាក់ទងអាសន្ននិងអង្គការណែនាំ",
            "⚖️ ច្បាប់ការងារនិងនីតិវិធីការពារសិទ្ធិ"
        ],
        "example_title": "ឧទាហរណ៍សំណួរ:",
        "examples": [
            "• ប្រាក់ខែរបស់ខ្ញុំត្រូវបានជំពាក់",
            "• ខ្ញុំត្រូវបានដកចេញដោយមិនយុត្តិធម៌",
            "• ខ្ញុំបានរបួសក្នុងពេលធ្វើការ",
            "• ខ្ញុំបានជួបការរំលោភផ្លូវភេទនៅកន្លែងធ្វើការ",
            "• ខ្ញុំបានជួបការវាយប្រហារឬរំលោភផ្លូវភេទ",
            "• ការធានារ៉ាប់រងអ្វីដែលមានសម្រាប់ជនជាតិផ្សេង?",
            "• លេខទូរស័ព្ទអ្វីដែលខ្ញុំគួរដឹងនៅកូរ៉េ?"
        ],
        "input_hint": "សូមសរសេរសំណួរការពារសិទ្ធិរបស់អ្នកខាងក្រោម! 💬"
    },
    "ky": {
        "title": "Чет эл жумушчуларынын укуктарын коргоо боюнча колдонмо",
        "info": "Төмөнкү укук коргоо темалары жөнүндө суроо беришиңиз мүмкүн:",
        "items": [
            "💰 Жумуш акысынын калтырылышы жана төлөнүшү",
            "🚫 Адилетсиз жумуштан келтирилиши жана келтирилиш жарыясы",
            "🏥 Өнөр жай кырсыгы жана жумуш менен байланыштуу жаракат",
            "🚨 Жумуш орундундагы жыныстык зомбулук жана жыныстык кол салуу",
            "📞 Чет элдиктер үчүн атайын камсыздандыруу жана кеңеш",
            "📱 Оор кырдаал байланышы жана кеңеш берүү мекемелери",
            "⚖️ Эмгек мыйзамдары жана укук коргоо процедурасы"
        ],
        "example_title": "Суроо мисалдары:",
        "examples": [
            "• Менинг жумуш акысым калтырылган",
            "• Мен адилетсиз түрдө жумуштан келтирилдим",
            "• Мен жумушта жаракат алдым",
            "• Мен жумуш орундунда жыныстык зомбулукка дуушар болдум",
            "• Мен жыныстык кол салуу же зомбулукка дуушар болдум",
            "• Чет элдиктер үчүн кандай камсыздандыруу бар?",
            "• Кореяда кайсы телефон номерилерин билишим керек?"
        ],
        "input_hint": "Төмөнкү укук коргоо сурооңузду жазыңыз! 💬"
    },
    "ur": {
        "title": "غیر ملکی مزدوروں کے حقوق کی حفاظت کی گائیڈ",
        "info": "آپ مندرجہ ذیل حقوق کی حفاظت کے موضوعات کے بارے میں پوچھ سکتے ہیں:",
        "items": [
            "💰 تنخواہ کی بکائی اور ادائیگی",
            "🚫 ناانصافی برطرفی اور برطرفی کی نوٹس",
            "🏥 صنعتی حادثات اور کام سے متعلق چوٹ",
            "🚨 کام کی جگہ پر جنسی ہراسانی اور جنسی حملہ",
            "📞 غیر ملکیوں کے لیے خصوصی انشورنس اور مشاورت",
            "📱 ہنگامی رابطے اور مشاورت کی ایجنسیاں",
            "⚖️ مزدوری کے قوانین اور حقوق کی حفاظت کے طریقہ کار"
        ],
        "example_title": "سوالات کی مثالیں:",
        "examples": [
            "• میری تنخواہ روک لی گئی ہے",
            "• مجھے ناانصافی سے برطرف کر دیا گیا",
            "• مجھے کام کے دوران چوٹ لگی",
            "• مجھے کام کی جگہ پر جنسی ہراسانی کا سامنا ہوا",
            "• مجھے جنسی حملہ یا ہراسانی کا سامنا ہوا",
            "• غیر ملکیوں کے لیے کیا انشورنس دستیاب ہے؟",
            "• کوریا میں کون سے فون نمبر جاننے چاہئیں؟"
        ],
        "input_hint": "ذیل میں اپنا حقوق کی حفاظت کا سوال لکھیں! 💬"
    }
}

# 언어별 마이크 안내 메시지
MIC_GUIDE_TEXTS = {
    "ko": "키보드의 마이크 버튼을 눌러 음성 입력을 사용하세요!",
    "en": "Tap the microphone button on your keyboard to use voice input!",
    "ja": "キーボードのマイクボタンを押して音声入力を使ってください！",
    "zh": "请点击键盘上的麦克风按钮进行语音输入！",
    "zh-TW": "請點擊鍵盤上的麥克風按鈕進行語音輸入！",
    "id": "Tekan tombol mikrofon di keyboard untuk menggunakan input suara!",
    "vi": "Nhấn nút micro trên bàn phím để nhập bằng giọng nói!",
    "fr": "Appuyez sur le bouton micro du clavier pour utiliser la saisie vocale !",
    "de": "Tippen Sie auf die Mikrofontaste Ihrer Tastatur, um die Spracheingabe zu verwenden!",
    "th": "แตะปุ่มไมโครโฟนบนแป้นพิมพ์เพื่อใช้การป้อนด้วยเสียง!"
}

# 외국인 근로자 권리구제 RAG 가이드 텍스트
FOREIGN_WORKER_GUIDE_TEXTS = {
    "ko": {
        "title": "외국인 근로자 권리구제 안내",
        "info": "다음과 같은 권리구제 관련 정보를 질문할 수 있습니다:",
        "items": [
            "💰 임금 체불 및 임금 지급",
            "🚫 부당해고 및 해고 예고",
            "🏥 산업재해 및 업무상 재해",
            "🚨 직장 내 성희롱 및 성폭력",
            "📞 외국인 전용 보험 및 상담",
            "📱 긴급 연락처 및 상담 기관",
            "⚖️ 노동법 및 권리구제 절차"
        ],
        "example_title": "질문 예시:",
        "examples": [
            "• 받아야 할 임금이 체불 되었어요",
            "• 부당하게 해고 되었어요",
            "• 일을 하다가 다쳤어요",
            "• 직장 내 성희롱을 당했어요",
            "• 성폭력이나 성추행을 당했어요",
            "• 외국인 전용보험은 어떤게 있나요?",
            "• 한국 체류시 꼭 알아둘 전화번호는요?"
        ],
        "input_hint": "권리구제 관련 질문을 입력해보세요! 💬"
    },
    "en": {
        "title": "Foreign Worker Rights Protection Guide",
        "info": "You can ask about the following rights protection topics:",
        "items": [
            "💰 Wage arrears and payment",
            "🚫 Unfair dismissal and dismissal notice",
            "🏥 Industrial accidents and work-related injuries",
            "🚨 Workplace sexual harassment and assault",
            "📞 Foreigner-only insurance and counseling",
            "📱 Emergency contacts and counseling agencies",
            "⚖️ Labor laws and rights protection procedures"
        ],
        "example_title": "Example questions:",
        "examples": [
            "• My wages have been withheld",
            "• I was unfairly dismissed",
            "• I got injured at work",
            "• I experienced sexual harassment at work",
            "• I was sexually assaulted or harassed",
            "• What insurance is available for foreigners?",
            "• What phone numbers should I know in Korea?"
        ],
        "input_hint": "Enter your rights protection question below! 💬"
    },
    "vi": {
        "title": "Hướng dẫn bảo vệ quyền lợi người lao động nước ngoài",
        "info": "Bạn có thể hỏi về các chủ đề bảo vệ quyền lợi sau:",
        "items": [
            "💰 Nợ lương và thanh toán lương",
            "🚫 Sa thải bất công và thông báo sa thải",
            "🏥 Tai nạn lao động và thương tích liên quan đến công việc",
            "🚨 Quấy rối tình dục và tấn công tình dục tại nơi làm việc",
            "📞 Bảo hiểm và tư vấn dành riêng cho người nước ngoài",
            "📱 Liên lạc khẩn cấp và cơ quan tư vấn",
            "⚖️ Luật lao động và thủ tục bảo vệ quyền lợi"
        ],
        "example_title": "Ví dụ câu hỏi:",
        "examples": [
            "• Lương của tôi bị nợ",
            "• Tôi bị sa thải bất công",
            "• Tôi bị thương tại nơi làm việc",
            "• Tôi bị quấy rối tình dục tại nơi làm việc",
            "• Tôi bị tấn công hoặc quấy rối tình dục",
            "• Bảo hiểm nào có sẵn cho người nước ngoài?",
            "• Số điện thoại nào tôi nên biết ở Hàn Quốc?"
        ],
        "input_hint": "Nhập câu hỏi bảo vệ quyền lợi của bạn bên dưới! 💬"
    },
    "ja": {
        "title": "外国人労働者権利保護ガイド",
        "info": "以下の権利保護に関するトピックについて質問できます:",
        "items": [
            "💰 賃金未払いと支払い",
            "🚫 不当解雇と解雇予告",
            "🏥 産業災害と業務上の災害",
            "🚨 職場でのセクハラと性的暴行",
            "📞 外国人専用保険とカウンセリング",
            "📱 緊急連絡先と相談機関",
            "⚖️ 労働法と権利保護手続き"
        ],
        "example_title": "質問例:",
        "examples": [
            "• 給料が未払いになっています",
            "• 不当に解雇されました",
            "• 仕事中に怪我をしました",
            "• 職場でセクハラを受けました",
            "• 性的暴行や性的嫌がらせを受けました",
            "• 外国人専用保険は何がありますか？",
            "• 韓国滞在中に知っておくべき電話番号は？"
        ],
        "input_hint": "権利保護に関する質問を入力してください！💬"
    },
    "zh": {
        "title": "外籍劳工权益保护指南",
        "info": "您可以询问以下权益保护主题:",
        "items": [
            "💰 工资拖欠和支付",
            "🚫 不当解雇和解雇通知",
            "🏥 工伤和工作相关伤害",
            "🚨 职场性骚扰和性侵犯",
            "📞 外国人专用保险和咨询",
            "📱 紧急联系方式和咨询机构",
            "⚖️ 劳动法和权益保护程序"
        ],
        "example_title": "问题示例:",
        "examples": [
            "• 我的工资被拖欠了",
            "• 我被不当解雇了",
            "• 我在工作中受伤了",
            "• 我在职场遭遇性骚扰",
            "• 我遭遇性侵犯或性骚扰",
            "• 外国人有什么保险？",
            "• 在韩国应该知道哪些电话号码？"
        ],
        "input_hint": "请在下方输入您的权益保护问题！💬"
    },
    "zh-TW": {
        "title": "外籍勞工權益保護指南",
        "info": "您可以詢問以下權益保護主題:",
        "items": [
            "💰 工資拖欠和支付",
            "🚫 不當解僱和解僱通知",
            "🏥 工傷和工作相關傷害",
            "🚨 職場性騷擾和性侵犯",
            "📞 外國人專用保險和諮詢",
            "📱 緊急聯繫方式和諮詢機構",
            "⚖️ 勞動法和權益保護程序"
        ],
        "example_title": "問題範例:",
        "examples": [
            "• 我的工資被拖欠了",
            "• 我被不當解僱了",
            "• 我在工作中受傷了",
            "• 我在職場遭遇性騷擾",
            "• 我遭遇性侵犯或性騷擾",
            "• 外國人有什麽保險？",
            "• 在韓國應該知道哪些電話號碼？"
        ],
        "input_hint": "請在下方輸入您的權益保護問題！💬"
    },
    "id": {
        "title": "Panduan Perlindungan Hak Pekerja Asing",
        "info": "Anda dapat menanyakan topik perlindungan hak berikut:",
        "items": [
            "💰 Tunggakan gaji dan pembayaran gaji",
            "🚫 Pemecatan tidak adil dan pemberitahuan pemecatan",
            "🏥 Kecelakaan kerja dan cedera terkait pekerjaan",
            "🚨 Pelecehan seksual dan serangan seksual di tempat kerja",
            "📞 Asuransi dan konseling khusus warga asing",
            "📱 Kontak darurat dan lembaga konseling",
            "⚖️ Undang-undang ketenagakerjaan dan prosedur perlindungan hak"
        ],
        "example_title": "Contoh pertanyaan:",
        "examples": [
            "• Gaji saya ditahan",
            "• Saya dipecat secara tidak adil",
            "• Saya terluka saat bekerja",
            "• Saya mengalami pelecehan seksual di tempat kerja",
            "• Saya mengalami serangan atau pelecehan seksual",
            "• Asuransi apa yang tersedia untuk warga asing?",
            "• Nomor telepon apa yang harus saya ketahui di Korea?"
        ],
        "input_hint": "Masukkan pertanyaan perlindungan hak Anda di bawah ini! 💬"
    },
    "th": {
        "title": "คู่มือการคุ้มครองสิทธิแรงงานต่างชาติ",
        "info": "คุณสามารถถามเกี่ยวกับหัวข้อการคุ้มครองสิทธิ์ต่อไปนี้:",
        "items": [
            "💰 ค้างชำระค่าจ้างและการจ่ายเงินเดือน",
            "🚫 การเลิกจ้างที่ไม่เป็นธรรมและการแจ้งเลิกจ้าง",
            "🏥 อุบัติเหตุจากการทำงานและการบาดเจ็บที่เกี่ยวข้องกับงาน",
            "🚨 การล่วงละเมิดทางเพศและการล่วงละเมิดทางเพศในที่ทำงาน",
            "📞 ประกันและบริการให้คำปรึกษาสำหรับชาวต่างชาติ",
            "📱 เบอร์ติดต่อฉุกเฉินและหน่วยงานให้คำปรึกษา",
            "⚖️ กฎหมายแรงงานและขั้นตอนการคุ้มครองสิทธิ์"
        ],
        "example_title": "ตัวอย่างคำถาม:",
        "examples": [
            "• เงินเดือนของฉันถูกค้างชำระ",
            "• ฉันถูกเลิกจ้างอย่างไม่เป็นธรรม",
            "• ฉันได้รับบาดเจ็บขณะทำงาน",
            "• ฉันประสบกับการล่วงละเมิดทางเพศในที่ทำงาน",
            "• ฉันประสบกับการล่วงละเมิดหรือคุกคามทางเพศ",
            "• ประกันอะไรที่มีสำหรับชาวต่างชาติ?",
            "• เบอร์โทรศัพท์อะไรที่ฉันควรรู้ในเกาหลี?"
        ],
        "input_hint": "ป้อนคำถามการคุ้มครองสิทธิ์ของคุณด้านล่าง! 💬"
    },
    "fr": {
        "title": "Guide de protection des droits des travailleurs étrangers",
        "info": "Vous pouvez poser des questions sur les sujets de protection des droits suivants:",
        "items": [
            "💰 Arriérés de salaire et paiement des salaires",
            "🚫 Licenciement abusif et préavis de licenciement",
            "🏥 Accidents du travail et blessures liées au travail",
            "🚨 Harcèlement sexuel et agression sexuelle sur le lieu de travail",
            "📞 Assurance et conseil réservés aux étrangers",
            "📱 Contacts d'urgence et agences de conseil",
            "⚖️ Lois du travail et procédures de protection des droits"
        ],
        "example_title": "Exemples de questions:",
        "examples": [
            "• Mon salaire a été retenu",
            "• J'ai été licencié injustement",
            "• Je me suis blessé au travail",
            "• J'ai subi du harcèlement sexuel au travail",
            "• J'ai subi une agression ou du harcèlement sexuel",
            "• Quelle assurance est disponible pour les étrangers?",
            "• Quels numéros de téléphone dois-je connaître en Corée?"
        ],
        "input_hint": "Entrez votre question de protection des droits ci-dessous! 💬"
    },
    "de": {
        "title": "Leitfaden zum Schutz der Rechte ausländischer Arbeitnehmer",
        "info": "Sie können Fragen zu folgenden Themen des Rechtsschutzes stellen:",
        "items": [
            "💰 Lohnrückstände und Lohnzahlung",
            "🚫 Unfaire Kündigung und Kündigungsfrist",
            "🏥 Arbeitsunfälle und arbeitsbedingte Verletzungen",
            "🚨 Sexuelle Belästigung und sexuelle Übergriffe am Arbeitsplatz",
            "📞 Ausländer-spezifische Versicherung und Beratung",
            "📱 Notfallkontakte und Beratungsstellen",
            "⚖️ Arbeitsgesetze und Rechtsschutzverfahren"
        ],
        "example_title": "Beispielfragen:",
        "examples": [
            "• Mein Lohn wurde einbehalten",
            "• Ich wurde unfair gekündigt",
            "• Ich habe mich bei der Arbeit verletzt",
            "• Ich habe sexuelle Belästigung am Arbeitsplatz erlebt",
            "• Ich habe sexuelle Übergriffe oder Belästigung erlebt",
            "• Welche Versicherung ist für Ausländer verfügbar?",
            "• Welche Telefonnummern sollte ich in Korea kennen?"
        ],
        "input_hint": "Geben Sie Ihre Rechtsschutzfrage unten ein! 💬"
    }
}

def transcribe_from_mic(input_box: ft.TextField, page: ft.Page, mic_button: ft.IconButton):
    if IS_SERVER:
        input_box.hint_text = "서버에서는 음성 입력이 지원되지 않습니다."
        page.update()
        return
    import sounddevice as sd
    from scipy.io.wavfile import write
    samplerate = 44100  # Sample rate
    duration = 5  # seconds
    filename = "temp_recording.wav"

    original_hint_text = input_box.hint_text
    try:
        # 1. 녹음 시작 알림
        mic_button.disabled = True
        input_box.hint_text = "녹음 중... (5초)"
        page.update()

        # 2. 녹음
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
        sd.wait()  # Wait until recording is finished

        # 3. 파일로 저장
        write(filename, samplerate, recording)

        # 4. Whisper API로 전송
        input_box.hint_text = "음성 분석 중..."
        page.update()
        with open(filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
              model="whisper-1",
              file=audio_file
            )
        
        # 5. 결과 입력
        input_box.value = transcript.text
        
    except Exception as e:
        input_box.hint_text = f"오류: {e}"
        print(f"Whisper STT 오류: {e}")
    finally:
        # 6. 정리
        input_box.hint_text = original_hint_text
        mic_button.disabled = False
        if os.path.exists(filename):
            os.remove(filename)
        page.update()

# 자주 깨지는 특수문자 자동 치환 함수
def safe_text(text):
    if not text:
        return text
    t = text
    # 마침표/쉼표 유사문자까지 모두 치환
    t = t.replace('·', '•')
    t = t.replace('。', '.')
    t = t.replace('．', '.')
    t = t.replace('｡', '.')
    t = t.replace('﹒', '.')
    t = t.replace('､', ',')
    t = t.replace('，', ',')
    t = t.replace('﹐', ',')
    t = t.replace('﹑', ',')
    t = t.replace('、', ',')
    t = t.replace('.', '.')
    t = t.replace(',', ',')
    # ... 이하 기존 특수문자 치환 ...
    t = t.replace('※', '*')
    t = t.replace('◆', '-')
    t = t.replace('■', '-')
    t = t.replace('●', '•')
    t = t.replace('◎', '○')
    t = t.replace('★', '*')
    t = t.replace('☆', '*')
    t = t.replace('▶', '>')
    t = t.replace('▷', '>')
    t = t.replace('◀', '<')
    t = t.replace('◁', '<')
    t = t.replace('→', '→')
    t = t.replace('←', '←')
    t = t.replace('↑', '↑')
    t = t.replace('↓', '↓')
    t = t.replace('∼', '~')
    t = t.replace('∑', 'Σ')
    t = t.replace('∏', 'Π')
    t = t.replace('∫', '∫')
    t = t.replace('√', '√')
    t = t.replace('∂', '∂')
    t = t.replace('∞', '∞')
    t = t.replace('≒', '≈')
    t = t.replace('≠', '≠')
    t = t.replace('≡', '=')
    t = t.replace('≪', '<<')
    t = t.replace('≫', '>>')
    t = t.replace('∵', 'because')
    t = t.replace('∴', 'therefore')
    t = t.replace('∇', '∇')
    t = t.replace('∈', '∈')
    t = t.replace('∋', '∋')
    t = t.replace('⊂', '⊂')
    t = t.replace('⊃', '⊃')
    t = t.replace('⊆', '⊆')
    t = t.replace('⊇', '⊇')
    t = t.replace('⊕', '+')
    t = t.replace('⊙', '○')
    t = t.replace('⊥', '⊥')
    t = t.replace('⌒', '~')
    t = t.replace('∠', '∠')
    t = t.replace('∟', '∟')
    t = t.replace('∩', '∩')
    t = t.replace('∪', '∪')
    t = t.replace('∧', '∧')
    t = t.replace('∨', '∨')
    t = t.replace('∃', '∃')
    t = t.replace('∀', '∀')
    t = t.replace('∅', '∅')
    t = t.replace('∝', '∝')
    t = t.replace('∵', 'because')
    t = t.replace('∴', 'therefore')
    t = t.replace('‰', '‰')
    t = t.replace('℉', '°F')
    t = t.replace('℃', '°C')
    t = t.replace('㎏', 'kg')
    t = t.replace('㎏', 'kg')
    t = t.replace('㎜', 'mm')
    t = t.replace('㎝', 'cm')
    t = t.replace('㎞', 'km')
    t = t.replace('㎖', 'ml')
    t = t.replace('㎗', 'dl')
    t = t.replace('㎍', 'μg')
    t = t.replace('㎚', 'nm')
    t = t.replace('㎛', 'μm')
    t = t.replace('㎧', 'm/s')
    t = t.replace('㎨', 'm/s²')
    t = t.replace('㎰', 'pH')
    t = t.replace('㎲', 'μs')
    t = t.replace('㎳', 'ms')
    t = t.replace('㎴', 'pF')
    t = t.replace('㎵', 'nF')
    t = t.replace('㎶', 'μV')
    t = t.replace('㎷', 'mV')
    t = t.replace('㎸', 'kV')
    t = t.replace('㎹', 'MV')
    t = t.replace('㎽', 'mW')
    t = t.replace('㎾', 'kW')
    t = t.replace('㎿', 'MW')
    t = t.replace('㏄', 'cc')
    t = t.replace('㏅', 'cd')
    t = t.replace('㏈', 'dB')
    t = t.replace('㏊', 'ha')
    t = t.replace('㏎', 'kn')
    t = t.replace('㏏', 'kt')
    t = t.replace('㏐', 'lm')
    t = t.replace('㏑', 'ln')
    t = t.replace('㏒', 'log')
    t = t.replace('㏓', 'lb')
    t = t.replace('㏔', 'p.m.')
    t = t.replace('㏕', 'rpm')
    t = t.replace('㏖', 'MBq')
    t = t.replace('㏗', 'pH')
    t = t.replace('㏘', 'sr')
    t = t.replace('㏙', 'Sv')
    t = t.replace('㏚', 'Wb')
    t = t.replace('㏛', 'rad')
    t = t.replace('㏜', 'Gy')
    t = t.replace('㏝', 'Pa')
    t = t.replace('㏞', 'ppm')
    t = t.replace('㏟', 'ppb')
    t = t.replace('㏠', 'ps')
    t = t.replace('㏡', 'a')
    t = t.replace('㏢', 'bar')
    t = t.replace('㏣', 'G')
    t = t.replace('㏤', 'Gal')
    t = t.replace('㏥', 'Bq')
    t = t.replace('㏦', 'C')
    t = t.replace('㏧', 'F')
    t = t.replace('㏨', 'H')
    t = t.replace('㏩', 'Hz')
    t = t.replace('㏪', 'J')
    t = t.replace('㏫', 'K')
    t = t.replace('㏬', 'L')
    t = t.replace('㏭', 'mol')
    t = t.replace('㏮', 'N')
    t = t.replace('㏯', 'Oe')
    t = t.replace('㏰', 'P')
    t = t.replace('㏱', 'Pa')
    t = t.replace('㏲', 'rad')
    t = t.replace('㏳', 'S')
    t = t.replace('㏴', 'St')
    t = t.replace('㏵', 'T')
    t = t.replace('㏶', 'V')
    t = t.replace('㏷', 'W')
    t = t.replace('㏸', 'Ω')
    t = t.replace('㏹', 'Å')
    t = t.replace('㏺', '㎖')
    t = t.replace('㏻', '㎗')
    t = t.replace('㏼', '㎍')
    t = t.replace('㏽', '㎚')
    t = t.replace('㏾', '㎛')
    return t

def ChatRoomPage(page, room_id, room_title, user_lang, target_lang, on_back=None, on_share=None, custom_translate_message=None, firebase_available=True, is_foreign_worker_rag=False):
    # 화면 크기에 따른 반응형 설정
    is_mobile = page.width < 600
    is_tablet = 600 <= page.width < 1024
    
    # 반응형 크기 계산
    title_size = 18 if is_mobile else 22
    nickname_size = 10 if is_mobile else 12
    message_size = 14 if is_mobile else 16
    translated_size = 10 if is_mobile else 12
    input_height = 45 if is_mobile else 50
    bubble_padding = 8 if is_mobile else 12
    header_padding = 12 if is_mobile else 16
    
    # --- 상태 및 컨트롤 초기화 ---
    chat_messages = ft.Column(
        auto_scroll=True,
        spacing=10 if is_mobile else 15,
        expand=True,
    )
    current_target_lang = [target_lang]
    is_korean = user_lang == "ko"
    # RAG 채팅방인지 확인
    is_rag_room = custom_translate_message is not None
    # 언어별 입력창 안내문구
    RAG_INPUT_HINTS = {
        "ko": "한국생활에 대해 질문하세요",
        "en": "Ask about life in Korea",
        "vi": "Hãy hỏi về cuộc sống ở Hàn Quốc",
        "ja": "韓国での生活について質問してください",
        "zh": "请咨询有关在韩国生活的问题",
        "fr": "Posez des questions sur la vie en Corée",
        "de": "Stellen Sie Fragen zum Leben in Korea",
        "th": "สอบถามเกี่ยวกับการใช้ชีวิตในเกาหลีได้เลย",
        "zh-TW": "請詢問有關在韓國生活的問題",
        "id": "Tanyakan tentang kehidupan di Korea",
    }
    input_hint = RAG_INPUT_HINTS.get(user_lang, RAG_INPUT_HINTS["en"]) if is_rag_room else {
        "ko": "메시지 입력",
        "en": "Type a message",
        "vi": "Nhập tin nhắn",
        "ja": "メッセージを入力",
        "zh": "输入消息",
        "fr": "Entrez un message",
        "de": "Nachricht eingeben",
        "th": "พิมพ์ข้อความ",
        "zh-TW": "輸入訊息",
        "id": "Ketik pesan",
    }.get(user_lang, "Type a message")
    input_box = ft.TextField(
        hint_text=input_hint, 
        expand=True, 
        height=input_height,
        font_family="system"
    )
    if is_rag_room:
        if is_foreign_worker_rag or room_id == "foreign_worker_rights_rag":
            # 외국인 근로자 RAG 방에서는 언어 선택 드롭다운 표시
            translate_switch = None
        else:
            # 일반 RAG 방에서는 번역 스위치 제거
            translate_switch = None
    else:
        switch_label = "번역 ON/OFF" if is_korean else "Translate ON/OFF"
        translate_switch = ft.Switch(label=switch_label, value=True)

    def on_target_lang_change(e):
        current_target_lang[0] = e.control.value

    # 번역 대상 언어 드롭다운 옵션 (국기+영어 국가명)
    target_lang_options = [
        ("ko", "🇰🇷 Korean"),
        ("en", "🇺🇸 English"),
        ("ja", "🇯🇵 Japanese"),
        ("zh", "🇨🇳 Chinese"),
        ("zh-TW", "🇹🇼 Taiwanese"),
        ("id", "🇮🇩 Indonesian"),
        ("ms", "🇲🇾 Malay"),
        ("ta", "🇮🇳 Tamil"),
        ("fr", "🇫🇷 French"),
        ("de", "🇩🇪 German"),
        ("th", "🇹🇭 Thai"),
        ("vi", "🇻🇳 Vietnamese"),
        ("uz", "🇺🇿 Uzbek"),
        ("ne", "🇳🇵 Nepali"),
        ("tet", "🇹🇱 Tetum"),
        ("lo", "🇱🇦 Lao"),
        ("mn", "🇲🇳 Mongolian"),
        ("my", "🇲🇲 Burmese"),
        ("bn", "🇧🇩 Bengali"),
        ("si", "🇱🇰 Sinhala"),
        ("km", "🇰🇭 Khmer"),
        ("ky", "🇰🇬 Kyrgyz"),
        ("ur", "🇵🇰 Urdu"),
    ]
    # 드롭다운 항상 생성
    target_lang_dropdown = ft.Dropdown(
        value=current_target_lang[0],
        options=[ft.dropdown.Option(key, text) for key, text in target_lang_options],
        width=180 if is_mobile else 220,
        on_change=on_target_lang_change
    )

    def create_message_bubble(msg_data, is_me):
        # 닉네임이 '익명'이고 본문/번역문이 모두 비어있으면 말풍선 생성하지 않음
        if msg_data.get('nickname', '') == '익명' and not msg_data.get('text', '').strip() and not msg_data.get('translated', '').strip():
            return None
        bubble_width = int(page.width * 0.5) if is_mobile else 400
        base_size = 16 if is_mobile else 18  # 기존보다 2pt 크게
        is_rag = msg_data.get('nickname', '') == 'RAG'
        font_family = "system" if is_rag else None
        # RAG 답변 특수문자 치환
        if is_rag:
            msg_data['text'] = safe_text(msg_data['text'])
            msg_data['translated'] = safe_text(msg_data.get('translated', ''))
        # 질문예시(가이드 메시지)라면 글자 크기 한 단계 키움
        nickname = msg_data.get('nickname', '')
        is_guide = is_rag and msg_data.get('is_guide', False)
        nickname_color = ft.Colors.WHITE if is_me else ft.Colors.BLACK87
        
        # 차단 버튼 (방장이고, 자신의 메시지가 아니고, 시스템/RAG 메시지가 아닐 때만 표시)
        block_button = None
        if not is_me and nickname not in ['시스템', 'RAG', '익명']:
            # 방장 권한 확인
            current_nickname = page.session.get('nickname') or ''
            current_user_id = page.session.get('user_id')
            if is_room_owner(room_id, current_nickname, current_user_id):
                block_button = ft.IconButton(
                    icon=ft.Icons.BLOCK,
                    icon_color=ft.Colors.RED_400,
                    icon_size=16,
                    tooltip="사용자 차단 (방장 전용)",
                    on_click=lambda e, nickname=nickname: block_user_from_message(nickname)
                )
        
        controls = [
            ft.Row([
            ft.Text(
                    nickname,
                    size=(base_size - 2) + (2 if is_guide else 0),
                    color=nickname_color,
                    italic=True,
                    font_family=font_family,
                    selectable=True,
                ),
                block_button if block_button else ft.Container()
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) if block_button else ft.Text(
                nickname,
                size=(base_size - 2) + (2 if is_guide else 0),
                color=nickname_color,
                italic=True,
                font_family=font_family,
                selectable=True,
            ),
            ft.Text(
                msg_data.get('text', ''),
                size=base_size + (2 if is_guide else 0),
                color=ft.Colors.WHITE if is_me else ft.Colors.BLACK87,
                font_family=font_family,
                selectable=True,
            ),
        ]
        if msg_data.get('translated', ''):
            controls.append(
                ft.Text(
                    msg_data.get('translated', ''),
                    size=(base_size - 2) + (2 if is_guide else 0),
                    color=ft.Colors.WHITE if is_me else ft.Colors.BLACK87,
                    italic=True,
                    font_family=font_family,
                    selectable=True,
                )
            )
        # Row로 감싸서 좌/우 정렬
        return ft.Row([
            ft.Container(
                content=ft.Column(controls, spacing=2),
            padding=12,
                bgcolor="#2563EB" if is_me else ft.Colors.GREY_200,
                border_radius=16,
                margin=ft.margin.only(top=6, left=8, right=8),
                width=bubble_width,
                alignment=ft.alignment.top_right if is_me else ft.alignment.top_left,
            )
        ], alignment=ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START)

    # --- 시스템 안내 메시지(가운데 정렬) 생성 함수 ---
    def create_system_message_bubble(text):
        return ft.Row([
            ft.Container(
                content=ft.Text(text, size=15 if is_mobile else 17, color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD),
                padding=10,
                bgcolor=ft.Colors.GREY_100,
                border_radius=12,
                alignment=ft.alignment.center,
            )
        ], alignment=ft.MainAxisAlignment.CENTER)

    # --- 입장/퇴장 감지용 유저 세트 ---
    current_users = set()

    # --- Firebase 리스너 콜백 ---
    def on_message(event):
        if not event or not event.data:
            return  # 데이터가 없으면 무시
        
        try:
            data = event.data
            if isinstance(data, str):
                import json
                data = json.loads(data)
            
            # 데이터가 유효한지 확인
            if not isinstance(data, dict):
                print(f"유효하지 않은 메시지 데이터 형식: {type(data)}")
                return
            
            msg_data = {
                'text': data.get('text', ''),
                'nickname': data.get('nickname', '익명'),
                'timestamp': str(data.get('timestamp', '')),
                'translated': data.get('translated', '')
            }
            
            # 차단된 사용자의 메시지는 무시
            if is_user_blocked(msg_data['nickname']):
                print(f"차단된 사용자 {msg_data['nickname']}의 메시지 필터링됨")
                return
            
            # 시스템 메시지면 무조건 가운데 정렬로 append
            if msg_data['nickname'] == '시스템':
                system_bubble = create_system_message_bubble(msg_data['text'])
                if system_bubble:  # None이 아닌 경우만 추가
                    chat_messages.controls.append(system_bubble)
                    page.update()
                return
            
            # 중복 메시지 방지: 최근 5개 메시지의 (nickname, text, timestamp)와 비교 (일반 메시지에만 적용)
            def get_msg_id(msg):
                return f"{msg['nickname']}|{msg['text']}|{msg['timestamp']}"
            new_id = get_msg_id(msg_data)
            for c in chat_messages.controls[-5:]:
                if hasattr(c, 'content') and hasattr(c.content, 'controls'):
                    try:
                        last_nickname = c.content.controls[0].value
                        last_text = c.content.controls[1].value
                        last_timestamp = getattr(c, 'timestamp', None) or ''
                        last_id = f"{last_nickname}|{last_text}|{last_timestamp}"
                        if last_id == new_id:
                            return  # 중복
                    except Exception:
                        continue
            
            # --- 입장/퇴장 감지 및 안내 메시지 ---
            nickname = msg_data['nickname']
            if nickname != '익명' and nickname != 'RAG' and nickname != '시스템':
                # 입장 감지
                if nickname not in current_users:
                    current_users.add(nickname)
                    join_text = f"{nickname}님이 채팅방에 들어왔습니다."
                    join_bubble = create_system_message_bubble(join_text)
                    if join_bubble:  # None이 아닌 경우만 추가
                        chat_messages.controls.append(join_bubble)
                        page.update()
            
            # 메시지 말풍선 생성
            is_me = msg_data['nickname'] == (page.session.get('nickname') or '')
            message_bubble = create_message_bubble(msg_data, is_me)
            
            # message_bubble이 유효한 경우에만 처리
            if message_bubble:
                setattr(message_bubble, 'timestamp', msg_data['timestamp'])
                chat_messages.controls.append(message_bubble)
                page.update()
            else:
                print(f"메시지 버블 생성 실패: {msg_data}")
                
        except Exception as e:
            print(f"메시지 처리 오류: {e}")
            import traceback
            traceback.print_exc()

    # --- 사용자 차단 함수 ---
    def block_user_from_message(nickname):
        """메시지에서 사용자 차단"""
        def confirm_block(e):
            # 로컬 차단 목록에 추가
            BLOCKED_USERS.add(nickname)
            
            # Firebase에 차단 정보 저장
            try:
                db.reference(f'rooms/{room_id}/blocked_users').child(nickname).set({
                    'blocked_at': time.time(),
                    'blocked_by': '방장'
                })
                print(f"사용자 {nickname} 차단됨 (방: {room_id})")
            except Exception as e:
                print(f"차단 정보 저장 오류: {e}")
            
            # 차단 메시지 표시
            block_msg_data = {
                'text': f"🚫 {nickname}님이 차단되었습니다.",
                'nickname': '시스템',
                'timestamp': time.time(),
                'translated': ''
            }
            block_bubble = create_message_bubble(block_msg_data, False)
            if block_bubble:  # None이 아닌 경우만 처리
                setattr(block_bubble, 'timestamp', block_msg_data['timestamp'])
                chat_messages.controls.append(block_bubble)
            page.update()
            
            # 다이얼로그 닫기
            if page.dialog:
                page.dialog.open = False
                page.update()
        
        def cancel_block(e):
            if page.dialog:
                page.dialog.open = False
                page.update()
        
        # 확인 다이얼로그 표시
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("사용자 차단"),
            content=ft.Text(f"{nickname}님을 차단하시겠습니까?\n차단된 사용자의 메시지는 더 이상 표시되지 않습니다."),
            actions=[
                ft.TextButton("취소", on_click=cancel_block),
                ft.TextButton("차단", on_click=confirm_block, style=ft.ButtonStyle(color=ft.Colors.RED))
            ]
        )
        
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    # --- 퇴장 감지용(페이지 언로드) ---
    def on_exit():
        nickname = page.session.get('nickname')
        if nickname and nickname in current_users:
            leave_text = f"{nickname}님이 채팅방을 나가셨습니다."
            chat_messages.controls.append(create_system_message_bubble(leave_text))
            current_users.remove(nickname)
            page.update()
    atexit.register(on_exit)

    # --- 메시지 전송 함수 ---
    def send_message(e=None):
        if not input_box.value or not input_box.value.strip():
            return
        message_text = input_box.value.strip()
        nickname = page.session.get('nickname') or '익명'
        
        # 부적절한 메시지 체크
        is_inappropriate, reason = is_inappropriate_message(message_text)
        if is_inappropriate:
            # 경고 메시지 표시
            warning_msg_data = {
                'text': f"⚠️ {reason}",
                'nickname': '시스템',
                'timestamp': time.time(),
                'translated': ''
            }
            warning_bubble = create_message_bubble(warning_msg_data, False)
            if warning_bubble:  # None이 아닌 경우만 처리
                setattr(warning_bubble, 'timestamp', warning_msg_data['timestamp'])
                chat_messages.controls.append(warning_bubble)
            page.update()
            return
        
        # 메시지 필터링 (부적절한 단어 마스킹)
        filtered_message = filter_message(message_text)
        if filtered_message != message_text:
            message_text = filtered_message
        
        # 입력창 초기화 (먼저 초기화하여 UI 반응성 향상)
        input_box.value = ""
        page.update()
        
        # 번역 처리
        translated_text = ""
        if translate_switch and translate_switch.value and current_target_lang[0]:
            try:
                translated_text = translate_message(message_text, current_target_lang[0])
            except Exception as e:
                translated_text = f"[번역 오류: {e}]"
        
        # Firebase에 메시지 저장 (외국인 근로자 RAG 방이 아닐 때만)
        if firebase_available and not (is_foreign_worker_rag or room_id == "foreign_worker_rights_rag"):
            try:
                message_data = {
                    'text': message_text,
                    'nickname': nickname,
                    'timestamp': time.time(),
                    'translated': translated_text
                }
                db.reference(f'rooms/{room_id}/messages').push(message_data)
            except Exception as e:
                print(f"Firebase 저장 오류: {e}")
        
        # 외국인 근로자 RAG 방이면 사용자 메시지와 RAG 답변을 직접 추가
        if is_foreign_worker_rag or room_id == "foreign_worker_rights_rag":
            # 사용자 메시지 추가
            user_msg_data = {
                'text': message_text,
                'nickname': nickname,
                'timestamp': time.time(),
                'translated': translated_text
            }
            user_bubble = create_message_bubble(user_msg_data, True)
            if user_bubble:  # None이 아닌 경우만 처리
                setattr(user_bubble, 'timestamp', user_msg_data['timestamp'])
                chat_messages.controls.append(user_bubble)
                page.update()
            
            # RAG 답변 추가 (더 안전한 처리)
            try:
                # 로딩 메시지 먼저 표시 (질문 바로 아래에 위치)
                loading_msg_data = {
                    'text': "답변을 생성하고 있습니다...",
                    'nickname': 'RAG',
                    'timestamp': time.time(),
                    'translated': ''
                }
                loading_bubble = create_message_bubble(loading_msg_data, False)
                if loading_bubble:  # None이 아닌 경우만 처리
                    setattr(loading_bubble, 'timestamp', loading_msg_data['timestamp'])
                    # 질문 바로 아래에 insert
                    chat_messages.controls.insert(len(chat_messages.controls), loading_bubble)
                page.update()
                
                # 외국인 근로자 RAG 방에서는 선택된 언어로 답변 생성
                if is_foreign_worker_rag or room_id == "foreign_worker_rights_rag":
                    selected_lang = current_target_lang[0] if current_target_lang[0] else user_lang
                    rag_answer = custom_translate_message(message_text, selected_lang)
                else:
                    # 일반 RAG 방에서는 기존 방식 사용
                    rag_answer = custom_translate_message(message_text, user_lang)
                
                # 로딩 메시지 위치에 답변을 insert (replace)
                idx = chat_messages.controls.index(loading_bubble)
                chat_messages.controls.remove(loading_bubble)
                if rag_answer and rag_answer.strip():  # 답변이 있을 때만 추가
                    rag_msg_data = {
                        'text': rag_answer,
                        'nickname': 'RAG',
                        'timestamp': time.time(),
                        'translated': ''
                    }
                    rag_bubble = create_message_bubble(rag_msg_data, False)
                    if rag_bubble:  # None이 아닌 경우만 처리
                        setattr(rag_bubble, 'timestamp', rag_msg_data['timestamp'])
                        chat_messages.controls.insert(idx, rag_bubble)
                    page.update()
                else:
                    page.update()
            except Exception as e:
                print(f'RAG 답변 오류: {e}')
                try:
                    if 'loading_bubble' in locals():
                        chat_messages.controls.remove(loading_bubble)
                except:
                    pass
                page.update()
                error_msg_data = {
                    'text': f"죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: {str(e)}",
                    'nickname': '시스템',
                    'timestamp': time.time(),
                    'translated': ''
                }
                error_bubble = create_message_bubble(error_msg_data, False)
                setattr(error_bubble, 'timestamp', error_msg_data['timestamp'])
                chat_messages.controls.append(error_bubble)
                page.update()
        # 일반 RAG 채팅방이면 RAG 답변만 직접 추가
        elif custom_translate_message is not None:
            try:
                # 로딩 메시지 먼저 표시
                loading_msg_data = {
                    'text': "답변을 생성하고 있습니다...",
                    'nickname': 'RAG',
                    'timestamp': time.time(),
                    'translated': ''
                }
                loading_bubble = create_message_bubble(loading_msg_data, False)
                if loading_bubble:  # None이 아닌 경우만 처리
                    setattr(loading_bubble, 'timestamp', loading_msg_data['timestamp'])
                    chat_messages.controls.append(loading_bubble)
                page.update()
                # RAG 답변 생성 (선택된 언어로)
                selected_lang = current_target_lang[0] if current_target_lang[0] else user_lang
                rag_answer = custom_translate_message(message_text, selected_lang)
                # 로딩 메시지 제거
                chat_messages.controls.remove(loading_bubble)
                if rag_answer and rag_answer.strip():  # 답변이 있을 때만 추가
                    rag_msg_data = {
                        'text': rag_answer,
                        'nickname': 'RAG',
                        'timestamp': time.time(),
                        'translated': ''
                    }
                    message_bubble = create_message_bubble(rag_msg_data, False)
                    if message_bubble:  # None이 아닌 경우만 처리
                        setattr(message_bubble, 'timestamp', rag_msg_data['timestamp'])
                        chat_messages.controls.append(message_bubble)
                    page.update()
                else:
                    # 답변이 없어도 화면 업데이트
                    page.update()
            except Exception as e:
                print(f'RAG 답변 오류: {e}')
                # 로딩 메시지가 있다면 제거
                try:
                    if 'loading_bubble' in locals():
                        chat_messages.controls.remove(loading_bubble)
                except:
                    pass
                # 오류 발생 시에도 화면 업데이트
                page.update()
                # 오류 메시지도 표시
                error_msg_data = {
                    'text': f"죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: {str(e)}",
                    'nickname': '시스템',
                    'timestamp': time.time(),
                    'translated': ''
                }
                error_bubble = create_message_bubble(error_msg_data, False)
                if error_bubble:  # None이 아닌 경우만 처리
                    setattr(error_bubble, 'timestamp', error_msg_data['timestamp'])
                    chat_messages.controls.append(error_bubble)
                page.update()

    # --- 뒤로가기 함수 ---
    def go_back(e):
        if on_back:
            on_back(e)

    # --- Firebase 리스너 설정 ---
    firebase_listener = None  # 리스너 객체 저장용 변수
    if firebase_available:
        try:
            # Firebase 리스너 설정
            firebase_listener = db.reference(f'rooms/{room_id}/messages').listen(on_message)
        except Exception as e:
            print(f"Firebase 리스너 설정 오류: {e}")

    # --- UI 구성 ---
    # RAG 채팅방이면 예시/가이드 메시지를 항상 맨 위에 추가 (중복 방지)
    def get_rag_guide_message():
        # 외국인 근로자 권리구제 RAG 방인지 확인 (방 ID와 파라미터 모두 확인)
        if is_foreign_worker_rag or room_id == "foreign_worker_rights_rag":
            guide_texts = FOREIGN_WORKER_GUIDE_TEXTS.get(user_lang, FOREIGN_WORKER_GUIDE_TEXTS["ko"])
        else:
            guide_texts = RAG_GUIDE_TEXTS.get(user_lang, RAG_GUIDE_TEXTS["ko"])
        guide_items = []
        for item in guide_texts["items"]:
            guide_items.append(ft.Text(item, size=14 if is_mobile else 16, color=ft.Colors.GREY_700, selectable=True))
        example_items = []
        for example in guide_texts["examples"]:
            example_items.append(ft.Text(example, size=13 if is_mobile else 14, color=ft.Colors.GREY_600, selectable=True))
        bubble_width = int(page.width * 0.9) if is_mobile else 400
        return ft.Container(
            content=ft.Column([
                ft.Text(guide_texts["title"], size=18 if is_mobile else 20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600, selectable=True),
                ft.Container(height=8),
                ft.Text(guide_texts["info"], size=15 if is_mobile else 16, color=ft.Colors.GREY_700, selectable=True),
                ft.Container(height=8),
                *guide_items,
                ft.Container(height=12),
                ft.Text(guide_texts["example_title"], size=15 if is_mobile else 16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700, selectable=True),
                ft.Container(height=6),
                *example_items,
                ft.Container(height=12),
                ft.Text(guide_texts["input_hint"], size=15 if is_mobile else 16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600, text_align=ft.TextAlign.CENTER, selectable=True),
            ], spacing=4),
            padding=16 if is_mobile else 20,
            bgcolor=ft.LinearGradient(["#E3F2FD", "#BBDEFB"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right),
            border_radius=12,
            margin=ft.margin.only(bottom=16),
            border=ft.border.all(1, "#2196F3"),
            width=bubble_width,
        )

    # 다국어 '빠른 채팅방' 타이틀 사전
    QUICK_ROOM_TITLES = {
        "ko": "빠른 채팅방",
        "en": "Quick Chat Room",
        "ja": "クイックチャットルーム",
        "zh": "快速聊天室",
        "zh-TW": "快速聊天室",
        "id": "Ruang Obrolan Cepat",
        "vi": "Phòng chat nhanh",
        "fr": "Salon de discussion rapide",
        "de": "Schnell-Chatraum",
        "th": "ห้องแชทด่วน"
    }
    # 공식 안내 채팅방(RAG) 헤더 타이틀 다국어 처리
    is_rag_room = custom_translate_message is not None
    rag_title = None
    if is_rag_room:
        if is_foreign_worker_rag or room_id == "foreign_worker_rights_rag":
            rag_title = FOREIGN_WORKER_GUIDE_TEXTS.get(user_lang, FOREIGN_WORKER_GUIDE_TEXTS["ko"])['title']
        else:
            rag_title = RAG_GUIDE_TEXTS.get(user_lang, RAG_GUIDE_TEXTS["en"])['title']
    # --- 채팅방 관리 함수 ---
    def show_room_settings(e):
        """채팅방 설정 다이얼로그 표시"""
        def close_settings(e):
            if page.overlay:
                page.overlay.pop()
                page.update()
        
        # 방장 권한 확인
        current_nickname = page.session.get('nickname') or ''
        current_user_id = page.session.get('user_id')
        is_owner = is_room_owner(room_id, current_nickname, current_user_id)
        
        # 차단된 사용자 목록 가져오기 (방장만)
        blocked_list = []
        if is_owner:
            try:
                blocked_ref = db.reference(f'rooms/{room_id}/blocked_users')
                blocked_data = blocked_ref.get()
                if blocked_data:
                    for nickname, data in blocked_data.items():
                        blocked_list.append(nickname)
            except:
                pass
        
        # 설정 다이얼로그 내용
        settings_content = ft.Column([
            ft.Text("채팅방 관리", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(f"방 제목: {display_room_title}", size=14),
            ft.Text(f"방 ID: {room_id}", size=12, color=ft.Colors.GREY_600),
            ft.Text(f"방장: {current_nickname if is_owner else '다른 사용자'}", size=12, color=ft.Colors.GREEN_600 if is_owner else ft.Colors.GREY_600),
            ft.Divider(),
            # 방장 전용 기능들
            ft.Text("방장 전용 기능", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600) if is_owner else ft.Container(),
            ft.Text("차단된 사용자", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"총 {len(blocked_list)}명", size=12, color=ft.Colors.GREY_600),
            ft.ElevatedButton(
                "차단 목록 보기",
                on_click=lambda e: show_blocked_users(blocked_list),
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_50, color=ft.Colors.RED_700)
            ) if is_owner and blocked_list else ft.Text("차단된 사용자가 없습니다.", size=12, color=ft.Colors.GREY_500) if is_owner else ft.Container(),
            ft.Divider(),
            ft.ElevatedButton(
                "채팅방 초기화",
                on_click=lambda e: clear_chat_history(),
                style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_50, color=ft.Colors.ORANGE_700)
            ) if is_owner else ft.Container(),
            ft.ElevatedButton("닫기", on_click=close_settings)
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # 오버레이로 표시
        settings_dialog = ft.Container(
            content=ft.Container(
                content=settings_content,
                padding=24,
                bgcolor=ft.Colors.WHITE,
                border_radius=16,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK26)
            ),
            alignment=ft.alignment.center,
            expand=True
        )
        
        page.overlay.append(settings_dialog)
        page.update()
    
    def show_blocked_users(blocked_list):
        """차단된 사용자 목록 표시"""
        def unblock_user_from_list(nickname):
            unblock_user(nickname, room_id)
            # 목록 새로고침
            if page.overlay:
                page.overlay.pop()
                page.update()
            show_room_settings(None)
        
        # 방장 권한 재확인
        current_nickname = page.session.get('nickname') or ''
        current_user_id = page.session.get('user_id')
        is_owner = is_room_owner(room_id, current_nickname, current_user_id)
        
        if not is_owner:
            # 방장이 아니면 접근 거부
            page.snack_bar = ft.SnackBar(
                content=ft.Text("방장만 차단 목록을 볼 수 있습니다."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            return
        
        blocked_content = ft.Column([
            ft.Text("차단된 사용자 목록", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("방장 전용 기능", size=12, color=ft.Colors.BLUE_600),
            ft.Divider(),
            *[ft.Row([
                ft.Text(nickname, size=14),
                ft.ElevatedButton(
                    "차단 해제",
                    on_click=lambda e, n=nickname: unblock_user_from_list(n),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_50, color=ft.Colors.GREEN_700)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) for nickname in blocked_list],
            ft.ElevatedButton("뒤로가기", on_click=lambda e: [page.overlay.pop(), page.update()])
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        blocked_dialog = ft.Container(
            content=ft.Container(
                content=blocked_content,
                padding=24,
                bgcolor=ft.Colors.WHITE,
                border_radius=16,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK26)
            ),
            alignment=ft.alignment.center,
            expand=True
        )
        
        page.overlay.append(blocked_dialog)
        page.update()
    
    def clear_chat_history():
        """채팅 기록 초기화"""
        # 방장 권한 확인
        current_nickname = page.session.get('nickname') or ''
        current_user_id = page.session.get('user_id')
        is_owner = is_room_owner(room_id, current_nickname, current_user_id)
        
        if not is_owner:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("방장만 채팅 기록을 초기화할 수 있습니다."),
                action="확인"
            )
            page.snack_bar.open = True
            page.update()
            return
        
        def confirm_clear(e):
            nonlocal firebase_listener  # 외부 변수 접근
            try:
                # Firebase에서 메시지 삭제
                db.reference(f'rooms/{room_id}/messages').delete()
                
                # 화면 메시지 초기화
                chat_messages.controls.clear()
                
                # 현재 사용자 목록도 초기화 (입장/퇴장 메시지 방지)
                current_users.clear()
                
                # Firebase 리스너 재설정 (기존 리스너 제거 후 새로 설정)
                if firebase_listener and firebase_available:
                    try:
                        firebase_listener.close()  # 기존 리스너 제거
                    except:
                        pass
                    # 새 리스너 설정
                    firebase_listener = db.reference(f'rooms/{room_id}/messages').listen(on_message)
                
                # 페이지 업데이트
                page.update()
                
                # 확인 메시지 표시 (Firebase에 저장하지 않고 화면에만 표시)
                clear_msg_data = {
                    'text': "채팅 기록이 초기화되었습니다.",
                    'nickname': '시스템',
                    'timestamp': time.time(),
                    'translated': ''
                }
                clear_bubble = create_message_bubble(clear_msg_data, False)
                if clear_bubble:  # None이 아닌 경우만 처리
                    setattr(clear_bubble, 'timestamp', clear_msg_data['timestamp'])
                    chat_messages.controls.append(clear_bubble)
                    page.update()
                
                # 성공 메시지 표시
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("채팅 기록이 성공적으로 초기화되었습니다."),
                    action="확인",
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
                
                # 다이얼로그 닫기
                if page.dialog:
                    page.dialog.open = False
                    page.update()
                    
            except Exception as e:
                print(f"채팅 기록 초기화 오류: {e}")
                import traceback
                traceback.print_exc()
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("채팅 기록 초기화 중 오류가 발생했습니다."),
                    action="확인"
                )
                page.snack_bar.open = True
                page.update()
        
        def cancel_clear(e):
            if page.dialog:
                page.dialog.open = False
                page.update()
        
        # 확인 다이얼로그 표시
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("채팅 기록 초기화"),
            content=ft.Text("정말로 모든 채팅 기록을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다."),
            actions=[
                ft.TextButton("취소", on_click=cancel_clear),
                ft.TextButton("초기화", on_click=confirm_clear, style=ft.ButtonStyle(color=ft.Colors.RED))
            ]
        )
        
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    # 헤더 (뒤로가기 + 방 제목 + 설정 버튼 + 공유 버튼)
    display_room_title = rag_title if is_rag_room else (
        QUICK_ROOM_TITLES.get(user_lang, "Quick Chat Room") if room_title in ["빠른 채팅방", "Quick Chat Room"] else room_title
    )
    
    # 방장 권한 확인
    current_nickname = page.session.get('nickname') or ''
    current_user_id = page.session.get('user_id')
    is_owner = is_room_owner(room_id, current_nickname, current_user_id)
    
    # 방장 표시 추가
    title_with_owner = f"{display_room_title} {'👑' if is_owner else ''}"
    
    header = ft.Container(
        content=ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back),
            ft.Text(title_with_owner, size=title_size, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87, expand=True, selectable=True),
            ft.IconButton(ft.Icons.SETTINGS, on_click=show_room_settings, tooltip="채팅방 관리"),
            ft.IconButton(ft.Icons.SHARE, on_click=on_share) if on_share else ft.Container(),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=header_padding,
        bgcolor=ft.Colors.WHITE,
        border_radius=8 if is_mobile else 10,
        margin=ft.margin.only(bottom=8),
        shadow=ft.BoxShadow(blur_radius=4, color="#B0BEC544")
    )

    # 언어별 마이크 안내 메시지
    MIC_GUIDE_TEXTS = {
        "ko": "키보드의 마이크 버튼을 눌러 음성 입력을 사용하세요!",
        "en": "Tap the microphone button on your keyboard to use voice input!",
        "ja": "キーボードのマイクボタンを押して音声入力を使ってください！",
        "zh": "请点击键盘上的麦克风按钮进行语音输入！",
        "zh-TW": "請點擊鍵盤上的麥克風按鈕進行語音輸入！",
        "id": "Tekan tombol mikrofon di keyboard untuk menggunakan input suara!",
        "vi": "Nhấn nút micro trên bàn phím để nhập bằng giọng nói!",
        "fr": "Appuyez sur le bouton micro du clavier pour utiliser la saisie vocale !",
        "de": "Tippen Sie auf die Mikrofontaste Ihrer Tastatur, um die Spracheingabe zu verwenden!",
        "th": "แตะปุ่มไมโครโฟนบนแป้นพิมพ์เพื่อใช้การป้อนด้วยเสียง!"
    }
    # AlertDialog 미리 생성
    mic_dialog = ft.AlertDialog(title=ft.Text(""), modal=True)

    def focus_input_box(e):
        input_box.focus()
        guide_text = MIC_GUIDE_TEXTS.get(user_lang, MIC_GUIDE_TEXTS["en"])
        mic_dialog.title = ft.Text(guide_text)
        mic_dialog.open = True
        page.update()
        # 3초 후 자동 닫힘
        def close_dialog():
            import time
            time.sleep(3)
            mic_dialog.open = False
            page.update()
        threading.Thread(target=close_dialog, daemon=True).start()

    # 입력 영역
    input_row = ft.Row([
        input_box,
        ft.IconButton(
            ft.Icons.MIC,
            on_click=focus_input_box,
            tooltip="음성 입력(키보드 마이크 버튼 사용)"
        ) if not IS_SERVER else ft.Container(),
        ft.IconButton(
            ft.Icons.SEND,
            on_click=send_message,
            tooltip="전송"
        ),
    ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # 입력창 위에 드롭다운 항상 표시
    input_area = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Text("답변 언어:", size=14, weight=ft.FontWeight.BOLD),
                target_lang_dropdown
            ], alignment=ft.MainAxisAlignment.START, spacing=12),
            padding=8 if is_mobile else 12,
            margin=ft.margin.only(bottom=4)
        ),
        input_row
    ], spacing=4)

    # chat_column을 스크롤 가능하게 만듦
    if is_rag_room:
        chat_column = ft.Column(
            controls=[get_rag_guide_message(), chat_messages],
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.ALWAYS
        )
    else:
        chat_column = ft.Column(
            controls=[chat_messages],
            expand=True,
            scroll=ft.ScrollMode.ALWAYS
        )

    # chat_area는 scroll 없이 Container만 사용
    chat_area = ft.Container(
        content=chat_column,
        expand=True,
        padding=8 if is_mobile else 12,
        bgcolor="#F6F8FC",
        border_radius=16,
        margin=ft.margin.only(bottom=8, left=8, right=8, top=8),
        border=ft.border.all(1, "#E0E7EF"),
        alignment=ft.alignment.center,
        width=min(page.width, 900)
    )

    # --- 채팅방 입장 시 시스템 메시지 push 함수 ---
    def push_join_system_message():
        nickname = page.session.get('nickname')
        if not (firebase_available and nickname and nickname not in ['익명', 'RAG', '시스템']):
            return
        try:
            messages_ref = db.reference(f'rooms/{room_id}/messages')
            messages = messages_ref.get()
            import time
            now = time.time()
            # 1. 방장(최초 입장자)만 예외 처리: 방에 메시지가 0개이고, 내가 방을 만든 사람일 때만 return
            if not messages or len(messages) == 0:
                # 방장 여부는 room_id 생성 직후 바로 입장하는 경우로 추정 (정확히 하려면 DB에 생성자 정보 필요)
                # 일단 최초 입장자만 안내 메시지 push 안 함
                return
            # 2. 최근 2분 내 같은 닉네임의 시스템 메시지가 이미 있으면 push 안 함
            for msg in messages.values():
                if (
                    msg.get('nickname') == '시스템'
                    and msg.get('text', '').startswith(f'{nickname}님이 채팅방에 들어왔습니다')
                    and now - float(msg.get('timestamp', 0)) < 120
                ):
                    return  # 중복 방지
            # 3. 안내 메시지 push (메시지 1개 이상이면 무조건 push)
            join_text = f"{nickname}님이 채팅방에 들어왔습니다."
            system_msg = {
                'text': join_text,
                'nickname': '시스템',
                'timestamp': now,
                'translated': ''
            }
            messages_ref.push(system_msg)
        except Exception as e:
            print(f"입장 시스템 메시지 push 오류: {e}")

    # --- 최초 진입 시 시스템 메시지 push ---
    push_join_system_message()

    # 전체 레이아웃
    return ft.View(
        f"/chat/{room_id}",
        controls=[
            header,
            chat_area,
            input_area,
        ],
        bgcolor="#F5F7FF",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.END
    )

# 환경변수에서 firebase_key.json 내용을 읽어서 파일로 저장
firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
if firebase_key_json:
    with open("firebase_key.json", "w", encoding="utf-8") as f:
        f.write(firebase_key_json)

# 차단된 사용자 목록 (세션별로 관리)
BLOCKED_USERS = set()

def block_user(nickname, room_id):
    """사용자 차단"""
    BLOCKED_USERS.add(nickname)
    # Firebase에 차단 정보 저장
    try:
        db.reference(f'rooms/{room_id}/blocked_users').child(nickname).set({
            'blocked_at': time.time(),
            'blocked_by': '방장'
        })
        print(f"사용자 {nickname} 차단됨")
    except Exception as e:
        print(f"차단 정보 저장 오류: {e}")

def unblock_user(nickname, room_id):
    """사용자 차단 해제"""
    BLOCKED_USERS.discard(nickname)
    # Firebase에서 차단 정보 삭제
    try:
        db.reference(f'rooms/{room_id}/blocked_users').child(nickname).delete()
        print(f"사용자 {nickname} 차단 해제됨")
    except Exception as e:
        print(f"차단 해제 오류: {e}")

def is_user_blocked(nickname):
    """사용자가 차단되었는지 확인"""
    return nickname in BLOCKED_USERS

def is_room_owner(room_id, nickname, user_id=None):
    """방장인지 확인"""
    try:
        room_ref = db.reference(f'/rooms/{room_id}')
        room_data = room_ref.get()
        if room_data:
            # 닉네임으로 확인
            if room_data.get('created_by') == nickname:
                return True
            # 사용자 ID로 확인 (더 정확함)
            if user_id and room_data.get('creator_id') == user_id:
                return True
        return False
    except Exception as e:
        print(f"방장 권한 확인 오류: {e}")
        return False
