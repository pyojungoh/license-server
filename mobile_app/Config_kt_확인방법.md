# Config.kt 에러 해결 방법

## 에러 원인
`Unresolved reference: ESP32_HEARTBEAT_CHAR_UUID` 에러가 발생하는 이유는 Android Studio 프로젝트 내의 `Config.kt` 파일에 해당 상수가 없기 때문입니다.

## 확인 방법

### 1. 파일 위치 확인
Android Studio에서 다음 경로의 파일을 확인하세요:
```
app/src/main/java/com/hanjin/Config.kt
```

### 2. 파일 내용 확인
`Config.kt` 파일이 열려있는지 확인하고, 다음 내용이 있는지 확인하세요:

```kotlin
package com.hanjin

object Config {
    // ... 기존 내용 ...
    
    // ESP32 BLE 설정
    const val ESP32_DEVICE_NAME = "한진택배 스캐너"
    const val ESP32_SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"
    const val ESP32_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789DEF"
    const val ESP32_HEARTBEAT_CHAR_UUID = "12345678-1234-1234-1234-123456789012"  // 이 줄이 있어야 함!
    
    // ... 나머지 내용 ...
}
```

## 해결 방법

### 방법 1: 파일에 상수 추가 (권장)
`Config.kt` 파일을 열고, `ESP32_CHARACTERISTIC_UUID` 다음에 다음 줄을 추가하세요:

```kotlin
const val ESP32_HEARTBEAT_CHAR_UUID = "12345678-1234-1234-1234-123456789012"
```

### 방법 2: 파일 다시 복사
`C:\hanjin\mobile_app\android\app\src\main\java\com\hanjin\Config.kt` 파일을 Android Studio 프로젝트의 같은 경로로 복사하세요.

### 방법 3: Android Studio에서 직접 수정
1. `Config.kt` 파일 열기
2. `ESP32_CHARACTERISTIC_UUID` 줄 다음에 다음 추가:
   ```kotlin
   const val ESP32_HEARTBEAT_CHAR_UUID = "12345678-1234-1234-1234-123456789012"
   ```
3. 저장 (Ctrl+S)
4. Gradle Sync

## 최종 확인
파일을 저장한 후:
1. **File → Sync Project with Gradle Files**
2. 에러가 사라지는지 확인







