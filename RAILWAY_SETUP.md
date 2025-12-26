# Railway PostgreSQL 연결 설정 가이드

## 문제: 테이블이 생성되지 않음

Railway에서 PostgreSQL 서비스를 추가했지만 테이블이 생성되지 않는 경우, 다음을 확인하세요.

## 1. 서비스 간 연결 확인

### PostgreSQL 서비스
- Railway 대시보드에서 PostgreSQL 서비스 확인
- Variables 섹션에서 `DATABASE_URL` 확인
- 이 변수는 자동으로 생성됩니다

### Flask 앱 서비스
- Flask 앱 서비스의 Variables 섹션 확인
- **중요**: `DATABASE_URL` 변수가 있어야 합니다
- PostgreSQL 서비스와 같은 프로젝트에 있어야 합니다

## 2. DATABASE_URL 연결 방법

### 방법 1: 자동 연결 (권장)
1. Railway 대시보드에서 Flask 앱 서비스 선택
2. Variables 탭으로 이동
3. "New Variable" 클릭
4. PostgreSQL 서비스의 Variables에서 `DATABASE_URL` 복사
5. Flask 앱 서비스에 `DATABASE_URL` 변수로 추가

### 방법 2: Railway 자동 연결
- PostgreSQL 서비스를 추가하면 Railway가 자동으로 `DATABASE_URL`을 생성
- Flask 앱 서비스가 같은 프로젝트에 있으면 자동으로 연결될 수 있음
- 하지만 명시적으로 변수를 추가하는 것이 더 안전합니다

## 3. 확인 방법

### Flask 앱 서비스의 Variables 확인
다음 변수들이 있어야 합니다:
- `DATABASE_URL`: PostgreSQL 연결 문자열 (자동 생성)
- `ADMIN_KEY`: 관리자 키 (선택사항, 기본값 사용 가능)
- `PORT`: 포트 번호 (자동 설정)

### 테이블 생성 확인
1. 웹 관리자 페이지 접속
2. 대시보드에서 "DB 연결 확인" 버튼 클릭
3. "테이블: 존재" 또는 "테이블: 없음" 확인

## 4. 수동 테이블 생성

테이블이 자동으로 생성되지 않으면:

### 방법 1: Railway CLI 사용
```bash
railway run python -c "from license_server import init_db; init_db()"
```

### 방법 2: 환경변수 설정 후 재배포
1. Flask 앱 서비스의 Variables에 `FORCE_INIT_DB=true` 추가
2. 재배포하면 자동으로 테이블 생성

### 방법 3: 웹 관리자 페이지에서 확인
- `/api/health` 엔드포인트 호출
- 테이블 존재 여부 확인

## 5. 문제 해결

### DATABASE_URL이 없는 경우
1. PostgreSQL 서비스의 Variables에서 `DATABASE_URL` 복사
2. Flask 앱 서비스의 Variables에 추가
3. 재배포

### 연결이 안 되는 경우
1. 두 서비스가 같은 프로젝트에 있는지 확인
2. PostgreSQL 서비스가 "Online" 상태인지 확인
3. `DATABASE_URL` 형식 확인:
   ```
   postgresql://user:password@host:port/database
   ```

### 테이블이 생성되지 않는 경우
1. `FORCE_INIT_DB=true` 환경변수 추가
2. 재배포
3. 또는 Railway CLI로 수동 실행

## 6. 현재 상태 확인

웹 관리자 페이지에서:
- 대시보드 → "DB 연결 확인" 버튼 클릭
- 다음 정보 확인:
  - 연결 상태
  - 데이터베이스 타입
  - 테이블 존재 여부
  - 라이선스 개수

