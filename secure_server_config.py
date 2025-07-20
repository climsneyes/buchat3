"""
자체 서버 기반 보안 채팅 시스템 설정
- AWS, GCP, Azure 등 VPS 사용
- 데이터 완전 통제 가능
- 한국 서버로 개인정보 보호
"""

import os
import json
from datetime import datetime

class SecureServerConfig:
    """보안 서버 설정"""
    
    # 추천 VPS 서비스들
    VPS_OPTIONS = {
        "aws_lightsail": {
            "name": "AWS Lightsail",
            "price": "월 $3.50부터",
            "location": "서울 리전",
            "features": ["한국 법률 적용", "데이터 완전 통제", "자동 백업"]
        },
        "gcp_compute": {
            "name": "Google Cloud Compute",
            "price": "월 $5부터", 
            "location": "서울 리전",
            "features": ["한국 데이터센터", "고성능", "확장성"]
        },
        "azure_vm": {
            "name": "Microsoft Azure VM",
            "price": "월 $4부터",
            "location": "서울 리전", 
            "features": ["한국 법률 준수", "엔터프라이즈급 보안"]
        },
        "naver_cloud": {
            "name": "네이버 클라우드",
            "price": "월 3만원부터",
            "location": "한국",
            "features": ["100% 한국 서버", "개인정보보호법 준수", "한국어 지원"]
        },
        "kt_cloud": {
            "name": "KT 클라우드",
            "price": "월 2.5만원부터",
            "location": "한국",
            "features": ["국내 서버", "통신사급 보안", "24/7 한국어 지원"]
        }
    }
    
    def __init__(self):
        self.config_file = "secure_server_config.json"
        self._load_config()
    
    def _load_config(self):
        """설정 로드"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'server_type': 'naver_cloud',
                'auto_delete_hours': 24,
                'encryption_enabled': True,
                'backup_enabled': True,
                'korean_law_compliance': True
            }
            self._save_config()
    
    def _save_config(self):
        """설정 저장"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get_server_info(self, server_type):
        """서버 정보 조회"""
        return self.VPS_OPTIONS.get(server_type, {})
    
    def update_config(self, key, value):
        """설정 업데이트"""
        self.config[key] = value
        self._save_config()

class SecurityFeatures:
    """보안 기능 설명"""
    
    @staticmethod
    def get_security_comparison():
        """보안 수준 비교"""
        return {
            "firebase": {
                "level": "낮음",
                "risks": [
                    "미국 법률 적용 (CLOUD Act)",
                    "Google 서버에 데이터 저장",
                    "정부 요청 시 데이터 접근 가능",
                    "개인정보 유출 시 대규모 피해"
                ],
                "privacy": "개인정보 수집 및 분석 가능"
            },
            "self_hosted_korea": {
                "level": "높음", 
                "benefits": [
                    "한국 법률 적용 (개인정보보호법)",
                    "데이터 완전 통제",
                    "서버 위치 직접 관리",
                    "필요시 즉시 데이터 삭제"
                ],
                "privacy": "개인정보 완전 보호"
            },
            "hybrid_approach": {
                "level": "중간",
                "benefits": [
                    "중요 데이터는 로컬 암호화",
                    "일반 데이터만 클라우드",
                    "비용 절약",
                    "보안과 편의성 균형"
                ],
                "privacy": "선택적 개인정보 보호"
            }
        }
    
    @staticmethod
    def get_korean_law_benefits():
        """한국 법률 준수 혜택"""
        return [
            "개인정보보호법 완전 준수",
            "개인정보처리방침 한국어 제공",
            "개인정보 유출 시 한국 법원 관할",
            "개인정보보호위원회 감독",
            "개인정보 삭제 요청 즉시 처리",
            "한국어 개인정보 처리 동의"
        ]

class CostAnalysis:
    """비용 분석"""
    
    @staticmethod
    def get_cost_comparison():
        """비용 비교"""
        return {
            "firebase": {
                "monthly": "무료 (사용량 제한)",
                "yearly": "약 10-50만원",
                "hidden_costs": [
                    "개인정보 유출 위험",
                    "법적 분쟁 비용",
                    "브랜드 이미지 손실"
                ]
            },
            "self_hosted": {
                "monthly": "3-5만원",
                "yearly": "36-60만원", 
                "benefits": [
                    "데이터 완전 통제",
                    "개인정보 보호",
                    "법적 안정성",
                    "브랜드 신뢰도 향상"
                ]
            }
        } 