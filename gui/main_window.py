import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, simpledialog, font
from core.adb_engine import ADBEngine

class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Super-ADB v2.5")
        self.root.geometry("1000x650")
        self.root.configure(fg_color="#F4F5F7")

        # --- PENGATURAN TEMA & WARNA ---
        self.COLOR_BG = "#FFFFFF"
        self.COLOR_ORANGE = "#F37B2F"
        self.COLOR_ORANGE_HOVER = "#D66420"
        self.COLOR_TEXT_MAIN = "#2D3748"
        self.COLOR_TEXT_MUTED = "#A0AEC0"

        # --- SISTEM FONT ---
        self.available_fonts = sorted(list(set(font.families())))
        
        preferred_fonts = ["Poppins", "Montserrat", "Segoe UI", "Helvetica", "Arial"]
        self.current_font_family = "Arial"
        for pref_font in preferred_fonts:
            if pref_font in self.available_fonts:
                self.current_font_family = pref_font
                break

        self.font_logo = ctk.CTkFont(family=self.current_font_family, size=22, weight="bold")
        self.font_menu = ctk.CTkFont(family=self.current_font_family, size=12, weight="bold")
        self.font_title = ctk.CTkFont(family=self.current_font_family, size=18, weight="bold")
        self.font_btn = ctk.CTkFont(family=self.current_font_family, size=13, weight="bold")
        self.font_normal = ctk.CTkFont(family=self.current_font_family, size=12)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1) 
        self.root.grid_columnconfigure(2, weight=1) 

        self.create_sidebar()
        self.create_main_content()
        self.create_terminal_panel()

        self.select_frame_by_name("sistem")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.root, width=90, corner_radius=0, fg_color=self.COLOR_BG)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="⚡\nADB", font=self.font_logo, text_color=self.COLOR_ORANGE)
        self.logo_label.grid(row=0, column=0, padx=15, pady=(20, 30))

        self.btn_sistem = self.create_sidebar_btn("💻\nSistem", "sistem", 1)
        self.btn_aplikasi = self.create_sidebar_btn("📦\nAplikasi", "aplikasi", 2)
        self.btn_jaringan = self.create_sidebar_btn("🌐\nJaringan", "jaringan", 3)
        self.btn_pengaturan = self.create_sidebar_btn("⚙️\nSetting", "pengaturan", 5)
        self.btn_pengaturan.grid(row=5, column=0, padx=15, pady=(0, 20))

    def create_sidebar_btn(self, text, name, row):
        btn = ctk.CTkButton(
            self.sidebar_frame, text=text, width=70, height=65, corner_radius=15,
            fg_color="transparent", text_color=self.COLOR_TEXT_MUTED,
            font=self.font_menu, hover_color="#FFF5F0",
            command=lambda: self.select_frame_by_name(name)
        )
        btn.grid(row=row, column=0, padx=10, pady=10)
        return btn

    def select_frame_by_name(self, name):
        self.btn_sistem.configure(fg_color=self.COLOR_ORANGE if name == "sistem" else "transparent",
                                  text_color=self.COLOR_BG if name == "sistem" else self.COLOR_TEXT_MUTED)
        self.btn_aplikasi.configure(fg_color=self.COLOR_ORANGE if name == "aplikasi" else "transparent",
                                    text_color=self.COLOR_BG if name == "aplikasi" else self.COLOR_TEXT_MUTED)
        self.btn_jaringan.configure(fg_color=self.COLOR_ORANGE if name == "jaringan" else "transparent",
                                    text_color=self.COLOR_BG if name == "jaringan" else self.COLOR_TEXT_MUTED)
        self.btn_pengaturan.configure(fg_color=self.COLOR_ORANGE if name == "pengaturan" else "transparent",
                                      text_color=self.COLOR_BG if name == "pengaturan" else self.COLOR_TEXT_MUTED)

        self.frame_sistem.grid_forget()
        self.frame_aplikasi.grid_forget()
        self.frame_jaringan.grid_forget()
        self.frame_pengaturan.grid_forget()

        if name == "sistem": self.frame_sistem.grid(row=0, column=0, sticky="nsew")
        elif name == "aplikasi": self.frame_aplikasi.grid(row=0, column=0, sticky="nsew")
        elif name == "jaringan": self.frame_jaringan.grid(row=0, column=0, sticky="nsew")
        elif name == "pengaturan": self.frame_pengaturan.grid(row=0, column=0, sticky="nsew")

    def create_main_content(self):
        self.main_wrapper = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_wrapper.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_wrapper.grid_rowconfigure(0, weight=1)
        self.main_wrapper.grid_columnconfigure(0, weight=1)

        self.frame_sistem = ctk.CTkFrame(self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20)
        self.frame_aplikasi = ctk.CTkFrame(self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20)
        self.frame_jaringan = ctk.CTkFrame(self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20)
        
        self.frame_pengaturan = ctk.CTkFrame(self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20)
        self.frame_pengaturan.bind("<Button-1>", self.hide_font_dropdown) 

        self.build_sistem_page()
        self.build_aplikasi_page()
        self.build_jaringan_page()
        self.build_pengaturan_page()

    def build_sistem_page(self):
        self.create_section_title(self.frame_sistem, "Informasi Sistem & Perangkat", 0)
        
        self.create_action_btn(self.frame_sistem, "Cek Perangkat Terhubung", ["adb", "devices"], 1)
        
        # Perintah Dasar (Merek, Model, Nama)
        cmd_spek_dasar = ["adb", "shell", "echo 'Merek:' $(getprop ro.product.brand) '| Model:' $(getprop ro.product.model) '| Nama:' $(getprop ro.product.name)"]
        self.create_action_btn(self.frame_sistem, "Info Perangkat Dasar", cmd_spek_dasar, 2)
        
        # --- FITUR BARU: CEK HARDWARE DETAIL ---
        # Menggunakan perintah shell panjang yang digabung dengan titik koma (;) untuk mengambil banyak info
        cmd_hardware_detail = [
            "adb", "shell",
            "echo '=== PLATFORM & OS ===';"
            "echo 'Android Ver : ' $(getprop ro.build.version.release);"
            "echo 'API Level   : ' $(getprop ro.build.version.sdk);"
            "echo 'Chipset     : ' $(getprop ro.board.platform);"
            "echo 'CPU Arch    : ' $(getprop ro.product.cpu.abi);"
            "echo ' ';"
            "echo '=== LAYAR (DISPLAY) ===';"
            "wm size;"
            "wm density;"
            "echo ' ';"
            "echo '=== MEMORI (RAM) ===';"
            "cat /proc/meminfo | grep MemTotal | awk '{printf \"Total RAM   : %.2f GB\\n\", $2/1024/1024}';"
        ]
        # Membuat tombol dengan warna oranye agar menonjol
        btn_hw = ctk.CTkButton(self.frame_sistem, text="Cek Hardware Lengkap", font=self.font_btn, fg_color=self.COLOR_ORANGE, hover_color=self.COLOR_ORANGE_HOVER, command=lambda: self.run_adb(cmd_hardware_detail))
        btn_hw.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        # ----------------------------------------

        self.create_action_btn(self.frame_sistem, "Status Baterai", ["adb", "shell", "dumpsys", "battery"], 4)
        self.create_action_btn(self.frame_sistem, "Reboot Normal", ["adb", "reboot"], 5)

    def build_aplikasi_page(self):
        self.create_section_title(self.frame_aplikasi, "Manajemen Aplikasi", 0)
        btn_install = ctk.CTkButton(self.frame_aplikasi, text="Pilih & Install APK", font=self.font_btn, fg_color=self.COLOR_ORANGE, hover_color=self.COLOR_ORANGE_HOVER, command=self.install_apk)
        btn_install.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.create_action_btn(self.frame_aplikasi, "List Semua Aplikasi", ["adb", "shell", "pm", "list", "packages"], 2)
        btn_uninstall = ctk.CTkButton(self.frame_aplikasi, text="Uninstall Aplikasi (Input)", font=self.font_btn, fg_color=self.COLOR_TEXT_MAIN, command=self.uninstall_app)
        btn_uninstall.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    def build_jaringan_page(self):
        self.create_section_title(self.frame_jaringan, "Jaringan & Wireless ADB", 0)
        self.create_action_btn(self.frame_jaringan, "Aktifkan Port TCP/IP 5555", ["adb", "tcpip", "5555"], 1)
        btn_connect = ctk.CTkButton(self.frame_jaringan, text="Connect ke IP HP", font=self.font_btn, fg_color=self.COLOR_ORANGE, hover_color=self.COLOR_ORANGE_HOVER, command=self.connect_wireless)
        btn_connect.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.create_action_btn(self.frame_jaringan, "Disconnect Semua", ["adb", "disconnect"], 3)

    # ==========================================
    # HALAMAN PENGATURAN (PERBAIKAN TRACE ERROR)
    # ==========================================
    def build_pengaturan_page(self):
        self.create_section_title(self.frame_pengaturan, "Pengaturan Tampilan", 0)
        
        self.lbl_info = ctk.CTkLabel(self.frame_pengaturan, text="Cari dan pilih font untuk aplikasi:", font=self.font_normal, text_color=self.COLOR_TEXT_MAIN)
        self.lbl_info.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        self.lbl_info.bind("<Button-1>", self.hide_font_dropdown)

        # MENGHAPUS StringVar dan trace untuk mencegah error saat close aplikasi
        self.entry_search = ctk.CTkEntry(
            self.frame_pengaturan, 
            placeholder_text="🔍 Ketik nama font di sini...",
            font=self.font_normal,
            width=300
        )
        self.entry_search.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        # MENGGUNAKAN EVENT BINDING:
        # <FocusIn> untuk memunculkan dropdown
        self.entry_search.bind("<FocusIn>", self.show_font_dropdown)
        # <KeyRelease> dipanggil setiap kali pengguna selesai menekan satu huruf di keyboard
        self.entry_search.bind("<KeyRelease>", self.filter_font_list)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.frame_pengaturan, 
            width=280, height=250, 
            fg_color="#F7FAFC", corner_radius=10
        )

        self.is_dropdown_visible = False
        self.font_buttons = {}
        self.prebuild_font_buttons()

    def prebuild_font_buttons(self):
        count = 0
        for f in self.available_fonts:
            if f.startswith('@'): continue
            
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=f, 
                fg_color="transparent", 
                text_color=self.COLOR_TEXT_MAIN,
                hover_color="#E2E8F0", 
                anchor="w",
                font=ctk.CTkFont(family=f, size=13),
                command=lambda font_name=f: self.change_font_family(font_name)
            )
            self.font_buttons[f] = btn
            btn.pack(fill="x", pady=2, padx=5)
            
            count += 1
            if count >= 150: break 

    def show_font_dropdown(self, event=None):
        if not self.is_dropdown_visible:
            self.scroll_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="w")
            self.is_dropdown_visible = True

    def hide_font_dropdown(self, event=None):
        if self.is_dropdown_visible:
            self.scroll_frame.grid_forget()
            self.is_dropdown_visible = False
            self.frame_pengaturan.focus_set() 

    def filter_font_list(self, event=None):
        # Mengambil teks langsung dari Entry widget (bukan dari StringVar)
        search_query = self.entry_search.get().lower()

        if search_query and not self.is_dropdown_visible:
            self.show_font_dropdown()

        for font_name, btn in self.font_buttons.items():
            if search_query in font_name.lower():
                if not btn.winfo_ismapped():
                    btn.pack(fill="x", pady=2, padx=5)
            else:
                if btn.winfo_ismapped():
                    btn.pack_forget()

    def change_font_family(self, selected_font):
        self.current_font_family = selected_font
        
        self.font_logo.configure(family=selected_font)
        self.font_menu.configure(family=selected_font)
        self.font_title.configure(family=selected_font)
        self.font_btn.configure(family=selected_font)
        self.font_normal.configure(family=selected_font)
        self.entry_search.configure(font=self.font_normal)

        # Ubah teks di entry secara manual
        self.entry_search.delete(0, tk.END)
        self.entry_search.insert(0, selected_font)
        
        self.hide_font_dropdown()

        # Reset daftar dengan trigger manual (mengakali event object)
        self.filter_font_list()

        self.txt_output.insert(tk.END, f"> Font diubah menjadi: {selected_font}\n")
        self.txt_output.see(tk.END)

    def create_section_title(self, parent, text, row):
        lbl = ctk.CTkLabel(parent, text=text, font=self.font_title, text_color=self.COLOR_TEXT_MAIN)
        lbl.grid(row=row, column=0, padx=20, pady=(20, 15), sticky="w")
        parent.grid_columnconfigure(0, weight=1)

    def create_action_btn(self, parent, text, command_list, row):
        btn = ctk.CTkButton(
            parent, text=text, fg_color="#EDF2F7", text_color=self.COLOR_TEXT_MAIN,
            hover_color="#E2E8F0", font=self.font_btn,
            command=lambda: self.run_adb(command_list)
        )
        btn.grid(row=row, column=0, padx=20, pady=8, sticky="ew")

    def create_terminal_panel(self):
        self.terminal_frame = ctk.CTkFrame(self.root, fg_color=self.COLOR_BG, corner_radius=20)
        self.terminal_frame.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        self.terminal_frame.grid_rowconfigure(1, weight=1)
        self.terminal_frame.grid_columnconfigure(0, weight=1)

        self.lbl_terminal = ctk.CTkLabel(self.terminal_frame, text="Terminal Log", font=self.font_title, text_color=self.COLOR_TEXT_MAIN)
        self.lbl_terminal.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.txt_output = tk.Text(
            self.terminal_frame, bg="#F7FAFC", fg="#2D3748", 
            font=("Consolas", 10), bd=0, highlightthickness=1, highlightcolor=self.COLOR_ORANGE
        )
        self.txt_output.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.txt_output.insert(tk.END, "Terminal siap...\n")
        self.txt_output.insert(tk.END, f"Font aktif: {self.current_font_family}\n")
        self.txt_output.insert(tk.END, "-"*30 + "\n")

    def run_adb(self, command):
        ADBEngine.execute_in_thread(command, self.txt_output)

    def install_apk(self):
        file_path = filedialog.askopenfilename(title="Pilih File APK", filetypes=[("APK Files", "*.apk")])
        if file_path:
            self.run_adb(["adb", "install", file_path])

    def uninstall_app(self):
        pkg_name = simpledialog.askstring("Uninstall App", "Masukkan Package Name:")
        if pkg_name:
            self.run_adb(["adb", "uninstall", pkg_name])

    def connect_wireless(self):
        ip_address = simpledialog.askstring("Connect Wireless", "Masukkan IP HP:")
        if ip_address:
            self.run_adb(["adb", "connect", ip_address])