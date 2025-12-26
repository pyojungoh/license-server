"""
Railway 배포용 엔트리 포인트
Railway는 app.py를 자동으로 찾습니다
"""
from license_server import app

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

