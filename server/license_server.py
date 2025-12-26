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

# 템플릿 폴더 경로 (현재 파일 기준)
template_dir = Path(__file__).parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))
CORS(app)  # CORS 허용 (클라이언트에서 접근 가능하도록)

# 관리자 키 (환경변수 또는 기본값)
ADMIN_KEY = os.environ.get('ADMIN_KEY', '2133781qQ!!@#')

# 데이터베이스 연결 설정
# Railway PostgreSQL 사용 (DATABASE_URL 환경변수)
# 없으면 로컬 SQLite 사용
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRESQL = bool(DATABASE_URL and DATABASE_URL.startswith('postgres'))

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
        
        # 기존 데이터 확인
        table_exists = False
        try:
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'licenses'
                """)
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name='licenses'
                """)
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                # 기존 데이터 개수 확인
                cursor.execute("SELECT COUNT(*) FROM licenses")
                existing_count = cursor.fetchone()[0]
                logger.info(f"✓ 기존 테이블 발견: {existing_count}개의 라이선스가 있습니다. 데이터를 보존합니다.")
                conn.close()
                return  # 테이블이 이미 있으면 생성하지 않음
            else:
                logger.info("테이블이 없습니다. 새로 생성합니다.")
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
    
    conn = None
    try:
        conn = get_db_connection()
        # PostgreSQL은 autocommit이 꺼져있으므로 명시적으로 설정
        if USE_POSTGRESQL:
            conn.autocommit = False
        
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        if USE_POSTGRESQL:
            cursor.execute("""
                INSERT INTO licenses (license_key, customer_name, customer_email, 
                                   created_date, expiry_date, subscription_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (license_key, customer_name, customer_email, now, expiry_date, subscription_type))
        else:
            cursor.execute("""
                INSERT INTO licenses (license_key, customer_name, customer_email, 
                                   created_date, expiry_date, subscription_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (license_key, customer_name, customer_email, 
                  now.isoformat(), expiry_date.isoformat(), subscription_type))
        
        # 커밋 확인
        conn.commit()
        
        # 커밋 후 데이터 확인 (디버깅)
        cursor.execute("SELECT COUNT(*) FROM licenses WHERE license_key = %s" if USE_POSTGRESQL else "SELECT COUNT(*) FROM licenses WHERE license_key = ?", 
                      (license_key,))
        count = cursor.fetchone()[0]
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"라이선스 생성 완료: {license_key}, DB에 저장 확인: {count}개")
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry_date': expiry_date.isoformat()
        })
    except Exception as e:
        if conn:
            conn.rollback()
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"라이선스 생성 실패: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'라이선스 생성 실패: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

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

@app.route('/api/health', methods=['GET'])
def health_check():
    """데이터베이스 연결 상태 확인"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 데이터베이스 타입 확인
        if USE_POSTGRESQL:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            db_type = "PostgreSQL"
            
            # 테이블 존재 확인
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'licenses'
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
        
        return jsonify({
            'success': True,
            'database_type': db_type,
            'database_version': db_version,
            'connected': True,
            'table_exists': table_exists,
            'license_count': license_count,
            'database_url_set': USE_POSTGRESQL,
            'database_url_present': bool(DATABASE_URL),
            'database_url_preview': DATABASE_URL[:50] + '...' if DATABASE_URL and len(DATABASE_URL) > 50 else DATABASE_URL
        })
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
        
        if USE_POSTGRESQL:
            licenses.append({
                'license_key': row.get('license_key'),
                'customer_name': row.get('customer_name') or '',
                'customer_email': row.get('customer_email') or '',
                'expiry_date': row.get('expiry_date').isoformat() if hasattr(row.get('expiry_date'), 'isoformat') else str(row.get('expiry_date')),
                'subscription_type': row.get('subscription_type'),
                'is_active': bool(row.get('is_active')),
                'is_expired': is_expired,
                'last_verified': row.get('last_verified').isoformat() if row.get('last_verified') and hasattr(row.get('last_verified'), 'isoformat') else (row.get('last_verified') or ''),
                'created_date': row.get('created_date').isoformat() if hasattr(row.get('created_date'), 'isoformat') else str(row.get('created_date')),
                'run_count': usage_data[0] or 0 if usage_data else 0,
                'total_invoices': usage_data[1] or 0 if usage_data else 0,
                'last_usage': usage_data[2].isoformat() if usage_data and usage_data[2] and hasattr(usage_data[2], 'isoformat') else (usage_data[2] if usage_data else None)
            })
        else:
            licenses.append({
                'license_key': row[0],
                'customer_name': row[1] or '',
                'customer_email': row[2] or '',
                'expiry_date': row[3],
                'subscription_type': row[4],
                'is_active': bool(row[5]),
                'is_expired': is_expired,
                'last_verified': row[6],
                'created_date': row[7],
                'run_count': usage_data[0] or 0,
                'total_invoices': usage_data[1] or 0,
                'last_usage': usage_data[2]
            })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'licenses': licenses
    })

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

