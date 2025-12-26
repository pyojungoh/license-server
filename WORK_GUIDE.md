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

**최종 업데이트**: 2025-12-27

