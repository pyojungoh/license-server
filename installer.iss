; Inno Setup 설치 스크립트
; 송장번호 일괄 처리 시스템 설치 프로그램 생성

#define MyAppName "송장번호 일괄 처리 시스템"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "표마왕"
#define MyAppPublisherURL "mailto:pyo0829@gmail.com"
#define MyAppExeName "송장번호일괄처리시스템.exe"

[Setup]
; 앱 정보
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppPublisherURL}
AppSupportURL={#MyAppPublisherURL}
AppUpdatesURL={#MyAppPublisherURL}

; 기본 설치 경로
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 출력 파일
OutputDir=installer
OutputBaseFilename={#MyAppName}_Setup_v{#MyAppVersion}

; 압축 설정
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; 권한 설정
PrivilegesRequired=admin

; 아이콘 (선택사항)
; SetupIconFile=icon.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 실행 파일
Source: "dist\송장번호일괄처리시스템.exe"; DestDir: "{app}"; Flags: ignoreversion
; 설정 파일 (기본값)
Source: "config\settings.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
; README 파일
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
; 드라이버 설치 가이드
Source: "DRIVER_INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "ESP32_SETUP_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Caption := '송장번호 일괄 처리 시스템 설치를 환영합니다.';
  WizardForm.WelcomeLabel2.Caption := '이 프로그램은 한진택배 송장번호를 자동으로 모바일 앱에 등록하는 시스템입니다.';
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;





