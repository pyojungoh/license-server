# 한진택배 자동화 시스템 - 모바일 앱

## 📱 앱 개요

이 앱은 ESP32와 통신하여 인증 토큰을 전송하는 안드로이드 앱입니다.

### 주요 기능
1. **서버 로그인**: ID/Password로 로그인
2. **토큰 발급**: 서버에서 액세스 토큰 발급 받기
3. **ESP32 BLE 스캔**: 블루투스로 ESP32 장치 검색
4. **토큰 전송**: ESP32로 인증 토큰 전송
5. **기기 등록**: 1인 1기기 정책으로 기기 UUID 등록

## 🏗️ 프로젝트 구조

```
mobile_app/
├── android/                    # 안드로이드 네이티브 앱
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/hanjin/
│   │   │   │   ├── MainActivity.kt          # 메인 화면
│   │   │   │   ├── LoginActivity.kt         # 로그인 화면
│   │   │   │   ├── BLEService.kt           # BLE 통신 서비스
│   │   │   │   ├── ApiService.kt           # 서버 API 클라이언트
│   │   │   │   └── utils/
│   │   │   │       └── DeviceUtils.kt      # 기기 UUID 생성
│   │   │   ├── res/
│   │   │   │   ├── layout/                 # XML 레이아웃
│   │   │   │   └── values/
│   │   │   │       └── strings.xml         # 문자열 리소스
│   │   │   └── AndroidManifest.xml         # 앱 매니페스트
│   │   └── build.gradle.kts                # Gradle 빌드 설정
│   └── build.gradle.kts
└── README.md
```

## 🔧 기술 스택

- **언어**: Kotlin
- **최소 SDK**: API 21 (Android 5.0)
- **타겟 SDK**: API 34 (Android 14)
- **라이브러리**:
  - Retrofit: HTTP 클라이언트
  - Gson: JSON 파싱
  - Android BLE API: 블루투스 통신

## 📋 필요한 권한

```xml
<uses-permission android:name="android.permission.BLUETOOTH"/>
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"/>
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.INTERNET"/>
```

## 🔐 ESP32 BLE 설정

### Service UUID
```
12345678-1234-1234-1234-123456789ABC
```

### Characteristic UUID
```
12345678-1234-1234-1234-123456789DEF
```

### ESP32 장치 이름
```
한진택배 스캐너
```

## 🌐 서버 API 엔드포인트

### 기본 URL
- 개발: `http://localhost:5000`
- 프로덕션: Railway 서버 URL (확인 필요)

### API 엔드포인트
- `POST /api/login`: 로그인 및 토큰 발급
- `POST /api/verify_token`: 토큰 검증
- `POST /api/request_device_change`: 기기 변경 신청

## 🚀 개발 가이드

자세한 개발 가이드는 각 단계별 가이드 문서를 참고하세요:
- [1단계: 프로젝트 구조 설계](docs/01_프로젝트_구조.md)
- [2단계: 서버 로그인 기능](docs/02_서버_로그인.md)
- [3단계: BLE 스캔 및 연결](docs/03_BLE_통신.md)
- [4단계: 토큰 전송](docs/04_토큰_전송.md)





