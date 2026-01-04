# ⚠️ 중요: 올바른 파일 선택하기

## 컴파일할 파일
✅ **`esp32_ble_hid.ino`** ← 이 파일만 사용하세요!

## 컴파일하지 말 것
❌ **`esp32_ble_hid_backup.ino`** ← 이 파일은 백업 파일이고 인코딩 문제로 컴파일 안 됩니다!

## Arduino IDE에서 올바른 파일 여는 방법

### 방법 1: 파일 탐색기에서 직접 열기
1. 이 폴더(`C:\hanjin\firmware\esp32_ble_hid`)를 열기
2. **`esp32_ble_hid.ino`** 파일을 더블클릭
   - ⚠️ `esp32_ble_hid_backup.ino` 파일은 클릭하지 마세요!

### 방법 2: Arduino IDE에서 열기
1. Arduino IDE 실행
2. **파일 → 열기** (Ctrl+O)
3. **`esp32_ble_hid.ino`** 파일 선택
   - ⚠️ backup이 붙은 파일은 선택하지 마세요!

### 방법 3: 현재 열린 파일이 backup이면
1. Arduino IDE 상단 탭에서 **`esp32_ble_hid_backup`** 탭이 열려있다면
2. 그 탭을 닫기 (X 버튼 클릭)
3. **파일 → 열기**로 **`esp32_ble_hid.ino`** 파일 다시 열기

## 확인 방법

Arduino IDE 상단 탭에 다음이 보여야 합니다:
- ✅ `esp32_ble_hid` (올바름)
- ❌ `esp32_ble_hid_backup` (잘못됨 - 닫으세요!)

## 왜 backup 파일은 안 되나요?

`esp32_ble_hid_backup.ino` 파일은 이전 버전 백업 파일로, 파일 저장 시 인코딩 문제가 발생하여 한글이 깨져 있습니다. 컴파일할 수 없으므로 사용하지 마세요.

현재 작업할 파일은 **`esp32_ble_hid.ino`** 하나뿐입니다!




