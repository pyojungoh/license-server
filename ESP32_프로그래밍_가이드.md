# ESP32 프로그래밍 가이드

## 목차
1. [필수 준비물](#필수-준비물)
2. [드라이버 설치](#드라이버-설치)
3. [Arduino IDE 설정](#arduino-ide-설정)
4. [라이브러리 설치](#라이브러리-설치)
5. [펌웨어 업로드](#펌웨어-업로드)
6. [블루투스 연결](#블루투스-연결)
7. [문제 해결](#문제-해결)

---

## 필수 준비물

### 하드웨어
- **ESP32 WIFI + 블루투스 듀얼 모드 WROOM 32 USB C타입 CH340 드라이버**
- USB 케이블 (데이터 전송 가능한 케이블)
- PC (Windows)

### 소프트웨어
- Arduino IDE (최신 버전)
- CH340 드라이버
- ESP32 BLE Keyboard 라이브러리

---

## 드라이버 설치

### 1. CH340 드라이버 다운로드
- CH340 드라이버를 다운로드합니다.
- 다운로드 링크: [CH340 드라이버](https://www.wch.cn/downloads/CH341SER_EXE.html)

### 2. 드라이버 설치
1. 다운로드한 드라이버 설치 파일 실행
2. "INSTALL" 버튼 클릭
3. 설치 완료 후 PC 재부팅 (필요한 경우)

### 3. 드라이버 설치 확인
1. ESP32를 PC에 USB로 연결
2. 장치 관리자에서 "COM 포트" 확인
3. "USB-SERIAL CH340" 또는 유사한 이름으로 표시되면 성공

**주의사항**: 
- 케이블이 데이터 전송을 지원하지 않으면 인식되지 않을 수 있습니다.
- 다른 케이블로 교체해보세요.

---

## Arduino IDE 설정

### 1. Arduino IDE 설치
- [Arduino IDE 공식 사이트](https://www.arduino.cc/en/software)에서 다운로드
- 설치 완료 후 실행

### 2. ESP32 보드 패키지 추가
1. Arduino IDE 실행
2. **파일 → 환경설정** (또는 `Ctrl + ,`)
3. "추가 보드 관리자 URLs"에 다음 URL 추가:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. **도구 → 보드 → 보드 관리자** 열기
5. 검색창에 "esp32" 입력
6. "esp32 by Espressif Systems" 설치 (버전 3.3.5 권장)

### 3. 보드 선택
1. **도구 → 보드 → ESP32 Arduino** → **ESP32 Dev Module** 선택
2. **도구 → 포트** → ESP32가 연결된 COM 포트 선택 (예: COM10)

### 4. 중요 설정
**도구 메뉴에서 다음 설정 확인:**
- **보드**: "ESP32 Dev Module"
- **Upload Speed**: "921600"
- **CPU Frequency**: "240MHz (WiFi/BT)"
- **Flash Frequency**: "80MHz"
- **Flash Mode**: "QIO"
- **Flash Size**: "4MB (32Mb)"
- **Partition Scheme**: "Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)"
- **Core Debug Level**: "None"
- **PSRAM**: "Disabled"
- **Port**: ESP32가 연결된 COM 포트

### 5. 스케치북 위치 설정 (중요!)
**문제**: 한글 경로가 포함된 스케치북 위치는 컴파일 오류를 발생시킬 수 있습니다.

**해결 방법**:
1. **파일 → 환경설정** (또는 `Ctrl + ,`)
2. "스케치북 위치"를 영문 경로로 변경
   - 예: `C:\Arduino\Sketchbook`
   - 기존: `C:\Users\사용자명\OneDrive\문서\Arduino` (한글 경로)
3. Arduino IDE 재시작

---

## 라이브러리 설치

### 1. ESP32 BLE Keyboard 라이브러리 설치
1. Arduino IDE 실행
2. **스케치 → 라이브러리 포함하기 → 라이브러리 관리** (또는 `Ctrl + Shift + I`)
3. 검색창에 "ESP32 BLE Keyboard" 입력
4. "ESP32 BLE Keyboard by Avinab Malla" 설치

### 2. GitHub에서 직접 설치 (대안)
1. [ESP32 BLE Keyboard GitHub](https://github.com/T-vK/ESP32-BLE-Keyboard) 접속
2. "Code" → "Download ZIP" 클릭
3. Arduino IDE에서 **스케치 → 라이브러리 포함하기 → .ZIP 라이브러리 추가**
4. 다운로드한 ZIP 파일 선택

### 3. 라이브러리 호환성 문제 해결
**문제**: ESP32 보드 패키지 버전 3.3.5와 라이브러리 호환성 문제

**에러 메시지**:
```
error: cannot convert 'std::string' to 'String'
error: no matching function for call to 'BLECharacteristic::setValue(std::string&)'
```

**해결 방법**:
1. 라이브러리 파일 직접 수정
2. 파일 위치: `C:\Users\사용자명\Documents\Arduino\libraries\ESP32_BLE_Keyboard\BleKeyboard.cpp`
3. 다음 줄 수정:

**105번째 줄**:
```cpp
// 변경 전
BLEDevice::init(deviceName);

// 변경 후
BLEDevice::init(String(deviceName.c_str()));
```

**116번째 줄**:
```cpp
// 변경 전
hid->manufacturer()->setValue(deviceManufacturer);

// 변경 후
hid->manufacturer()->setValue(String(deviceManufacturer.c_str()));
```

---

## 펌웨어 업로드

### 1. 펌웨어 파일 열기
1. Arduino IDE 실행
2. **파일 → 열기**
3. `firmware/esp32_ble_hid/esp32_ble_hid.ino` 파일 열기

### 2. 펌웨어 확인
- 디바이스 이름: "BLT AI 로봇"
- 시리얼 통신으로 텍스트 수신 후 블루투스 키보드로 전송
- 각 입력 후 자동으로 Enter 키 전송

### 3. 컴파일 및 업로드
1. **스케치 → 검증/컴파일** (또는 `Ctrl + R`)
   - 컴파일 성공 메시지 확인
   - 스케치 크기 확인 (약 83% 사용)
2. **스케치 → 업로드** (또는 `Ctrl + U`)
   - 업로드 진행 상황 확인
   - "업로드 완료" 메시지 확인

### 4. 업로드 성공 확인
- ESP32의 LED가 깜빡이면 정상
- 시리얼 모니터에서 "BLT AI 로봇 준비 완료" 메시지 확인 가능

---

## 블루투스 연결

### 1. ESP32 재부팅
**중요**: 펌웨어 업로드 후 ESP32를 재부팅해야 블루투스가 활성화됩니다.

**재부팅 방법**:
1. **방법 1**: ESP32의 **EN (Enable) 버튼** 누르기
2. **방법 2**: USB 케이블을 뽑았다가 다시 연결
3. **방법 3**: Arduino IDE에서 **도구 → 포트** → 포트 다시 선택

### 2. 모바일에서 블루투스 연결
1. 모바일 기기의 **설정 → 블루투스** 열기
2. 블루투스 케이블 켜기
3. "BLT AI 로봇" 검색 및 연결
4. 페어링 완료

### 3. 연결 확인
- PC에서 시리얼 모니터로 테스트 메시지 전송
- 모바일 앱에서 입력이 들어오는지 확인

---

## 문제 해결

### 문제 1: ESP32가 PC에서 인식되지 않음
**원인**:
- 드라이버 미설치
- 케이블이 데이터 전송을 지원하지 않음
- COM 포트 충돌

**해결 방법**:
1. CH340 드라이버 재설치
2. 다른 USB 케이블 사용
3. 다른 USB 포트 사용
4. Arduino IDE의 시리얼 모니터 닫기 (포트 점유 해제)

### 문제 2: 컴파일 오류
**원인**:
- 한글 경로가 포함된 스케치북 위치
- 라이브러리 호환성 문제
- ESP32 보드 패키지 미설치

**해결 방법**:
1. 스케치북 위치를 영문 경로로 변경
2. `BleKeyboard.cpp` 파일 수정 (위 참고)
3. ESP32 보드 패키지 재설치

### 문제 3: 업로드 실패
**원인**:
- COM 포트 선택 오류
- ESP32가 부팅 모드가 아님
- 다른 프로그램이 포트를 사용 중

**해결 방법**:
1. 올바른 COM 포트 선택 확인
2. ESP32의 **BOOT 버튼**을 누른 상태에서 업로드 시작
3. Arduino IDE의 시리얼 모니터 닫기
4. 다른 시리얼 통신 프로그램 종료

### 문제 4: 블루투스 연결 안 됨
**원인**:
- 펌웨어 업로드 후 재부팅 안 함
- 이전 블루투스 연결 정보가 남아있음
- 모바일 앱이 블루투스 키보드 입력을 받지 않음

**해결 방법**:
1. ESP32 재부팅 (EN 버튼 또는 USB 재연결)
2. 모바일에서 이전 "BLT AI 로봇" 연결 삭제
3. 모바일 재부팅
4. 다시 페어링 시도

### 문제 5: 입력이 모바일로 전송되지 않음
**원인**:
- 블루투스 연결 안 됨
- 모바일 앱이 포커스되지 않음
- 시리얼 통신 오류

**해결 방법**:
1. 블루투스 연결 상태 확인
2. 모바일 앱을 포그라운드로 가져오기
3. PC에서 시리얼 모니터로 테스트 메시지 전송
4. 시리얼 통신 속도 확인 (115200 baud)

---

## 버튼 설명

### ESP32 보드의 버튼
- **BOOT 버튼**: 펌웨어 업로드 시 사용 (필요한 경우)
- **EN (Enable) 버튼**: ESP32 재부팅 (리셋)

**사용 시나리오**:
- 펌웨어 업로드가 안 될 때: BOOT 버튼 누른 상태에서 업로드
- 블루투스 연결이 안 될 때: EN 버튼 눌러서 재부팅

---

## 완료 체크리스트

- [ ] CH340 드라이버 설치 완료
- [ ] Arduino IDE 설치 완료
- [ ] ESP32 보드 패키지 설치 완료
- [ ] 스케치북 위치 영문 경로로 변경
- [ ] ESP32 BLE Keyboard 라이브러리 설치 완료
- [ ] 라이브러리 호환성 문제 해결 (필요한 경우)
- [ ] 펌웨어 업로드 성공
- [ ] 모바일에서 블루투스 연결 성공
- [ ] PC에서 모바일로 입력 전송 테스트 성공

---

## 다음 단계

ESP32 설정이 완료되면:
1. PC 프로그램 (`src/gui_app.py`) 실행
2. COM 포트 선택
3. 엑셀 파일 업로드
4. "동기화 실행" 버튼 클릭
5. 모바일 앱에서 송장번호 자동 입력 확인

---

## 참고 자료

- [ESP32 공식 문서](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/)
- [Arduino ESP32 GitHub](https://github.com/espressif/arduino-esp32)
- [ESP32 BLE Keyboard 라이브러리](https://github.com/T-vK/ESP32-BLE-Keyboard)

---

**작성일**: 2025년 1월  
**작성자**: AI Assistant  
**업데이트**: ESP32 프로그래밍 가이드





