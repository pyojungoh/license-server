"""
WSGI 엔트리 포인트 (Railway용)
"""
from license_server import app, init_db, USE_POSTGRESQL, DATABASE_URL
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 앱 시작 시 데이터베이스 초기화 (런타임에만 실행)
# 실패해도 앱은 시작되도록 함 (나중에 재시도 가능)
if USE_POSTGRESQL:
    if not DATABASE_URL:
        logger.error("⚠️ DATABASE_URL이 설정되지 않았습니다! SQLite 모드로 전환됩니다.")
    else:
        logger.info(f"✓ PostgreSQL 모드: DATABASE_URL 설정됨 (길이: {len(DATABASE_URL)})")
else:
    logger.warning("⚠️ SQLite 모드: DATABASE_URL이 없거나 postgres로 시작하지 않음")

try:
    init_db()
    logger.info("✓ 데이터베이스 초기화 완료")
except Exception as e:
    logger.error(f"✗ 데이터베이스 초기화 실패: {e}", exc_info=True)
    logger.warning("앱은 계속 실행되지만 데이터베이스 연결이 필요합니다.")

if __name__ == "__main__":
    app.run()

