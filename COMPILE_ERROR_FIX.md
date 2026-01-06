# 컴파일 오류 해결 가이드

## 🔴 발생한 오류

1. **타입 변환 오류**: `std::string`을 `String`으로 변환할 수 없음
2. **UTF-8 인코딩 오류**: 경로에 한글이 포함되어 있을 수 있음

## 🔧 해결 방법

### 방법 1: 호환되는 라이브러리 버전 사용 (추천)

ESP32 보드 패키지 3.3.5와 호환되는 라이브러리를 사용해야 합니다.

#### Step 1: 기존 라이브러리 제거
1. Arduino IDE에서 **스케치 → 라이브러리 포함하기 → 라이브러리 관리**
2. 설치된 "ESP32 BLE Keyboard" 라이브러리 찾기
3. **제거** 클릭

#### Step 2: 호환되는 라이브러리 설치

**옵션 A: T-vK 버전 (추천)**
1. GitHub에서 다운로드: https://github.com/T-vK/ESP32-BLE-Keyboard
2. **릴리스** 페이지에서 최신 버전 다운로드
3. **스케치 → 라이브러리 포함하기 → .ZIP 라이브러리 추가**

**옵션 B: Neil Kolban 버전 (대안)**
1. GitHub: https://github.com/nkolban/ESP32_BLE_Arduino
2. 이 라이브러리는 ESP32 BLE 전체 라이브러리이므로, 다른 방법 필요

### 방법 2: ESP32 보드 패키지 버전 다운그레이드

ESP32 보드 패키지를 이전 버전으로 변경:

1. **도구 → 보드 → 보드 관리자**
2. **esp32** 검색
3. **esp32 by Espressif Systems** 선택
4. **버전 선택**: 2.0.11 또는 2.0.9 선택
5. **설치** 클릭

### 방법 3: 스케치북 위치 변경 (UTF-8 오류 해결)

경로에 한글이 있으면 오류가 발생할 수 있습니다:

1. **파일 → 환경설정**
2. **스케치북 위치** 확인
3. 한글이 포함되어 있으면 영어 경로로 변경:
   - 예: `C:\Arduino\Sketchbook`
4. Arduino IDE 재시작

### 방법 4: 펌웨어 코드 수정 (고급)

라이브러리 소스 코드를 직접 수정:

1. 라이브러리 폴더 찾기:
   ```
   C:\Users\pyo08\OneDrive\문서\Arduino\libraries\ESP32_BLE_Keyboard\
   ```

2. `BleKeyboard.cpp` 파일 열기

3. 105번째 줄 수정:
   ```cpp
   // 기존:
   BLEDevice::init(deviceName);
   
   // 수정:
   BLEDevice::init(String(deviceName.c_str()));
   ```

4. 116번째 줄 수정:
   ```cpp
   // 기존:
   hid->manufacturer()->setValue(deviceManufacturer);
   
   // 수정:
   hid->manufacturer()->setValue(String(deviceManufacturer.c_str()));
   ```

## ✅ 추천 해결 순서

1. **먼저 시도**: 방법 1 (호환되는 라이브러리 설치)
2. **안 되면**: 방법 2 (보드 패키지 다운그레이드)
3. **여전히 안 되면**: 방법 3 (스케치북 위치 변경)
4. **최후의 수단**: 방법 4 (코드 직접 수정)

## 🔍 라이브러리 호환성 확인

- **ESP32 보드 패키지 3.x**: T-vK 버전 라이브러리 사용
- **ESP32 보드 패키지 2.x**: Neil Kolban 버전 또는 T-vK 버전 모두 가능

## 📝 다음 단계

오류가 해결되면:
1. 펌웨어 파일 다시 열기
2. 컴파일 확인 (✓ 버튼)
3. 업로드 진행

---

**가장 빠른 해결책**: T-vK의 ESP32-BLE-Keyboard 라이브러리 최신 버전을 사용하세요!










