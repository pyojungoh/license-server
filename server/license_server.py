"""
라이선스 서버
온라인 라이선스 인증 및 구독 관리 서버
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
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

# 데이터베이스 초기화
# Railway Volume을 사용하거나 환경변수로 경로 지정
# Volume이 마운트되면 /app/data, 없으면 /app 사용
volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '/app/data')
DB_DIR = Path(volume_path)
DB_DIR.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성
DB_PATH = DB_DIR / "licenses.db"

def init_db():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 라이선스 테이블
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
    
    # 구독 기록 테이블
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
    
    # 사용 통계 테이블
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
    
    # 인덱스 생성 (조회 성능 향상)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_stats_license_date 
        ON usage_stats(license_key, usage_date)
    """)
    
    conn.commit()
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 라이선스 확인
    cursor.execute("""
        SELECT * FROM licenses 
        WHERE license_key = ? AND is_active = 1
    """, (license_key,))
    
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '유효하지 않은 라이선스 키입니다.'}), 400
    
    # 하드웨어 ID 확인
    stored_hw_id = license_data[5]  # hardware_id 컬럼
    
    if stored_hw_id and stored_hw_id != hardware_id:
        conn.close()
        return jsonify({
            'success': False, 
            'message': '이 라이선스는 다른 컴퓨터에 등록되어 있습니다.'
        }), 400
    
    # 하드웨어 ID가 없으면 등록
    if not stored_hw_id:
        cursor.execute("""
            UPDATE licenses 
            SET hardware_id = ?, customer_name = ?, customer_email = ?
            WHERE license_key = ?
        """, (hardware_id, customer_name, customer_email, license_key))
        conn.commit()
    
    # 만료일 확인
    expiry_date = datetime.datetime.fromisoformat(license_data[6])
    if datetime.datetime.now() > expiry_date:
        conn.close()
        return jsonify({
            'success': False, 
            'message': f'라이선스가 만료되었습니다. (만료일: {expiry_date.strftime("%Y-%m-%d")})'
        }), 400
    
    # 검증 시간 업데이트
    cursor.execute("""
        UPDATE licenses 
        SET last_verified = ?
        WHERE license_key = ?
    """, (datetime.datetime.now().isoformat(), license_key))
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM licenses 
        WHERE license_key = ? AND hardware_id = ? AND is_active = 1
    """, (license_key, hardware_id))
    
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '유효하지 않은 라이선스입니다.'}), 400
    
    expiry_date = datetime.datetime.fromisoformat(license_data[6])
    is_expired = datetime.datetime.now() > expiry_date
    
    # 검증 시간 업데이트
    cursor.execute("""
        UPDATE licenses 
        SET last_verified = ?
        WHERE license_key = ?
    """, (datetime.datetime.now().isoformat(), license_key))
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO licenses (license_key, customer_name, customer_email, 
                           created_date, expiry_date, subscription_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (license_key, customer_name, customer_email, 
          datetime.datetime.now().isoformat(), expiry_date.isoformat(), subscription_type))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'license_key': license_key,
        'expiry_date': expiry_date.isoformat()
    })

@app.route('/api/extend_license', methods=['POST'])
def extend_license():
    """라이선스 연장 (구독 갱신)"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    period_days = data.get('period_days', 30)
    amount = data.get('amount', 0)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 기존 라이선스 확인
    cursor.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key,))
    license_data = cursor.fetchone()
    
    if not license_data:
        conn.close()
        return jsonify({'success': False, 'message': '라이선스를 찾을 수 없습니다.'}), 400
    
    # 만료일 연장
    current_expiry = datetime.datetime.fromisoformat(license_data[6])
    if current_expiry < datetime.datetime.now():
        # 이미 만료된 경우 오늘부터 시작
        new_expiry = datetime.datetime.now() + datetime.timedelta(days=period_days)
    else:
        # 아직 유효한 경우 기존 만료일부터 연장
        new_expiry = current_expiry + datetime.timedelta(days=period_days)
    
    cursor.execute("""
        UPDATE licenses 
        SET expiry_date = ?
        WHERE license_key = ?
    """, (new_expiry.isoformat(), license_key))
    
    # 구독 기록 추가
    cursor.execute("""
        INSERT INTO subscriptions (license_key, payment_date, amount, period_days)
        VALUES (?, ?, ?, ?)
    """, (license_key, datetime.datetime.now().isoformat(), amount, period_days))
    
    conn.commit()
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

@app.route('/api/license_info', methods=['POST'])
def get_license_info():
    """라이선스 정보 조회"""
    data = request.json
    license_key = data.get('license_key', '').upper()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT license_key, customer_name, expiry_date, subscription_type, last_verified
        FROM licenses 
        WHERE license_key = ?
    """, (license_key,))
    
    license_data = cursor.fetchone()
    conn.close()
    
    if not license_data:
        return jsonify({'success': False, 'message': '라이선스를 찾을 수 없습니다.'}), 400
    
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT license_key, customer_name, customer_email, expiry_date, 
               subscription_type, is_active, last_verified, created_date
        FROM licenses
        ORDER BY created_date DESC
    """)
    
    licenses = []
    for row in cursor.fetchall():
        expiry_date = datetime.datetime.fromisoformat(row[3])
        is_expired = datetime.datetime.now() > expiry_date
        
        # 사용 통계 조회
        cursor.execute("""
            SELECT 
                COUNT(*) as run_count,
                SUM(total_invoices) as total_invoices,
                MAX(usage_date) as last_usage
            FROM usage_stats
            WHERE license_key = ?
        """, (row[0],))
        
        usage_data = cursor.fetchone()
        
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 전체 라이선스 수
    cursor.execute("SELECT COUNT(*) FROM licenses")
    total_licenses = cursor.fetchone()[0]
    
    # 활성 라이선스 수
    now = datetime.datetime.now().isoformat()
    cursor.execute("""
        SELECT COUNT(*) FROM licenses 
        WHERE expiry_date > ? AND is_active = 1
    """, (now,))
    active_licenses = cursor.fetchone()[0]
    
    # 만료된 라이선스 수
    cursor.execute("""
        SELECT COUNT(*) FROM licenses 
        WHERE expiry_date <= ? OR is_active = 0
    """, (now,))
    expired_licenses = cursor.fetchone()[0]
    
    # 총 수익
    cursor.execute("SELECT SUM(amount) FROM subscriptions")
    total_revenue = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'success': True,
        'total_licenses': total_licenses,
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'total_revenue': total_revenue
    })

if __name__ == '__main__':
    # 데이터베이스 초기화
    DB_PATH.parent.mkdir(exist_ok=True)
    init_db()
    
    print("=" * 60)
    print("라이선스 서버 시작")
    print("=" * 60)
    print(f"데이터베이스: {DB_PATH}")
    print("서버 주소: http://localhost:5000")
    print("=" * 60)
    
    # 포트 설정 (환경변수 또는 기본값)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

