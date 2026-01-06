# ESP32 BLE Keyboard 라이브러리 설치 가이드

## 🔍 필요한 라이브러리

펌웨어 코드에서 사용하는 라이브러리:
- **BleKeyboard.h** - ESP32를 BLE HID 키보드로 동작시키는 라이브러리

## 📥 설치 방법

### 방법 1: Arduino IDE 라이브러리 관리자에서 설치 (추천)

1. **Arduino IDE 실행**

2. **스케치 → 라이브러리 포함하기 → 라이브러리 관리** (또는 `Ctrl + Shift + I`)

3. **검색창에 다음 중 하나로 검색**:
   - `ESP32 BLE Keyboard` ← 이걸로 검색!
   - 또는 `BleKeyboard`

4. **정확한 라이브러리 찾기**:
   - **"ESP32 BLE Keyboard"** by **Neil Kolban** 또는 **T-vK**
   - 설명에 "BLE HID Keyboard" 또는 "Bluetooth Low Energy Keyboard" 포함
   - 버전: 최신 버전 (보통 0.3.2 이상)

5. **INSTALL 버튼 클릭**

### 방법 2: GitHub에서 직접 설치

만약 라이브러리 관리자에서 찾을 수 없다면:

1. **GitHub에서 다운로드**:
   - https://github.com/T-vK/ESP32-BLE-Keyboard
   - 또는 https://github.com/nkolban/ESP32_BLE_Arduino

2. **Arduino IDE에서 설치**:
   - **스케치 → 라이브러리 포함하기 → .ZIP 라이브러리 추가**
   - 다운로드한 ZIP 파일 선택

## ✅ 설치 확인

라이브러리가 설치되었는지 확인:

1. **스케치 → 라이브러리 포함하기 → 라이브러리 관리**
2. 검색창에 `ESP32 BLE Keyboard` 입력
3. **설치됨** 표시가 보이면 성공!

## 🐛 문제 해결

### 문제 1: 검색 결과에 라이브러리가 안 보임

**해결**:
- 검색어를 바꿔보세요:
  - `ESP32 BLE Keyboard`
  - `BleKeyboard`
  - `ESP32 BLE HID`
- 라이브러리 관리자 새로고침 (검색창 비우고 다시 검색)

### 문제 2: 여러 개의 비슷한 라이브러리가 보임

**선택 기준**:
- ✅ **"ESP32 BLE Keyboard"** by **Neil Kolban** 또는 **T-vK** (추천)
- ✅ 설명에 "HID Keyboard" 포함
- ✅ 최신 버전 (0.3.2 이상)
- ❌ "ble-keyboard-mouse-client" - 다른 라이브러리 (사용 안 함)
- ❌ "blesdlib" - 다른 라이브러리 (사용 안 함)

### 문제 3: 컴파일 오류 발생

**해결**:
1. ESP32 보드 패키지가 설치되었는지 확인
2. 라이브러리 버전 확인 (최신 버전 사용)
3. Arduino IDE 재시작

## 📝 다음 단계

라이브러리 설치가 완료되면:

1. ✅ **펌웨어 업로드**: `firmware/esp32_ble_hid.ino` 파일 열기
2. ✅ **보드 선택**: 도구 → 보드 → ESP32 Arduino → ESP32 Dev Module
3. ✅ **포트 선택**: 도구 → 포트 → COM10
4. ✅ **업로드**: 스케치 → 업로드

---

**참고**: 만약 정확한 라이브러리를 찾을 수 없다면, 펌웨어 코드를 수정하여 다른 라이브러리를 사용할 수도 있습니다.











