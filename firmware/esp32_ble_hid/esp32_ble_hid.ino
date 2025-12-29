/*
 * 한진택배 송장번호 자동 등록 시스템
 * ESP32 BLE HID 키보드 펌웨어
 * 
 * 기능:
 * - BLE HID 키보드로 동작
 * - 시리얼 통신으로 텍스트 수신
 * - 수신한 텍스트를 키보드 입력으로 변환
 * - Tab 키 + 엔터 키로 입력 버튼 클릭 (방법 1)
 * 
 * 입력 버튼 클릭 방법들:
 * 방법 1: 송장번호 입력 → Tab 키 → 엔터 키
 * 방법 2: 송장번호 입력 → 엔터 키 2회
 * 방법 3 (현재 적용): 송장번호 입력 → Tab 키 2회 → 엔터 키 → Shift+Tab 2회 (입력 필드 복귀)
 */

#include <BleKeyboard.h>

// BLE 키보드 객체 생성
// 파라미터: 장치 이름, 제조사 이름, 배터리 레벨(0-100)
BleKeyboard bleKeyboard("한진택배 스캐너", "Hanjin Automation", 100);

// 연결 상태 LED 핀 (내장 LED 사용, GPIO2)
#define LED_PIN 2

// 연결 상태 추적
bool wasConnected = false;
String connectedMacAddress = "";  // 연결된 장치의 MAC 주소

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
      
      // 연결된 장치의 MAC 주소 확인 (BLE에서 접근 가능한 경우)
      // 주의: ESP32 BLE Keyboard 라이브러리에서 직접 MAC 주소를 얻을 수 없을 수 있음
      // 대안: 고정된 장치 ID 사용 또는 다른 방법 고려
      connectedMacAddress = "";  // 실제 구현 시 BLE API로 MAC 주소 가져오기
    } else {
      Serial.println("\n✗ 블루투스 연결 끊김");
      digitalWrite(LED_PIN, LOW);   // LED 끄기
      connectedMacAddress = "";
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
        // "GET_CONNECTED_MAC" 명령 처리
        if (text == "GET_CONNECTED_MAC") {
          if (isConnected && connectedMacAddress.length() > 0) {
            Serial.print("MAC:");
            Serial.println(connectedMacAddress);
          } else {
            // MAC 주소를 얻을 수 없는 경우, ESP32 자체 MAC 주소나 고정값 반환
            // 실제 구현: BLE에서 연결된 장치 MAC 주소 가져오기
            Serial.println("MAC:00:00:00:00:00:00");  // 기본값 (실제 구현 필요)
          }
          continue;  // 다음 루프로
        }
        
        Serial.print("→ 수신: ");
        Serial.println(text);
        
        // 블루투스 연결 확인
        if (bleKeyboard.isConnected()) {
          // 키보드로 텍스트 입력
          bleKeyboard.print(text);
          delay(150);  // 입력 안정화 대기
          
          // === 방법 1: Tab 키 + 엔터 키 ===
          // bleKeyboard.write(KEY_TAB);      // Tab 키: 포커스를 입력 필드에서 다음 요소로 이동
          // delay(100);                      // Tab 키 처리 대기
          // bleKeyboard.write(KEY_RETURN);   // 엔터 키: 입력 버튼 클릭
          // delay(50);
          
          // === 방법 2: 엔터 키 2회 ===
          // bleKeyboard.write(KEY_RETURN);   // 첫 번째 엔터: 입력 필드 완료
          // delay(200);                      // 처리 대기
          // bleKeyboard.write(KEY_RETURN);   // 두 번째 엔터: 입력 버튼 클릭
          // delay(50);
          
          // === 방법 3: Tab 키 2회 + 엔터 키 + Shift+Tab 2회 (현재 적용) ===
          bleKeyboard.write(KEY_TAB);      // 첫 번째 Tab
          delay(100);                      // Tab 키 처리 대기
          bleKeyboard.write(KEY_TAB);      // 두 번째 Tab: 입력 버튼으로 포커스 이동
          delay(100);                      // Tab 키 처리 대기
          bleKeyboard.write(KEY_RETURN);   // 엔터 키: 입력 버튼 클릭
          delay(200);                      // 입력 처리 대기
          
          // Shift + Tab으로 입력 필드로 포커스 복귀
          bleKeyboard.press(KEY_LEFT_SHIFT);  // Shift 키 누르기
          bleKeyboard.write(KEY_TAB);         // Tab 키: 역방향 이동 (입력 필드로)
          bleKeyboard.release(KEY_LEFT_SHIFT); // Shift 키 떼기
          delay(100);                         // 처리 대기
          
          bleKeyboard.press(KEY_LEFT_SHIFT);  // Shift 키 누르기
          bleKeyboard.write(KEY_TAB);         // Tab 키: 역방향 이동 (입력 필드로)
          bleKeyboard.release(KEY_LEFT_SHIFT); // Shift 키 떼기
          delay(100);                         // 처리 대기
          
          Serial.println("  ✓ 전송 완료 (송장번호 + Tab 2회 + Enter + Shift+Tab 2회)");
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

