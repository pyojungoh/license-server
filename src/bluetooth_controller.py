"""
BLT AI 로봇 블루투스 컨트롤러 모듈
BLT AI 로봇과 시리얼 통신을 통해 블루투스 HID 키보드로 텍스트를 전송합니다.
"""

import serial
import time
from typing import Optional
import logging

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
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("BLT AI 로봇 연결 종료")
    
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
    
    def get_connected_mac_address(self) -> Optional[str]:
        """
        ESP32를 통해 연결된 모바일 기기의 MAC 주소 확인
        
        Returns:
            MAC 주소 (예: "AA:BB:CC:DD:EE:FF") 또는 None
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("BLT AI 로봇이 연결되지 않았습니다.")
            return None
        
        try:
            # 기존 버퍼 비우기
            self.serial_conn.reset_input_buffer()
            
            # "GET_CONNECTED_MAC" 명령 전송
            command = "GET_CONNECTED_MAC\n"
            self.serial_conn.write(command.encode('utf-8'))
            self.serial_conn.flush()
            
            # 응답 대기 (최대 2초)
            timeout_time = time.time() + 2.0
            response_lines = []
            
            while time.time() < timeout_time:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        logger.debug(f"ESP32 응답: {line}")
                        
                        # "MAC:" 접두사가 있는 경우 처리
                        if line.startswith('MAC:'):
                            mac_part = line[4:].strip()  # "MAC:" 제거
                            # MAC 주소 형식 확인 (XX:XX:XX:XX:XX:XX)
                            if ':' in mac_part and len(mac_part.split(':')) == 6:
                                # MAC 주소 추출 (공백 제거, 대문자로 변환)
                                mac = mac_part.replace(' ', '').replace('-', ':').upper()
                                if len(mac) == 17:  # MAC 주소 길이 확인
                                    logger.info(f"MAC 주소 수신: {mac}")
                                    return mac
                        # "MAC:" 접두사 없이 MAC 주소만 있는 경우
                        elif ':' in line and len(line.split(':')) == 6:
                            mac = line.replace(' ', '').replace('-', ':').upper()
                            if len(mac) == 17:
                                logger.info(f"MAC 주소 수신: {mac}")
                                return mac
                time.sleep(0.1)
            
            logger.warning(f"MAC 주소 수신 타임아웃. 응답: {response_lines}")
            return None
            
        except Exception as e:
            logger.error(f"MAC 주소 확인 실패: {e}")
            return None
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.disconnect()

