/*
 * 한진택배 송장번호 자동 등록 시스템
 * ESP32 BLE HID 키보드 펌웨어
 * 
 * 기능:
 * - BLE HID 키보드로 동작
 * - 시리얼 통신으로 텍스트 수신
 * - 수신한 텍스트를 키보드 입력으로 변환
 * - 엔터 키 자동 전송 (바코드 스캐너처럼)
 */

#include <BleKeyboard.h>

// BLE 키보드 객체 생성
// 파라미터: 장치 이름, 제조사 이름, 배터리 레벨(0-100)
BleKeyboard bleKeyboard("한진택배 스캐너", "Hanjin Automation", 100);

// 연결 상태 LED 핀 (내장 LED 사용, GPIO2)
#define LED_PIN 2

// 연결 상태 추적
bool wasConnected = false;

void setup() {
  // 시리얼 통신 시작 (115200 baud)
  Serial.begin(115200);
  Serial.println("\n=================================");
  Serial.println("ESP32 BLE HID 키보드 시작");
  Serial.println("=================================");
  
  // LED 핀 설정
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // BLE 키보드 시작
  bleKeyboard.begin();
  Serial.println("블루투스 키보드 초기화 완료");
  Serial.println("모바일 기기에서 '한진택배 스캐너'를 찾아 페어링하세요.");
}

void loop() {
  // 연결 상태 확인
  bool isConnected = bleKeyboard.isConnected();
  
  // 연결 상태가 변경되었을 때
  if (isConnected != wasConnected) {
    wasConnected = isConnected;
    if (isConnected) {
      Serial.println("\n✓ 블루투스 연결됨!");
      digitalWrite(LED_PIN, HIGH);  // LED 켜기
    } else {
      Serial.println("\n✗ 블루투스 연결 끊김");
      digitalWrite(LED_PIN, LOW);   // LED 끄기
    }
  }
  
  // 연결되어 있을 때만 처리
  if (isConnected) {
    // 시리얼로부터 데이터 수신
    if (Serial.available() > 0) {
      // 한 줄 읽기 (개행 문자까지)
      String text = Serial.readStringUntil('\n');
      text.trim();  // 앞뒤 공백 제거
      
      // 빈 문자열이 아니면 처리
      if (text.length() > 0) {
        Serial.print("→ 수신: ");
        Serial.println(text);
        
        // 블루투스 연결 확인
        if (bleKeyboard.isConnected()) {
          // 키보드로 텍스트 입력
          bleKeyboard.print(text);
          delay(100);  // 입력 안정화 대기
          
          // 엔터 키 전송 (바코드 스캐너처럼)
          bleKeyboard.write(KEY_RETURN);
          delay(50);
          
          Serial.println("  ✓ 전송 완료");
        } else {
          Serial.println("  ✗ 블루투스 연결 안 됨");
        }
      }
    }
  } else {
    // 연결되지 않았을 때는 주기적으로 상태 출력
    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 3000) {
      Serial.println("블루투스 연결 대기 중...");
      lastPrint = millis();
    }
    delay(100);
  }
  
  // 짧은 딜레이 (CPU 부하 감소)
  delay(10);
}

