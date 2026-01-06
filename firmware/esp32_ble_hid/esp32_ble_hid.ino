/*
 * 한진택배 송장번호 자동 등록 시스템
 * ESP32 BLE HID 키보드 펌웨어
 * 
 * 기능:
 * - BLE HID 키보드로 동작
 * - 시리얼 통신으로 텍스트 수신
 * - 수신한 텍스트를 키보드 입력으로 변환
 * - Tab 키 2회 + 엔터 키 + Shift+Tab 2회 (입력 필드 복귀)
 * - 모바일 앱으로부터 인증 토큰 수신 및 검증
 */

#include <BleKeyboard.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

// BLE 키보드 객체 생성
// 파라미터: 장치 이름, 제조사 이름, 배터리 레벨(0-100)
BleKeyboard bleKeyboard("한진택배 스캐너", "Hanjin Automation", 100);

// 연결 상태 LED 핀 (내장 LED 사용, GPIO2)
#define LED_PIN 2

// 연결 상태 추적
bool wasConnected = false;

// 인증 상태 (모바일 앱으로부터 토큰을 받아야만 true가 됨)
bool isActivated = false;

// 토큰 저장 변수
String storedToken = "";

// 토큰 및 Heartbeat 시간 추적
unsigned long tokenReceivedTime = 0;
unsigned long lastHeartbeatTime = 0;
const unsigned long TOKEN_VALIDITY_MS = 3600000;  // 토큰 유효 시간: 1시간 (1000 * 60 * 60)
const unsigned long HEARTBEAT_TIMEOUT_MS = 60000;  // Heartbeat 타임아웃: 60초 (앱이 이 시간 동안 신호를 안 보내면 꺼진 것으로 간주)

// Custom BLE Service UUID (온라인 UUID 생성기로 생성한 고유값)
#define SERVICE_UUID        "12345678-1234-1234-1234-123456789ABC"
#define CHARACTERISTIC_UUID "12345678-1234-1234-1234-123456789DEF"
#define HEARTBEAT_CHAR_UUID "12345678-1234-1234-1234-123456789012"  // Heartbeat용 Characteristic UUID

// 토큰 수신 콜백 클래스
class TokenReceiveCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        // getValue()는 Arduino String을 반환 (ESP32 BLE 라이브러리 최신 버전)
        String rxValue = pCharacteristic->getValue();
        
        if (rxValue.length() > 0) {
            Serial.print("→ 토큰 수신: ");
            Serial.println(rxValue);
            
            // TODO: 서버에 토큰 검증 요청 (현재는 단순히 토큰이 있으면 인증 성공)
            // 나중에 WiFi를 통해 서버 API 호출하여 검증
            if (rxValue.length() > 10) {  // 최소 토큰 길이 체크
                storedToken = rxValue;  // 토큰 저장
                isActivated = true;
                tokenReceivedTime = millis();  // 토큰 수신 시간 저장
                lastHeartbeatTime = millis();  // 초기 Heartbeat 시간 설정
                Serial.println("✓ 인증 성공! 키보드 기능 활성화됨 (1시간 유효, 앱이 켜져 있어야 함)");
                digitalWrite(LED_PIN, HIGH);  // LED 켜기 (인증 성공 표시)
            } else {
                storedToken = "";  // 토큰 초기화
                isActivated = false;
                tokenReceivedTime = 0;
                Serial.println("✗ 인증 실패: 유효하지 않은 토큰");
                digitalWrite(LED_PIN, LOW);
            }
        }
    }
};

// Heartbeat 수신 콜백 클래스 (앱 생존 확인용)
class HeartbeatCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        String rxValue = pCharacteristic->getValue();
        if (rxValue == "HEARTBEAT" || rxValue.length() > 0) {
            lastHeartbeatTime = millis();  // Heartbeat 수신 시간 업데이트
            // Serial.println("✓ Heartbeat 수신 (앱 실행 중)");
        }
    }
};

void setup() {
  // 시리얼 통신 시작 (115200 baud)
  Serial.begin(115200);
  Serial.println("\n=================================");
  Serial.println("ESP32 BLE HID 키보드 시작");
  Serial.println("=================================");
  
  // LED 핀 설정
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // BLE 키보드 시작 (내부적으로 BLEDevice::init() 호출)
  bleKeyboard.begin();
  Serial.println("✓ 블루투스 키보드 초기화 완료");
  
  // Custom BLE Service 추가 (토큰 수신용 + Heartbeat용)
  BLEServer *pServer = BLEDevice::getServer();
  
  if (pServer != nullptr) {
    // 토큰 수신용 서비스 생성
    BLEService *pTokenService = pServer->createService(SERVICE_UUID);
    
    // 토큰 수신용 특성(Characteristic) 생성 (WRITE 속성)
    BLECharacteristic *pTokenCharacteristic = pTokenService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_WRITE
    );
    
    // Heartbeat 수신용 특성(Characteristic) 생성 (WRITE 속성)
    BLECharacteristic *pHeartbeatCharacteristic = pTokenService->createCharacteristic(
      HEARTBEAT_CHAR_UUID,
      BLECharacteristic::PROPERTY_WRITE
    );
    
    // 콜백 함수 연결
    pTokenCharacteristic->setCallbacks(new TokenReceiveCallbacks());
    pHeartbeatCharacteristic->setCallbacks(new HeartbeatCallbacks());
    
    // 서비스 시작
    pTokenService->start();
    
    Serial.println("✓ 토큰 수신 서비스 시작됨");
    Serial.println("  Service UUID: " + String(SERVICE_UUID));
    Serial.println("  Token Characteristic UUID: " + String(CHARACTERISTIC_UUID));
    Serial.println("  Heartbeat Characteristic UUID: " + String(HEARTBEAT_CHAR_UUID));
  } else {
    Serial.println("✗ BLE 서버를 가져올 수 없습니다.");
  }
  
  Serial.println("\n=================================");
  Serial.println("모바일 기기에서 '한진택배 스캐너'를 찾아 페어링하세요.");
  Serial.println("앱에서 인증 토큰을 전송하면 키보드 기능이 활성화됩니다.");
  Serial.println("=================================\n");
}

void loop() {
  // 연결 상태 확인
  bool isConnected = bleKeyboard.isConnected();
  
  // 연결 상태가 변경되었을 때
  if (isConnected != wasConnected) {
    wasConnected = isConnected;
    if (isConnected) {
      Serial.println("\n✓ 블루투스 연결됨!");
      // LED는 인증 상태에 따라 제어 (인증되면 켜짐)
      if (isActivated) {
        digitalWrite(LED_PIN, HIGH);
      }
    } else {
      Serial.println("\n✗ 블루투스 연결 끊김");
      digitalWrite(LED_PIN, LOW);
      isActivated = false;  // 연결이 끊기면 인증 상태 초기화
      storedToken = "";  // 토큰 초기화
    }
  }
  
  // 토큰 및 Heartbeat 유효성 검사
  unsigned long currentTime = millis();
  bool isTokenValid = (tokenReceivedTime > 0) && ((currentTime - tokenReceivedTime) < TOKEN_VALIDITY_MS);
  bool isAppAlive = (lastHeartbeatTime > 0) && ((currentTime - lastHeartbeatTime) < HEARTBEAT_TIMEOUT_MS);
  
  // 토큰 만료 또는 앱이 꺼진 경우 비활성화
  if (isActivated && (!isTokenValid || !isAppAlive)) {
    isActivated = false;
    storedToken = "";  // 토큰 초기화
    tokenReceivedTime = 0;
    lastHeartbeatTime = 0;
    digitalWrite(LED_PIN, LOW);
    if (!isTokenValid) {
      Serial.println("⏰ 토큰 만료됨 (1시간 경과) - 앱에서 재인증 필요");
    } else if (!isAppAlive) {
      Serial.println("📱 앱이 꺼진 것으로 감지됨 - 앱을 켜고 재인증 필요");
    }
  }
  
  // 시리얼로부터 데이터 수신 (인증 여부와 관계없이 GET_TOKEN 명령은 처리)
  if (Serial.available() > 0) {
    // 한 줄 읽기 (개행 문자까지)
    String text = Serial.readStringUntil('\n');
    text.trim();  // 앞뒤 공백 제거
    
    // 빈 문자열이 아니면 처리
    if (text.length() > 0) {
      // GET_TOKEN 명령 처리
      if (text == "GET_TOKEN") {
        if (storedToken.length() > 0) {
          Serial.print("TOKEN:");
          Serial.println(storedToken);
        } else {
          Serial.println("TOKEN:NOT_SET");
        }
        return;  // 명령 처리 완료, loop() 계속 진행
      }
      
      // 인증되어 있고 연결되어 있을 때만 키보드 기능 동작
      if (isActivated && isConnected && isTokenValid && isAppAlive) {
        Serial.print("→ 수신: ");
        Serial.println(text);
        
        // 키보드로 텍스트 입력
        bleKeyboard.print(text);
        delay(150);  // 입력 안정화 대기
        
        // Tab 키 2회 + 엔터 키 + Shift+Tab 2회 (입력 필드 복귀)
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
        // 인증되지 않았거나 연결되지 않았을 때는 키보드 입력 무시
        Serial.println("⚠ 키보드 입력 무시됨 (인증되지 않음 또는 연결되지 않음)");
      }
    }
  }
  
  // 인증 상태 확인 및 메시지 출력
  if (!isActivated || !isConnected || !isTokenValid || !isAppAlive) {
    // 인증되지 않았거나 연결되지 않았을 때
    if (!isConnected) {
      // 연결 대기 중
      static unsigned long lastPrint = 0;
      if (millis() - lastPrint > 3000) {
        Serial.println("블루투스 연결 대기 중...");
        lastPrint = millis();
      }
      delay(100);
    } else if (!isActivated) {
      // 연결되었지만 인증되지 않음 (앱에서 토큰 전송 대기)
      static unsigned long lastPrint = 0;
      if (millis() - lastPrint > 3000) {
        Serial.println("⏳ 인증 토큰 대기 중... (앱에서 토큰을 전송하세요)");
        lastPrint = millis();
      }
      delay(100);
    }
  }
  
  // 짧은 딜레이 (CPU 부하 감소)
  delay(10);
}

