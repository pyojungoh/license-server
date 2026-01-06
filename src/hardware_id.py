"""
하드웨어 ID 추출 모듈
컴퓨터 고유 식별자 생성
"""

import platform
import hashlib
import subprocess
import uuid

def get_hardware_id() -> str:
    """
    컴퓨터 고유 하드웨어 ID 생성
    
    Returns:
        하드웨어 ID (해시값)
    """
    # 여러 하드웨어 정보 수집
    hw_info = []
    
    try:
        # CPU 정보
        if platform.system() == 'Windows':
            try:
                cpu_id = subprocess.check_output('wmic cpu get ProcessorId', shell=True).decode().strip()
                if cpu_id and 'ProcessorId' not in cpu_id:
                    hw_info.append(cpu_id.split()[0])
            except:
                pass
            
            # 하드디스크 시리얼
            try:
                disk_id = subprocess.check_output('wmic diskdrive get serialnumber', shell=True).decode().strip()
                if disk_id and 'SerialNumber' not in disk_id:
                    hw_info.append(disk_id.split()[0])
            except:
                pass
            
            # MAC 주소
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
            hw_info.append(mac)
        else:
            # Linux/Mac
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                               for elements in range(0, 2*6, 2)][::-1])
                hw_info.append(mac)
            except:
                pass
            
            # 머신 ID
            try:
                with open('/etc/machine-id', 'r') as f:
                    hw_info.append(f.read().strip())
            except:
                pass
        
        # 플랫폼 정보
        hw_info.append(platform.processor())
        hw_info.append(platform.machine())
        
    except Exception as e:
        # 오류 발생 시 기본값 사용
        hw_info.append(str(uuid.getnode()))
    
    # 모든 정보를 합쳐서 해시 생성
    combined = ''.join(filter(None, hw_info))
    hardware_id = hashlib.sha256(combined.encode()).hexdigest()[:32].upper()
    
    return hardware_id

if __name__ == "__main__":
    # 테스트
    hw_id = get_hardware_id()
    print(f"하드웨어 ID: {hw_id}")












