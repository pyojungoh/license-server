# 한진택배 송장번호 자동 등록 시스템

## 📋 프로젝트 개요

한진택배 모바일 앱의 수동 스캔/입력 작업을 PC에서 자동화하여, 엑셀에 있는 대량의 운송장 번호를 사람의 개입 없이 앱에 일괄 등록하는 로컬 프로그램입니다.

## 🎯 프로젝트 목표

1. **Pain Point 해결**: 한진택배는 특정 송장 등록 업무에 대해 API나 PC 일괄 처리 프로그램을 제공하지 않아, 담당자가 모바일 앱을 켜고 일일이 번호를 타이핑해야 하는 비효율을 해결
2. **효율성 증대**: 블루투스 HID 키보드 에뮬레이션을 통해 수백 건의 송장을 자동으로 처리하여 단순 반복 업무 시간을 단축

## 🔧 기술 스택

### 하드웨어
- **ESP32-WROOM-32 개발 보드**
  - USB-C 타입
  - CH340 드라이버 포함
  - 블루투스 + WiFi 듀얼 모드
  - 가격: 약 7,990원

### 소프트웨어
- **Python 3.8+**
- **Arduino IDE** (ESP32 펌웨어 개발용)
- **필요 라이브러리**:
  - `pyserial`: ESP32와 시리얼 통신
  - `openpyxl` 또는 `pandas`: 엑셀 파일 읽기
  - `colorama`: 터미널 출력 개선 (선택)

## 🏗️ 시스템 아키텍처

```
[PC Python 프로그램]
    ↓ USB 시리얼 통신
[ESP32 개발 보드]
    ↓ BLE HID 키보드 프로토콜
[모바일 앱 (한진택배)]
```

## 📦 하드웨어 구성

### 구매 제품
- **제품명**: ESP32 WIFI + 블루투스 듀얼 모드 WROOM 32 USB C타입 CH340 드라이버
- **특징**:
  - USB-C 포트로 PC 연결
  - CH340 USB-to-Serial 칩 (Windows 호환)
  - 핀 헤더 포함 (사용하지 않음, 보관만)
  - 블루투스 HID 프로파일 지원 가능

### 연결 방법
1. ESP32를 PC의 USB 포트에 연결 (USB-C 케이블 사용)
2. Windows에서 CH340 드라이버 자동 인식 (또는 수동 설치)
3. 모바일 기기와 블루투스 페어링

## 📁 프로젝트 구조

```
hanjin/
├── README.md                 # 프로젝트 문서 (이 파일)
├── requirements.txt          # Python 라이브러리 목록
├── config/
│   └── settings.json         # 설정 파일 (딜레이, 재시도 등)
├── data/
│   └── invoices.xlsx         # 입력 데이터 (사용자가 준비)
├── logs/
│   └── automation_YYYYMMDD.log  # 실행 로그
├── firmware/
│   └── esp32_ble_hid.ino     # ESP32 펌웨어 (Arduino)
└── src/
    ├── main.py               # 메인 프로그램
    ├── excel_reader.py       # 엑셀 읽기 모듈
    ├── bluetooth_controller.py  # ESP32 제어 모듈
    └── utils.py              # 유틸리티 함수
```

## 🚀 구현 계획

### Phase 1: 환경 설정 및 펌웨어 개발
- [x] ESP32 개발 보드 구매
- [ ] Arduino IDE 설치 및 ESP32 보드 설정
- [ ] BLE HID 키보드 펌웨어 개발
- [ ] 펌웨어 업로드 및 테스트

### Phase 2: Python 제어 프로그램 개발
- [ ] 시리얼 통신 모듈 개발
- [ ] 엑셀 읽기 모듈 개발
- [ ] 메인 자동화 로직 개발
- [ ] 로깅 및 에러 처리 구현

### Phase 3: 통합 테스트
- [ ] PC ↔ ESP32 통신 테스트
- [ ] ESP32 ↔ 모바일 블루투스 연결 테스트
- [ ] 전체 워크플로우 테스트
- [ ] 대량 데이터 처리 테스트

### Phase 4: 최적화 및 문서화
- [ ] 딜레이 최적화
- [ ] 에러 복구 로직 강화
- [ ] 사용자 가이드 작성
- [ ] 배포 준비

## 📝 다음 단계 (제품 도착 후)

### Step 1: 하드웨어 설정 (예상 시간: 30분)

1. **ESP32 연결**
   ```bash
   # ESP32를 PC USB 포트에 연결
   # Windows 장치 관리자에서 COM 포트 확인
   ```

2. **CH340 드라이버 설치** (필요시)
   - Windows 10/11은 대부분 자동 인식
   - 인식 안 되면: [CH340 드라이버 다운로드](http://www.wch.cn/downloads/CH341SER_EXE.html)

3. **COM 포트 확인**
   - 장치 관리자 → 포트(COM & LPT) → USB-SERIAL CH340 확인
   - COM 번호 기록 (예: COM3)

### Step 2: Arduino IDE 설정 (예상 시간: 30분)

1. **Arduino IDE 설치**
   - [Arduino IDE 다운로드](https://www.arduino.cc/en/software)

2. **ESP32 보드 추가**
   ```
   파일 → 환경설정 → 추가 보드 관리자 URL에 추가:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   
   도구 → 보드 → 보드 관리자 → "esp32" 검색 → 설치
   ```

3. **보드 선택**
   ```
   도구 → 보드 → ESP32 Arduino → ESP32 Dev Module
   도구 → 포트 → COM3 (확인한 포트 번호)
   ```

### Step 3: 펌웨어 개발 및 업로드 (예상 시간: 1시간)

1. **BLE HID 키보드 펌웨어 작성**
   - `firmware/esp32_ble_hid.ino` 파일 생성
   - BLE HID 키보드 프로파일 구현
   - 시리얼 통신으로 텍스트 수신 → 키보드 입력으로 변환

2. **펌웨어 업로드**
   ```
   스케치 → 업로드
   ```

3. **테스트**
   - 시리얼 모니터로 연결 확인
   - 모바일과 블루투스 페어링 테스트

### Step 4: Python 환경 설정 (예상 시간: 15분)

1. **Python 가상환경 생성** (선택)
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. **필요 라이브러리 설치**
   ```bash
   pip install -r requirements.txt
   ```

### Step 5: Python 프로그램 개발 (예상 시간: 2시간)

1. **시리얼 통신 모듈** (`src/bluetooth_controller.py`)
   - ESP32와 시리얼 통신
   - 텍스트 전송 함수

2. **엑셀 읽기 모듈** (`src/excel_reader.py`)
   - `invoices.xlsx` 파일 읽기
   - 송장번호 추출 (문자열로 처리하여 앞자리 0 보존)

3. **메인 프로그램** (`src/main.py`)
   - 설정 로드
   - 엑셀 데이터 읽기
   - 자동화 로직 실행
   - 진행 상황 표시 및 로깅

### Step 6: 통합 테스트 (예상 시간: 1시간)

1. **연결 테스트**
   - PC ↔ ESP32 시리얼 통신 확인
   - ESP32 ↔ 모바일 블루투스 연결 확인

2. **기능 테스트**
   - 단일 송장번호 입력 테스트
   - 여러 송장번호 연속 입력 테스트

3. **대량 처리 테스트**
   - 엑셀 파일로 실제 데이터 테스트
   - 에러 처리 확인

## ⚙️ 설정 파일 예시

### `config/settings.json`
```json
{
  "serial": {
    "port": "COM3",
    "baudrate": 115200,
    "timeout": 1.0
  },
  "delays": {
    "min_action": 0.5,
    "max_action": 1.0,
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

## 🔒 안전장치

1. **시작 전 확인**
   - 3초 카운트다운
   - 모바일 앱이 입력 대기 상태인지 확인

2. **실행 중 안전장치**
   - ESC 키로 즉시 중단
   - 실패한 항목 목록 저장
   - 진행 상황 자동 저장 (중단 시 재개 가능)

3. **에러 처리**
   - 시리얼 통신 오류 처리
   - 블루투스 연결 끊김 감지
   - 재시도 로직

## 📊 예상 성능

- **처리 속도**: 건당 약 3~4초 (딜레이 포함)
- **100건 처리**: 약 5~7분
- **500건 처리**: 약 25~35분

## 🐛 알려진 이슈 및 해결 방법

### 이슈 1: COM 포트 인식 안 됨
- **해결**: CH340 드라이버 재설치

### 이슈 2: 블루투스 페어링 실패
- **해결**: 모바일 블루투스 설정에서 ESP32 삭제 후 재페어링

### 이슈 3: 입력이 너무 빠름
- **해결**: `settings.json`에서 딜레이 값 증가

## 📚 참고 자료

- [ESP32 Arduino Core 문서](https://docs.espressif.com/projects/arduino-esp32/en/latest/)
- [BLE HID 프로파일 스펙](https://www.bluetooth.com/specifications/specs/human-interface-device-profile-1-0/)
- [PySerial 문서](https://pyserial.readthedocs.io/)

## 📞 지원

문제가 발생하면 로그 파일(`logs/automation_YYYYMMDD.log`)을 확인하세요.

---

**작성일**: 2024-12-24  
**버전**: 1.0.0










