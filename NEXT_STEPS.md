# 다음 단계 - ESP32 인식 완료! 🎉

ESP32가 정상적으로 인식되었습니다. 이제 다음 단계를 진행하세요.

## ✅ 현재 상태
- [x] ESP32 연결 완료
- [x] PC에서 인식 완료
- [ ] COM 포트 번호 확인
- [ ] 설정 파일 업데이트
- [ ] Arduino IDE 설정

## 🔍 Step 1: COM 포트 번호 확인 (지금 해야 할 일!)

### 방법 1: 장치 관리자에서 확인
1. `Win + X` → **장치 관리자**
2. **포트(COM & LPT)** 확장
3. **USB-SERIAL CH340 (COMx)** 항목 확인
4. **COM 번호 기록** (예: COM3, COM4, COM5 등)

### 방법 2: PowerShell에서 확인
```powershell
Get-PnpDevice -Class Ports | Where-Object {$_.Status -eq "OK"}
```

## ⚙️ Step 2: 설정 파일 업데이트

1. `config/settings.json` 파일 열기
2. `"port": "COM3"` 부분을 실제 COM 번호로 변경

예시:
```json
{
  "serial": {
    "port": "COM4",  ← 여기를 실제 COM 번호로 변경!
    "baudrate": 115200,
    "timeout": 1.0
  },
  ...
}
```

## 📝 Step 3: 다음 단계 확인

이제 다음 문서를 따라 진행하세요:

1. **Arduino IDE 설정**: `QUICK_START.md`의 2단계 참고
2. **펌웨어 업로드**: `QUICK_START.md`의 3단계 참고
3. **블루투스 페어링**: `QUICK_START.md`의 4단계 참고

## 💡 참고사항

### 케이블 문제였던 이유
- 일부 USB 케이블은 **충전 전용**으로만 작동 (데이터 전송 불가)
- **데이터 전송이 가능한 케이블**을 사용해야 함
- 앞으로도 이 케이블을 사용하세요!

### COM 포트 번호
- PC마다 COM 포트 번호가 다를 수 있습니다
- USB 포트를 바꾸면 COM 번호가 바뀔 수 있습니다
- 항상 장치 관리자에서 확인하세요

---

**다음**: COM 포트 번호를 확인하고 설정 파일을 업데이트한 후, Arduino IDE 설정을 시작하세요!

