"""
송장번호 일괄 처리 시스템 - GUI 애플리케이션
만든이: 표마왕 (pyo0829@gmail.com)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial.tools.list_ports
import threading
import time
from pathlib import Path
import sys
import json
import datetime
import re

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from bluetooth_controller import BluetoothController
from excel_reader import ExcelReader
from utils import setup_logging
from user_auth_manager import UserAuthManager
from hardware_id import get_hardware_id
from colorama import init

# colorama 초기화
init(autoreset=True)


class HanjinAutomationApp:
    """한진택배 자동화 GUI 애플리케이션"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("송장번호 일괄 처리 시스템")
        self.root.geometry("950x700")
        self.root.resizable(False, False)
        
        # 변수
        self.controller = None
        self.is_running = False
        self.config_file = Path(__file__).parent.parent / "config" / "settings.json"
        self.loaded_invoices = []  # 로드된 송장번호 리스트
        self.auto_logout_timer = None  # 자동 로그아웃 타이머
        
        # 설정 로드 (라이선스 서버 URL 필요)
        self.config = self.load_config()
        
        # 사용자 인증 관리자 (서버 URL 설정 필요)
        server_url = self.config.get("license_server", {}).get("url", "http://localhost:5000")
        self.user_auth_manager = UserAuthManager(server_url=server_url)
        self.current_user_id = None
        self.current_user_info = None
        
        # 세션 파일 삭제 (프로그램 재시작 시 항상 로그인 강제)
        # clear_session()은 show_login에서 자동으로 처리됨 (세션 확인 코드 제거)
        
        # 로그인 화면 표시
        if not self.show_login():
            return
        
        # GUI 생성
        self.create_widgets()
        
        # COM 포트 목록 새로고침
        self.refresh_ports()
        
        # 블루투스 상태 확인 (주기적)
        self.check_bluetooth_status()
        
        # 1시간 후 자동 로그아웃 타이머 시작
        self.start_auto_logout_timer()
    
    def log(self, message):
        """로그 메시지 추가 (create_widgets 이후에 사용 가능)"""
        if hasattr(self, 'log_text'):
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
    
    def load_config(self):
        """설정 파일 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 기본 설정
        return {
            "serial": {"port": "COM3", "baudrate": 115200, "timeout": 1.0},
            "delays": {"min_between": 1.0, "max_between": 2.0},
            "retry": {"max_attempts": 3, "retry_delay": 2.0},
            "excel": {"file_path": "", "column_name": "InvoiceNumber", "sheet_name": "Sheet1"},
            "license_server": {"url": "https://license-server-production-e83a.up.railway.app"}
        }
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 실패: {e}")
    
    def show_login(self):
        """로그인 화면 표시 (항상 로그인 창 표시)"""
        # 세션 확인 제거 - 항상 로그인 창 표시
        
        # 로그인 창 표시
        login_window = tk.Toplevel(self.root)
        login_window.title("로그인 / 회원가입")
        login_window.geometry("400x600")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()
        
        # 창을 화면 중앙에 배치
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_window.winfo_screenheight() // 2) - (600 // 2)
        login_window.geometry(f"400x600+{x}+{y}")
        
        # Notebook (탭) 생성
        notebook = ttk.Notebook(login_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # === 로그인 탭 ===
        login_frame = ttk.Frame(notebook, padding="20")
        notebook.add(login_frame, text="로그인")
        
        ttk.Label(login_frame, text="로그인", font=("맑은 고딕", 16, "bold")).pack(pady=15)
        
        ttk.Label(login_frame, text="아이디:").pack(pady=5)
        user_id_var = tk.StringVar()
        user_id_entry = ttk.Entry(login_frame, textvariable=user_id_var, width=30)
        user_id_entry.pack(pady=5)
        user_id_entry.focus()
        
        ttk.Label(login_frame, text="비밀번호:").pack(pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(login_frame, textvariable=password_var, width=30, show="*")
        password_entry.pack(pady=5)
        
        login_status_label = ttk.Label(login_frame, text="", foreground="red", wraplength=350)
        login_status_label.pack(pady=10)
        
        login_success = [False]  # 클로저를 위한 리스트
        
        def do_login():
            user_id = user_id_var.get().strip()
            password = password_var.get()
            
            if not user_id or not password:
                login_status_label.config(text="아이디와 비밀번호를 입력하세요.", foreground="red")
                return
            
            login_status_label.config(text="로그인 중...", foreground="blue")
            login_window.update()  # UI 업데이트
            
            try:
                hardware_id = get_hardware_id()
                success, message, user_info = self.user_auth_manager.login(user_id, password, hardware_id)
                
                if success and user_info:
                    self.current_user_id = user_id
                    self.current_user_info = user_info
                    login_success[0] = True
                    login_window.destroy()
                else:
                    login_status_label.config(text=message, foreground="red")
            except Exception as e:
                import traceback
                error_msg = f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
                login_status_label.config(text=error_msg, foreground="red")
                print(f"로그인 오류:\n{traceback.format_exc()}")
        
        def on_enter(event):
            do_login()
        
        password_entry.bind('<Return>', on_enter)
        user_id_entry.bind('<Return>', lambda e: password_entry.focus())
        
        ttk.Button(login_frame, text="로그인", command=do_login, width=15).pack(pady=10)
        
        # === 회원가입 탭 ===
        register_frame = ttk.Frame(notebook, padding="20")
        notebook.add(register_frame, text="회원가입")
        
        ttk.Label(register_frame, text="회원가입", font=("맑은 고딕", 16, "bold")).pack(pady=10)
        
        # 아이디
        ttk.Label(register_frame, text="아이디 *:").pack(pady=5)
        reg_user_id_var = tk.StringVar()
        reg_user_id_entry = ttk.Entry(register_frame, textvariable=reg_user_id_var, width=30)
        reg_user_id_entry.pack(pady=2)
        
        # 비밀번호
        ttk.Label(register_frame, text="비밀번호 *:").pack(pady=5)
        reg_password_var = tk.StringVar()
        reg_password_entry = ttk.Entry(register_frame, textvariable=reg_password_var, width=30, show="*")
        reg_password_entry.pack(pady=2)
        
        # 이름
        ttk.Label(register_frame, text="이름 *:").pack(pady=5)
        reg_name_var = tk.StringVar()
        reg_name_entry = ttk.Entry(register_frame, textvariable=reg_name_var, width=30)
        reg_name_entry.pack(pady=2)
        
        # 이메일
        ttk.Label(register_frame, text="이메일:").pack(pady=5)
        reg_email_var = tk.StringVar()
        reg_email_entry = ttk.Entry(register_frame, textvariable=reg_email_var, width=30)
        reg_email_entry.pack(pady=2)
        
        # 전화번호
        ttk.Label(register_frame, text="전화번호:").pack(pady=5)
        reg_phone_var = tk.StringVar()
        reg_phone_entry = ttk.Entry(register_frame, textvariable=reg_phone_var, width=30)
        reg_phone_entry.pack(pady=2)
        
        register_status_label = ttk.Label(register_frame, text="", foreground="red", wraplength=350)
        register_status_label.pack(pady=10)
        
        def do_register():
            user_id = reg_user_id_var.get().strip()
            password = reg_password_var.get()
            name = reg_name_var.get().strip()
            email = reg_email_var.get().strip()
            phone = reg_phone_var.get().strip()
            
            if not user_id or not password or not name:
                register_status_label.config(text="아이디, 비밀번호, 이름을 입력하세요.", foreground="red")
                return
            
            register_status_label.config(text="회원가입 중...", foreground="blue")
            login_window.update()
            
            success, message = self.user_auth_manager.register(user_id, password, name, email, phone)
            
            if success:
                register_status_label.config(text=message, foreground="green")
                # 성공 시 로그인 탭으로 이동
                notebook.select(0)
                # 입력 필드 초기화
                reg_user_id_var.set("")
                reg_password_var.set("")
                reg_name_var.set("")
                reg_email_var.set("")
                reg_phone_var.set("")
            else:
                register_status_label.config(text=message, foreground="red")
        
        ttk.Button(register_frame, text="회원가입", command=do_register, width=15).pack(pady=10)
        
        # 창이 닫힐 때까지 대기
        login_window.wait_window()
        
        return login_success[0]
    
    def create_widgets(self):
        """GUI 위젯 생성"""
        # 메뉴바 생성
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="로그아웃", command=lambda: self.perform_logout("로그아웃하시겠습니까?"))
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_closing)
        
        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="관리자에게 메시지 보내기", command=self.show_admin_message_window)
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 그리드 가중치 설정 (창 크기 조정 시 비율 유지)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0)  # 오른쪽 미리보기는 고정 크기
        main_frame.rowconfigure(5, weight=1)  # 로그 영역이 남은 공간 차지
        
        # 제목 및 라이선스 정보
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(title_frame, text="송장번호 일괄 처리 시스템", 
                               font=("맑은 고딕", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # 제작자 정보
        author_label = ttk.Label(title_frame, text="만든이: 표마왕 (pyo0829@gmail.com)", 
                                font=("맑은 고딕", 9), foreground="gray")
        author_label.pack(side=tk.LEFT, padx=20)
        
        # 사용자 정보
        if self.current_user_info:
            expiry_date = self.current_user_info.get('expiry_date', '')
            expiry_display = expiry_date[:10] if expiry_date else 'N/A'
            user_text = f"사용자: {self.current_user_info.get('name', '')} ({self.current_user_id}) | 만료: {expiry_display}"
            user_label = ttk.Label(title_frame, text=user_text, font=("맑은 고딕", 8), foreground="gray")
            user_label.pack(side=tk.RIGHT)
        
        # === 설정 (포트 + 딜레이) ===
        settings_frame = ttk.LabelFrame(main_frame, text="설정", padding="8")
        settings_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)
        
        # COM 포트 설정
        ttk.Label(settings_frame, text="포트:").grid(row=0, column=0, padx=5)
        self.port_var = tk.StringVar(value=self.config["serial"]["port"])
        self.port_combo = ttk.Combobox(settings_frame, textvariable=self.port_var, width=12)
        self.port_combo.grid(row=0, column=1, padx=5)
        
        refresh_btn = ttk.Button(settings_frame, text="새로고침", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5)
        
        # 구분선
        ttk.Separator(settings_frame, orient=tk.VERTICAL).grid(row=0, column=3, padx=10, sticky=(tk.N, tk.S))
        
        # 딜레이 설정
        ttk.Label(settings_frame, text="딜레이:").grid(row=0, column=4, padx=5)
        ttk.Label(settings_frame, text="최소").grid(row=0, column=5, padx=2)
        self.min_delay_var = tk.StringVar(value=str(self.config["delays"]["min_between"]))
        min_delay_spin = ttk.Spinbox(settings_frame, from_=0.5, to=10.0, increment=0.5, 
                                     textvariable=self.min_delay_var, width=8)
        min_delay_spin.grid(row=0, column=6, padx=2)
        
        ttk.Label(settings_frame, text="최대").grid(row=0, column=7, padx=2)
        self.max_delay_var = tk.StringVar(value=str(self.config["delays"]["max_between"]))
        max_delay_spin = ttk.Spinbox(settings_frame, from_=0.5, to=10.0, increment=0.5, 
                                     textvariable=self.max_delay_var, width=8)
        max_delay_spin.grid(row=0, column=8, padx=2)
        
        # === 블루투스 상태 ===
        bt_frame = ttk.LabelFrame(main_frame, text="블루투스 연결 상태", padding="8")
        bt_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)
        
        self.bt_status_label = ttk.Label(bt_frame, text="연결 확인 중...", font=("맑은 고딕", 10))
        self.bt_status_label.grid(row=0, column=0, padx=5)
        
        self.bt_status_indicator = ttk.Label(bt_frame, text="●", font=("맑은 고딕", 20), foreground="gray")
        self.bt_status_indicator.grid(row=0, column=1, padx=5)
        
        check_btn = ttk.Button(bt_frame, text="연결 확인", command=self.check_bluetooth_connection)
        check_btn.grid(row=0, column=2, padx=5)
        
        # === 엑셀 파일 선택 ===
        excel_frame = ttk.LabelFrame(main_frame, text="엑셀 파일", padding="8")
        excel_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3)
        
        self.excel_path_var = tk.StringVar(value=self.config["excel"].get("file_path", ""))
        excel_entry = ttk.Entry(excel_frame, textvariable=self.excel_path_var, width=40)
        excel_entry.grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(excel_frame, text="찾아보기", command=self.browse_excel_file)
        browse_btn.grid(row=0, column=1, padx=5)
        
        load_btn = ttk.Button(excel_frame, text="파일 업로드", command=self.load_excel_file)
        load_btn.grid(row=0, column=2, padx=5)
        
        # === 엑셀 파일 미리보기 (오른쪽) ===
        preview_frame = ttk.LabelFrame(main_frame, text="엑셀 파일 미리보기", padding="8")
        preview_frame.grid(row=3, column=2, rowspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=3, padx=5)
        
        # 총 건수 및 새로고침 버튼 프레임
        header_frame = ttk.Frame(preview_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.total_count_var = tk.StringVar(value="총 0건")
        total_label = ttk.Label(header_frame, textvariable=self.total_count_var, 
                               font=("맑은 고딕", 12, "bold"))
        total_label.pack(side=tk.LEFT)
        
        refresh_excel_btn = ttk.Button(header_frame, text="새로고침", command=self.reset_excel_data, width=10)
        refresh_excel_btn.pack(side=tk.RIGHT, padx=5)
        
        # 리스트 박스
        list_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.excel_listbox = tk.Listbox(preview_frame, width=28, 
                                        yscrollcommand=list_scroll.set,
                                        font=("맑은 고딕", 9))
        self.excel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.excel_listbox.yview)
        
        # === 진행 상황 ===
        progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="8")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3)
        
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="대기 중...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=3)
        
        # === 로그 영역 ===
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="8")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=3)
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=6, width=60, yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        # === 버튼 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.sync_btn = ttk.Button(button_frame, text="동기화 실행", command=self.start_automation, 
                                   width=15, state=tk.DISABLED)
        self.sync_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="중지", command=self.stop_automation, 
                                   width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        save_config_btn = ttk.Button(button_frame, text="설정 저장", command=self.save_settings, width=15)
        save_config_btn.pack(side=tk.LEFT, padx=5)
    
    def refresh_ports(self):
        """COM 포트 목록 새로고침"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0] if ports else "")
        self.log("COM 포트 목록 새로고침 완료")
    
    def check_bluetooth_connection(self):
        """블루투스 연결 확인"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("경고", "COM 포트를 선택하세요.")
            return
        
        try:
            controller = BluetoothController(port=port, baudrate=115200)
            if controller.connect():
                # 시리얼로 블루투스 상태 확인 시도
                time.sleep(1)
                controller.disconnect()
                self.bt_status_label.config(text="BLT AI 로봇 연결됨 (블루투스 상태는 모바일에서 확인)")
                self.bt_status_indicator.config(foreground="green")
                self.log("BLT AI 로봇 연결 확인 완료")
            else:
                self.bt_status_label.config(text="BLT AI 로봇 연결 실패")
                self.bt_status_indicator.config(foreground="red")
                self.log("BLT AI 로봇 연결 실패")
        except Exception as e:
            self.bt_status_label.config(text=f"연결 오류: {str(e)}")
            self.bt_status_indicator.config(foreground="red")
            self.log(f"연결 오류: {e}")
    
    def verify_mac_address_optional(self):
        """MAC 주소 검증 (선택사항 - 실패해도 계속 진행 가능)"""
        if not self.current_user_id:
            return True  # 사용자 ID가 없으면 검증 스킵
        
        # 개발 모드에서는 검증 스킵
        dev_mode_file = Path(__file__).parent.parent / "config" / "dev_mode.txt"
        if dev_mode_file.exists():
            try:
                with open(dev_mode_file, 'r', encoding='utf-8') as f:
                    if f.read().strip().lower() == 'true':
                        self.log("⚠️ 개발 모드: MAC 주소 검증을 건너뜁니다.")
                        return True
            except:
                pass
        
        port = self.port_var.get()
        if not port:
            self.log("⚠️ COM 포트가 선택되지 않았습니다. MAC 주소 검증을 건너뜁니다.")
            return True  # 포트가 없어도 검증 스킵하고 계속 진행
        
        try:
            # 먼저 등록된 MAC 주소 목록 가져오기
            import requests
            server_url = self.config.get("license_server", {}).get("url", "http://localhost:5000")
            try:
                mac_response = requests.post(
                    f"{server_url}/api/list_user_mac_addresses",
                    json={"user_id": self.current_user_id},
                    timeout=5
                )
                registered_macs = []
                if mac_response.status_code == 200:
                    mac_data = mac_response.json()
                    if mac_data.get('success'):
                        registered_macs = [mac.get('mac_address', '').upper() for mac in mac_data.get('mac_addresses', [])]
            except:
                registered_macs = []
            
            # AI BOT 연결
            controller = BluetoothController(port=port, baudrate=115200)
            if not controller.connect():
                self.log("⚠️ AI BOT 연결에 실패했습니다. MAC 주소 검증을 건너뜁니다.")
                if registered_macs:
                    self.log(f"등록된 MAC 주소: {', '.join(registered_macs)}")
                return True  # 연결 실패해도 검증 스킵하고 계속 진행
            
            # MAC 주소 자동 조회 비활성화 (GET_CONNECTED_MAC 명령이 송장번호 입력 필드에 들어가는 것을 방지)
            # MAC 주소 확인 기능 제거 - 송장번호 전송에만 집중
            self.log("MAC 주소 자동 조회 기능이 비활성화되어 있습니다.")
            mac_address = None
            response_messages = []
            
            controller.disconnect()
            
            # MAC 주소 형식 정규화 (대문자, 콜론 포함)
            if mac_address:
                mac_address = mac_address.upper().replace(' ', '').replace('-', ':')
                # 콜론이 없으면 추가
                if ':' not in mac_address and len(mac_address) == 12:
                    mac_address = ':'.join([mac_address[i:i+2] for i in range(0, 12, 2)])
            
            # MAC 주소를 얻지 못한 경우 - 경고만 표시하고 계속 진행
            if not mac_address or mac_address == "00:00:00:00:00:00":
                self.log("⚠️ AI BOT에서 MAC 주소를 자동으로 확인할 수 없습니다.")
                if registered_macs:
                    self.log(f"등록된 MAC 주소: {', '.join(registered_macs)}")
                self.log("MAC 주소 검증을 건너뛰고 계속 진행합니다.")
                return True  # 검증 실패해도 True 반환 (계속 진행)
            
            # 서버에서 MAC 주소 검증
            hardware_id = get_hardware_id()
            allowed, message = self.user_auth_manager.verify_mac_address(
                self.current_user_id, 
                mac_address, 
                hardware_id
            )
            
            if not allowed:
                self.log(f"⚠️ MAC 주소 검증 실패: {mac_address}")
                if registered_macs:
                    self.log(f"등록된 MAC 주소: {', '.join(registered_macs)}")
                self.log("MAC 주소가 일치하지 않지만 계속 진행합니다.")
                # 검증 실패해도 True 반환 (계속 진행)
                return True
            
            # 성공 시 로그만 표시
            self.log(f"✓ MAC 주소 검증 성공: {mac_address}")
            return True
            
        except Exception as e:
            self.log(f"⚠️ MAC 주소 검증 중 오류 발생: {e}")
            self.log("MAC 주소 검증을 건너뛰고 계속 진행합니다.")
            return True  # 오류 발생해도 계속 진행
    
    def check_bluetooth_status(self):
        """블루투스 상태 주기적 확인 (5초마다)"""
        if not self.is_running:
            # 간단한 연결 확인만 수행
            pass
        self.root.after(5000, self.check_bluetooth_status)
    
    def browse_excel_file(self):
        """엑셀 파일 선택"""
        try:
            filename = filedialog.askopenfilename(
                title="엑셀 파일 선택",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
            if filename:
                self.excel_path_var.set(filename)
                self.log(f"엑셀 파일 선택: {filename}")
                
                # 파일 존재 확인만 (비동기 처리 안 함)
                if Path(filename).exists():
                    self.log("파일 경로 확인 완료")
                else:
                    self.log("경고: 파일을 찾을 수 없습니다.")
                    messagebox.showwarning("경고", "선택한 파일을 찾을 수 없습니다.")
        except Exception as e:
            self.log(f"파일 선택 오류: {e}")
            messagebox.showerror("오류", f"파일 선택 중 오류가 발생했습니다:\n{e}")
    
    def reset_excel_data(self):
        """엑셀 데이터 초기화 (새로고침)"""
        self.loaded_invoices = []
        self.excel_listbox.delete(0, tk.END)
        self.total_count_var.set("총 0건")
        self.sync_btn.config(state=tk.DISABLED)
        self.progress_var.set("대기 중...")
        self.progress_bar['value'] = 0
        self.log("엑셀 데이터 초기화 완료. 새 파일을 업로드할 수 있습니다.")
    
    def load_excel_file(self):
        """엑셀 파일 로드 및 미리보기"""
        excel_path = self.excel_path_var.get()
        if not excel_path:
            messagebox.showwarning("경고", "엑셀 파일을 선택하세요.")
            return
        
        if not Path(excel_path).is_absolute():
            project_root = Path(__file__).parent.parent
            excel_path = project_root / excel_path
        
        if not Path(excel_path).exists():
            messagebox.showerror("오류", "엑셀 파일을 찾을 수 없습니다.")
            return
        
        try:
            self.log("엑셀 파일 읽기 중...")
            self.progress_var.set("엑셀 파일 읽기 중...")
            self.root.update()
            
            reader = ExcelReader(
                file_path=str(excel_path),
                sheet_name=self.config["excel"].get("sheet_name", "Sheet1")
            )
            
            self.loaded_invoices = reader.read_invoices()
            total = len(self.loaded_invoices)
            
            if total == 0:
                messagebox.showwarning("경고", "엑셀 파일에 송장번호가 없습니다.")
                self.total_count_var.set("총 0건")
                self.excel_listbox.delete(0, tk.END)
                self.sync_btn.config(state=tk.DISABLED)
                return
            
            # 리스트 박스에 표시
            self.excel_listbox.delete(0, tk.END)
            for idx, invoice in enumerate(self.loaded_invoices, 1):
                self.excel_listbox.insert(tk.END, f"{idx}. {invoice}")
            
            # 총 건수 표시
            self.total_count_var.set(f"총 {total}건")
            
            # 동기화 실행 버튼 활성화
            self.sync_btn.config(state=tk.NORMAL)
            
            self.log(f"엑셀 파일 업로드 완료: {total}건")
            self.progress_var.set(f"파일 업로드 완료: {total}건")
            messagebox.showinfo("완료", f"엑셀 파일이 로드되었습니다.\n총 {total}건의 송장번호를 확인했습니다.")
            
        except Exception as e:
            self.log(f"엑셀 파일 읽기 실패: {e}")
            messagebox.showerror("오류", f"엑셀 파일을 읽을 수 없습니다:\n{e}")
            self.total_count_var.set("총 0건")
            self.excel_listbox.delete(0, tk.END)
            self.sync_btn.config(state=tk.DISABLED)
    
    def save_settings(self):
        """설정 저장"""
        self.config["serial"]["port"] = self.port_var.get()
        self.config["delays"]["min_between"] = float(self.min_delay_var.get())
        self.config["delays"]["max_between"] = float(self.max_delay_var.get())
        self.config["excel"]["file_path"] = self.excel_path_var.get()
        # 컬럼명은 기본값 사용 (설정에서 변경 불가)
        
        self.save_config()
        messagebox.showinfo("완료", "설정이 저장되었습니다.")
        self.log("설정 저장 완료")
    
    def log(self, message):
        """로그 메시지 추가"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_automation(self):
        """동기화 실행 (자동화 시작)"""
        if not self.current_user_id:
            messagebox.showerror("오류", "로그인이 필요합니다.")
            return
        
        # MAC 주소 검증 (선택사항 - 사용자가 취소하면 계속 진행)
        # AI BOT에서 MAC 주소 자동 확인이 어려우므로, 검증 실패 시에도 진행 가능하도록 변경
        try:
            if not self.verify_mac_address_optional():
                # 사용자가 취소하지 않았고 검증이 실패한 경우만 중단
                return
        except:
            # 검증 중 오류 발생 시에도 계속 진행 (자동화가 멈추지 않도록)
            self.log("MAC 주소 검증 중 오류 발생, 계속 진행합니다.")
        
        if self.is_running:
            return
        
        # 유효성 검사
        if not self.port_var.get():
            messagebox.showerror("오류", "COM 포트를 선택하세요.")
            return
        
        if not self.loaded_invoices:
            messagebox.showerror("오류", "엑셀 파일을 먼저 로드하세요.")
            return
        
        # 설정 저장
        self.save_settings()
        
        # 확인 메시지
        if not messagebox.askyesno("확인", f"동기화를 시작하시겠습니까?\n\n총 {len(self.loaded_invoices)}건의 송장번호를 모바일로 전송합니다.\n\n모바일 앱이 준비되어 있어야 합니다."):
            return
        
        # 스레드에서 실행
        self.is_running = True
        self.sync_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.run_automation, daemon=True)
        thread.start()
    
    def stop_automation(self):
        """자동화 중지"""
        self.is_running = False
        self.log("중지 요청...")
    
    def run_automation(self):
        """자동화 실행 (별도 스레드)"""
        try:
            # BLT AI 로봇 연결
            self.log("BLT AI 로봇 연결 중...")
            self.progress_var.set("BLT AI 로봇 연결 중...")
            
            port = self.port_var.get()
            controller = BluetoothController(port=port, baudrate=115200)
            
            if not controller.connect():
                self.log("BLT AI 로봇 연결 실패!")
                messagebox.showerror("오류", "BLT AI 로봇 연결에 실패했습니다.")
                self.automation_finished()
                return
            
            self.log("BLT AI 로봇 연결 성공!")
            self.controller = controller
            
            # AI BOT 시리얼 메시지 모니터링 시작
            controller.start_serial_monitoring(log_callback=lambda msg: self.log(msg))
            
            # 이미 로드된 엑셀 데이터 사용
            invoices = self.loaded_invoices
            total = len(invoices)
            
            if total == 0:
                self.log("송장번호가 없습니다!")
                messagebox.showerror("오류", "송장번호가 없습니다.")
                self.automation_finished()
                return
            
            self.log(f"총 {total}건의 송장번호를 전송합니다.")
            
            # 자동화 실행
            self.log("자동화 시작...")
            self.progress_bar['maximum'] = total
            self.progress_bar['value'] = 0
            
            success_count = 0
            fail_count = 0
            
            import random
            
            for idx, invoice in enumerate(invoices, 1):
                if not self.is_running:
                    self.log("사용자에 의해 중지되었습니다.")
                    break
                
                self.progress_var.set(f"처리 중: {idx}/{total} - {invoice}")
                self.progress_bar['value'] = idx
                
                if controller.send_text(invoice):
                    success_count += 1
                    self.log(f"[{idx}/{total}] 성공: {invoice}")
                else:
                    fail_count += 1
                    self.log(f"[{idx}/{total}] 실패: {invoice}")
                
                # 딜레이
                if idx < total:
                    delay_min = float(self.min_delay_var.get())
                    delay_max = float(self.max_delay_var.get())
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)
            
            # 완료
            self.log(f"\n처리 완료! 성공: {success_count}건, 실패: {fail_count}건")
            self.progress_var.set(f"완료! 성공: {success_count}건, 실패: {fail_count}건")
            messagebox.showinfo("완료", f"처리 완료!\n성공: {success_count}건\n실패: {fail_count}건")
            
            # 사용 통계 서버에 전송
            try:
                self.log("사용 통계 전송 중...")
                # MAC 주소 조회 제거 (GET_CONNECTED_MAC 명령이 송장번호 입력 필드에 들어가는 것을 방지)
                mac_address = None
                
                hardware_id = get_hardware_id()
                success, msg = self.user_auth_manager.record_usage(
                    user_id=self.current_user_id,
                    total_invoices=total,
                    success_count=success_count,
                    fail_count=fail_count,
                    mac_address=mac_address,
                    hardware_id=hardware_id
                )
                if success:
                    self.log("사용 통계 전송 완료")
                else:
                    self.log(f"통계 전송 실패: {msg}")
            except Exception as stat_error:
                self.log(f"통계 전송 오류: {stat_error}")
            
        except Exception as e:
            self.log(f"오류 발생: {e}")
            messagebox.showerror("오류", f"오류가 발생했습니다:\n{e}")
        finally:
            if self.controller:
                self.controller.disconnect()
            self.automation_finished()
    
    def start_auto_logout_timer(self):
        """1시간 후 자동 로그아웃 타이머 시작"""
        # 기존 타이머 취소
        if self.auto_logout_timer:
            self.root.after_cancel(self.auto_logout_timer)
        
        # 1시간 = 3600000 밀리초 후 자동 로그아웃
        self.auto_logout_timer = self.root.after(3600000, self.auto_logout)
        self.log("⏰ 1시간 후 자동 로그아웃 예약됨")
    
    def auto_logout(self):
        """자동 로그아웃 실행"""
        if self.current_user_id:
            self.log("⏰ 1시간 경과 - 자동 로그아웃됩니다.")
            self.perform_logout("세션이 만료되었습니다. 다시 로그인해주세요.")
    
    def perform_logout(self, message: str = "로그아웃되었습니다."):
        """로그아웃 수행"""
        # 확인 메시지 표시 (자동 로그아웃이 아닌 경우만)
        if "세션이 만료" not in message:
            if not messagebox.askyesno("로그아웃", message):
                return
        
        # 자동 로그아웃 타이머 취소
        if self.auto_logout_timer:
            self.root.after_cancel(self.auto_logout_timer)
            self.auto_logout_timer = None
        
        # 서버에 로그아웃 요청
        if self.current_user_id:
            try:
                self.user_auth_manager.logout(self.current_user_id)
            except:
                pass
        
        # 세션 삭제
        self.user_auth_manager.clear_session()
        self.current_user_id = None
        self.current_user_info = None
        
        # 자동 로그아웃이 아닌 경우에만 메시지 표시
        if "세션이 만료" not in message:
            messagebox.showinfo("로그아웃", "로그아웃되었습니다.")
        
        # GUI 위젯 모두 제거
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 로그인 화면 다시 표시
        if not self.show_login():
            self.root.quit()
            return
        
        # GUI 다시 생성
        self.create_widgets()
        self.refresh_ports()
        self.check_bluetooth_status()
        
        # 자동 로그아웃 타이머 다시 시작
        self.start_auto_logout_timer()
    
    def show_admin_message_window(self):
        """관리자에게 메시지 보내기 창"""
        if not self.current_user_id:
            messagebox.showwarning("경고", "로그인이 필요합니다.")
            return
        
        # 새 창 생성
        msg_window = tk.Toplevel(self.root)
        msg_window.title("관리자에게 메시지 보내기")
        msg_window.geometry("500x550")
        msg_window.resizable(False, False)
        msg_window.transient(self.root)
        msg_window.grab_set()
        
        # 창을 화면 중앙에 배치
        msg_window.update_idletasks()
        x = (msg_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (msg_window.winfo_screenheight() // 2) - (550 // 2)
        msg_window.geometry(f"500x550+{x}+{y}")
        
        # 메인 프레임
        main_frame = ttk.Frame(msg_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 아이디 (읽기 전용)
        ttk.Label(main_frame, text="아이디:").grid(row=0, column=0, sticky=tk.W, pady=5)
        user_id_var = tk.StringVar(value=self.current_user_id)
        user_id_entry = ttk.Entry(main_frame, textvariable=user_id_var, state="readonly", width=40)
        user_id_entry.grid(row=0, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
        
        # 종류 (라디오 버튼)
        ttk.Label(main_frame, text="종류:").grid(row=1, column=0, sticky=tk.W, pady=5)
        category_frame = ttk.Frame(main_frame)
        category_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        category_var = tk.StringVar(value="기타")
        categories = ["입금확인", "사용방법", "오류", "기타"]
        for idx, cat in enumerate(categories):
            ttk.Radiobutton(category_frame, text=cat, variable=category_var, value=cat).grid(row=0, column=idx, padx=5)
        
        # 제목
        ttk.Label(main_frame, text="제목:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=5)
        title_var = tk.StringVar()
        title_entry = ttk.Entry(main_frame, textvariable=title_var, width=40)
        title_entry.grid(row=2, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
        title_entry.focus()
        
        # 내용
        ttk.Label(main_frame, text="내용:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        content_text = tk.Text(main_frame, width=40, height=10, wrap=tk.WORD)
        content_text.grid(row=3, column=1, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 스크롤바
        content_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=content_text.yview)
        content_scroll.grid(row=3, column=2, sticky=(tk.N, tk.S), pady=5)
        content_text.config(yscrollcommand=content_scroll.set)
        
        # 회신받을 전화번호 (선택사항)
        ttk.Label(main_frame, text="회신받을 전화번호:").grid(row=4, column=0, sticky=tk.W, pady=5)
        phone_label_hint = ttk.Label(main_frame, text="(선택사항)", font=("맑은 고딕", 8), foreground="gray")
        phone_label_hint.grid(row=4, column=0, sticky=tk.E, pady=5)
        phone_var = tk.StringVar()
        phone_entry = ttk.Entry(main_frame, textvariable=phone_var, width=40)
        phone_entry.grid(row=4, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
        
        # 상태 메시지
        status_label = ttk.Label(main_frame, text="", foreground="red", wraplength=400)
        status_label.grid(row=5, column=0, columnspan=3, pady=10)
        
        # 그리드 가중치 설정
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        def send_message():
            """메시지 전송"""
            # 아이디 확인 (이미 설정되어 있어야 함)
            user_id = user_id_var.get().strip()
            if not user_id:
                status_label.config(text="아이디가 없습니다. 다시 로그인해주세요.", foreground="red")
                messagebox.showerror("오류", "아이디가 없습니다. 다시 로그인해주세요.")
                msg_window.destroy()
                return
            
            # 종류 확인
            category = category_var.get()
            if not category:
                status_label.config(text="종류를 선택해주세요.", foreground="red")
                messagebox.showwarning("경고", "종류를 선택해주세요.")
                return
            
            # 제목 확인
            title = title_var.get().strip()
            if not title:
                status_label.config(text="제목을 입력해주세요.", foreground="red")
                messagebox.showwarning("경고", "제목을 입력해주세요.")
                title_entry.focus()
                return
            
            # 내용 확인
            content = content_text.get("1.0", tk.END).strip()
            if not content:
                status_label.config(text="내용을 입력해주세요.", foreground="red")
                messagebox.showwarning("경고", "내용을 입력해주세요.")
                content_text.focus()
                return
            
            phone = phone_var.get().strip()
            
            # 전송
            status_label.config(text="전송 중...", foreground="blue")
            msg_window.update()
            
            success, message = self.user_auth_manager.send_admin_message(
                category=category,
                title=title,
                content=content,
                phone=phone
            )
            
            if success:
                status_label.config(text=message, foreground="green")
                messagebox.showinfo("성공", message)
                # 창 닫기
                msg_window.destroy()
            else:
                status_label.config(text=message, foreground="red")
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="전송", command=send_message, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=msg_window.destroy, width=15).pack(side=tk.LEFT, padx=5)
        
        # Enter 키로 전송
        def on_enter(event):
            send_message()
        
        title_entry.bind("<Return>", lambda e: content_text.focus())
        msg_window.bind("<Return>", on_enter)
        
        msg_window.focus_set()
    
    def on_closing(self):
        """프로그램 종료 시 정리"""
        # 자동 로그아웃 타이머 취소
        if self.auto_logout_timer:
            self.root.after_cancel(self.auto_logout_timer)
        
        # 서버에 로그아웃 요청
        if self.current_user_id:
            try:
                self.user_auth_manager.logout(self.current_user_id)
            except:
                pass
        
        # 세션 삭제
        self.user_auth_manager.clear_session()
        
        # AI BOT 연결 종료
        if self.controller:
            self.controller.disconnect()
        
        self.root.destroy()
    
    def automation_finished(self):
        """자동화 완료 후 UI 업데이트"""
        self.is_running = False
        if self.loaded_invoices:
            self.sync_btn.config(state=tk.NORMAL)
        else:
            self.sync_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0


def main():
    """메인 함수"""
    root = tk.Tk()
    app = HanjinAutomationApp(root)
    
    # 프로그램 종료 시 정리 함수 연결
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()


if __name__ == "__main__":
    main()

