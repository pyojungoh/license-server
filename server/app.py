"""
Railway 배포용 엔트리 포인트
Railway는 app.py를 자동으로 찾습니다
"""
import sys
from pathlib import Path

# 현재 파일의 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from license_server import app

# Railway가 app 객체를 찾을 수 있도록
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

