"""
라이선스 키 생성 도구
판매용 라이선스 키를 생성합니다.
"""

import secrets
import string
import datetime
import json
from pathlib import Path
import hashlib

def generate_license_key(days: int = 365, customer_name: str = "") -> tuple[str, str]:
    """
    라이선스 키 생성
    
    Args:
        days: 유효 기간 (일)
        customer_name: 고객명 (선택)
        
    Returns:
        (license_key, expiry_date_str)
    """
    # 랜덤 라이선스 키 생성 (16자리)
    license_key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    
    # 만료일 계산
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
    expiry_date_str = expiry_date.isoformat()
    
    return license_key, expiry_date_str

def create_license_file(license_key: str, expiry_date: str, output_dir: Path = None):
    """
    라이선스 파일 생성 (고객에게 제공할 파일)
    """
    if output_dir is None:
        output_dir = Path("licenses")
    
    output_dir.mkdir(exist_ok=True)
    
    license_data = {
        "license_key": license_key,
        "expiry_date": expiry_date,
        "activated_date": datetime.datetime.now().isoformat()
    }
    
    # 라이선스 파일 저장
    license_file = output_dir / f"license_{license_key[:8]}.json"
    with open(license_file, 'w', encoding='utf-8') as f:
        json.dump(license_data, f, indent=2, ensure_ascii=False)
    
    # 텍스트 파일로도 저장 (고객이 쉽게 복사할 수 있도록)
    txt_file = output_dir / f"license_{license_key[:8]}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"라이선스 키: {license_key}\n")
        f.write(f"만료일: {expiry_date[:10]}\n")
        f.write(f"\n프로그램 실행 후 라이선스 등록 화면에서 위 키를 입력하세요.\n")
    
    return license_file, txt_file

def main():
    """라이선스 생성 메인 함수"""
    print("=" * 60)
    print("라이선스 키 생성 도구")
    print("=" * 60)
    
    # 고객 정보 입력
    customer_name = input("고객명 (선택): ").strip()
    
    # 유효 기간 입력
    while True:
        try:
            days_input = input("유효 기간 (일, 기본값 365): ").strip()
            days = int(days_input) if days_input else 365
            if days > 0:
                break
            print("양수를 입력하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 라이선스 생성
    license_key, expiry_date = generate_license_key(days, customer_name)
    
    print("\n생성된 라이선스:")
    print(f"  라이선스 키: {license_key}")
    print(f"  만료일: {expiry_date[:10]}")
    print(f"  유효 기간: {days}일")
    
    # 파일 생성
    json_file, txt_file = create_license_file(license_key, expiry_date)
    
    print(f"\n라이선스 파일 생성 완료:")
    print(f"  JSON: {json_file}")
    print(f"  TXT: {txt_file}")
    
    # 라이선스 정보 저장 (판매 관리용)
    sales_record = {
        "license_key": license_key,
        "customer_name": customer_name,
        "expiry_date": expiry_date,
        "created_date": datetime.datetime.now().isoformat(),
        "days": days
    }
    
    sales_file = Path("licenses") / "sales_records.json"
    sales_records = []
    if sales_file.exists():
        with open(sales_file, 'r', encoding='utf-8') as f:
            sales_records = json.load(f)
    
    sales_records.append(sales_record)
    
    with open(sales_file, 'w', encoding='utf-8') as f:
        json.dump(sales_records, f, indent=2, ensure_ascii=False)
    
    print(f"\n판매 기록 저장: {sales_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()











