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
        """세션 정보 저장 (로그인 시간 포함)"""
        now = datetime.datetime.now()
        session_data = {
            "user_id": user_info.get("user_id"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "login_time": now.isoformat(),
            "expiry_date": user_info.get("expiry_date")
        }
        
        self.session_file.parent.mkdir(exist_ok=True)
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.session_data = session_data
    
    def is_session_expired(self) -> bool:
        """세션이 만료되었는지 확인 (1시간)"""
        if not self.session_data:
            return True
        
        login_time_str = self.session_data.get("login_time")
        if not login_time_str:
            return True
        
        try:
            login_time = datetime.datetime.fromisoformat(login_time_str)
            now = datetime.datetime.now()
            elapsed = (now - login_time).total_seconds()
            # 1시간 = 3600초
            return elapsed >= 3600
        except:
            return True
    
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
            # PC 프로그램이므로 device_uuid는 전송하지 않음 (모바일 앱 전용)
            
            response = requests.post(
                f"{self.server_url}/api/login",
                json=payload,
                timeout=10
            )
            
            # 응답 상태 코드에 따른 처리
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"서버 응답 JSON 파싱 실패: {e}, 응답 내용: {response.text[:200]}")
                return False, "서버 응답을 처리할 수 없습니다.", None
            
            if response.status_code == 200:
                # 성공 응답
                if data.get('success'):
                    user_info = data.get('user_info')
                    if user_info:
                        self.save_session(user_info)
                        logger.info(f"로그인 성공: {user_id}")
                        return True, "로그인 성공", user_info
                    else:
                        logger.error(f"로그인 응답에 user_info가 없습니다: {data}")
                        return False, "로그인 응답 형식이 올바르지 않습니다.", None
                else:
                    error_msg = data.get('message', '로그인 실패')
                    logger.warning(f"로그인 실패: {error_msg}")
                    return False, error_msg, None
            else:
                # 오류 응답 (400, 403, 500 등)
                error_msg = data.get('message', f'서버 오류가 발생했습니다. (상태 코드: {response.status_code})')
                logger.error(f"로그인 실패 (상태 코드 {response.status_code}): {error_msg}")
                return False, error_msg, None
                
        except requests.exceptions.ConnectionError:
            logger.error("서버 연결 실패")
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요.", None
        except requests.exceptions.Timeout:
            logger.error("서버 응답 시간 초과")
            return False, "서버 응답 시간이 초과되었습니다.", None
        except Exception as e:
            logger.error(f"로그인 오류: {e}", exc_info=True)
            return False, f"로그인 처리 중 오류가 발생했습니다: {str(e)}", None
    
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
    
    def register(self, user_id: str, password: str, name: str, email: str = "", phone: str = "") -> Tuple[bool, str]:
        """
        회원가입
        
        Args:
            user_id: 사용자 ID
            password: 비밀번호
            name: 이름
            email: 이메일 (선택사항)
            phone: 전화번호 (선택사항)
            
        Returns:
            (성공 여부, 메시지)
        """
        try:
            payload = {
                "user_id": user_id,
                "password": password,
                "name": name,
                "email": email,
                "phone": phone
            }
            
            response = requests.post(
                f"{self.server_url}/api/register",
                json=payload,
                timeout=10
            )
            
            # 응답 상태 코드에 따른 처리
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError) as e:
                logger.error(f"서버 응답 JSON 파싱 실패: {e}, 응답 내용: {response.text[:200]}")
                return False, f"서버 응답을 처리할 수 없습니다. (상태 코드: {response.status_code})"
            
            if response.status_code == 200:
                # 성공 응답
                if data.get('success'):
                    logger.info(f"회원가입 성공: {user_id}")
                    return True, data.get('message', '회원가입이 완료되었습니다.')
                else:
                    error_msg = data.get('message', '회원가입 실패')
                    logger.warning(f"회원가입 실패: {error_msg}")
                    return False, error_msg
            else:
                # 오류 응답 (400, 500 등)
                error_msg = data.get('message', f'서버 오류가 발생했습니다. (상태 코드: {response.status_code})')
                logger.error(f"회원가입 실패 (상태 코드 {response.status_code}): {error_msg}")
                return False, error_msg
                
        except requests.exceptions.ConnectionError:
            logger.error("서버 연결 실패")
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except requests.exceptions.Timeout:
            logger.error("서버 응답 시간 초과")
            return False, "서버 응답 시간이 초과되었습니다."
        except Exception as e:
            logger.error(f"회원가입 오류: {e}", exc_info=True)
            return False, f"회원가입 처리 중 오류가 발생했습니다: {str(e)}"
    
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
    
    def send_admin_message(self, category: str, title: str, content: str, phone: str = "") -> Tuple[bool, str]:
        """
        관리자에게 메시지 전송
        
        Args:
            category: 종류 (입금확인, 사용방법, 오류, 기타)
            title: 제목
            content: 내용
            phone: 회신받을 전화번호 (선택사항)
            
        Returns:
            (성공 여부, 메시지)
        """
        if not self.session_data or not self.session_data.get("user_id"):
            return False, "로그인이 필요합니다."
        
        user_id = self.session_data.get("user_id")
        
        try:
            payload = {
                "user_id": user_id,
                "category": category,
                "title": title,
                "content": content
            }
            
            if phone:
                payload["phone"] = phone
            
            response = requests.post(
                f"{self.server_url}/api/send_admin_message",
                json=payload,
                timeout=10
            )
            
            # 응답 상태 코드에 따른 처리
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        logger.info(f"관리자 메시지 전송 성공: {user_id}")
                        return True, data.get('message', '메시지가 전송되었습니다.')
                    else:
                        error_msg = data.get('message', '메시지 전송 실패')
                        logger.warning(f"관리자 메시지 전송 실패: {error_msg}")
                        return False, error_msg
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"서버 응답 JSON 파싱 실패: {e}, 응답 내용: {response.text[:200]}")
                    return False, "서버 응답을 처리할 수 없습니다."
            elif response.status_code == 400:
                # 클라이언트 오류 (필수 항목 누락 등)
                try:
                    data = response.json()
                    error_msg = data.get('message', '요청 데이터가 올바르지 않습니다.')
                    logger.warning(f"관리자 메시지 전송 실패 (400): {error_msg}")
                    return False, error_msg
                except (ValueError, json.JSONDecodeError):
                    return False, "필수 항목을 모두 입력해주세요."
            elif response.status_code == 500:
                # 서버 오류 (하지만 메시지는 전송되었을 수 있음)
                try:
                    data = response.json()
                    error_msg = data.get('message', '서버 오류가 발생했습니다.')
                    logger.error(f"관리자 메시지 전송 서버 오류 (500): {error_msg}")
                    # 500 에러지만 메시지는 도착했을 수 있으므로 안내
                    return False, f"{error_msg}\n(메시지는 전송되었을 수 있습니다. 텔레그램을 확인해주세요.)"
                except (ValueError, json.JSONDecodeError):
                    return False, "서버 오류가 발생했습니다.\n(메시지는 전송되었을 수 있습니다. 텔레그램을 확인해주세요.)"
            else:
                # 기타 오류
                try:
                    data = response.json()
                    error_msg = data.get('message', f'서버 오류가 발생했습니다. (상태 코드: {response.status_code})')
                    logger.error(f"관리자 메시지 전송 실패 (상태 코드 {response.status_code}): {error_msg}")
                    return False, error_msg
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"서버 응답 JSON 파싱 실패: {e}, 응답 내용: {response.text[:200]}")
                    return False, f"서버 응답을 처리할 수 없습니다. (상태 코드: {response.status_code})"
                
        except requests.exceptions.ConnectionError:
            logger.error("서버 연결 실패")
            return False, "서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except requests.exceptions.Timeout:
            logger.error("서버 응답 시간 초과")
            return False, "서버 응답 시간이 초과되었습니다."
        except Exception as e:
            logger.error(f"관리자 메시지 전송 오류: {e}", exc_info=True)
            return False, f"오류가 발생했습니다: {str(e)}"
    
    def check_token_owner(self, access_token: str, user_id: str) -> Tuple[bool, bool, str]:
        """
        토큰 소유자 확인
        
        Args:
            access_token: 액세스 토큰
            user_id: PC 프로그램 로그인 사용자 ID
            
        Returns:
            (성공 여부, 일치 여부, 메시지)
        """
        if not access_token or not user_id:
            return False, False, "토큰과 사용자 ID가 필요합니다."
        
        try:
            payload = {
                "access_token": access_token,
                "user_id": user_id
            }
            
            response = requests.post(
                f"{self.server_url}/api/check_token_owner",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    match = data.get('match', False)
                    message = data.get('message', '')
                    return True, match, message
                else:
                    return False, False, data.get('message', '확인 실패')
            else:
                data = response.json()
                return False, False, data.get('message', '서버 오류가 발생했습니다.')
                
        except requests.exceptions.ConnectionError:
            logger.error("서버 연결 실패")
            return False, False, "서버에 연결할 수 없습니다."
        except requests.exceptions.Timeout:
            logger.error("서버 응답 시간 초과")
            return False, False, "서버 응답 시간이 초과되었습니다."
        except Exception as e:
            logger.error(f"토큰 소유자 확인 오류: {e}", exc_info=True)
            return False, False, f"오류가 발생했습니다: {str(e)}"

