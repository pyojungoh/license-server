"""
BLT AI 로봇 블루투스 컨트롤러 모듈
BLT AI 로봇과 시리얼 통신을 통해 블루투스 HID 키보드로 텍스트를 전송합니다.
"""

import serial
import time
from typing import Optional, Callable
import logging
import threading

logger = logging.getLogger(__name__)


class BluetoothController:
    """BLT AI 로봇과 시리얼 통신을 통한 블루투스 HID 키보드 제어"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        """
        초기화
        
        Args:
            port: COM 포트 번호 (예: 'COM3')
            baudrate: 보레이트 (기본값: 115200)
            timeout: 타임아웃 (초)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.serial_monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        self.serial_log_callback: Optional[Callable[[str], None]] = None
    
    def connect(self) -> bool:
        """
        BLT AI 로봇과 시리얼 연결
        
        Returns:
            연결 성공 여부
        """
        try:
            logger.info(f"BLT AI 로봇 연결 시도: {self.port} (보레이트: {self.baudrate})")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            # 연결 안정화 대기
            time.sleep(2)
            logger.info("BLT AI 로봇 연결 성공")
            return True
        except serial.SerialException as e:
            logger.error(f"시리얼 포트 연결 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"연결 실패: {e}")
            return False
    
    def disconnect(self):
        """연결 종료"""
        # 시리얼 모니터링 중지
        self.stop_serial_monitoring()
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("BLT AI 로봇 연결 종료")
    
    def start_serial_monitoring(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        AI BOT 시리얼 메시지를 백그라운드에서 모니터링하여 로그로 표시
        
        Args:
            log_callback: 시리얼 메시지를 전달할 콜백 함수 (선택사항)
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.warning("시리얼 연결이 없어 모니터링을 시작할 수 없습니다.")
            return
        
        if self.monitor_running:
            logger.debug("시리얼 모니터링이 이미 실행 중입니다.")
            return
        
        self.serial_log_callback = log_callback
        self.monitor_running = True
        
        def monitor_loop():
            """시리얼 메시지를 읽는 스레드 함수"""
            logger.debug("AI BOT 시리얼 모니터링 시작")
            if self.serial_log_callback:
                self.serial_log_callback("AI BOT 시리얼 모니터링 시작")
            
            while self.monitor_running and self.serial_conn and self.serial_conn.is_open:
                try:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            # "전송 완료 (송장번호 + Tab..." 메시지는 필터링 (표시하지 않음)
                            if "전송 완료" in line and "Tab" in line:
                                logger.debug(f"AI BOT (필터링됨): {line}")
                                continue
                            
                            # 로그 콜백으로 전달
                            if self.serial_log_callback:
                                self.serial_log_callback(f"[AI BOT] {line}")
                            logger.debug(f"AI BOT: {line}")
                    time.sleep(0.1)  # CPU 사용량 감소
                except Exception as e:
                    if self.monitor_running:  # 정상 종료가 아닌 경우만 로그
                        logger.error(f"시리얼 모니터링 오류: {e}")
                    break
            
            logger.debug("AI BOT 시리얼 모니터링 종료")
            if self.serial_log_callback:
                self.serial_log_callback("AI BOT 시리얼 모니터링 종료")
        
        self.serial_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.serial_monitor_thread.start()
    
    def stop_serial_monitoring(self):
        """시리얼 모니터링 중지"""
        if self.monitor_running:
            self.monitor_running = False
            if self.serial_monitor_thread:
                self.serial_monitor_thread.join(timeout=1.0)
            self.serial_monitor_thread = None
            self.serial_log_callback = None
            logger.debug("AI BOT 시리얼 모니터링 중지 요청")
    
    def send_text(self, text: str) -> bool:
        """
        텍스트를 BLT AI 로봇으로 전송 (블루투스 키보드 입력으로 변환됨)
        
        Args:
            text: 전송할 텍스트 (송장번호 등)
            
        Returns:
            전송 성공 여부
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("BLT AI 로봇이 연결되지 않았습니다.")
            return False
        
        try:
            # 텍스트 + 개행 문자 전송
            message = f"{text}\n"
            self.serial_conn.write(message.encode('utf-8'))
            self.serial_conn.flush()  # 버퍼 비우기
            logger.debug(f"텍스트 전송: {text}")
            return True
        except serial.SerialTimeoutException:
            logger.error("전송 타임아웃")
            return False
        except Exception as e:
            logger.error(f"전송 실패: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        연결 상태 확인
        
        Returns:
            연결 여부
        """
        return self.serial_conn is not None and self.serial_conn.is_open
    
    def get_connected_mac_address(self, log_callback=None) -> tuple[Optional[str], list[str]]:
        """
        AI BOT을 통해 연결된 모바일 기기의 MAC 주소 확인
        
        Args:
            log_callback: 로그 메시지를 전달할 콜백 함수 (선택사항)
        
        Returns:
            (MAC 주소, 응답 메시지 리스트) 튜플
            MAC 주소 (예: "AA:BB:CC:DD:EE:FF") 또는 None
            응답 메시지 리스트는 모든 AI BOT 응답을 포함
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            msg = "BLT AI 로봇이 연결되지 않았습니다."
            logger.error(msg)
            if log_callback:
                log_callback(msg)
            return None, []
        
        try:
            # 기존 버퍼 비우기
            self.serial_conn.reset_input_buffer()
            if log_callback:
                log_callback("AI BOT에 MAC 주소 요청 전송 중...")
            
            # "GET_CONNECTED_MAC" 명령 전송
            command = "GET_CONNECTED_MAC\n"
            self.serial_conn.write(command.encode('utf-8'))
            self.serial_conn.flush()
            if log_callback:
                log_callback(f"AI BOT 명령 전송: GET_CONNECTED_MAC")
            
            # 응답 대기 (최대 3초)
            timeout_time = time.time() + 3.0
            response_lines = []
            
            while time.time() < timeout_time:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        if log_callback:
                            log_callback(f"AI BOT 응답: {line}")
                        logger.debug(f"AI BOT 응답: {line}")
                        
                        # "MAC:" 접두사가 있는 경우 처리
                        if line.startswith('MAC:'):
                            mac_part = line[4:].strip()  # "MAC:" 제거
                            # MAC 주소 형식 확인 (XX:XX:XX:XX:XX:XX)
                            if ':' in mac_part and len(mac_part.split(':')) == 6:
                                # MAC 주소 추출 (공백 제거, 대문자로 변환)
                                mac = mac_part.replace(' ', '').replace('-', ':').upper()
                                if len(mac) == 17:  # MAC 주소 길이 확인
                                    msg = f"MAC 주소 수신: {mac}"
                                    logger.info(msg)
                                    if log_callback:
                                        log_callback(msg)
                                    return mac, response_lines
                        # "MAC:" 접두사 없이 MAC 주소만 있는 경우
                        elif ':' in line and len(line.split(':')) == 6:
                            mac = line.replace(' ', '').replace('-', ':').upper()
                            if len(mac) == 17:
                                msg = f"MAC 주소 수신: {mac}"
                                logger.info(msg)
                                if log_callback:
                                    log_callback(msg)
                                return mac, response_lines
                time.sleep(0.1)
            
            msg = f"MAC 주소 수신 타임아웃 (3초). 받은 응답: {response_lines if response_lines else '없음'}"
            logger.warning(msg)
            if log_callback:
                log_callback(msg)
            return None, response_lines
            
        except Exception as e:
            msg = f"MAC 주소 확인 실패: {e}"
            logger.error(msg)
            if log_callback:
                log_callback(msg)
            return None, []
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.connect()
        return self
    
    def get_token(self, log_callback=None) -> Optional[str]:
        """
        ESP32에 등록된 토큰 조회
        
        Args:
            log_callback: 로그 메시지를 전달할 콜백 함수 (선택사항)
        
        Returns:
            토큰 문자열 또는 None (토큰이 없거나 조회 실패 시)
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            msg = "BLT AI 로봇이 연결되지 않았습니다."
            logger.error(msg)
            if log_callback:
                log_callback(msg)
            return None
        
        try:
            # 기존 버퍼 비우기
            self.serial_conn.reset_input_buffer()
            if log_callback:
                log_callback("AI BOT에 토큰 조회 요청 전송 중...")
            
            # "GET_TOKEN" 명령 전송
            command = "GET_TOKEN\n"
            self.serial_conn.write(command.encode('utf-8'))
            self.serial_conn.flush()
            if log_callback:
                log_callback("AI BOT 명령 전송: GET_TOKEN")
            
            # 응답 대기 (최대 2초)
            timeout_time = time.time() + 2.0
            
            while time.time() < timeout_time:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        if log_callback:
                            log_callback(f"AI BOT 응답: {line}")
                        logger.debug(f"AI BOT 응답: {line}")
                        
                        # "TOKEN:" 접두사가 있는 경우 처리
                        if line.startswith('TOKEN:'):
                            token_part = line[6:].strip()  # "TOKEN:" 제거
                            if token_part == "NOT_SET":
                                msg = "ESP32에 토큰이 등록되지 않았습니다."
                                logger.warning(msg)
                                if log_callback:
                                    log_callback(msg)
                                return None
                            elif token_part:
                                logger.info("토큰 조회 성공")
                                if log_callback:
                                    log_callback("토큰 조회 성공")
                                return token_part
                time.sleep(0.1)
            
            msg = "토큰 조회 타임아웃 (2초)"
            logger.warning(msg)
            if log_callback:
                log_callback(msg)
            return None
            
        except Exception as e:
            msg = f"토큰 조회 실패: {e}"
            logger.error(msg)
            if log_callback:
                log_callback(msg)
            return None
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.disconnect()

