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
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.disconnect()

