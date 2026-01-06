"""
라이선스 관리 모듈
"""

import json
import hashlib
import datetime
from pathlib import Path
from typing import Optional, Dict


class LicenseManager:
    """라이선스 관리 클래스"""
    
    def __init__(self):
        self.license_file = Path(__file__).parent.parent / "config" / "license.json"
        self.license_data: Optional[Dict] = None
        self.load_license()
    
    def load_license(self):
        """라이선스 파일 로드"""
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    self.license_data = json.load(f)
            except:
                self.license_data = None
        else:
            self.license_data = None
    
    def save_license(self, license_key: str, expiry_date: str):
        """라이선스 저장"""
        license_data = {
            "license_key": license_key,
            "expiry_date": expiry_date,
            "activated_date": datetime.datetime.now().isoformat()
        }
        
        self.license_file.parent.mkdir(exist_ok=True)
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
        
        self.license_data = license_data
    
    def validate_license(self) -> tuple[bool, str]:
        """
        라이선스 유효성 검사
        
        Returns:
            (유효 여부, 메시지)
        """
        if not self.license_data:
            return False, "라이선스가 등록되지 않았습니다."
        
        license_key = self.license_data.get("license_key", "")
        expiry_date_str = self.license_data.get("expiry_date", "")
        
        if not license_key or not expiry_date_str:
            return False, "라이선스 정보가 올바르지 않습니다."
        
        # 만료일 확인
        try:
            expiry_date = datetime.datetime.fromisoformat(expiry_date_str)
            if datetime.datetime.now() > expiry_date:
                return False, f"라이선스가 만료되었습니다. (만료일: {expiry_date_str[:10]})"
        except:
            return False, "라이선스 만료일 형식이 올바르지 않습니다."
        
        # 라이선스 키 검증 (간단한 해시 검증)
        # 실제로는 서버에서 검증해야 하지만, 여기서는 간단한 로컬 검증만
        expected_hash = hashlib.sha256(f"{license_key}{expiry_date_str}".encode()).hexdigest()
        
        return True, f"라이선스 유효 (만료일: {expiry_date_str[:10]})"
    
    def is_licensed(self) -> bool:
        """라이선스가 유효한지 확인"""
        valid, _ = self.validate_license()
        return valid
    
    def get_license_info(self) -> Dict:
        """라이선스 정보 반환"""
        if not self.license_data:
            return {}
        return {
            "license_key": self.license_data.get("license_key", "")[:8] + "..." if self.license_data.get("license_key") else "",
            "expiry_date": self.license_data.get("expiry_date", ""),
            "activated_date": self.license_data.get("activated_date", "")
        }


def generate_license_key(days: int = 30) -> tuple[str, str]:
    """
    라이선스 키 생성 (테스트용)
    
    Args:
        days: 유효 기간 (일)
        
    Returns:
        (license_key, expiry_date)
    """
    import secrets
    import string
    
    # 랜덤 라이선스 키 생성
    license_key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    
    # 만료일 계산
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
    expiry_date_str = expiry_date.isoformat()
    
    return license_key, expiry_date_str












