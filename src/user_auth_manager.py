"""
사용자 인증 관리 모듈
서버와 통신하여 사용자 인증 및 MAC 주소 검증
"""

import json
import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# 개발 모드: 환경 변수 또는 개발 모드 파일로 제어
DEV_MODE_FILE = Path(__file__).parent.parent / "config" / "dev_mode.txt"
DEV_MODE = False
if DEV_MODE_FILE.exists():
    try:
        with open(DEV_MODE_FILE, 'r', encoding='utf-8') as f:
            DEV_MODE = f.read().strip().lower() == 'true'
    except:
        pass

class UserAuthManager:
    """사용자 인증 관리 클래스"""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        초기화
        
        Args:
            server_url: 서버 URL
        """
        self.server_url = server_url.rstrip('/')
        self.session_file = Path(__file__).parent.parent / "config" / "session.json"
        self.session_data: Optional[Dict] = None
        self.load_session()
    
    def load_session(self):
        """세션 정보 로드"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    self.session_data = json.load(f)
            except Exception as e:
                logger.error(f"세션 파일 로드 실패: {e}")
                self.session_data = None
        else:
            self.session_data = None
    
    def save_session(self, user_info: Dict):
        """세션 정보 저장"""
        session_data = {
            "user_id": user_info.get("user_id"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "login_time": datetime.datetime.now().isoformat(),
            "expiry_date": user_info.get("expiry_date")
        }
        
        self.session_file.parent.mkdir(exist_ok=True)
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.session_data = session_data
    
    def clear_session(self):
        """세션 정보 삭제"""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception as e:
                logger.error(f"세션 파일 삭제 실패: {e}")
        self.session_data = None
    
    def login(self, user_id: str, password: str, hardware_id: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        로그인
        
        Args:
            user_id: 사용자 ID
            password: 비밀번호
            hardware_id: 하드웨어 ID (선택사항)
            
        Returns:
            (성공 여부, 메시지, 사용자 정보)
        """
        if DEV_MODE:
            logger.warning("⚠️ 개발 모드: 로그인을 우회합니다.")
            return True, "로그인 성공 (개발 모드)", {"user_id": user_id, "name": "개발자", "is_active": True}
        
        try:
            payload = {
                "user_id": user_id,
                "password": password
            }
            if hardware_id:
                payload["hardware_id"] = hardware_id
            
            response = requests.post(
                f"{self.server_url}/api/login",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    user_info = data.get('user_info', {})
                    self.save_session(user_info)
                    logger.info(f"로그인 성공: {user_id}")
                    return True, "로그인 성공", user_info
                else:
                    return False, data.get('message', '로그인 실패'), None
            else:
                data = response.json()
                return False, data.get('message', '서버 오류가 발생했습니다.'), None
                
        except requests.exceptions.ConnectionError:
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요.", None
        except requests.exceptions.Timeout:
            return False, "서버 응답 시간이 초과되었습니다.", None
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            return False, f"오류가 발생했습니다: {str(e)}", None
    
    def logout(self, user_id: str) -> Tuple[bool, str]:
        """
        로그아웃
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            (성공 여부, 메시지)
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/logout",
                json={"user_id": user_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.clear_session()
                    logger.info(f"로그아웃: {user_id}")
                    return True, "로그아웃되었습니다."
                else:
                    return False, data.get('message', '로그아웃 실패')
            else:
                return False, "서버 오류가 발생했습니다."
                
        except Exception as e:
            logger.error(f"로그아웃 오류: {e}")
            self.clear_session()  # 오류 발생 시에도 세션 삭제
            return True, "로그아웃되었습니다."  # 클라이언트에서는 성공으로 처리
    
    def verify_mac_address(self, user_id: str, mac_address: str, hardware_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        MAC 주소 검증
        
        Args:
            user_id: 사용자 ID
            mac_address: MAC 주소
            hardware_id: 하드웨어 ID (선택사항)
            
        Returns:
            (허용 여부, 메시지)
        """
        if DEV_MODE:
            logger.warning("⚠️ 개발 모드: MAC 주소 검증을 우회합니다.")
            return True, "MAC 주소 검증 완료 (개발 모드)"
        
        if not user_id or not mac_address:
            return False, "사용자 ID와 MAC 주소가 필요합니다."
        
        try:
            payload = {
                "user_id": user_id,
                "mac_address": mac_address.upper()
            }
            if hardware_id:
                payload["hardware_id"] = hardware_id
            
            response = requests.post(
                f"{self.server_url}/api/verify_mac_address",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('allowed'):
                    logger.info(f"MAC 주소 검증 성공: {user_id}, {mac_address}")
                    return True, "허용된 사용자입니다."
                else:
                    logger.warning(f"MAC 주소 검증 실패: {user_id}, {mac_address}")
                    return False, data.get('message', '등록되지 않은 사용자입니다.')
            else:
                data = response.json()
                return False, data.get('message', '서버 오류가 발생했습니다.')
                
        except requests.exceptions.ConnectionError:
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except Exception as e:
            logger.error(f"MAC 주소 검증 오류: {e}")
            return False, f"오류가 발생했습니다: {str(e)}"
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        사용자 정보 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 정보 딕셔너리 또는 None
        """
        if DEV_MODE:
            return {"user_id": user_id, "name": "개발자", "is_active": True}
        
        try:
            response = requests.post(
                f"{self.server_url}/api/user_info",
                json={"user_id": user_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('user_info')
            return None
                
        except Exception as e:
            logger.error(f"사용자 정보 조회 오류: {e}")
            return None
    
    def record_usage(self, user_id: str, total_invoices: int, success_count: int, fail_count: int, 
                     mac_address: Optional[str] = None, hardware_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        사용량 기록
        
        Args:
            user_id: 사용자 ID
            total_invoices: 총 송장 수
            success_count: 성공 건수
            fail_count: 실패 건수
            mac_address: MAC 주소 (선택사항)
            hardware_id: 하드웨어 ID (선택사항)
            
        Returns:
            (성공 여부, 메시지)
        """
        if not user_id:
            return False, "사용자 ID가 필요합니다."
        
        try:
            payload = {
                "user_id": user_id,
                "total_invoices": total_invoices,
                "success_count": success_count,
                "fail_count": fail_count
            }
            if mac_address:
                payload["mac_address"] = mac_address.upper()
            if hardware_id:
                payload["hardware_id"] = hardware_id
            
            response = requests.post(
                f"{self.server_url}/api/record_user_usage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info("사용량 기록 성공")
                    return True, "사용량이 기록되었습니다."
                else:
                    return False, data.get('message', '사용량 기록 실패')
            else:
                return False, "서버 오류가 발생했습니다."
                
        except requests.exceptions.ConnectionError:
            logger.warning("서버 연결 실패, 사용량 기록 건너뜀")
            return False, "서버에 연결할 수 없습니다. 사용량은 기록되지 않았습니다."
        except Exception as e:
            logger.error(f"사용량 기록 오류: {e}")
            return False, f"오류가 발생했습니다: {str(e)}"

