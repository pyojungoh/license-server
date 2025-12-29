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
        
        # 설정 로드 (라이선스 서버 URL 필요)
        self.config = self.load_config()
        
        # 사용자 인증 관리자 (서버 URL 설정 필요)
        server_url = self.config.get("license_server", {}).get("url", "http://localhost:5000")
        self.user_auth_manager = UserAuthManager(server_url=server_url)
        self.current_user_id = None
        self.current_user_info = None
        
        # 로그인 화면 표시
        if not self.show_login():
            return
        
        # GUI 생성
        self.create_widgets()
        
        # COM 포트 목록 새로고침
        self.refresh_ports()
        
        # 블루투스 상태 확인 (주기적)
        self.check_bluetooth_status()
    
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
        """로그인 화면 표시"""
        # 세션 확인 (자동 로그인)
        session_data = self.user_auth_manager.session_data
        if session_data:
            user_id = session_data.get('user_id')
            if user_id:
                # 세션이 있으면 자동으로 사용자 정보 로드
                user_info = self.user_auth_manager.get_user_info(user_id)
                if user_info and user_info.get('is_active'):
                    self.current_user_id = user_id
                    self.current_user_info = user_info
                    # MAC 주소 검증은 나중에 수행
                    return True
        
        # 로그인 창 표시
        login_window = tk.Toplevel(self.root)
        login_window.title("로그인")
        login_window.geometry("400x250")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()
        
        # 창을 화면 중앙에 배치
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_window.winfo_screenheight() // 2) - (250 // 2)
        login_window.geometry(f"400x250+{x}+{y}")
        
        ttk.Label(login_window, text="로그인", font=("맑은 고딕", 16, "bold")).pack(pady=15)
        
        ttk.Label(login_window, text="아이디:").pack(pady=5)
        user_id_var = tk.StringVar()
        user_id_entry = ttk.Entry(login_window, textvariable=user_id_var, width=30)
        user_id_entry.pack(pady=5)
        user_id_entry.focus()
        
        ttk.Label(login_window, text="비밀번호:").pack(pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(login_window, textvariable=password_var, width=30, show="*")
        password_entry.pack(pady=5)
        
        status_label = ttk.Label(login_window, text="", foreground="red", wraplength=350)
        status_label.pack(pady=10)
        
        login_success = [False]  # 클로저를 위한 리스트
        
        def do_login():
            user_id = user_id_var.get().strip()
            password = password_var.get()
            
            if not user_id or not password:
                status_label.config(text="아이디와 비밀번호를 입력하세요.", foreground="red")
                return
            
            status_label.config(text="로그인 중...", foreground="blue")
            login_window.update()
            
            hardware_id = get_hardware_id()
            success, message, user_info = self.user_auth_manager.login(user_id, password, hardware_id)
            
            if success and user_info:
                self.current_user_id = user_id
                self.current_user_info = user_info
                login_success[0] = True
                login_window.destroy()
            else:
                status_label.config(text=message, foreground="red")
        
        def on_enter(event):
            do_login()
        
        password_entry.bind('<Return>', on_enter)
        user_id_entry.bind('<Return>', lambda e: password_entry.focus())
        
        ttk.Button(login_window, text="로그인", command=do_login, width=15).pack(pady=10)
        
        # 창이 닫힐 때까지 대기
        login_window.wait_window()
        
        return login_success[0]
    
    def create_widgets(self):
        """GUI 위젯 생성"""
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
    
    def verify_mac_address(self):
        """MAC 주소 검증"""
        if not self.current_user_id:
            return False
        
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("경고", "COM 포트를 선택하세요.")
            return False
        
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
            
            # ESP32 연결
            controller = BluetoothController(port=port, baudrate=115200)
            if not controller.connect():
                error_msg = "ESP32 연결에 실패했습니다."
                if registered_macs:
                    error_msg += f"\n\n등록된 MAC 주소 목록:\n" + "\n".join([f"  - {mac}" for mac in registered_macs])
                messagebox.showerror("오류", error_msg)
                return False
            
            # MAC 주소 확인 (로그 콜백 사용)
            self.log("ESP32에 MAC 주소 요청 전송 중...")
            mac_address, response_messages = controller.get_connected_mac_address(
                log_callback=lambda msg: self.log(f"[ESP32] {msg}")
            )
            
            if response_messages:
                self.log(f"ESP32 응답 메시지 수신: {len(response_messages)}개")
                for msg in response_messages:
                    self.log(f"  → {msg}")
            else:
                self.log("ESP32로부터 응답 없음")
            
            controller.disconnect()
            
            # MAC 주소 형식 정규화 (대문자, 콜론 포함)
            if mac_address:
                mac_address = mac_address.upper().replace(' ', '').replace('-', ':')
                # 콜론이 없으면 추가
                if ':' not in mac_address and len(mac_address) == 12:
                    mac_address = ':'.join([mac_address[i:i+2] for i in range(0, 12, 2)])
            
            if not mac_address or mac_address == "00:00:00:00:00:00":
                error_msg = "MAC 주소를 확인할 수 없습니다.\nESP32와 블루투스 연결을 확인하세요."
                if registered_macs:
                    error_msg += f"\n\n등록된 MAC 주소 목록:\n" + "\n".join([f"  - {mac}" for mac in registered_macs])
                messagebox.showerror("오류", error_msg)
                return False
            
            # 서버에서 MAC 주소 검증
            hardware_id = get_hardware_id()
            allowed, message = self.user_auth_manager.verify_mac_address(
                self.current_user_id, 
                mac_address, 
                hardware_id
            )
            
            if not allowed:
                error_msg = f"{message}\n\n"
                error_msg += f"연결된 휴대폰의 MAC 주소: {mac_address}\n\n"
                
                if registered_macs:
                    error_msg += f"등록된 MAC 주소 목록:\n"
                    for registered_mac in registered_macs:
                        if registered_mac == mac_address:
                            error_msg += f"  ✓ {registered_mac} (일치)\n"
                        else:
                            # 대소문자 비교
                            if registered_mac.upper() == mac_address.upper():
                                error_msg += f"  ⚠ {registered_mac} (대소문자 차이)\n"
                            else:
                                error_msg += f"  - {registered_mac}\n"
                    error_msg += f"\n현재 MAC 주소와 등록된 MAC 주소가 일치하지 않습니다.\n"
                else:
                    error_msg += f"등록된 MAC 주소가 없습니다.\n"
                
                error_msg += "\n관리자에게 문의하여 MAC 주소를 등록해주세요."
                
                messagebox.showerror("등록되지 않은 사용자", error_msg)
                return False
            
            # 성공 메시지 (선택사항)
            success_msg = f"MAC 주소 검증 성공!\n\n연결된 MAC 주소: {mac_address}"
            if registered_macs:
                success_msg += f"\n\n등록된 MAC 주소와 일치합니다."
            messagebox.showinfo("검증 성공", success_msg)
            
            return True
            
        except Exception as e:
            error_msg = f"MAC 주소 검증 중 오류가 발생했습니다:\n{e}"
            try:
                if registered_macs:
                    error_msg += f"\n\n등록된 MAC 주소 목록:\n" + "\n".join([f"  - {mac}" for mac in registered_macs])
            except:
                pass
            messagebox.showerror("오류", error_msg)
            return False
    
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
        
        # MAC 주소 검증
        if not self.verify_mac_address():
            return
        
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
                # MAC 주소 다시 확인
                mac_address = None
                if controller.is_connected():
                    mac_address, _ = controller.get_connected_mac_address(
                        log_callback=lambda msg: self.log(f"[ESP32] {msg}")
                    )
                
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
    root.mainloop()


if __name__ == "__main__":
    main()

