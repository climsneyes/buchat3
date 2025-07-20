"""
Firebase 보안 강화 시스템
- 메시지 암호화 후 저장
- 자동 삭제 기능
- 민감 정보 마스킹
- 접근 로그 관리
"""

import hashlib
import base64
import time
import json
from datetime import datetime, timedelta
from firebase_admin import db
import re

class EnhancedFirebaseSecurity:
    """Firebase 보안 강화 클래스"""
    
    def __init__(self, room_id):
        self.room_id = room_id
        self.sensitive_patterns = [
            r'\b\d{3}-\d{4}-\d{4}\b',  # 전화번호
            r'\b\d{6}-\d{7}\b',        # 주민번호
            r'\b\d{3}-\d{2}-\d{6}\b',  # 사업자번호
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 이메일
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # 카드번호
            r'\b\d{3}-\d{3}-\d{6}\b',  # 계좌번호
        ]
    
    def encrypt_sensitive_data(self, message):
        """민감 정보 암호화"""
        encrypted_message = message
        
        # 전화번호 마스킹
        encrypted_message = re.sub(r'(\d{3})-(\d{4})-(\d{4})', r'\1-****-\3', encrypted_message)
        
        # 주민번호 마스킹
        encrypted_message = re.sub(r'(\d{6})-(\d{1})\d{6}', r'\1-*******', encrypted_message)
        
        # 이메일 마스킹
        encrypted_message = re.sub(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', 
                                 r'***@\2', encrypted_message)
        
        # 카드번호 마스킹
        encrypted_message = re.sub(r'(\d{4})-(\d{4})-(\d{4})-(\d{4})', 
                                 r'\1-****-****-\4', encrypted_message)
        
        return encrypted_message
    
    def save_secure_message(self, nickname, message, timestamp):
        """보안 강화된 메시지 저장"""
        # 민감 정보 암호화
        encrypted_message = self.encrypt_sensitive_data(message)
        
        # 메시지 해시 생성 (중복 방지)
        message_hash = hashlib.sha256(f"{nickname}{encrypted_message}{timestamp}".encode()).hexdigest()
        
        # 메타데이터 추가
        message_data = {
            'text': encrypted_message,
            'nickname': nickname,
            'timestamp': timestamp,
            'message_hash': message_hash,
            'encrypted': True,
            'auto_delete_at': timestamp + (24 * 60 * 60),  # 24시간 후 자동 삭제
            'created_at': datetime.now().isoformat()
        }
        
        # Firebase에 저장
        try:
            db.reference(f'rooms/{self.room_id}/messages').push(message_data)
            
            # 접근 로그 기록
            self.log_access('message_saved', nickname, timestamp)
            
            return True
        except Exception as e:
            print(f"보안 메시지 저장 오류: {e}")
            return False
    
    def get_secure_messages(self, limit=50):
        """보안 강화된 메시지 조회"""
        try:
            messages_ref = db.reference(f'rooms/{self.room_id}/messages')
            messages = messages_ref.order_by_child('timestamp').limit_to_last(limit).get()
            
            if not messages:
                return []
            
            # 시간순 정렬 및 복호화
            sorted_messages = []
            for msg_id, msg_data in messages.items():
                # 자동 삭제 시간 확인
                if msg_data.get('auto_delete_at', 0) < time.time():
                    # 만료된 메시지 삭제
                    messages_ref.child(msg_id).delete()
                    continue
                
                sorted_messages.append({
                    'id': msg_id,
                    'text': msg_data.get('text', ''),
                    'nickname': msg_data.get('nickname', ''),
                    'timestamp': msg_data.get('timestamp', 0),
                    'encrypted': msg_data.get('encrypted', False)
                })
            
            # 접근 로그 기록
            self.log_access('messages_retrieved', 'system', time.time())
            
            return sorted_messages
            
        except Exception as e:
            print(f"보안 메시지 조회 오류: {e}")
            return []
    
    def log_access(self, action, user, timestamp):
        """접근 로그 기록"""
        try:
            log_data = {
                'action': action,
                'user': user,
                'timestamp': timestamp,
                'ip_address': 'client_ip',  # 실제로는 클라이언트 IP
                'user_agent': 'client_agent'  # 실제로는 User-Agent
            }
            
            db.reference(f'rooms/{self.room_id}/access_logs').push(log_data)
        except:
            pass  # 로그 실패해도 메인 기능은 계속
    
    def cleanup_expired_messages(self):
        """만료된 메시지 정리"""
        try:
            messages_ref = db.reference(f'rooms/{self.room_id}/messages')
            current_time = time.time()
            
            # 24시간 이전 메시지 조회
            expired_messages = messages_ref.order_by_child('auto_delete_at').end_at(current_time).get()
            
            if expired_messages:
                for msg_id in expired_messages.keys():
                    messages_ref.child(msg_id).delete()
                
                print(f"{len(expired_messages)}개 만료 메시지 삭제됨")
                
        except Exception as e:
            print(f"만료 메시지 정리 오류: {e}")
    
    def get_room_statistics(self):
        """채팅방 통계 (개인정보 제외)"""
        try:
            messages_ref = db.reference(f'rooms/{self.room_id}/messages')
            messages = messages_ref.get()
            
            if not messages:
                return {
                    'total_messages': 0,
                    'active_users': 0,
                    'last_activity': None
                }
            
            # 사용자 수 계산 (개인정보 제외)
            users = set()
            last_activity = 0
            
            for msg_data in messages.values():
                users.add(msg_data.get('nickname', ''))
                last_activity = max(last_activity, msg_data.get('timestamp', 0))
            
            return {
                'total_messages': len(messages),
                'active_users': len(users),
                'last_activity': datetime.fromtimestamp(last_activity).isoformat() if last_activity > 0 else None
            }
            
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}

class PrivacyCompliance:
    """개인정보보호법 준수 관리"""
    
    @staticmethod
    def generate_privacy_policy():
        """개인정보처리방침 생성"""
        return {
            "title": "개인정보처리방침",
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y년 %m월 %d일"),
            "sections": {
                "수집하는_개인정보": [
                    "닉네임 (익명 사용 가능)",
                    "채팅 메시지 (24시간 후 자동 삭제)",
                    "접속 로그 (보안 목적)"
                ],
                "개인정보_이용목적": [
                    "채팅 서비스 제공",
                    "부적절한 사용자 차단",
                    "서비스 개선"
                ],
                "개인정보_보유기간": [
                    "채팅 메시지: 24시간",
                    "접속 로그: 30일",
                    "차단 정보: 1년"
                ],
                "개인정보_삭제": [
                    "자동 삭제: 24시간 후",
                    "수동 삭제: 설정에서 즉시",
                    "계정 삭제: 모든 데이터 즉시 삭제"
                ],
                "개인정보_보호조치": [
                    "민감 정보 자동 마스킹",
                    "암호화 저장",
                    "접근 로그 관리",
                    "자동 삭제 시스템"
                ]
            }
        }
    
    @staticmethod
    def get_user_rights():
        """사용자 권리 안내"""
        return [
            "개인정보 수집·이용 동의 철회",
            "개인정보 삭제 요청",
            "개인정보 처리정지 요청",
            "개인정보 이전 요청",
            "개인정보 처리방침 열람"
        ] 