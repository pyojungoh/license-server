"""
WSGI 엔트리 포인트 (Railway용)
"""
from license_server import app, init_db, USE_POSTGRESQL, DATABASE_URL
import logging
import sys

logger = logging.getLogger(__name__)

# 앱 시작 시 데이터베이스 초기화 (런타임에만 실행)
# PostgreSQL 연결 확인 후 초기화
if USE_POSTGRESQL:
    if not DATABASE_URL:
        logger.error("DATABASE_URL이 설정되지 않았습니다!")
        sys.exit(1)
    logger.info(f"PostgreSQL 모드: DATABASE_URL 설정됨 (길이: {len(DATABASE_URL)})")
else:
    logger.warning("SQLite 모드: DATABASE_URL이 없거나 postgres로 시작하지 않음")

try:
    init_db()
    logger.info("데이터베이스 초기화 완료")
except Exception as e:
    logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)
    # PostgreSQL 연결 실패는 치명적이므로 재시도하거나 실패 처리
    if USE_POSTGRESQL:
        logger.error("PostgreSQL 연결 실패 - 앱을 시작할 수 없습니다")
        # Railway에서는 계속 시도하도록 함 (자동 재시작)

if __name__ == "__main__":
    app.run()

