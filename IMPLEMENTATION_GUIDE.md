# 구현 가이드 - 단계별 실행 매뉴얼

## 🚀 제품 도착 후 즉시 시작하기

이 가이드는 ESP32 개발 보드를 받은 후 바로 코딩을 시작할 수 있도록 단계별로 안내합니다.

---

## Step 0: CH340 드라이버 설치 (5분) ⚠️ 먼저 해야 할 일!

**ESP32를 연결하기 전에 드라이버를 먼저 설치하는 것을 권장합니다!**

### 0.1 드라이버 다운로드
1. [WCH 공식 사이트 방문](http://www.wch.cn/downloads/CH341SER_EXE.html)
2. **CH341SER.EXE** 파일 다운로드

### 0.2 드라이버 설치
1. 다운로드한 **CH341SER.EXE** 실행
2. 관리자 권한 요청 시 **예** 클릭
3. **INSTALL** 버튼 클릭
4. "The driver has been installed successfully!" 메시지 확인

> 📖 **상세 가이드**: `DRIVER_INSTALL.md` 파일 참고

**체크리스트**:
- [ ] CH340 드라이버 다운로드 완료
- [ ] 드라이버 설치 완료

---

## Step 1: 하드웨어 연결 및 확인 (10분)

### 1.1 ESP32 연결
1. ESP32 개발 보드를 PC의 USB 포트에 연결 (USB-C 케이블 사용)
2. Windows에서 장치 인식 대기 (약 10초)

### 1.2 COM 포트 확인
1. `Win + X` → 장치 관리자
2. 포트(COM & LPT) 확장
3. **USB-SERIAL CH340 (COMx)** 확인
   - ✅ 정상: **USB-SERIAL CH340 (COM3)** 같은 항목이 보임
   - ❌ 문제: **알 수 없는 장치** 또는 **느낌표(!)** 표시
4. COM 번호 기록 (예: COM3, COM4 등)

### 1.3 드라이버 문제 해결 (필요시)
- Windows 10/11은 대부분 자동 인식되지만, 안 되면:
  - `DRIVER_INSTALL.md`의 트러블슈팅 섹션 참고
  - 드라이버 재설치

**체크리스트**:
- [ ] ESP32가 PC에 연결됨
- [ ] COM 포트 번호 확인 완료 (예: COM3)
- [ ] 드라이버 정상 작동 확인

---

## Step 2: Arduino IDE 설정 (30분)

### 2.1 Arduino IDE 설치
1. [Arduino IDE 다운로드](https://www.arduino.cc/en/software)
2. 설치 실행 (기본 설정으로 진행)

### 2.2 ESP32 보드 패키지 추가
1. Arduino IDE 실행
2. **파일 → 환경설정** (또는 `Ctrl + ,`)
3. **추가 보드 관리자 URL**에 다음 URL 추가:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. **확인** 클릭

### 2.3 ESP32 보드 설치
1. **도구 → 보드 → 보드 관리자**
2. 검색창에 `esp32` 입력
3. **esp32 by Espressif Systems** 선택
4. **설치** 클릭 (다운로드 및 설치에 시간 소요)

### 2.4 보드 및 포트 선택
1. **도구 → 보드 → ESP32 Arduino → ESP32 Dev Module**
2. **도구 → 포트 → COMx** (Step 1.2에서 확인한 포트)

### 2.5 BLE 키보드 라이브러리 설치
1. **스케치 → 라이브러리 포함하기 → 라이브러리 관리**
2. 검색창에 `ESP32 BLE Keyboard` 입력
3. **ESP32 BLE Keyboard by Neil Kolban** 설치

**체크리스트**:
- [ ] Arduino IDE 설치 완료
- [ ] ESP32 보드 패키지 설치 완료
- [ ] 보드 및 포트 선택 완료
- [ ] BLE 키보드 라이브러리 설치 완료

---

## Step 3: 펌웨어 개발 및 업로드 (1시간)

### 3.1 펌웨어 파일 생성
1. Arduino IDE에서 **파일 → 새 파일**
2. 다음 코드를 입력 (기본 템플릿):

```cpp
#include <BleKeyboard.h>

BleKeyboard bleKeyboard("한진택배 스캐너", "제조사", 100);

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 BLE HID 키보드 시작");
  bleKeyboard.begin();
}

void loop() {
  if (bleKeyboard.isConnected()) {
    if (Serial.available()) {
      String text = Serial.readStringUntil('\n');
      text.trim();
      
      if (text.length() > 0) {
        Serial.print("전송: ");
        Serial.println(text);
        bleKeyboard.print(text);
        bleKeyboard.write(KEY_RETURN); // 엔터 키
        delay(100);
      }
    }
  } else {
    Serial.println("블루투스 연결 대기 중...");
    delay(1000);
  }
}
```

### 3.2 펌웨어 업로드
1. ESP32를 PC에 연결
2. **스케치 → 업로드** (또는 `Ctrl + U`)
3. 업로드 완료 대기 (약 30초)

**주의**: 업로드 중 ESP32의 BOOT 버튼을 눌러야 할 수 있음

### 3.3 시리얼 모니터 테스트
1. **도구 → 시리얼 모니터** (또는 `Ctrl + Shift + M`)
2. 보레이트: **115200** 선택
3. "블루투스 연결 대기 중..." 메시지 확인

**체크리스트**:
- [ ] 펌웨어 업로드 성공
- [ ] 시리얼 모니터에서 메시지 확인
- [ ] 블루투스 연결 대기 상태 확인

---

## Step 4: 블루투스 페어링 테스트 (15분)

### 4.1 모바일에서 페어링
1. 모바일 기기의 **설정 → 블루투스** 열기
2. 사용 가능한 장치 목록에서 **"한진택배 스캐너"** 찾기
3. 페어링 클릭
4. 페어링 완료 확인

### 4.2 키보드 입력 테스트
1. 모바일에서 **메모장** 앱 열기
2. 시리얼 모니터에서 텍스트 입력:
   ```
   테스트123
   ```
3. 모바일 메모장에 텍스트가 입력되는지 확인

**체크리스트**:
- [ ] 모바일과 블루투스 페어링 완료
- [ ] 키보드 입력 테스트 성공

---

## Step 5: Python 환경 설정 (15분)

### 5.1 Python 설치 확인
```bash
python --version
# Python 3.8 이상이어야 함
```

### 5.2 가상환경 생성 (선택사항)
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 5.3 필요한 라이브러리 설치
```bash
pip install pyserial openpyxl colorama
```

또는 `requirements.txt`가 있다면:
```bash
pip install -r requirements.txt
```

**체크리스트**:
- [ ] Python 3.8+ 설치 확인
- [ ] 필요한 라이브러리 설치 완료

---

## Step 6: Python 프로그램 개발 (2시간)

### 6.1 프로젝트 구조 생성
```bash
mkdir -p config data logs src firmware
```

### 6.2 시리얼 통신 모듈 작성
**파일**: `src/bluetooth_controller.py`

```python
import serial
import time
from typing import Optional

class BluetoothController:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
    
    def connect(self) -> bool:
        """ESP32와 시리얼 연결"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # 연결 안정화 대기
            return True
        except Exception as e:
            print(f"연결 실패: {e}")
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
    
    def send_text(self, text: str) -> bool:
        """텍스트 전송"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False
        
        try:
            # 텍스트 + 개행 문자 전송
            self.serial_conn.write(f"{text}\n".encode('utf-8'))
            return True
        except Exception as e:
            print(f"전송 실패: {e}")
            return False
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.serial_conn is not None and self.serial_conn.is_open
```

### 6.3 엑셀 읽기 모듈 작성
**파일**: `src/excel_reader.py`

```python
from openpyxl import load_workbook
from typing import List

class ExcelReader:
    def __init__(self, file_path: str, column_name: str = "InvoiceNumber", sheet_name: str = "Sheet1"):
        self.file_path = file_path
        self.column_name = column_name
        self.sheet_name = sheet_name
    
    def read_invoices(self) -> List[str]:
        """엑셀에서 송장번호 읽기"""
        wb = load_workbook(self.file_path)
        ws = wb[self.sheet_name]
        
        # 헤더 행 찾기
        header_row = 1
        column_idx = None
        for cell in ws[header_row]:
            if cell.value == self.column_name:
                column_idx = cell.column
                break
        
        if column_idx is None:
            raise ValueError(f"컬럼 '{self.column_name}'을 찾을 수 없습니다.")
        
        # 데이터 읽기
        invoices = []
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            value = row[column_idx - 1]
            if value:
                # 문자열로 변환 (앞자리 0 보존)
                invoices.append(str(value))
        
        return invoices
```

### 6.4 메인 프로그램 작성
**파일**: `src/main.py`

```python
import json
import time
import random
from pathlib import Path
from bluetooth_controller import BluetoothController
from excel_reader import ExcelReader

def load_config():
    """설정 파일 로드"""
    config_path = Path("config/settings.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 기본 설정
        return {
            "serial": {"port": "COM3", "baudrate": 115200},
            "delays": {"min_between": 2.0, "max_between": 3.0},
            "excel": {"file_path": "data/invoices.xlsx", "column_name": "InvoiceNumber"}
        }

def random_delay(min_sec: float, max_sec: float):
    """랜덤 딜레이"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def main():
    # 설정 로드
    config = load_config()
    
    # ESP32 연결
    controller = BluetoothController(
        port=config["serial"]["port"],
        baudrate=config["serial"]["baudrate"]
    )
    
    print("ESP32 연결 중...")
    if not controller.connect():
        print("연결 실패!")
        return
    
    print("연결 성공!")
    print("3초 후 시작합니다...")
    time.sleep(3)
    
    # 엑셀 읽기
    reader = ExcelReader(
        file_path=config["excel"]["file_path"],
        column_name=config["excel"]["column_name"]
    )
    
    invoices = reader.read_invoices()
    total = len(invoices)
    
    print(f"총 {total}건의 송장번호를 처리합니다.")
    
    # 자동화 실행
    success_count = 0
    fail_count = 0
    
    for idx, invoice in enumerate(invoices, 1):
        print(f"[{idx}/{total}] 처리 중: {invoice}")
        
        if controller.send_text(invoice):
            success_count += 1
            print(f"  ✓ 성공")
        else:
            fail_count += 1
            print(f"  ✗ 실패")
        
        # 딜레이 (마지막 항목 제외)
        if idx < total:
            delay_min = config["delays"]["min_between"]
            delay_max = config["delays"]["max_between"]
            random_delay(delay_min, delay_max)
    
    # 결과 출력
    print("\n" + "="*50)
    print(f"처리 완료!")
    print(f"성공: {success_count}건")
    print(f"실패: {fail_count}건")
    print("="*50)
    
    # 연결 종료
    controller.disconnect()

if __name__ == "__main__":
    main()
```

### 6.5 설정 파일 생성
**파일**: `config/settings.json`

```json
{
  "serial": {
    "port": "COM3",
    "baudrate": 115200,
    "timeout": 1.0
  },
  "delays": {
    "min_between": 2.0,
    "max_between": 3.0
  },
  "retry": {
    "max_attempts": 3,
    "retry_delay": 2.0
  },
  "excel": {
    "file_path": "data/invoices.xlsx",
    "column_name": "InvoiceNumber",
    "sheet_name": "Sheet1"
  }
}
```

**체크리스트**:
- [ ] 프로젝트 구조 생성 완료
- [ ] 시리얼 통신 모듈 작성 완료
- [ ] 엑셀 읽기 모듈 작성 완료
- [ ] 메인 프로그램 작성 완료
- [ ] 설정 파일 생성 완료

---

## Step 7: 테스트 및 실행 (30분)

### 7.1 엑셀 파일 준비
1. `data/invoices.xlsx` 파일 생성
2. 첫 번째 행에 `InvoiceNumber` 헤더 추가
3. 두 번째 행부터 송장번호 입력 (테스트용으로 5~10개)

### 7.2 설정 파일 수정
1. `config/settings.json` 열기
2. `port` 값을 실제 COM 포트 번호로 수정

### 7.3 실행
```bash
cd src
python main.py
```

### 7.4 결과 확인
- 모바일 앱에서 송장번호가 자동으로 입력되는지 확인
- 터미널에서 진행 상황 확인

**체크리스트**:
- [ ] 엑셀 파일 준비 완료
- [ ] 설정 파일 수정 완료
- [ ] 프로그램 실행 성공
- [ ] 모바일 앱에서 입력 확인

---

## 🐛 트러블슈팅

### 문제 1: COM 포트 인식 안 됨
**해결**:
- USB 케이블 교체
- 다른 USB 포트 시도
- CH340 드라이버 재설치

### 문제 2: 펌웨어 업로드 실패
**해결**:
- ESP32의 BOOT 버튼을 누른 상태에서 업로드 시작
- 보드 선택 확인 (ESP32 Dev Module)
- 포트 선택 확인

### 문제 3: 블루투스 페어링 실패
**해결**:
- 모바일 블루투스 설정에서 기존 연결 삭제
- ESP32 재부팅
- 페어링 재시도

### 문제 4: Python에서 시리얼 연결 실패
**해결**:
- COM 포트 번호 확인
- 다른 프로그램에서 포트 사용 중인지 확인
- 관리자 권한으로 실행

---

## ✅ 완료 체크리스트

- [ ] Step 1: 하드웨어 연결 완료
- [ ] Step 2: Arduino IDE 설정 완료
- [ ] Step 3: 펌웨어 업로드 완료
- [ ] Step 4: 블루투스 페어링 완료
- [ ] Step 5: Python 환경 설정 완료
- [ ] Step 6: Python 프로그램 개발 완료
- [ ] Step 7: 테스트 및 실행 완료

---

**다음 단계**: 모든 체크리스트가 완료되면 실제 데이터로 대량 테스트를 진행하세요!


