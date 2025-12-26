# 라이선스 서버

온라인 라이선스 인증 및 구독 관리 서버

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python license_server.py
```

또는 `start_server.bat` 실행

서버 주소: http://localhost:5000

## API 엔드포인트

### 1. 라이선스 활성화
```
POST /api/activate
{
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "hardware_id": "하드웨어ID",
    "customer_name": "고객명",
    "customer_email": "이메일"
}
```

### 2. 라이선스 검증
```
POST /api/verify
{
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "hardware_id": "하드웨어ID"
}
```

### 3. 라이선스 생성 (관리자)
```
POST /api/create_license
{
    "admin_key": "관리자키",
    "customer_name": "고객명",
    "customer_email": "이메일",
    "subscription_type": "monthly",
    "period_days": 30
}
```

### 4. 라이선스 연장
```
POST /api/extend_license
{
    "license_key": "XXXX-XXXX-XXXX-XXXX",
    "period_days": 30,
    "amount": 30000
}
```

## 관리자 키 설정

`license_server.py` 파일에서 관리자 키를 변경하세요:
```python
if admin_key != 'YOUR_ADMIN_KEY_HERE':  # 여기 변경
```

## 데이터베이스

SQLite 데이터베이스: `licenses.db`

- `licenses` 테이블: 라이선스 정보
- `subscriptions` 테이블: 구독 기록

## 배포

### 로컬 서버
- 개발/테스트용으로 localhost에서 실행

### 클라우드 배포
- **Heroku**: 무료 티어 사용 가능
- **AWS EC2**: 월 약 5,000원
- **Google Cloud**: 무료 티어 사용 가능
- **네이버 클라우드**: 국내 서버, 빠른 속도

### 도메인 연결
- 무료 도메인: Freenom, DuckDNS
- 유료 도메인: 가비아, 후이즈 등

## 보안

1. **HTTPS 사용**: Let's Encrypt 무료 SSL 인증서
2. **관리자 키**: 강력한 비밀번호 사용
3. **방화벽**: 필요한 포트만 개방
4. **백업**: 데이터베이스 정기 백업

