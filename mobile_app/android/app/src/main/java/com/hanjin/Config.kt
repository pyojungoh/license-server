package com.hanjin

/**
 * 앱 설정 상수
 */
object Config {
    // 서버 URL (개발/프로덕션 환경별 설정 필요)
    const val SERVER_URL = "https://license-server-production-e83a.up.railway.app"
    // 개발 환경: "http://10.0.2.2:5000" (에뮬레이터)
    // 개발 환경 (실기기): "http://[PC의_로컬_IP]:5000"
    // 프로덕션: Railway 서버 URL
    
    // ESP32 BLE 설정
    const val ESP32_DEVICE_NAME = "한진택배 스캐너"
    const val ESP32_SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"
    const val ESP32_CHARACTERISTIC_UUID = "12345678-1234-1234-1234-123456789DEF"
    const val ESP32_HEARTBEAT_CHAR_UUID = "12345678-1234-1234-1234-123456789012"
    
    // API 엔드포인트
    const val API_LOGIN = "/api/login"
    const val API_VERIFY_TOKEN = "/api/verify_token"
    const val API_DEVICE_CHANGE = "/api/request_device_change"
}

