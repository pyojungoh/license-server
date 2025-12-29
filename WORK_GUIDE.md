# 작업 규칙 및 기술 스택 가이드

## 📋 프로젝트 개요

**프로젝트명**: 송장번호 일괄 처리 시스템  
**라이선스 서버**: 온라인 라이선스 인증 및 구독 관리 시스템

---

## 🚀 배포 환경

### 서버 배포
- **플랫폼**: Railway
- **URL**: https://license-server-production-e83a.up.railway.app
- **배포 방법**: GitHub 연동 자동 배포
- **저장소**: https://github.com/pyojungoh/license-server.git

### 배포 설정
- **Root Directory**: `server`
- **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
- **Python Version**: 3.11
- **포트**: Railway가 자동 할당 (환경변수 `PORT` 사용)

### 배포 파일
- `server/Procfile`: Railway 배포 설정
- `server/wsgi.py`: WSGI 엔트리 포인트
- `server/requirements.txt`: Python 의존성

---

## 🎨 프론트엔드

### 웹 관리자 페이지
- **기술**: 순수 HTML + JavaScript (Vanilla JS)
- **템플릿 엔진**: Flask Jinja2
- **위치**: `server/templates/`
- **파일**:
  - `login.html`: 로그인 페이지
  - `index.html`: 메인 관리자 페이지

### 클라이언트 GUI 프로그램
- **기술**: Python Tkinter
- **위치**: `src/gui_app.py`
- **실행**: `python src/gui_app.py` 또는 `run_gui.bat`

---

## 💾 데이터베이스

### 데이터베이스 종류
- **SQLite3**
- **파일 위치**: `server/licenses.db` (Railway 배포 시 `/app/licenses.db`)

### 데이터베이스 스키마

#### `licenses` 테이블
```sql
CREATE TABLE licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT UNIQUE NOT NULL,
    customer_name TEXT,
    customer_email TEXT,
    hardware_id TEXT,
    created_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    subscription_type TEXT DEFAULT 'monthly',
    last_verified TEXT
)
```

#### `subscriptions` 테이블
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL,
    period_days INTEGER NOT NULL,
    FOREIGN KEY (license_key) REFERENCES licenses(license_key)
)
```

---

## 🔧 백엔드

### 서버 프레임워크
- **Flask 2.0+**
- **Gunicorn**: 프로덕션 WSGI 서버
- **Flask-CORS**: CORS 처리

### 주요 모듈
- `server/license_server.py`: 메인 서버 파일
- `server/wsgi.py`: WSGI 엔트리 포인트
- `src/online_license_manager.py`: 클라이언트 라이선스 관리
- `src/hardware_id.py`: 하드웨어 ID 추출

### API 엔드포인트
- `GET /`: 웹 관리자 페이지
- `GET /login`: 로그인 페이지
- `POST /api/activate`: 라이선스 활성화
- `POST /api/verify`: 라이선스 검증
- `POST /api/create_license`: 라이선스 생성 (관리자)
- `POST /api/extend_license`: 라이선스 연장
- `POST /api/list_licenses`: 라이선스 목록 (관리자)
- `POST /api/stats`: 통계 정보 (관리자)
- `POST /api/license_info`: 라이선스 정보 조회

---

## 🔐 보안 설정

### 관리자 키
- **환경변수**: `ADMIN_KEY`
- **기본값**: `2133781qQ!!@#` (프로덕션에서는 반드시 변경!)
- **설정 위치**: Railway Variables

### 하드웨어 바인딩
- 각 라이선스는 하드웨어 ID와 바인딩
- 하드웨어 ID는 CPU, 디스크, MAC 주소 조합

---

## 📁 프로젝트 구조

```
hanjin/
├── server/                 # 서버 코드
│   ├── license_server.py   # 메인 서버
│   ├── wsgi.py            # WSGI 엔트리
│   ├── app.py             # Railway 엔트리 (참고용)
│   ├── Procfile           # Railway 배포 설정
│   ├── requirements.txt   # 서버 의존성
│   ├── templates/         # 웹 템플릿
│   │   ├── login.html
│   │   └── index.html
│   └── licenses.db        # 데이터베이스 (로컬)
├── src/                   # 클라이언트 코드
│   ├── gui_app.py         # GUI 프로그램
│   ├── online_license_manager.py
│   ├── hardware_id.py
│   └── ...
├── config/                # 설정 파일
│   └── settings.json
└── .gitignore
```

---

## 🔄 배포 워크플로우

### 코드 수정 후 배포
1. 로컬에서 코드 수정
2. `git add .`
3. `git commit -m "메시지"`
4. `git push`
5. Railway가 자동으로 재배포

### 환경 변수 변경
1. Railway 대시보드 → Settings → Variables
2. 변수 추가/수정
3. 자동 재배포

---

## 🛠️ 개발 환경

### 코딩 준비 상태

#### Python 환경
- ✅ **Python 버전**: 3.13.4
- ✅ **필수 라이브러리 설치 확인**:
  - `pyserial` (3.5) - 시리얼 통신
  - `openpyxl` (3.1.5) - 엑셀 파일 읽기
  - `colorama` (0.4.6) - 터미널 색상 출력
  - `requests` (2.31.0) - HTTP 통신
  - `Flask` (3.0.0) - 웹 서버
  - `Flask-Cors` (4.0.0) - CORS 처리

#### 프로젝트 구조
```
hanjin/
├── src/                      # 클라이언트 소스 코드
│   ├── main.py              # 메인 프로그램 (터미널 버전)
│   ├── gui_app.py           # GUI 애플리케이션 (Tkinter)
│   ├── bluetooth_controller.py  # ESP32 시리얼 통신
│   ├── excel_reader.py      # 엑셀 파일 읽기
│   ├── online_license_manager.py  # 온라인 라이선스 관리
│   ├── hardware_id.py       # 하드웨어 ID 추출
│   ├── license_manager.py   # 로컬 라이선스 관리 (레거시)
│   └── utils.py             # 유틸리티 함수
├── server/                   # 서버 코드 (Railway 배포)
│   ├── license_server.py    # Flask 라이선스 서버
│   ├── wsgi.py              # WSGI 엔트리 포인트
│   └── templates/           # 웹 관리 페이지
├── firmware/                 # ESP32 펌웨어
│   └── esp32_ble_hid/
│       └── esp32_ble_hid.ino
├── config/                   # 설정 파일
│   ├── settings.json        # 프로그램 설정
│   ├── dev_mode.txt         # 개발 모드 설정
│   └── license.json         # 로컬 라이선스 정보
├── data/                     # 데이터 파일
│   └── invoices.xlsx        # 엑셀 입력 파일
└── logs/                     # 로그 파일
```

#### 주요 기능 구현 상태
- ✅ GUI 애플리케이션 (Tkinter)
- ✅ ESP32 시리얼 통신
- ✅ 엑셀 파일 읽기 (헤더 없이 1행 1열부터)
- ✅ 온라인 라이선스 검증 (강제 온라인 검증 지원)
- ✅ 하드웨어 ID 바인딩
- ✅ 개발 모드 지원 (라이선스 검증 우회)
- ✅ 서버 API (Railway 배포 완료)
- ✅ ESP32 BLE HID 펌웨어

#### 설정 파일
- **`config/settings.json`**: 프로그램 설정 (COM 포트, 딜레이, 엑셀 경로 등)
- **`config/dev_mode.txt`**: 개발 모드 설정 (`true`/`false`)
- **`config/license.json`**: 로컬 라이선스 정보

#### 실행 방법
```bash
# GUI 프로그램 실행
cd c:\hanjin
python src/gui_app.py
# 또는
run_gui.bat

# CLI 프로그램 실행
python src/main.py

# 서버 실행 (로컬)
cd server
python license_server.py
```

### 로컬 개발
```bash
# 서버 실행
cd server
pip install -r requirements.txt
python license_server.py

# 클라이언트 실행
python src/gui_app.py
```

### 서버 URL 설정
- **로컬**: `http://localhost:5000`
- **프로덕션**: `https://license-server-production-e83a.up.railway.app`
- **설정 위치**: `config/settings.json` 또는 `src/gui_app.py`

---

## 📝 작업 규칙

### 1. 코드 수정
- 수정 전에 현재 상태 확인
- 변경 사항은 명확한 커밋 메시지 작성
- 테스트 후 푸시

### 2. 배포
- Railway는 GitHub 푸시 시 자동 배포
- 배포 후 로그 확인 필수
- 문제 발생 시 즉시 롤백

### 3. 데이터베이스
- 프로덕션 DB는 Railway에서 관리
- 로컬 개발용 DB는 `server/licenses.db`
- DB 스키마 변경 시 마이그레이션 고려

### 4. 보안
- 관리자 키는 환경변수로 관리
- 하드웨어 ID는 해시 처리
- HTTPS 사용 (Railway 자동 제공)

### 5. 버전 관리
- 메인 브랜치: `main`
- 중요한 변경은 커밋 전 검토
- 배포 전 테스트 필수

---

## 🔗 주요 링크

- **GitHub 저장소**: https://github.com/pyojungoh/license-server.git
- **Railway 대시보드**: https://railway.app
- **서버 URL**: https://license-server-production-e83a.up.railway.app

---

## ⚠️ 주의사항

1. **관리자 키**: 프로덕션에서는 반드시 강력한 키로 변경
2. **데이터베이스 백업**: 정기적으로 백업 필요
3. **환경변수**: 민감한 정보는 절대 코드에 하드코딩 금지
4. **포트**: Railway가 자동 할당하므로 `$PORT` 환경변수 사용
5. **HTTPS**: Railway가 자동 제공, HTTP는 사용하지 않음

---

---

## 📝 코딩 준비 체크리스트

### 환경 설정
- [ ] Python 3.8+ 설치 확인
- [ ] 필수 라이브러리 설치 (`pip install -r requirements.txt`)
- [ ] COM 포트 확인 (ESP32 연결 시)
- [ ] 설정 파일 확인 (`config/settings.json`)

### 개발 시작 전
- [ ] `WORK_GUIDE.md` 확인
- [ ] `작업내역.md` 확인 (최근 변경사항)
- [ ] 개발 모드 설정 확인 (`config/dev_mode.txt`)
- [ ] 라이선스 서버 URL 확인

### 작업 시작
1. 현재 코드 상태 파악
2. 변경할 파일 확인
3. 테스트 계획 수립
4. 코드 수정
5. 테스트 수행
6. 커밋 및 푸시

---

**최종 업데이트**: 2025-01-27



