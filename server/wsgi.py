"""
WSGI 엔트리 포인트 (Railway용)
"""
from license_server import app, init_db
import logging

# 앱 시작 시 데이터베이스 초기화 (런타임에만 실행)
try:
    init_db()
    logger = logging.getLogger(__name__)
    logger.info("데이터베이스 초기화 완료")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"데이터베이스 초기화 중 오류 (무시 가능): {e}")

if __name__ == "__main__":
    app.run()

