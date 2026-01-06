"""
데이터베이스 백업 스크립트
라이선스 데이터를 JSON 파일로 백업
"""

import os
import json
import datetime
from license_server import get_db_connection, USE_POSTGRESQL
from psycopg2.extras import RealDictCursor

def backup_licenses():
    """라이선스 데이터 백업"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    
    # 라이선스 데이터 가져오기
    cursor.execute("SELECT * FROM licenses")
    licenses = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            license_data = dict(row)
            # datetime 객체를 문자열로 변환
            for key, value in license_data.items():
                if hasattr(value, 'isoformat'):
                    license_data[key] = value.isoformat()
        else:
            license_data = {
                'id': row[0],
                'license_key': row[1],
                'customer_name': row[2],
                'customer_email': row[3],
                'hardware_id': row[4],
                'created_date': row[5],
                'expiry_date': row[6],
                'is_active': bool(row[7]),
                'subscription_type': row[8],
                'last_verified': row[9] if len(row) > 9 else None
            }
        licenses.append(license_data)
    
    # 구독 기록 가져오기
    cursor.execute("SELECT * FROM subscriptions")
    subscriptions = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            sub_data = dict(row)
            for key, value in sub_data.items():
                if hasattr(value, 'isoformat'):
                    sub_data[key] = value.isoformat()
        else:
            sub_data = {
                'id': row[0],
                'license_key': row[1],
                'payment_date': row[2],
                'amount': row[3],
                'period_days': row[4]
            }
        subscriptions.append(sub_data)
    
    # 사용 통계 가져오기
    cursor.execute("SELECT * FROM usage_stats")
    usage_stats = []
    for row in cursor.fetchall():
        if USE_POSTGRESQL:
            stat_data = dict(row)
            for key, value in stat_data.items():
                if hasattr(value, 'isoformat'):
                    stat_data[key] = value.isoformat()
        else:
            stat_data = {
                'id': row[0],
                'license_key': row[1],
                'usage_date': row[2],
                'total_invoices': row[3],
                'success_count': row[4],
                'fail_count': row[5]
            }
        usage_stats.append(stat_data)
    
    conn.close()
    
    # 백업 데이터 구성
    backup_data = {
        'backup_date': datetime.datetime.now().isoformat(),
        'licenses': licenses,
        'subscriptions': subscriptions,
        'usage_stats': usage_stats
    }
    
    # 백업 파일 저장
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    print(f"백업 완료: {backup_file}")
    print(f"라이선스: {len(licenses)}개")
    print(f"구독 기록: {len(subscriptions)}개")
    print(f"사용 통계: {len(usage_stats)}개")
    
    return backup_file

if __name__ == '__main__':
    backup_licenses()












