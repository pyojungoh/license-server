# 빠른 시작 가이드

ESP32 제품을 받은 후 바로 시작할 수 있는 간단한 가이드입니다.

## 📦 준비물 확인

- [x] ESP32 개발 보드
- [ ] USB-C 케이블
- [ ] PC (Windows)
- [ ] 모바일 기기 (Android/iOS)

## 🚀 6단계로 시작하기

### 0단계: CH340 드라이버 설치 (5분) ⚠️ 중요!
**ESP32를 연결하기 전에 먼저 드라이버를 설치하세요!**

1. [CH340 드라이버 다운로드](http://www.wch.cn/downloads/CH341SER_EXE.html)
2. 다운로드한 **CH341SER.EXE** 실행
3. **INSTALL** 버튼 클릭
4. 설치 완료 확인

> 📖 **상세 가이드**: `DRIVER_INSTALL.md` 파일 참고

### 1단계: ESP32 연결 및 확인 (5분)
1. ESP32를 PC USB 포트에 연결
2. 장치 관리자에서 COM 포트 확인 (예: COM3)
   - `Win + X` → 장치 관리자 → 포트(COM & LPT) → USB-SERIAL CH340 확인
3. `config/settings.json`에서 포트 번호 수정

### 2단계: Arduino IDE 설정 (20분)
1. [Arduino IDE 다운로드](https://www.arduino.cc/en/software)
2. **파일 → 환경설정 → 추가 보드 관리자 URL**에 추가:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **도구 → 보드 → 보드 관리자**에서 `esp32` 검색 후 설치
4. **스케치 → 라이브러리 포함하기 → 라이브러리 관리**에서 `ESP32 BLE Keyboard` 설치

### 3단계: 펌웨어 업로드 (10분)
1. `firmware/esp32_ble_hid.ino` 파일을 Arduino IDE에서 열기
2. **도구 → 보드 → ESP32 Arduino → ESP32 Dev Module** 선택
3. **도구 → 포트 → COMx** 선택 (1단계에서 확인한 포트)
4. **스케치 → 업로드** 클릭

### 4단계: 블루투스 페어링 (5분)
1. 모바일 기기에서 **설정 → 블루투스** 열기
2. **"한진택배 스캐너"** 찾아서 페어링
3. 모바일 메모장 앱에서 테스트 (시리얼 모니터에서 텍스트 입력)

### 5단계: Python 프로그램 실행 (5분)
1. 라이브러리 설치:
   ```bash
   pip install -r requirements.txt
   ```
2. 엑셀 파일 준비:
   - `data/invoices.xlsx` 파일 생성
   - 첫 번째 행에 `InvoiceNumber` 헤더
   - 두 번째 행부터 송장번호 입력
3. 실행:
   ```bash
   cd src
   python main.py
   ```

## ✅ 완료!

이제 자동으로 송장번호가 입력됩니다!

## 🐛 문제 해결

### COM 포트 인식 안 됨
- **드라이버 설치 확인**: `DRIVER_INSTALL.md` 참고
- USB 케이블 교체
- 다른 USB 포트 시도
- CH340 드라이버 재설치

### 펌웨어 업로드 실패
- ESP32의 BOOT 버튼 누른 상태에서 업로드
- 보드 및 포트 선택 확인

### 블루투스 페어링 실패
- 모바일에서 기존 연결 삭제 후 재시도
- ESP32 재부팅

### Python 실행 오류
- COM 포트 번호 확인 (`config/settings.json`)
- 다른 프로그램에서 포트 사용 중인지 확인

---

더 자세한 내용은 `IMPLEMENTATION_GUIDE.md`를 참고하세요.

