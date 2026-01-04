"""
라이선스 서버
온라인 라이선스 인증 및 구독 관리 서버
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import secrets
import datetime
from pathlib import Path
import json
import os
import bcrypt
import requests

# 템플릿 폴더 경로 (현재 파일 기준)
template_dir = Path(__file__).parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))
CORS(app)  # CORS 허용 (클라이언트에서 접근 가능하도록)

# 관리자 키 (환경변수 또는 기본값)
ADMIN_KEY = os.environ.get('ADMIN_KEY', '2133781qQ!!@#')

# 텔레그램 봇 설정 (환경변수)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# 데이터베이스 연결 설정
# Railway PostgreSQL 사용 (DATABASE_URL 환경변수)
# 없으면 로컬 SQLite 사용
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
# PostgreSQL 감지: postgresql:// 또는 postgres://로 시작하는지 확인
USE_POSTGRESQL = bool(DATABASE_URL and (DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')))

if not USE_POSTGRESQL:
    # 로컬 개발용 SQLite
    volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '/app/data')
    DB_DIR = Path(volume_path)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = DB_DIR / "licenses.db"

def get_db_connection():
    """데이터베이스 연결 반환"""
    if USE_POSTGRESQL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

def init_db():
    """데이터베이스 초기화 (안전하게 - 기존 데이터 보존)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # PostgreSQL 연결 확인
    if USE_POSTGRESQL:
        if not DATABASE_URL:
            logger.error("USE_POSTGRESQL이 True인데 DATABASE_URL이 없습니다!")
            raise ValueError("DATABASE_URL이 설정되지 않았습니다")
        logger.info(f"PostgreSQL 연결 시도: {DATABASE_URL[:30]}...")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 테이블 확인 (필수 테이블들 체크)
        required_tables = ['licenses', 'users', 'user_devices', 'user_access_tokens']
        tables_exist = {}
        try:
            if USE_POSTGRESQL:
                for table_name in required_tables:
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    """, (table_name,))
                    tables_exist[table_name] = cursor.fetchone()[0] > 0
            else:
                for table_name in required_tables:
                    cursor.execute("""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table_name,))
                    tables_exist[table_name] = cursor.fetchone()[0] > 0
            
            # 기존 데이터 개수 확인 및 로깅
            if tables_exist.get('licenses', False):
                cursor.execute("SELECT COUNT(*) FROM licenses")
                existing_count = cursor.fetchone()[0]
                logger.info(f"✓ 기존 licenses 테이블 발견: {existing_count}개의 라이선스가 있습니다.")
            
            if tables_exist.get('users', False):
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                logger.info(f"✓ 기존 users 테이블 발견: {user_count}명의 사용자가 있습니다.")
            
            # 모든 필수 테이블이 존재하는지 확인
            all_tables_exist = all(tables_exist.get(table, False) for table in required_tables)
            if all_tables_exist:
                logger.info("기존 테이블이 모두 존재합니다. 데이터를 보존합니다.")
                conn.close()
                return  # 테이블이 이미 있으면 생성하지 않음
            else:
                missing_tables = [table for table in required_tables if not tables_exist.get(table, False)]
                logger.info(f"일부 테이블이 없습니다. 누락된 테이블: {missing_tables}. 필요한 테이블을 생성합니다.")
        except Exception as e:
            # 연결은 성공했지만 쿼리 실패
            logger.warning(f"테이블 확인 중 오류 (테이블 생성 시도): {e}")
            # 테이블이 없을 수 있으므로 생성 시도
        
        # 테이블 생성
        if USE_POSTGRESQL:
            # PostgreSQL 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id SERIAL PRIMARY KEY,
                    license_key VARCHAR(255) UNIQUE NOT NULL,
                    customer_name VARCHAR(255),
                    customer_email VARCHAR(255),
                    hardware_id VARCHAR(255),
                    created_date TIMESTAMP NOT NULL,
                    expiry_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    subscription_type VARCHAR(50) DEFAULT 'monthly',
                    last_verified TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    license_key VARCHAR(255) NOT NULL,
                    payment_date TIMESTAMP NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    period_days INTEGER NOT NULL,
                    FOREIGN KEY (license_key) REFERENCES licenses(license_key)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id SERIAL PRIMARY KEY,
                    license_key VARCHAR(255) NOT NULL,
                    usage_date TIMESTAMP NOT NULL,
                    total_invoices INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (license_key) REFERENCES licenses(license_key)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_stats_license_date 
                ON usage_stats(license_key, usage_date)
            """)
            
            # 사용자 계정 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    hardware_id VARCHAR(255),
                    created_date TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    subscription_type VARCHAR(50) DEFAULT 'monthly',
                    start_date TIMESTAMP NOT NULL,
                    expiry_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS allowed_mac_addresses (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    mac_address VARCHAR(17) NOT NULL,
                    device_name VARCHAR(100),
                    registered_date TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, mac_address)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    usage_date TIMESTAMP NOT NULL,
                    total_invoices INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    hardware_id VARCHAR(255),
                    mac_address VARCHAR(17),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_payments (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    payment_date TIMESTAMP NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    period_days INTEGER NOT NULL,
                    payment_method VARCHAR(50),
                    note TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # 사용자 기기 등록 테이블 (1인 1기기 정책용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_devices (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    device_uuid VARCHAR(255) UNIQUE NOT NULL,
                    device_name VARCHAR(100),
                    registered_date TIMESTAMP DEFAULT NOW(),
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, device_uuid)
                )
            """)
            
            # 인증 토큰 테이블 (액세스 토큰 저장)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_access_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    device_uuid VARCHAR(255) NOT NULL,
                    access_token VARCHAR(500) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    created_date TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (device_uuid) REFERENCES user_devices(device_uuid) ON DELETE CASCADE
                )
            """)
            
            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expiry ON user_subscriptions(expiry_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_allowed_mac_user_id ON allowed_mac_addresses(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_allowed_mac_address ON allowed_mac_addresses(mac_address)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_usage_user_id ON user_usage(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_usage_date ON user_usage(usage_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_payments_user_id ON user_payments(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_devices_user_id ON user_devices(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_devices_device_uuid ON user_devices(device_uuid)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_user_id ON user_access_tokens(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_token_hash ON user_access_tokens(token_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_expires_at ON user_access_tokens(expires_at)
            """)
        else:
            # SQLite 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
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
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL,
                    payment_date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    period_days INTEGER NOT NULL,
                    FOREIGN KEY (license_key) REFERENCES licenses(license_key)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    total_invoices INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (license_key) REFERENCES licenses(license_key)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_stats_license_date 
                ON usage_stats(license_key, usage_date)
            """)
            
            # 사용자 계정 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    hardware_id TEXT,
                    created_date TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    subscription_type TEXT DEFAULT 'monthly',
                    start_date TEXT NOT NULL,
                    expiry_date TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS allowed_mac_addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    mac_address TEXT NOT NULL,
                    device_name TEXT,
                    registered_date TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, mac_address)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    total_invoices INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    hardware_id TEXT,
                    mac_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    payment_date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    period_days INTEGER NOT NULL,
                    payment_method TEXT,
                    note TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # 사용자 기기 등록 테이블 (1인 1기기 정책용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    device_uuid TEXT UNIQUE NOT NULL,
                    device_name TEXT,
                    registered_date TEXT NOT NULL,
                    last_used TEXT,
                    is_active INTEGER DEFAULT 1,
                    UNIQUE(user_id, device_uuid)
                )
            """)
            
            # 인증 토큰 테이블 (액세스 토큰 저장)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_access_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    device_uuid TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expiry ON user_subscriptions(expiry_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_allowed_mac_user_id ON allowed_mac_addresses(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_allowed_mac_address ON allowed_mac_addresses(mac_address)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_usage_user_id ON user_usage(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_usage_date ON user_usage(usage_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_payments_user_id ON user_payments(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_devices_user_id ON user_devices(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_devices_device_uuid ON user_devices(device_uuid)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_user_id ON user_access_tokens(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_token_hash ON user_access_tokens(token_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_access_tokens_expires_at ON user_access_tokens(expires_at)
            """)
        
        conn.commit()
        logger.info("✓ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"✗ 데이터베이스 초기화 실패: {e}")
        raise
    finally:
        if conn:
            conn.close()

def generate_license_key() -> str:
    """라이선스 키 생성"""
    return ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(16))

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_access_token() -> str:
    """액세스 토큰 생성 (랜덤 문자열)"""
    return secrets.token_urlsafe(32)  # 32바이트 랜덤 토큰 생성

def hash_token(token: str) -> str:
    """토큰 해시 (DB 저장용)"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

@app.route('/api/activate', methods=['POST'])
def activate_license():
    """라이선스 활성화"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    hardware_id = data.get('hardware_id', '')
    customer_name = data.get('customer_name', '')
    customer_email = data.get('customer_email', '')
    
    if not license_key or not hardware_id:
        return jsonify({'success': False, 'message': '라이선스 키와 하드웨어 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 라이선스 확인
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT * FROM licenses 
            WHERE license_key = %s AND is_active = TRUE
        """, (license_key,))
    else:
        cursor.execute("""
            SELECT * FROM licenses 
            WHERE license_key = ? AND is_active = 1
        """, (license_key,))
    
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '유효하지 않은 라이선스 키입니다.'}), 400
    
    # 하드웨어 ID 확인 (PostgreSQL은 dict, SQLite는 tuple)
    if USE_POSTGRESQL:
        stored_hw_id = license_data.get('hardware_id')
        expiry_date_str = license_data.get('expiry_date')
    else:
        stored_hw_id = license_data[5]  # hardware_id 컬럼
        expiry_date_str = license_data[6]  # expiry_date 컬럼
    
    if stored_hw_id and stored_hw_id != hardware_id:
        conn.close()
        return jsonify({
            'success': False, 
            'message': '이 라이선스는 다른 컴퓨터에 등록되어 있습니다.'
        }), 400
    
    # 하드웨어 ID가 없으면 등록
    if not stored_hw_id:
        if USE_POSTGRESQL:
            cursor.execute("""
                UPDATE licenses 
                SET hardware_id = %s, customer_name = %s, customer_email = %s
                WHERE license_key = %s
            """, (hardware_id, customer_name, customer_email, license_key))
        else:
            cursor.execute("""
                UPDATE licenses 
                SET hardware_id = ?, customer_name = ?, customer_email = ?
                WHERE license_key = ?
            """, (hardware_id, customer_name, customer_email, license_key))
        conn.commit()
    
    # 만료일 확인
    if isinstance(expiry_date_str, str):
        expiry_date = datetime.datetime.fromisoformat(expiry_date_str)
    else:
        expiry_date = expiry_date_str  # 이미 datetime 객체
    
    if datetime.datetime.now() > expiry_date:
        conn.close()
        return jsonify({
            'success': False, 
            'message': f'라이선스가 만료되었습니다. (만료일: {expiry_date.strftime("%Y-%m-%d")})'
        }), 400
    
    # 검증 시간 업데이트
    now = datetime.datetime.now()
    if USE_POSTGRESQL:
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = %s
            WHERE license_key = %s
        """, (now, license_key))
    else:
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = ?
            WHERE license_key = ?
        """, (now.isoformat(), license_key))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '라이선스가 활성화되었습니다.',
        'expiry_date': expiry_date.isoformat()
    })

@app.route('/api/verify', methods=['POST'])
def verify_license():
    """라이선스 검증 (주기적 검증)"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    hardware_id = data.get('hardware_id', '')
    
    if not license_key or not hardware_id:
        return jsonify({'success': False, 'message': '라이선스 키와 하드웨어 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT * FROM licenses 
            WHERE license_key = %s AND hardware_id = %s AND is_active = TRUE
        """, (license_key, hardware_id))
    else:
        cursor.execute("""
            SELECT * FROM licenses 
            WHERE license_key = ? AND hardware_id = ? AND is_active = 1
        """, (license_key, hardware_id))
    
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '유효하지 않은 라이선스입니다.'}), 400
    
    if USE_POSTGRESQL:
        expiry_date = license_data.get('expiry_date')
        if isinstance(expiry_date, str):
            expiry_date = datetime.datetime.fromisoformat(expiry_date)
    else:
        expiry_date = datetime.datetime.fromisoformat(license_data[6])
    
    is_expired = datetime.datetime.now() > expiry_date
    
    # 검증 시간 업데이트
    now = datetime.datetime.now()
    if USE_POSTGRESQL:
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = %s
            WHERE license_key = %s
        """, (now, license_key))
    else:
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = ?
            WHERE license_key = ?
        """, (now.isoformat(), license_key))
    conn.commit()
    conn.close()
    
    if is_expired:
        return jsonify({
            'success': False,
            'message': f'라이선스가 만료되었습니다. (만료일: {expiry_date.strftime("%Y-%m-%d")})',
            'expiry_date': expiry_date.isoformat()
        })
    
    return jsonify({
        'success': True,
        'message': '라이선스가 유효합니다.',
        'expiry_date': expiry_date.isoformat()
    })

@app.route('/api/create_license', methods=['POST'])
def create_license():
    """새 라이선스 생성 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')  # 간단한 관리자 키
    
    # 관리자 키 확인
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    customer_name = data.get('customer_name', '')
    customer_email = data.get('customer_email', '')
    subscription_type = data.get('subscription_type', 'monthly')  # monthly, yearly
    period_days = data.get('period_days', 30)  # 기본 30일
    
    license_key = generate_license_key()
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=period_days)
    
    import logging
    logger = logging.getLogger(__name__)
    
    conn = None
    cursor = None
    try:
        logger.info(f"라이선스 생성 시작: customer_name={customer_name}, period_days={period_days}")
        logger.info(f"데이터베이스 모드: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
        
        conn = get_db_connection()
        # PostgreSQL은 autocommit이 꺼져있으므로 명시적으로 설정
        if USE_POSTGRESQL:
            conn.autocommit = False
            logger.info("PostgreSQL 연결 성공, autocommit=False 설정")
        
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        logger.info(f"라이선스 키 생성: {license_key}, 만료일: {expiry_date}")
        
        if USE_POSTGRESQL:
            logger.info("PostgreSQL INSERT 실행 중...")
            cursor.execute("""
                INSERT INTO licenses (license_key, customer_name, customer_email, 
                                   created_date, expiry_date, subscription_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (license_key, customer_name, customer_email, now, expiry_date, subscription_type))
            logger.info("PostgreSQL INSERT 완료")
        else:
            logger.info("SQLite INSERT 실행 중...")
            cursor.execute("""
                INSERT INTO licenses (license_key, customer_name, customer_email, 
                                   created_date, expiry_date, subscription_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (license_key, customer_name, customer_email, 
                  now.isoformat(), expiry_date.isoformat(), subscription_type))
            logger.info("SQLite INSERT 완료")
        
        # 커밋 실행
        logger.info("커밋 실행 중...")
        conn.commit()
        logger.info("커밋 완료")
        
        # 커밋 후 데이터 확인 (디버깅)
        cursor.execute("SELECT COUNT(*) FROM licenses WHERE license_key = %s" if USE_POSTGRESQL else "SELECT COUNT(*) FROM licenses WHERE license_key = ?", 
                      (license_key,))
        count = cursor.fetchone()[0]
        logger.info(f"라이선스 생성 완료: {license_key}, DB에 저장 확인: {count}개")
        
        if count == 0:
            logger.error(f"경고: 라이선스가 저장되지 않았습니다! {license_key}")
            return jsonify({'success': False, 'message': '라이선스가 저장되지 않았습니다.'}), 500
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry_date': expiry_date.isoformat()
        })
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error("롤백 실행됨")
        import traceback
        logger.error(f"라이선스 생성 실패: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'라이선스 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("데이터베이스 연결 종료")

@app.route('/api/extend_license', methods=['POST'])
def extend_license():
    """라이선스 연장 (구독 갱신)"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    period_days = data.get('period_days', 30)
    amount = data.get('amount', 0)
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 기존 라이선스 확인
    if USE_POSTGRESQL:
        cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
    else:
        cursor.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key,))
    
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '라이선스를 찾을 수 없습니다.'}), 400
    
    # 만료일 연장
    if USE_POSTGRESQL:
        current_expiry = license_data.get('expiry_date')
        if isinstance(current_expiry, str):
            current_expiry = datetime.datetime.fromisoformat(current_expiry)
    else:
        current_expiry = datetime.datetime.fromisoformat(license_data[6])
    
    if current_expiry < datetime.datetime.now():
        # 이미 만료된 경우 오늘부터 시작
        new_expiry = datetime.datetime.now() + datetime.timedelta(days=period_days)
    else:
        # 아직 유효한 경우 기존 만료일부터 연장
        new_expiry = current_expiry + datetime.timedelta(days=period_days)
    
    try:
        now = datetime.datetime.now()
        if USE_POSTGRESQL:
            cursor.execute("""
                UPDATE licenses 
                SET expiry_date = %s
                WHERE license_key = %s
            """, (new_expiry, license_key))
            
            cursor.execute("""
                INSERT INTO subscriptions (license_key, payment_date, amount, period_days)
                VALUES (%s, %s, %s, %s)
            """, (license_key, now, amount, period_days))
        else:
            cursor.execute("""
                UPDATE licenses 
                SET expiry_date = ?
                WHERE license_key = ?
            """, (new_expiry.isoformat(), license_key))
            
            cursor.execute("""
                INSERT INTO subscriptions (license_key, payment_date, amount, period_days)
                VALUES (?, ?, ?, ?)
            """, (license_key, now.isoformat(), amount, period_days))
        
        conn.commit()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"라이선스 연장 완료: {license_key}, 새 만료일: {new_expiry}")
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"라이선스 연장 실패: {e}")
        return jsonify({'success': False, 'message': f'라이선스 연장 실패: {str(e)}'}), 500
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': '라이선스가 연장되었습니다.',
        'expiry_date': new_expiry.isoformat()
    })

@app.route('/login')
def login():
    """로그인 페이지"""
    return render_template('login.html')

@app.route('/')
def index():
    """웹 관리자 페이지"""
    return render_template('index.html')

@app.route('/test')
def test_page():
    """한진택배 앱 테스트 페이지"""
    return render_template('test.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """데이터베이스 연결 상태 확인"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Health check: USE_POSTGRESQL={USE_POSTGRESQL}, DATABASE_URL 존재={bool(DATABASE_URL)}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 데이터베이스 타입 확인
        if USE_POSTGRESQL:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            db_type = "PostgreSQL"
            
            # 현재 데이터베이스 이름 확인
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            
            # 테이블 존재 확인 (public 스키마만)
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'licenses'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            # 데이터 개수 확인
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM licenses")
                license_count = cursor.fetchone()[0]
            else:
                license_count = 0
        else:
            cursor.execute("SELECT sqlite_version();")
            db_version = cursor.fetchone()[0]
            db_type = "SQLite"
            db_name = str(DB_PATH) if DB_PATH else "N/A"
            
            # 테이블 존재 확인
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='licenses'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            # 데이터 개수 확인
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM licenses")
                license_count = cursor.fetchone()[0]
            else:
                license_count = 0
        
        conn.close()
        
        result = {
            'success': True,
            'database_type': db_type,
            'database_name': db_name,
            'database_version': db_version,
            'connected': True,
            'table_exists': table_exists,
            'license_count': license_count,
            'database_url_set': USE_POSTGRESQL,
            'database_url_present': bool(DATABASE_URL),
            'database_url_preview': DATABASE_URL[:50] + '...' if DATABASE_URL and len(DATABASE_URL) > 50 else (DATABASE_URL or 'None')
        }
        
        logger.info(f"Health check 결과: {result}")
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'connected': False,
            'error': str(e),
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') == 'True' else None
        }), 500

@app.route('/api/license_info', methods=['POST'])
def get_license_info():
    """라이선스 정보 조회"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT license_key, customer_name, expiry_date, subscription_type, last_verified
            FROM licenses 
            WHERE license_key = %s
        """, (license_key,))
    else:
        cursor.execute("""
            SELECT license_key, customer_name, expiry_date, subscription_type, last_verified
            FROM licenses 
            WHERE license_key = ?
        """, (license_key,))
    
    license_data = cursor.fetchone()
    conn.close()
    
    if not license_data:
        return jsonify({'success': False, 'message': '라이선스를 찾을 수 없습니다.'}), 400
    
    if USE_POSTGRESQL:
        expiry_date = license_data.get('expiry_date')
        if hasattr(expiry_date, 'isoformat'):
            expiry_date = expiry_date.isoformat()
        last_verified = license_data.get('last_verified')
        if last_verified and hasattr(last_verified, 'isoformat'):
            last_verified = last_verified.isoformat()
        
        return jsonify({
            'success': True,
            'license_key': license_data.get('license_key'),
            'customer_name': license_data.get('customer_name'),
            'expiry_date': expiry_date,
            'subscription_type': license_data.get('subscription_type'),
            'last_verified': last_verified
        })
    else:
        return jsonify({
            'success': True,
            'license_key': license_data[0],
            'customer_name': license_data[1],
            'expiry_date': license_data[2],
            'subscription_type': license_data[3],
            'last_verified': license_data[4]
        })

@app.route('/api/list_licenses', methods=['POST'])
def list_licenses():
    """라이선스 목록 조회 (관리자용)"""
    conn = None
    cursor = None
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type이 application/json이어야 합니다.'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
        
        admin_key = data.get('admin_key', '')
        
        if admin_key != ADMIN_KEY:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute("""
                SELECT license_key, customer_name, customer_email, expiry_date, 
                       subscription_type, is_active, last_verified, created_date
                FROM licenses
                ORDER BY created_date DESC
            """)
        else:
            cursor.execute("""
                SELECT license_key, customer_name, customer_email, expiry_date, 
                       subscription_type, is_active, last_verified, created_date
                FROM licenses
                ORDER BY created_date DESC
            """)
        
        licenses = []
        for row in cursor.fetchall():
            if USE_POSTGRESQL:
                expiry_date_val = row.get('expiry_date')
                if isinstance(expiry_date_val, str):
                    expiry_date = datetime.datetime.fromisoformat(expiry_date_val)
                else:
                    expiry_date = expiry_date_val
                license_key_val = row.get('license_key')
            else:
                expiry_date = datetime.datetime.fromisoformat(row[3])
                license_key_val = row[0]
            
            is_expired = datetime.datetime.now() > expiry_date
            
            # 사용 통계 조회
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as run_count,
                        SUM(total_invoices) as total_invoices,
                        MAX(usage_date) as last_usage
                    FROM usage_stats
                    WHERE license_key = %s
                """, (license_key_val,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as run_count,
                        SUM(total_invoices) as total_invoices,
                        MAX(usage_date) as last_usage
                    FROM usage_stats
                    WHERE license_key = ?
                """, (license_key_val,))
            
            usage_data = cursor.fetchone()
            
            # 사용 통계 데이터 안전하게 추출
            if USE_POSTGRESQL:
                if usage_data:
                    run_count = usage_data.get('run_count') or 0
                    total_invoices = usage_data.get('total_invoices') or 0
                    last_usage = usage_data.get('last_usage')
                else:
                    run_count = 0
                    total_invoices = 0
                    last_usage = None
            else:
                if usage_data:
                    run_count = usage_data[0] or 0
                    total_invoices = usage_data[1] or 0
                    last_usage = usage_data[2]
                else:
                    run_count = 0
                    total_invoices = 0
                    last_usage = None
            
            # 날짜 형식 변환
            if last_usage:
                if isinstance(last_usage, str):
                    last_usage_str = last_usage
                elif hasattr(last_usage, 'isoformat'):
                    last_usage_str = last_usage.isoformat()
                else:
                    last_usage_str = str(last_usage)
            else:
                last_usage_str = None
            
            if USE_POSTGRESQL:
                # expiry_date 처리
                expiry_date_val = row.get('expiry_date')
                if isinstance(expiry_date_val, str):
                    expiry_date_obj = datetime.datetime.fromisoformat(expiry_date_val.replace('Z', '+00:00'))
                elif hasattr(expiry_date_val, 'isoformat'):
                    expiry_date_obj = expiry_date_val
                else:
                    expiry_date_obj = expiry_date_val
                
                expiry_date_str = expiry_date_obj.isoformat() if hasattr(expiry_date_obj, 'isoformat') else str(expiry_date_obj)
                
                # last_verified 처리
                last_verified_val = row.get('last_verified')
                if last_verified_val:
                    if isinstance(last_verified_val, str):
                        last_verified_str = last_verified_val
                    elif hasattr(last_verified_val, 'isoformat'):
                        last_verified_str = last_verified_val.isoformat()
                    else:
                        last_verified_str = str(last_verified_val)
                else:
                    last_verified_str = ''
                
                # created_date 처리
                created_date_val = row.get('created_date')
                if created_date_val:
                    if isinstance(created_date_val, str):
                        created_date_str = created_date_val
                    elif hasattr(created_date_val, 'isoformat'):
                        created_date_str = created_date_val.isoformat()
                    else:
                        created_date_str = str(created_date_val)
                else:
                    created_date_str = ''
                
                licenses.append({
                    'license_key': row.get('license_key', ''),
                    'customer_name': row.get('customer_name') or '',
                    'customer_email': row.get('customer_email') or '',
                    'expiry_date': expiry_date_str,
                    'subscription_type': row.get('subscription_type') or '',
                    'is_active': bool(row.get('is_active')),
                    'is_expired': is_expired,
                    'last_verified': last_verified_str,
                    'created_date': created_date_str,
                    'run_count': run_count,
                    'total_invoices': total_invoices,
                    'last_usage': last_usage_str
                })
            else:
                licenses.append({
                    'license_key': row[0] or '',
                    'customer_name': row[1] or '',
                    'customer_email': row[2] or '',
                    'expiry_date': row[3] or '',
                    'subscription_type': row[4] or '',
                    'is_active': bool(row[5] if len(row) > 5 else True),  # 기본값 True
                    'is_expired': is_expired,
                    'last_verified': row[6] or '' if len(row) > 6 else '',
                    'created_date': row[7] or '' if len(row) > 7 else '',
                    'run_count': run_count,
                    'total_invoices': total_invoices,
                    'last_usage': last_usage_str
                })
        
        return jsonify({
            'success': True,
            'licenses': licenses
        })
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"라이선스 목록 조회 중 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'라이선스 목록 조회 실패: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/toggle_license', methods=['POST'])
def toggle_license():
    """라이선스 활성화/비활성화 토글 (관리자용)"""
    conn = None
    cursor = None
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type이 application/json이어야 합니다.'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
        
        admin_key = data.get('admin_key', '')
        license_key = data.get('license_key', '').upper()
        
        if admin_key != ADMIN_KEY:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        if not license_key:
            return jsonify({'success': False, 'message': '라이선스 키가 필요합니다.'}), 400
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 현재 상태 확인
        if USE_POSTGRESQL:
            cursor.execute("SELECT is_active FROM licenses WHERE license_key = %s", (license_key,))
        else:
            cursor.execute("SELECT is_active FROM licenses WHERE license_key = ?", (license_key,))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': '라이선스를 찾을 수 없습니다.'}), 404
        
        # PostgreSQL과 SQLite에서 데이터 추출 방식이 다름
        if USE_POSTGRESQL:
            current_status = result.get('is_active') if isinstance(result, dict) else result[0]
        else:
            current_status = result[0]
        
        new_status = not bool(current_status)
        
        # 상태 업데이트
        if USE_POSTGRESQL:
            cursor.execute("""
                UPDATE licenses 
                SET is_active = %s 
                WHERE license_key = %s
            """, (new_status, license_key))
        else:
            cursor.execute("""
                UPDATE licenses 
                SET is_active = ? 
                WHERE license_key = ?
            """, (1 if new_status else 0, license_key))
        
        conn.commit()
        
        action = '활성화' if new_status else '중지'
        return jsonify({
            'success': True,
            'message': f'라이선스가 {action}되었습니다.',
            'is_active': new_status
        })
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"라이선스 토글 중 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'라이선스 상태 변경 실패: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/stats', methods=['POST'])
def get_stats():
    """통계 정보 조회 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 전체 라이선스 수
    cursor.execute("SELECT COUNT(*) FROM licenses")
    total_licenses = cursor.fetchone()[0]
    
    # 활성 라이선스 수 (만료일이 미래이고 활성화된 것)
    now = datetime.datetime.now()
    if USE_POSTGRESQL:
        # PostgreSQL: expiry_date는 TIMESTAMP 타입
        cursor.execute("""
            SELECT COUNT(*) FROM licenses 
            WHERE expiry_date > %s AND is_active = TRUE
        """, (now,))
    else:
        # SQLite: expiry_date는 TEXT(ISO 문자열)
        cursor.execute("""
            SELECT COUNT(*) FROM licenses 
            WHERE expiry_date > ? AND is_active = 1
        """, (now.isoformat(),))
    active_licenses = cursor.fetchone()[0]
    
    # 만료된 라이선스 수 (만료일이 지났거나 비활성화된 것)
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT COUNT(*) FROM licenses 
            WHERE expiry_date <= %s OR is_active = FALSE
        """, (now,))
    else:
        cursor.execute("""
            SELECT COUNT(*) FROM licenses 
            WHERE expiry_date <= ? OR is_active = 0
        """, (now.isoformat(),))
    expired_licenses = cursor.fetchone()[0]
    
    # 총 수익
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM subscriptions")
    total_revenue = cursor.fetchone()[0] or 0
    
    # 디버깅: 실제 데이터 확인
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT license_key, expiry_date, is_active, created_date 
            FROM licenses 
            ORDER BY created_date DESC 
            LIMIT 5
        """)
    else:
        cursor.execute("""
            SELECT license_key, expiry_date, is_active, created_date 
            FROM licenses 
            ORDER BY created_date DESC 
            LIMIT 5
        """)
    debug_data = cursor.fetchall()
    
    conn.close()
    
    # 디버깅 로그 (개발 환경에서만)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Stats Debug - Total: {total_licenses}, Active: {active_licenses}, Expired: {expired_licenses}, Now: {now}")
    logger.info(f"Debug Data: {debug_data}")
    
    return jsonify({
        'success': True,
        'total_licenses': total_licenses,
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'total_revenue': total_revenue
    })

@app.route('/api/record_usage', methods=['POST'])
def record_usage():
    """사용 통계 기록"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    hardware_id = data.get('hardware_id', '')
    total_invoices = data.get('total_invoices', 0)
    success_count = data.get('success_count', 0)
    fail_count = data.get('fail_count', 0)
    
    if not license_key or not hardware_id:
        return jsonify({'success': False, 'message': '라이선스 키와 하드웨어 ID가 필요합니다.'}), 400
    
    # 라이선스 및 하드웨어 ID 검증
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT hardware_id FROM licenses 
            WHERE license_key = %s AND hardware_id = %s AND is_active = TRUE
        """, (license_key, hardware_id))
    else:
        cursor.execute("""
            SELECT hardware_id FROM licenses 
            WHERE license_key = ? AND hardware_id = ? AND is_active = 1
        """, (license_key, hardware_id))
    
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': '유효하지 않은 라이선스입니다.'}), 400
    
    # 사용 통계 저장
    now = datetime.datetime.now()
    if USE_POSTGRESQL:
        cursor.execute("""
            INSERT INTO usage_stats (license_key, usage_date, total_invoices, success_count, fail_count)
            VALUES (%s, %s, %s, %s, %s)
        """, (license_key, now, total_invoices, success_count, fail_count))
        
        # 마지막 사용 시간 업데이트
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = %s
            WHERE license_key = %s
        """, (now, license_key))
    else:
        cursor.execute("""
            INSERT INTO usage_stats (license_key, usage_date, total_invoices, success_count, fail_count)
            VALUES (?, ?, ?, ?, ?)
        """, (license_key, now.isoformat(), total_invoices, success_count, fail_count))
        
        # 마지막 사용 시간 업데이트
        cursor.execute("""
            UPDATE licenses 
            SET last_verified = ?
            WHERE license_key = ?
        """, (now.isoformat(), license_key))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '사용 통계가 기록되었습니다.'
    })

@app.route('/api/login', methods=['POST'])
def user_login():
    """
    사용자 로그인 (PC 프로그램 및 모바일 앱용)
    - PC 프로그램: device_uuid 없이 로그인 (단순 인증만 수행)
    - 모바일 앱: device_uuid 필요 (1인 1기기 정책), 액세스 토큰 발급
    """
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
        
        user_id = data.get('user_id', '').strip()
        password = data.get('password', '')
        device_uuid = data.get('device_uuid', '').strip()  # 모바일 기기 UUID
        device_name = data.get('device_name', '').strip()  # 기기 이름 (선택사항)
        
        if not user_id or not password:
            return jsonify({'success': False, 'message': '아이디와 비밀번호가 필요합니다.'}), 400
        
        # device_uuid는 선택사항 (PC 프로그램 로그인 시에는 없을 수 있음)
        is_mobile_app = bool(device_uuid)
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        # 사용자 조회
        if USE_POSTGRESQL:
            cursor.execute("SELECT user_id, password_hash, name, email, is_active FROM users WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT user_id, password_hash, name, email, is_active FROM users WHERE user_id = ?", (user_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            if conn:
                conn.close()
            return jsonify({'success': False, 'message': '아이디 또는 비밀번호가 잘못되었습니다.'}), 400
        
        # 비밀번호 확인 (컬럼명 직접 지정으로 안전하게 처리)
        if USE_POSTGRESQL:
            password_hash = user_data.get('password_hash') if user_data else None
            is_active = user_data.get('is_active') if user_data else False
            name = user_data.get('name') if user_data else ''
            email = user_data.get('email') if user_data else ''
        else:
            # SQLite: SELECT에서 지정한 순서대로 (user_id, password_hash, name, email, is_active)
            try:
                password_hash = user_data[1] if len(user_data) > 1 else None
                name = user_data[2] if len(user_data) > 2 else ''
                email = user_data[3] if len(user_data) > 3 else ''
                is_active = bool(user_data[4] if len(user_data) > 4 else False)
            except (IndexError, TypeError):
                if conn:
                    conn.close()
                return jsonify({'success': False, 'message': '사용자 데이터 오류가 발생했습니다.'}), 500
        
        if not password_hash:
            if conn:
                conn.close()
            return jsonify({'success': False, 'message': '아이디 또는 비밀번호가 잘못되었습니다.'}), 400
        
        if not verify_password(password, password_hash):
            if conn:
                conn.close()
            return jsonify({'success': False, 'message': '아이디 또는 비밀번호가 잘못되었습니다.'}), 400
        
        # 계정 활성화 확인
        if not is_active:
            if conn:
                conn.close()
            return jsonify({'success': False, 'message': '비활성화된 계정입니다. 관리자에게 문의하세요.'}), 400
        
        now = datetime.datetime.now()
        
        # PC 프로그램 로그인 (UUID 없음): 단순 인증만 수행, 토큰 발급 안 함
        if not is_mobile_app:
            # last_login만 업데이트
            if USE_POSTGRESQL:
                cursor.execute("UPDATE users SET last_login = %s WHERE user_id = %s", (now, user_id))
            else:
                cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now.isoformat(), user_id))
            
            # 구독 정보 조회
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT expiry_date FROM user_subscriptions 
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY expiry_date DESC LIMIT 1
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT expiry_date FROM user_subscriptions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY expiry_date DESC LIMIT 1
                """, (user_id,))
            
            sub_data = cursor.fetchone()
            expiry_date = None
            if sub_data:
                try:
                    if USE_POSTGRESQL:
                        expiry_date_val = sub_data.get('expiry_date')
                    else:
                        expiry_date_val = sub_data[0] if len(sub_data) > 0 else None
                    
                    if expiry_date_val:
                        if isinstance(expiry_date_val, str):
                            expiry_date = datetime.datetime.fromisoformat(expiry_date_val)
                        else:
                            expiry_date = expiry_date_val
                except (IndexError, TypeError, ValueError):
                    expiry_date = None
            
            conn.commit()
            conn.close()
            
            # PC 프로그램 로그인 응답 (토큰 없음)
            return jsonify({
                'success': True,
                'message': '로그인 성공',
                'user_info': {
                    'user_id': user_id,
                    'name': name,
                    'email': email,
                    'expiry_date': expiry_date.isoformat() if expiry_date else None,
                    'is_active': True
                }
            })
        
        # 모바일 앱 로그인 (UUID 있음): 기기 등록 및 토큰 발급
        access_token = None
        expires_at = None
        
        if is_mobile_app:
            # 모바일 앱 로그인: 기기 등록 및 토큰 발급
            
            # 기기 등록 여부 확인 (1인 1기기 정책)
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT * FROM user_devices 
                    WHERE user_id = %s AND is_active = TRUE
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM user_devices 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
            
            registered_device = cursor.fetchone()
            
            if registered_device:
                # 이미 등록된 기기가 있는 경우
                if USE_POSTGRESQL:
                    registered_uuid = registered_device.get('device_uuid')
                else:
                    registered_uuid = registered_device[2]  # device_uuid 컬럼
                
                if registered_uuid != device_uuid:
                    # 다른 기기에서 로그인 시도 → 거부
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': '등록된 기기가 아닙니다. 다른 기기에서 로그인할 수 없습니다.',
                        'code': 'DEVICE_MISMATCH'
                    }), 403
                else:
                    # 같은 기기에서 재로그인 → 기기 정보 업데이트
                    if USE_POSTGRESQL:
                        cursor.execute("""
                            UPDATE user_devices 
                            SET last_used = %s, device_name = %s
                            WHERE user_id = %s AND device_uuid = %s
                        """, (now, device_name or None, user_id, device_uuid))
                    else:
                        cursor.execute("""
                            UPDATE user_devices 
                            SET last_used = ?, device_name = ?
                            WHERE user_id = ? AND device_uuid = ?
                        """, (now.isoformat(), device_name or None, user_id, device_uuid))
            else:
                # 최초 로그인 → 기기 등록
                if USE_POSTGRESQL:
                    cursor.execute("""
                        INSERT INTO user_devices (user_id, device_uuid, device_name, registered_date, last_used)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, device_uuid, device_name or None, now, now))
                else:
                    cursor.execute("""
                        INSERT INTO user_devices (user_id, device_uuid, device_name, registered_date, last_used)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, device_uuid, device_name or None, now.isoformat(), now.isoformat()))
            
            # 기존 토큰 비활성화 (새 토큰 발급 전)
            if USE_POSTGRESQL:
                cursor.execute("""
                    UPDATE user_access_tokens 
                    SET is_active = FALSE 
                    WHERE user_id = %s AND device_uuid = %s AND is_active = TRUE
                """, (user_id, device_uuid))
            else:
                cursor.execute("""
                    UPDATE user_access_tokens 
                    SET is_active = 0 
                    WHERE user_id = ? AND device_uuid = ? AND is_active = 1
                """, (user_id, device_uuid))
            
            # 액세스 토큰 생성
            access_token = generate_access_token()
            token_hash = hash_token(access_token)
            expires_at = now + datetime.timedelta(days=7)  # 7일 유효
        
            # 토큰 저장
            if USE_POSTGRESQL:
                cursor.execute("""
                    INSERT INTO user_access_tokens 
                    (user_id, device_uuid, access_token, token_hash, created_date, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, device_uuid, access_token, token_hash, now, expires_at))
            else:
                cursor.execute("""
                    INSERT INTO user_access_tokens 
                    (user_id, device_uuid, access_token, token_hash, created_date, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, device_uuid, access_token, token_hash, now.isoformat(), expires_at.isoformat()))
            
            # 구독 정보 조회
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT expiry_date FROM user_subscriptions 
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY expiry_date DESC LIMIT 1
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT expiry_date FROM user_subscriptions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY expiry_date DESC LIMIT 1
                """, (user_id,))
            
            sub_data = cursor.fetchone()
            expiry_date = None
            if sub_data:
                try:
                    if USE_POSTGRESQL:
                        expiry_date_val = sub_data.get('expiry_date')
                    else:
                        expiry_date_val = sub_data[0] if len(sub_data) > 0 else None
                    
                    if expiry_date_val:
                        if isinstance(expiry_date_val, str):
                            expiry_date = datetime.datetime.fromisoformat(expiry_date_val)
                        else:
                            expiry_date = expiry_date_val
                except (IndexError, TypeError, ValueError):
                    expiry_date = None
            
            # last_login 업데이트
            if USE_POSTGRESQL:
                cursor.execute("UPDATE users SET last_login = %s WHERE user_id = %s", (now, user_id))
            else:
                cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now.isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            # 모바일 앱 로그인 응답 (토큰 포함)
            return jsonify({
                'success': True,
                'message': '로그인 성공',
                'access_token': access_token,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'user_info': {
                    'user_id': user_id,
                    'name': name,
                    'email': email,
                    'expiry_date': expiry_date.isoformat() if expiry_date else None,
                    'is_active': True
                }
            })
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"[LOGIN ERROR] {error_msg}")
        if 'conn' in locals():
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({
            'success': False,
            'message': f'로그인 처리 중 오류가 발생했습니다: {error_msg}'
        }), 500

@app.route('/api/list_user_devices', methods=['POST'])
def list_user_devices():
    """사용자의 등록된 기기 목록 조회 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    user_id = data.get('user_id', '').strip()
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            cursor.execute("""
                SELECT device_uuid, device_name, registered_date, last_used, is_active
                FROM user_devices
                WHERE user_id = %s
                ORDER BY registered_date DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT device_uuid, device_name, registered_date, last_used, is_active
                FROM user_devices
                WHERE user_id = ?
                ORDER BY registered_date DESC
            """, (user_id,))
        
        devices = []
        for row in cursor.fetchall():
            if USE_POSTGRESQL:
                devices.append({
                    'device_uuid': row.get('device_uuid'),
                    'device_name': row.get('device_name') or '',
                    'registered_date': row.get('registered_date').isoformat() if row.get('registered_date') and hasattr(row.get('registered_date'), 'isoformat') else (row.get('registered_date') or ''),
                    'last_used': row.get('last_used').isoformat() if row.get('last_used') and hasattr(row.get('last_used'), 'isoformat') else (row.get('last_used') or ''),
                    'is_active': bool(row.get('is_active'))
                })
            else:
                devices.append({
                    'device_uuid': row[0],
                    'device_name': row[1] or '',
                    'registered_date': row[2] or '',
                    'last_used': row[3] or '',
                    'is_active': bool(row[4])
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'devices': devices
        })
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({
            'success': False,
            'message': f'기기 목록 조회 실패: {str(e)}'
        }), 500

@app.route('/api/remove_user_device', methods=['POST'])
def remove_user_device():
    """사용자의 등록된 기기 삭제 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    user_id = data.get('user_id', '').strip()
    device_uuid = data.get('device_uuid', '').strip()
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    if not user_id or not device_uuid:
        return jsonify({'success': False, 'message': '사용자 ID와 기기 UUID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        # 기기 삭제 (연관된 토큰도 함께 삭제됨 - CASCADE)
        if USE_POSTGRESQL:
            cursor.execute("""
                DELETE FROM user_devices
                WHERE user_id = %s AND device_uuid = %s
            """, (user_id, device_uuid))
        else:
            cursor.execute("""
                DELETE FROM user_devices
                WHERE user_id = ? AND device_uuid = ?
            """, (user_id, device_uuid))
        
        deleted_count = cursor.rowcount
        
        if deleted_count == 0:
            conn.close()
            return jsonify({'success': False, 'message': '해당 기기를 찾을 수 없습니다.'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '기기가 삭제되었습니다.'
        })
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({
            'success': False,
            'message': f'기기 삭제 실패: {str(e)}'
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """사용자 로그아웃"""
    data = request.json
    user_id = data.get('user_id', '')
    device_uuid = data.get('device_uuid', '')
    
    if user_id and device_uuid:
        # 토큰 비활성화
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute("""
                UPDATE user_access_tokens 
                SET is_active = FALSE 
                WHERE user_id = %s AND device_uuid = %s AND is_active = TRUE
            """, (user_id, device_uuid))
        else:
            cursor.execute("""
                UPDATE user_access_tokens 
                SET is_active = 0 
                WHERE user_id = ? AND device_uuid = ? AND is_active = 1
            """, (user_id, device_uuid))
        
        conn.commit()
        conn.close()
    
    return jsonify({
        'success': True,
        'message': '로그아웃되었습니다.'
    })

@app.route('/api/verify_token', methods=['POST'])
def verify_token():
    """
    액세스 토큰 검증 (ESP32에서 호출)
    모바일 앱이 ESP32로 전송한 토큰의 유효성을 확인
    """
    data = request.json
    access_token = data.get('access_token', '').strip()
    
    if not access_token:
        return jsonify({
            'success': False,
            'valid': False,
            'message': '토큰이 필요합니다.'
        }), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 토큰 해시로 검색
    token_hash = hash_token(access_token)
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT ut.*, u.is_active as user_active
            FROM user_access_tokens ut
            JOIN users u ON ut.user_id = u.user_id
            WHERE ut.token_hash = %s AND ut.is_active = TRUE
        """, (token_hash,))
    else:
        cursor.execute("""
            SELECT ut.*, u.is_active as user_active
            FROM user_access_tokens ut
            JOIN users u ON ut.user_id = u.user_id
            WHERE ut.token_hash = ? AND ut.is_active = 1
        """, (token_hash,))
    
    token_data = cursor.fetchone()
    conn.close()
    
    if not token_data:
        return jsonify({
            'success': True,
            'valid': False,
            'message': '유효하지 않은 토큰입니다.'
        })
    
    # 만료 시간 확인
    if USE_POSTGRESQL:
        expires_at_str = token_data.get('expires_at')
        user_active = token_data.get('user_active')
    else:
        expires_at_str = token_data[6]  # expires_at 컬럼
        user_active = bool(token_data[9])  # user_active 컬럼
    
    if isinstance(expires_at_str, str):
        expires_at = datetime.datetime.fromisoformat(expires_at_str)
    else:
        expires_at = expires_at_str
    
    now = datetime.datetime.now()
    
    if expires_at < now:
        return jsonify({
            'success': True,
            'valid': False,
            'message': '토큰이 만료되었습니다.'
        })
    
    if not user_active:
        return jsonify({
            'success': True,
            'valid': False,
            'message': '비활성화된 사용자입니다.'
        })
    
    # 토큰 유효
    if USE_POSTGRESQL:
        user_id = token_data.get('user_id')
    else:
        user_id = token_data[1]  # user_id 컬럼
    
    return jsonify({
        'success': True,
        'valid': True,
        'message': '토큰이 유효합니다.',
        'user_id': user_id
    })

@app.route('/api/request_device_change', methods=['POST'])
def request_device_change():
    """
    기기 변경 신청 (월 1회 제한)
    사용자가 폰을 바꿨을 경우 새 기기로 등록 변경
    """
    data = request.json
    user_id = data.get('user_id', '').strip()
    password = data.get('password', '')
    new_device_uuid = data.get('new_device_uuid', '').strip()
    device_name = data.get('device_name', '').strip()
    
    if not user_id or not password or not new_device_uuid:
        return jsonify({
            'success': False,
            'message': '아이디, 비밀번호, 새 기기 UUID가 필요합니다.'
        }), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 사용자 확인
    if USE_POSTGRESQL:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    else:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 400
    
    # 비밀번호 확인
    if USE_POSTGRESQL:
        password_hash = user_data.get('password_hash')
    else:
        password_hash = user_data[2]
    
    if not verify_password(password, password_hash):
        conn.close()
        return jsonify({'success': False, 'message': '비밀번호가 잘못되었습니다.'}), 400
    
    # 기존 기기 확인
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT * FROM user_devices 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT * FROM user_devices 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
    
    old_device = cursor.fetchone()
    
    if not old_device:
        conn.close()
        return jsonify({'success': False, 'message': '등록된 기기가 없습니다.'}), 400
    
    # 기기 변경 제한 확인 (월 1회)
    if USE_POSTGRESQL:
        if old_device.get('registered_date'):
            registered_date_str = old_device.get('registered_date')
            if isinstance(registered_date_str, str):
                registered_date = datetime.datetime.fromisoformat(registered_date_str)
            else:
                registered_date = registered_date_str
            
            # 30일 이내에 변경했는지 확인
            days_since_registration = (datetime.datetime.now() - registered_date).days
            if days_since_registration < 30:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'기기 변경은 30일마다 1회만 가능합니다. ({30 - days_since_registration}일 후 가능)'
                }), 403
    
    # 기존 기기 비활성화
    if USE_POSTGRESQL:
        cursor.execute("""
            UPDATE user_devices 
            SET is_active = FALSE 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        
        # 기존 토큰 비활성화
        cursor.execute("""
            UPDATE user_access_tokens 
            SET is_active = FALSE 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        
        # 새 기기 등록
        cursor.execute("""
            INSERT INTO user_devices (user_id, device_uuid, device_name, registered_date, last_used)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, new_device_uuid, device_name or None, datetime.datetime.now(), datetime.datetime.now()))
    else:
        cursor.execute("""
            UPDATE user_devices 
            SET is_active = 0 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        
        cursor.execute("""
            UPDATE user_access_tokens 
            SET is_active = 0 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        
        cursor.execute("""
            INSERT INTO user_devices (user_id, device_uuid, device_name, registered_date, last_used)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, new_device_uuid, device_name or None, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '기기가 성공적으로 변경되었습니다. 다시 로그인해주세요.'
    })

@app.route('/api/register', methods=['POST'])
def register():
    """사용자 자체 회원가입 (비활성 상태로 생성)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
        
        user_id = data.get('user_id', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not user_id or not password or not name:
            return jsonify({'success': False, 'message': '아이디, 비밀번호, 이름이 필요합니다.'}), 400
        
        # 비밀번호 해싱
        try:
            password_hash = hash_password(password)
        except Exception as e:
            logger.error(f"비밀번호 해싱 실패: {e}")
            return jsonify({'success': False, 'message': f'비밀번호 처리 실패: {str(e)}'}), 500
        
        conn = None
        try:
            conn = get_db_connection()
            if USE_POSTGRESQL:
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()
            
            now = datetime.datetime.now()
            try:
                # is_active = False로 생성 (관리자 승인 필요)
                if USE_POSTGRESQL:
                    cursor.execute("""
                        INSERT INTO users (user_id, password_hash, name, email, phone, created_date, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, password_hash, name, email, phone, now, False))
                else:
                    cursor.execute("""
                        INSERT INTO users (user_id, password_hash, name, email, phone, created_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, password_hash, name, email, phone, now.isoformat(), 0))
                
                conn.commit()
                logger.info(f"회원가입 성공 (비활성): {user_id}")
                
                return jsonify({
                    'success': True,
                    'message': '회원가입이 완료되었습니다. 관리자 승인 후 이용 가능합니다.'
                })
            except Exception as e:
                if conn:
                    conn.rollback()
                error_msg = str(e)
                logger.error(f"회원가입 실패: {error_msg}")
                
                if 'UNIQUE constraint' in error_msg or 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    return jsonify({'success': False, 'message': '이미 존재하는 사용자 ID입니다.'}), 400
                elif 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                    return jsonify({'success': False, 'message': '데이터베이스 테이블이 없습니다. 서버 관리자에게 문의하세요.'}), 500
                else:
                    return jsonify({'success': False, 'message': f'회원가입 실패: {error_msg}'}), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        logger.error(f"회원가입 처리 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'회원가입 처리 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/verify_mac_address', methods=['POST'])
def verify_mac_address():
    """MAC 주소 검증"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    mac_address = data.get('mac_address', '').strip().upper()
    hardware_id = data.get('hardware_id', '')
    
    if not user_id or not mac_address:
        return jsonify({'success': False, 'message': '사용자 ID와 MAC 주소가 필요합니다.'}), 400
    
    # MAC 주소 형식 검증 (기본)
    if len(mac_address) != 17 or mac_address.count(':') != 5:
        return jsonify({'success': False, 'message': '올바른 MAC 주소 형식이 아닙니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 허용된 MAC 주소 확인
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT * FROM allowed_mac_addresses 
            WHERE user_id = %s AND mac_address = %s AND is_active = TRUE
        """, (user_id, mac_address))
    else:
        cursor.execute("""
            SELECT * FROM allowed_mac_addresses 
            WHERE user_id = ? AND mac_address = ? AND is_active = 1
        """, (user_id, mac_address))
    
    mac_data = cursor.fetchone()
    
    if mac_data:
        conn.close()
        return jsonify({
            'success': True,
            'allowed': True,
            'message': '허용된 사용자입니다.'
        })
    else:
        conn.close()
        return jsonify({
            'success': True,
            'allowed': False,
            'message': '등록되지 않은 사용자입니다. 관리자에게 문의하세요.'
        })

@app.route('/api/create_user', methods=['POST'])
def create_user():
    """사용자 생성 (관리자용)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
            
        admin_key = data.get('admin_key', '')
        
        if admin_key != ADMIN_KEY:
            logger.warning(f"권한 없음: admin_key={admin_key[:10]}...")
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        user_id = data.get('user_id', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not user_id or not password or not name:
            return jsonify({'success': False, 'message': '아이디, 비밀번호, 이름이 필요합니다.'}), 400
        
        # 비밀번호 해싱
        try:
            password_hash = hash_password(password)
        except Exception as e:
            logger.error(f"비밀번호 해싱 실패: {e}")
            return jsonify({'success': False, 'message': f'비밀번호 처리 실패: {str(e)}'}), 500
        
        conn = None
        try:
            conn = get_db_connection()
            if USE_POSTGRESQL:
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()
            
            now = datetime.datetime.now()
            try:
                if USE_POSTGRESQL:
                    cursor.execute("""
                        INSERT INTO users (user_id, password_hash, name, email, phone, created_date, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, password_hash, name, email, phone, now, True))
                else:
                    cursor.execute("""
                        INSERT INTO users (user_id, password_hash, name, email, phone, created_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, password_hash, name, email, phone, now.isoformat(), True))
                
                conn.commit()
                logger.info(f"사용자 생성 성공: {user_id}")
                
                return jsonify({
                    'success': True,
                    'message': '사용자 계정이 생성되었습니다.',
                    'user_id': user_id
                })
            except Exception as e:
                if conn:
                    conn.rollback()
                error_msg = str(e)
                logger.error(f"사용자 생성 실패: {error_msg}")
                
                if 'UNIQUE constraint' in error_msg or 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    return jsonify({'success': False, 'message': '이미 존재하는 사용자 ID입니다.'}), 400
                elif 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                    return jsonify({'success': False, 'message': '데이터베이스 테이블이 없습니다. 서버 관리자에게 문의하세요.'}), 500
                else:
                    return jsonify({'success': False, 'message': f'사용자 생성 실패: {error_msg}'}), 500
            finally:
                if conn:
                    conn.close()
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            return jsonify({'success': False, 'message': f'데이터베이스 연결 실패: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"create_user 예외: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'서버 오류: {str(e)}'}), 500

@app.route('/api/list_users', methods=['POST'])
def list_users():
    """사용자 목록 조회 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, u.is_active, u.created_date, u.last_login,
                   us.expiry_date
            FROM users u
            LEFT JOIN user_subscriptions us ON u.user_id = us.user_id AND us.is_active = TRUE
            ORDER BY u.created_date DESC
        """)
    else:
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, u.is_active, u.created_date, u.last_login,
                   us.expiry_date
            FROM users u
            LEFT JOIN user_subscriptions us ON u.user_id = us.user_id AND us.is_active = 1
            ORDER BY u.created_date DESC
        """)
    
    users = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            user_id = row.get('user_id')
            expiry_date_val = row.get('expiry_date')
            if expiry_date_val:
                if isinstance(expiry_date_val, str):
                    expiry_date = expiry_date_val
                else:
                    expiry_date = expiry_date_val.isoformat()
            else:
                expiry_date = None
            
            # 사용자 통계 정보 조회 (작업 횟수, 총 송장 건수)
            cursor.execute("""
                SELECT 
                    COUNT(*) as work_count,
                    SUM(total_invoices) as total_invoices,
                    SUM(success_count) as total_success,
                    SUM(fail_count) as total_fail
                FROM user_usage
                WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()
            
            work_count = stats.get('work_count') or 0 if stats else 0
            total_invoices = stats.get('total_invoices') or 0 if stats else 0
            total_success = stats.get('total_success') or 0 if stats else 0
            total_fail = stats.get('total_fail') or 0 if stats else 0
            
            users.append({
                'user_id': user_id,
                'name': row.get('name'),
                'email': row.get('email'),
                'is_active': bool(row.get('is_active')),
                'created_date': row.get('created_date').isoformat() if row.get('created_date') and hasattr(row.get('created_date'), 'isoformat') else (row.get('created_date') or ''),
                'last_login': row.get('last_login').isoformat() if row.get('last_login') and hasattr(row.get('last_login'), 'isoformat') else (row.get('last_login') or ''),
                'expiry_date': expiry_date,
                'work_count': work_count,
                'total_invoices': total_invoices,
                'total_success': total_success,
                'total_fail': total_fail
            })
        else:
            user_id = row[0]
            expiry_date_val = row[6] if len(row) > 6 else None
            expiry_date = expiry_date_val if expiry_date_val else None
            
            # 사용자 통계 정보 조회 (작업 횟수, 총 송장 건수)
            cursor.execute("""
                SELECT 
                    COUNT(*) as work_count,
                    SUM(total_invoices) as total_invoices,
                    SUM(success_count) as total_success,
                    SUM(fail_count) as total_fail
                FROM user_usage
                WHERE user_id = ?
            """, (user_id,))
            stats = cursor.fetchone()
            
            work_count = stats[0] or 0 if stats else 0
            total_invoices = stats[1] or 0 if stats else 0
            total_success = stats[2] or 0 if stats else 0
            total_fail = stats[3] or 0 if stats else 0
            
            users.append({
                'user_id': user_id,
                'name': row[1],
                'email': row[2],
                'is_active': bool(row[3]),
                'created_date': row[4] or '',
                'last_login': row[5] or '',
                'expiry_date': expiry_date,
                'work_count': work_count,
                'total_invoices': total_invoices,
                'total_success': total_success,
                'total_fail': total_fail
            })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'users': users
    })

@app.route('/api/register_mac_address', methods=['POST'])
def register_mac_address():
    """MAC 주소 등록 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    user_id = data.get('user_id', '').strip()
    mac_address = data.get('mac_address', '').strip().upper()
    device_name = data.get('device_name', '').strip()
    
    if not user_id or not mac_address:
        return jsonify({'success': False, 'message': '사용자 ID와 MAC 주소가 필요합니다.'}), 400
    
    # MAC 주소 형식 검증
    if len(mac_address) != 17 or mac_address.count(':') != 5:
        return jsonify({'success': False, 'message': '올바른 MAC 주소 형식이 아닙니다. (예: AA:BB:CC:DD:EE:FF)'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    now = datetime.datetime.now()
    try:
        if USE_POSTGRESQL:
            cursor.execute("""
                INSERT INTO allowed_mac_addresses (user_id, mac_address, device_name, registered_date)
                VALUES (%s, %s, %s, %s)
            """, (user_id, mac_address, device_name, now))
        else:
            cursor.execute("""
                INSERT INTO allowed_mac_addresses (user_id, mac_address, device_name, registered_date)
                VALUES (?, ?, ?, ?)
            """, (user_id, mac_address, device_name, now.isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'MAC 주소가 등록되었습니다.'
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        if 'UNIQUE constraint' in str(e) or 'duplicate key' in str(e).lower():
            return jsonify({'success': False, 'message': '이미 등록된 MAC 주소입니다.'}), 400
        return jsonify({'success': False, 'message': f'MAC 주소 등록 실패: {str(e)}'}), 500

@app.route('/api/list_user_mac_addresses', methods=['POST'])
def list_user_mac_addresses():
    """사용자별 MAC 주소 목록 조회"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    admin_key = data.get('admin_key', '')  # 관리자용 (선택사항)
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    # 관리자가 아니면 자신의 MAC 주소만 조회 가능
    is_admin = admin_key == ADMIN_KEY
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT mac_address, device_name, registered_date, is_active
            FROM allowed_mac_addresses
            WHERE user_id = %s
            ORDER BY registered_date DESC
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT mac_address, device_name, registered_date, is_active
            FROM allowed_mac_addresses
            WHERE user_id = ?
            ORDER BY registered_date DESC
        """, (user_id,))
    
    mac_addresses = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            registered_date_val = row.get('registered_date')
            if registered_date_val and hasattr(registered_date_val, 'isoformat'):
                registered_date = registered_date_val.isoformat()
            else:
                registered_date = registered_date_val or ''
            
            mac_addresses.append({
                'mac_address': row.get('mac_address'),
                'device_name': row.get('device_name') or '',
                'registered_date': registered_date,
                'is_active': bool(row.get('is_active'))
            })
        else:
            mac_addresses.append({
                'mac_address': row[0],
                'device_name': row[1] or '',
                'registered_date': row[2] or '',
                'is_active': bool(row[3])
            })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'mac_addresses': mac_addresses
    })

@app.route('/api/remove_mac_address', methods=['POST'])
def remove_mac_address():
    """MAC 주소 삭제 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    user_id = data.get('user_id', '').strip()
    mac_address = data.get('mac_address', '').strip().upper()
    
    if not user_id or not mac_address:
        return jsonify({'success': False, 'message': '사용자 ID와 MAC 주소가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            DELETE FROM allowed_mac_addresses
            WHERE user_id = %s AND mac_address = %s
        """, (user_id, mac_address))
    else:
        cursor.execute("""
            DELETE FROM allowed_mac_addresses
            WHERE user_id = ? AND mac_address = ?
        """, (user_id, mac_address))
    
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    
    if deleted_count > 0:
        return jsonify({
            'success': True,
            'message': 'MAC 주소가 삭제되었습니다.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'MAC 주소를 찾을 수 없습니다.'
        }), 404

@app.route('/api/user_info', methods=['POST'])
def user_info():
    """사용자 정보 조회"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, u.is_active, us.expiry_date, us.subscription_type
            FROM users u
            LEFT JOIN user_subscriptions us ON u.user_id = us.user_id AND us.is_active = TRUE
            WHERE u.user_id = %s
            ORDER BY us.expiry_date DESC LIMIT 1
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, u.is_active, us.expiry_date, us.subscription_type
            FROM users u
            LEFT JOIN user_subscriptions us ON u.user_id = us.user_id AND us.is_active = 1
            WHERE u.user_id = ?
            ORDER BY us.expiry_date DESC LIMIT 1
        """, (user_id,))
    
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data:
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
    
    if USE_POSTGRESQL:
        expiry_date_val = user_data.get('expiry_date')
        expiry_date = expiry_date_val.isoformat() if expiry_date_val and hasattr(expiry_date_val, 'isoformat') else (expiry_date_val or None)
        
        return jsonify({
            'success': True,
            'user_info': {
                'user_id': user_data.get('user_id'),
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'expiry_date': expiry_date,
                'is_active': bool(user_data.get('is_active')),
                'subscription_type': user_data.get('subscription_type') or 'monthly'
            }
        })
    else:
        expiry_date_val = user_data[4] if len(user_data) > 4 else None
        expiry_date = expiry_date_val if expiry_date_val else None
        
        return jsonify({
            'success': True,
            'user_info': {
                'user_id': user_data[0],
                'name': user_data[1],
                'email': user_data[2],
                'expiry_date': expiry_date,
                'is_active': bool(user_data[3]),
                'subscription_type': user_data[5] if len(user_data) > 5 else 'monthly'
            }
        })

@app.route('/api/extend_user_subscription', methods=['POST'])
def extend_user_subscription():
    """사용자 구독 연장 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    user_id = data.get('user_id', '').strip()
    period_days = data.get('period_days', 30)
    amount = data.get('amount', 0)
    payment_method = data.get('payment_method', '')
    note = data.get('note', '')
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 현재 구독 확인
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT expiry_date FROM user_subscriptions
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY expiry_date DESC LIMIT 1
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT expiry_date FROM user_subscriptions
            WHERE user_id = ? AND is_active = 1
            ORDER BY expiry_date DESC LIMIT 1
        """, (user_id,))
    
    sub_data = cursor.fetchone()
    now = datetime.datetime.now()
    
    if sub_data:
        if USE_POSTGRESQL:
            current_expiry_val = sub_data.get('expiry_date')
        else:
            current_expiry_val = sub_data[0]
        
        if isinstance(current_expiry_val, str):
            current_expiry = datetime.datetime.fromisoformat(current_expiry_val)
        else:
            current_expiry = current_expiry_val
        
        if current_expiry < now:
            new_expiry = now + datetime.timedelta(days=period_days)
        else:
            new_expiry = current_expiry + datetime.timedelta(days=period_days)
        
        # 기존 구독 비활성화
        if USE_POSTGRESQL:
            cursor.execute("""
                UPDATE user_subscriptions SET is_active = FALSE
                WHERE user_id = %s AND is_active = TRUE
            """, (user_id,))
        else:
            cursor.execute("""
                UPDATE user_subscriptions SET is_active = 0
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
    else:
        new_expiry = now + datetime.timedelta(days=period_days)
    
    # 새 구독 생성
    if USE_POSTGRESQL:
        cursor.execute("""
            INSERT INTO user_subscriptions (user_id, subscription_type, start_date, expiry_date, is_active)
            VALUES (%s, 'monthly', %s, %s, TRUE)
        """, (user_id, now, new_expiry))
        
        cursor.execute("""
            INSERT INTO user_payments (user_id, payment_date, amount, period_days, payment_method, note)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, now, amount, period_days, payment_method, note))
        
        # users 테이블의 is_active를 True로 변경 (구독 연장 = 활성화)
        cursor.execute("""
            UPDATE users SET is_active = TRUE WHERE user_id = %s
        """, (user_id,))
    else:
        cursor.execute("""
            INSERT INTO user_subscriptions (user_id, subscription_type, start_date, expiry_date, is_active)
            VALUES (?, 'monthly', ?, ?, 1)
        """, (user_id, now.isoformat(), new_expiry.isoformat()))
        
        cursor.execute("""
            INSERT INTO user_payments (user_id, payment_date, amount, period_days, payment_method, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, now.isoformat(), amount, period_days, payment_method, note))
        
        # users 테이블의 is_active를 1로 변경 (구독 연장 = 활성화)
        cursor.execute("""
            UPDATE users SET is_active = 1 WHERE user_id = ?
        """, (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '구독이 연장되었습니다.',
        'expiry_date': new_expiry.isoformat()
    })

@app.route('/api/record_user_usage', methods=['POST'])
def record_user_usage():
    """사용자 사용량 기록"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    total_invoices = data.get('total_invoices', 0)
    success_count = data.get('success_count', 0)
    fail_count = data.get('fail_count', 0)
    mac_address = data.get('mac_address', '').strip().upper()
    hardware_id = data.get('hardware_id', '')
    
    if not user_id:
        return jsonify({'success': False, 'message': '사용자 ID가 필요합니다.'}), 400
    
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    now = datetime.datetime.now()
    if USE_POSTGRESQL:
        cursor.execute("""
            INSERT INTO user_usage (user_id, usage_date, total_invoices, success_count, fail_count, mac_address, hardware_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, now, total_invoices, success_count, fail_count, mac_address, hardware_id))
    else:
        cursor.execute("""
            INSERT INTO user_usage (user_id, usage_date, total_invoices, success_count, fail_count, mac_address, hardware_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, now.isoformat(), total_invoices, success_count, fail_count, mac_address, hardware_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '사용량이 기록되었습니다.'
    })

@app.route('/api/usage_stats', methods=['POST'])
def get_usage_stats():
    """사용 통계 조회 (관리자용)"""
    data = request.json
    admin_key = data.get('admin_key', '')
    license_key = data.get('license_key', '').upper()
    
    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if license_key:
        # 특정 라이선스 통계
        if USE_POSTGRESQL:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    SUM(total_invoices) as total_invoices,
                    SUM(success_count) as total_success,
                    SUM(fail_count) as total_fail,
                    MAX(usage_date) as last_usage
                FROM usage_stats
                WHERE license_key = %s
            """, (license_key,))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    SUM(total_invoices) as total_invoices,
                    SUM(success_count) as total_success,
                    SUM(fail_count) as total_fail,
                    MAX(usage_date) as last_usage
                FROM usage_stats
                WHERE license_key = ?
            """, (license_key,))
    else:
        # 전체 통계
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(total_invoices) as total_invoices,
                SUM(success_count) as total_success,
                SUM(fail_count) as total_fail,
                MAX(usage_date) as last_usage
            FROM usage_stats
        """)
    
    result = cursor.fetchone()
    
    # 라이선스별 상세 통계
    if USE_POSTGRESQL:
        cursor.execute("""
            SELECT 
                license_key,
                COUNT(*) as run_count,
                SUM(total_invoices) as total_invoices,
                SUM(success_count) as total_success,
                SUM(fail_count) as total_fail,
                MAX(usage_date) as last_usage
            FROM usage_stats
            GROUP BY license_key
            ORDER BY last_usage DESC
        """)
    else:
        cursor.execute("""
            SELECT 
                license_key,
                COUNT(*) as run_count,
                SUM(total_invoices) as total_invoices,
                SUM(success_count) as total_success,
                SUM(fail_count) as total_fail,
                MAX(usage_date) as last_usage
            FROM usage_stats
            GROUP BY license_key
            ORDER BY last_usage DESC
        """)
    
    license_stats = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            license_stats.append({
                'license_key': row[0],
                'run_count': row[1],
                'total_invoices': row[2] or 0,
                'total_success': row[3] or 0,
                'total_fail': row[4] or 0,
                'last_usage': row[5].isoformat() if row[5] and hasattr(row[5], 'isoformat') else (row[5] or '')
            })
        else:
            license_stats.append({
                'license_key': row[0],
                'run_count': row[1],
                'total_invoices': row[2] or 0,
                'total_success': row[3] or 0,
                'total_fail': row[4] or 0,
                'last_usage': row[5]
            })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'summary': {
            'total_runs': result[0] or 0,
            'total_invoices': result[1] or 0,
            'total_success': result[2] or 0,
            'total_fail': result[3] or 0,
            'last_usage': result[4].isoformat() if result[4] and hasattr(result[4], 'isoformat') else (result[4] or '')
        },
        'by_license': license_stats
    })

def send_telegram_message(message: str) -> bool:
    """
    텔레그램 봇으로 메시지 전송
    
    Args:
        message: 전송할 메시지 내용
        
    Returns:
        전송 성공 여부
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("텔레그램 봇 설정이 없습니다. TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("텔레그램 메시지 전송 성공")
            return True
        else:
            logger.error(f"텔레그램 메시지 전송 실패: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 오류: {e}")
        return False

@app.route('/api/send_admin_message', methods=['POST'])
def send_admin_message():
    """
    관리자에게 메시지 전송 (텔레그램 봇)
    
    요청 데이터:
    - user_id: 사용자 ID
    - category: 종류 (입금확인, 사용방법, 오류, 기타)
    - title: 제목
    - content: 내용
    - phone: 회신받을 전화번호 (선택사항)
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
        
        user_id = data.get('user_id', '').strip()
        category = data.get('category', '').strip()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        phone = data.get('phone', '').strip()
        
        # 필수 필드 확인
        if not user_id or not category or not title or not content or not phone:
            return jsonify({'success': False, 'message': '필수 항목을 모두 입력해주세요. (아이디, 종류, 제목, 내용, 전화번호)'}), 400
        
        # 카테고리 유효성 검사
        valid_categories = ['입금확인', '사용방법', '오류', '기타']
        if category not in valid_categories:
            return jsonify({'success': False, 'message': f'유효하지 않은 종류입니다. ({", ".join(valid_categories)})'}), 400
        
        # 텔레그램 메시지 포맷팅
        try:
            # 한국 표준시(KST, UTC+9)로 시간 변환
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))  # UTC+9
            now = datetime.datetime.now(timezone.utc).astimezone(kst)
            time_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""<b>📩 관리자 메시지</b>

<b>아이디:</b> {user_id}
<b>종류:</b> {category}
<b>제목:</b> {title}

<b>내용:</b>
{content}

<b>회신 전화번호:</b> {phone.strip()}"""
            
            message += f"\n\n<i>수신 시간: {time_str}</i>"
            
            # 텔레그램으로 전송
            telegram_sent = send_telegram_message(message)
            
            if telegram_sent:
                return jsonify({
                    'success': True,
                    'message': '메시지가 전송되었습니다.'
                }), 200
            else:
                # 텔레그램 전송 실패
                logger.warning("텔레그램 메시지 전송 실패")
                return jsonify({
                    'success': False,
                    'message': '메시지 전송에 실패했습니다. 나중에 다시 시도해주세요.'
                }), 500
        except Exception as format_error:
            logger.error(f"메시지 포맷팅 오류: {format_error}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'메시지 처리 중 오류가 발생했습니다: {str(format_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"관리자 메시지 전송 오류: {e}", exc_info=True)
        # 에러 발생해도 텔레그램 메시지는 전송되었을 수 있으므로 명확한 에러 메시지
        try:
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        except:
            pass
        return jsonify({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 데이터베이스 초기화
    if not USE_POSTGRESQL:
        DB_PATH.parent.mkdir(exist_ok=True)
    init_db()
    
    print("=" * 60)
    print("라이선스 서버 시작")
    print("=" * 60)
    if USE_POSTGRESQL:
        print("데이터베이스: PostgreSQL (Railway)")
    else:
        print(f"데이터베이스: SQLite ({DB_PATH})")
    print("서버 주소: http://localhost:5000")
    print("=" * 60)
    
    # 포트 설정 (환경변수 또는 기본값)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

