"""
온라인 라이선스 관리 모듈
서버와 통신하여 라이선스 인증 및 검증
"""

import json
import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
from hardware_id import get_hardware_id

logger = logging.getLogger(__name__)

class OnlineLicenseManager:
    """온라인 라이선스 관리 클래스"""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        초기화
        
        Args:
            server_url: 라이선스 서버 URL
        """
        self.server_url = server_url.rstrip('/')
        self.license_file = Path(__file__).parent.parent / "config" / "license.json"
        self.license_data: Optional[Dict] = None
        self.hardware_id = get_hardware_id()
        self.load_license()
    
    def load_license(self):
        """로컬 라이선스 파일 로드"""
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    self.license_data = json.load(f)
            except Exception as e:
                logger.error(f"라이선스 파일 로드 실패: {e}")
                self.license_data = None
        else:
            self.license_data = None
    
    def save_license(self, license_key: str, expiry_date: str):
        """로컬 라이선스 파일 저장"""
        license_data = {
            "license_key": license_key,
            "expiry_date": expiry_date,
            "hardware_id": self.hardware_id,
            "activated_date": datetime.datetime.now().isoformat()
        }
        
        self.license_file.parent.mkdir(exist_ok=True)
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
        
        self.license_data = license_data
    
    def activate_license(self, license_key: str, customer_name: str = "", customer_email: str = "") -> Tuple[bool, str]:
        """
        라이선스 활성화 (서버에 등록)
        
        Args:
            license_key: 라이선스 키
            customer_name: 고객명
            customer_email: 고객 이메일
            
        Returns:
            (성공 여부, 메시지)
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/activate",
                json={
                    "license_key": license_key.upper(),
                    "hardware_id": self.hardware_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    expiry_date = data.get('expiry_date')
                    self.save_license(license_key.upper(), expiry_date)
                    logger.info("라이선스 활성화 성공")
                    return True, "라이선스가 활성화되었습니다."
                else:
                    return False, data.get('message', '라이선스 활성화 실패')
            else:
                data = response.json()
                return False, data.get('message', '서버 오류가 발생했습니다.')
                
        except requests.exceptions.ConnectionError:
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except requests.exceptions.Timeout:
            return False, "서버 응답 시간이 초과되었습니다."
        except Exception as e:
            logger.error(f"라이선스 활성화 오류: {e}")
            return False, f"오류가 발생했습니다: {str(e)}"
    
    def verify_license(self, force_online: bool = False) -> Tuple[bool, str]:
        """
        라이선스 검증
        
        Args:
            force_online: 강제로 온라인 검증 (기본값: False, 주기적 검증)
            
        Returns:
            (유효 여부, 메시지)
        """
        if not self.license_data:
            return False, "라이선스가 등록되지 않았습니다."
        
        license_key = self.license_data.get("license_key", "")
        stored_hw_id = self.license_data.get("hardware_id", "")
        
        # 하드웨어 ID 확인
        if stored_hw_id != self.hardware_id:
            return False, "라이선스가 다른 컴퓨터에 등록되어 있습니다."
        
        # 로컬 만료일 확인
        expiry_date_str = self.license_data.get("expiry_date", "")
        if expiry_date_str:
            try:
                expiry_date = datetime.datetime.fromisoformat(expiry_date_str)
                if datetime.datetime.now() > expiry_date:
                    return False, f"라이선스가 만료되었습니다. (만료일: {expiry_date.strftime('%Y-%m-%d')})"
            except:
                pass
        
        # 온라인 검증 (매일 1회 또는 강제 검증)
        should_verify_online = force_online
        if not force_online:
            last_verified = self.license_data.get("last_verified", "")
            if last_verified:
                try:
                    last_date = datetime.datetime.fromisoformat(last_verified)
                    # 24시간마다 온라인 검증
                    if (datetime.datetime.now() - last_date).total_seconds() > 86400:
                        should_verify_online = True
                except:
                    should_verify_online = True
            else:
                should_verify_online = True
        
        if should_verify_online:
            try:
                response = requests.post(
                    f"{self.server_url}/api/verify",
                    json={
                        "license_key": license_key,
                        "hardware_id": self.hardware_id
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        # 검증 시간 업데이트
                        self.license_data["last_verified"] = datetime.datetime.now().isoformat()
                        self.license_data["expiry_date"] = data.get('expiry_date', expiry_date_str)
                        with open(self.license_file, 'w', encoding='utf-8') as f:
                            json.dump(self.license_data, f, indent=2, ensure_ascii=False)
                        return True, "라이선스가 유효합니다."
                    else:
                        return False, data.get('message', '라이선스 검증 실패')
                else:
                    # 온라인 검증 실패해도 로컬 검증 통과면 경고만
                    logger.warning("온라인 검증 실패, 로컬 검증 사용")
                    return True, "라이선스가 유효합니다. (오프라인 모드)"
                    
            except requests.exceptions.ConnectionError:
                # 인터넷 연결 없으면 로컬 검증만 사용
                logger.warning("서버 연결 실패, 로컬 검증 사용")
                return True, "라이선스가 유효합니다. (오프라인 모드)"
            except Exception as e:
                logger.warning(f"온라인 검증 오류: {e}, 로컬 검증 사용")
                return True, "라이선스가 유효합니다. (오프라인 모드)"
        
        return True, "라이선스가 유효합니다."
    
    def is_licensed(self) -> bool:
        """라이선스가 유효한지 확인"""
        valid, _ = self.verify_license()
        return valid
    
    def get_license_info(self) -> Dict:
        """라이선스 정보 반환"""
        if not self.license_data:
            return {}
        
        expiry_date_str = self.license_data.get("expiry_date", "")
        expiry_date_display = ""
        if expiry_date_str:
            try:
                expiry_date = datetime.datetime.fromisoformat(expiry_date_str)
                expiry_date_display = expiry_date.strftime("%Y-%m-%d")
            except:
                expiry_date_display = expiry_date_str[:10]
        
        return {
            "license_key": self.license_data.get("license_key", "")[:8] + "..." if self.license_data.get("license_key") else "",
            "expiry_date": expiry_date_display,
            "hardware_id": self.hardware_id[:8] + "..."
        }
    
    def extend_license(self, period_days: int = 30, amount: float = 0) -> Tuple[bool, str]:
        """
        라이선스 연장 (구독 갱신)
        
        Args:
            period_days: 연장 기간 (일)
            amount: 결제 금액
            
        Returns:
            (성공 여부, 메시지)
        """
        if not self.license_data:
            return False, "라이선스가 등록되지 않았습니다."
        
        license_key = self.license_data.get("license_key", "")
        
        try:
            response = requests.post(
                f"{self.server_url}/api/extend_license",
                json={
                    "license_key": license_key,
                    "period_days": period_days,
                    "amount": amount
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    expiry_date = data.get('expiry_date')
                    self.license_data["expiry_date"] = expiry_date
                    with open(self.license_file, 'w', encoding='utf-8') as f:
                        json.dump(self.license_data, f, indent=2, ensure_ascii=False)
                    logger.info("라이선스 연장 성공")
                    return True, f"라이선스가 {period_days}일 연장되었습니다."
                else:
                    return False, data.get('message', '라이선스 연장 실패')
            else:
                return False, "서버 오류가 발생했습니다."
                
        except requests.exceptions.ConnectionError:
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except Exception as e:
            logger.error(f"라이선스 연장 오류: {e}")
            return False, f"오류가 발생했습니다: {str(e)}"

