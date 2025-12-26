"""
데이터베이스 헬퍼 모듈
PostgreSQL과 SQLite를 모두 지원
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Union, Any

# 데이터베이스 타입 확인
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRESQL = DATABASE_URL is not None

if not USE_POSTGRESQL:
    from pathlib import Path
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

def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """
    쿼리 실행 헬퍼 함수
    
    Args:
        query: SQL 쿼리 (PostgreSQL: %s, SQLite: ?)
        params: 쿼리 파라미터
        fetch_one: 하나의 결과만 반환
        fetch_all: 모든 결과 반환
        
    Returns:
        쿼리 결과
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # PostgreSQL은 %s, SQLite는 ? 사용
        if USE_POSTGRESQL:
            # ?를 %s로 변환
            query = query.replace('?', '%s')
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def get_row_dict(cursor, row):
    """행을 딕셔너리로 변환"""
    if USE_POSTGRESQL:
        # PostgreSQL은 RealDictCursor 사용 시 자동으로 dict
        if hasattr(cursor, 'description'):
            return dict(zip([col[0] for col in cursor.description], row))
    # SQLite는 튜플
    return row

