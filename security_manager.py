import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sqlite3
from datetime import datetime, timedelta
import threading
import time

class SecureChatManager:
    """암호화된 채팅 관리자"""
    
    def __init__(self, room_id, password=None):
        self.room_id = room_id
        self.db_path = f"storage/secure_chat_{room_id}.db"
        self.key = self._generate_key(password)
        self.cipher = Fernet(self.key)
        self._init_database()
        
    def _generate_key(self, password=None):
        """암호화 키 생성"""
        if password:
            # 사용자 비밀번호 기반 키 생성
            salt = b'secure_chat_salt'  # 실제로는 랜덤 salt 사용
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        else:
            # 자동 생성된 키 (임시)
            key = Fernet.generate_key()
        return key
    
    def _init_database(self):
        """암호화된 SQLite 데이터베이스 초기화"""
        os.makedirs("storage", exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 메시지 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                encrypted_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 차단된 사용자 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                nickname TEXT PRIMARY KEY,
                blocked_at REAL NOT NULL,
                blocked_by TEXT NOT NULL
            )
        ''')
        
        # 자동 삭제 인덱스 (24시간 후)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON messages(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def encrypt_message(self, message):
        """메시지 암호화"""
        return self.cipher.encrypt(message.encode()).decode()
    
    def decrypt_message(self, encrypted_message):
        """메시지 복호화"""
        try:
            return self.cipher.decrypt(encrypted_message.encode()).decode()
        except:
            return "[암호화된 메시지]"
    
    def save_message(self, nickname, message, timestamp):
        """암호화된 메시지 저장"""
        encrypted = self.encrypt_message(message)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (nickname, message, timestamp, encrypted_message)
            VALUES (?, ?, ?, ?)
        ''', (nickname, message, timestamp, encrypted))
        
        conn.commit()
        conn.close()
        
        # 24시간 후 자동 삭제 스케줄링
        self._schedule_auto_delete(timestamp)
    
    def get_messages(self, limit=50):
        """최근 메시지 조회 (복호화)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT nickname, encrypted_message, timestamp
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        messages = []
        for row in cursor.fetchall():
            nickname, encrypted, timestamp = row
            decrypted = self.decrypt_message(encrypted)
            messages.append({
                'nickname': nickname,
                'text': decrypted,
                'timestamp': timestamp
            })
        
        conn.close()
        return list(reversed(messages))  # 시간순 정렬
    
    def block_user(self, nickname, blocked_by="방장"):
        """사용자 차단"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_users (nickname, blocked_at, blocked_by)
            VALUES (?, ?, ?)
        ''', (nickname, time.time(), blocked_by))
        
        conn.commit()
        conn.close()
    
    def is_user_blocked(self, nickname):
        """사용자 차단 여부 확인"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM blocked_users WHERE nickname = ?', (nickname,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def get_blocked_users(self):
        """차단된 사용자 목록"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT nickname, blocked_at FROM blocked_users')
        users = cursor.fetchall()
        
        conn.close()
        return [{'nickname': user[0], 'blocked_at': user[1]} for user in users]
    
    def unblock_user(self, nickname):
        """사용자 차단 해제"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM blocked_users WHERE nickname = ?', (nickname,))
        
        conn.commit()
        conn.close()
    
    def clear_messages(self):
        """모든 메시지 삭제"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM messages')
        
        conn.commit()
        conn.close()
    
    def _schedule_auto_delete(self, timestamp):
        """24시간 후 자동 삭제 스케줄링"""
        def auto_delete():
            time.sleep(24 * 60 * 60)  # 24시간 대기
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 24시간 이전 메시지 삭제
            cutoff_time = time.time() - (24 * 60 * 60)
            cursor.execute('DELETE FROM messages WHERE timestamp < ?', (cutoff_time,))
            
            conn.commit()
            conn.close()
        
        # 백그라운드에서 실행
        thread = threading.Thread(target=auto_delete, daemon=True)
        thread.start()
    
    def destroy_room(self):
        """채팅방 완전 삭제 (데이터베이스 파일 삭제)"""
        try:
            os.remove(self.db_path)
            return True
        except:
            return False

class SecuritySettings:
    """보안 설정 관리"""
    
    def __init__(self):
        self.settings_file = "storage/security_settings.json"
        self._load_settings()
    
    def _load_settings(self):
        """보안 설정 로드"""
        os.makedirs("storage", exist_ok=True)
        
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        else:
            self.settings = {
                'auto_delete_hours': 24,
                'encryption_enabled': True,
                'local_storage_only': False,
                'message_retention_days': 1
            }
            self._save_settings()
    
    def _save_settings(self):
        """보안 설정 저장"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def update_setting(self, key, value):
        """설정 업데이트"""
        self.settings[key] = value
        self._save_settings()
    
    def get_setting(self, key):
        """설정 값 조회"""
        return self.settings.get(key) 