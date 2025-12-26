# Windows 설치 파일 생성 가이드

## 📌 두 가지 배포 방식

### 1. 단일 실행 파일 (Portable)
- **파일**: `dist/송장번호일괄처리시스템.exe`
- **특징**: 설치 없이 바로 실행 가능
- **용도**: 빠른 테스트, 포터블 버전

### 2. 설치 프로그램 (Installer) ⭐ 권장
- **파일**: `installer/송장번호 일괄 처리 시스템_Setup_v1.0.0.exe`
- **특징**: Windows 표준 설치 마법사, 시작 메뉴 등록
- **용도**: 정식 배포, 고객 제공

---

## 1. 필요한 도구 설치

### PyInstaller 설치
```bash
pip install pyinstaller
```

### Inno Setup 설치
1. https://jrsoftware.org/isdl.php 에서 Inno Setup 다운로드
2. 설치 실행 (기본 설정으로 설치)

## 2. 실행 파일 빌드

### 방법 1: 빌드 스크립트 사용 (권장)
```bash
python build_installer.py
```

### 방법 2: PyInstaller 직접 실행
```bash
pyinstaller build_installer.spec
```

빌드가 완료되면 `dist/송장번호일괄처리시스템.exe` 파일이 생성됩니다.

## 3. 설치 프로그램 생성

### Inno Setup Compiler 실행
1. Inno Setup Compiler 실행
2. `File` → `Open` → `installer.iss` 선택
3. `Build` → `Compile` 클릭

또는 명령줄에서:
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 출력 파일
- 위치: `installer/` 폴더
- 파일명: `송장번호 일괄 처리 시스템_Setup_v1.0.0.exe`

## 4. 테스트

1. 생성된 설치 파일 실행
2. 설치 과정 확인
3. 프로그램 실행 확인
4. 기능 테스트

## 5. 배포

생성된 `installer/송장번호 일괄 처리 시스템_Setup_v1.0.0.exe` 파일을 배포합니다.

## 문제 해결

### 빌드 오류
- `ModuleNotFoundError`: `requirements.txt`의 모든 패키지가 설치되어 있는지 확인
- `FileNotFoundError`: 경로가 올바른지 확인

### 실행 오류
- `dist/송장번호일괄처리시스템.exe`를 직접 실행하여 오류 확인
- 콘솔 모드로 빌드하여 오류 메시지 확인 (`console=True`)

### 설치 프로그램 오류
- Inno Setup 스크립트 문법 확인
- 경로가 올바른지 확인

