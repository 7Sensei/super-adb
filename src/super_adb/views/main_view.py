from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, font, simpledialog

import customtkinter as ctk

from super_adb.viewmodels.main_viewmodel import MainViewModel


class MainView(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, viewmodel: MainViewModel) -> None:
        super().__init__(master, fg_color="#F4F5F7")
        self.viewmodel = viewmodel
        self.COLOR_BG = "#FFFFFF"
        self.COLOR_ORANGE = "#F37B2F"
        self.COLOR_ORANGE_HOVER = "#D66420"
        self.COLOR_TEXT_MAIN = "#2D3748"
        self.COLOR_TEXT_MUTED = "#A0AEC0"

        self.available_fonts = sorted(set(font.families()))
        preferred_fonts = ["Poppins", "Montserrat", "Segoe UI", "Helvetica", "Arial"]
        self.current_font_family = next(
            (item for item in preferred_fonts if item in self.available_fonts), "Arial"
        )
        self.font_logo = ctk.CTkFont(family=self.current_font_family, size=22, weight="bold")
        self.font_menu = ctk.CTkFont(family=self.current_font_family, size=12, weight="bold")
        self.font_title = ctk.CTkFont(family=self.current_font_family, size=18, weight="bold")
        self.font_btn = ctk.CTkFont(family=self.current_font_family, size=13, weight="bold")
        self.font_normal = ctk.CTkFont(family=self.current_font_family, size=12)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self._create_sidebar()
        self._create_main_content()
        self._create_terminal_panel()
        self._bind_viewmodel()
        self._select_frame("sistem")

    def _bind_viewmodel(self) -> None:
        self.viewmodel.log.connect(self._append_log)

    def _create_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color=self.COLOR_BG)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="⚡\nADB",
            font=self.font_logo,
            text_color=self.COLOR_ORANGE,
        )
        self.logo_label.grid(row=0, column=0, padx=15, pady=(20, 30))
        self.btn_sistem = self._create_sidebar_btn("💻\nSistem", "sistem", 1)
        self.btn_aplikasi = self._create_sidebar_btn("📦\nAplikasi", "aplikasi", 2)
        self.btn_jaringan = self._create_sidebar_btn("🌐\nJaringan", "jaringan", 3)
        self.btn_pengaturan = self._create_sidebar_btn("⚙️\nSetting", "pengaturan", 5)
        self.btn_pengaturan.grid(row=5, column=0, padx=15, pady=(0, 20))

    def _create_sidebar_btn(self, text: str, name: str, row: int) -> ctk.CTkButton:
        button = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            width=70,
            height=65,
            corner_radius=15,
            fg_color="transparent",
            text_color=self.COLOR_TEXT_MUTED,
            font=self.font_menu,
            hover_color="#FFF5F0",
            command=lambda: self._select_frame(name),
        )
        button.grid(row=row, column=0, padx=10, pady=10)
        return button

    def _select_frame(self, name: str) -> None:
        buttons = {
            "sistem": self.btn_sistem,
            "aplikasi": self.btn_aplikasi,
            "jaringan": self.btn_jaringan,
            "pengaturan": self.btn_pengaturan,
        }
        frames = {
            "sistem": self.frame_sistem,
            "aplikasi": self.frame_aplikasi,
            "jaringan": self.frame_jaringan,
            "pengaturan": self.frame_pengaturan,
        }
        for key, button in buttons.items():
            active = key == name
            button.configure(
                fg_color=self.COLOR_ORANGE if active else "transparent",
                text_color=self.COLOR_BG if active else self.COLOR_TEXT_MUTED,
            )
        for frame in frames.values():
            frame.grid_forget()
        if name in frames:
            frames[name].grid(row=0, column=0, sticky="nsew")

    def _create_main_content(self) -> None:
        self.main_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.main_wrapper.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_wrapper.grid_rowconfigure(0, weight=1)
        self.main_wrapper.grid_columnconfigure(0, weight=1)
        self.frame_sistem = ctk.CTkFrame(
            self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20
        )
        self.frame_aplikasi = ctk.CTkFrame(
            self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20
        )
        self.frame_jaringan = ctk.CTkFrame(
            self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20
        )
        self.frame_pengaturan = ctk.CTkFrame(
            self.main_wrapper, fg_color=self.COLOR_BG, corner_radius=20
        )
        self.frame_pengaturan.bind("<Button-1>", self._hide_font_dropdown)
        self._build_system_page()
        self._build_app_page()
        self._build_network_page()
        self._build_settings_page()

    def _build_system_page(self) -> None:
        self._create_section_title(self.frame_sistem, "Informasi Sistem & Perangkat", 0)
        self._create_action_btn(
            self.frame_sistem, "Cek Perangkat Terhubung", self.viewmodel.check_devices, 1
        )
        self._create_action_btn(
            self.frame_sistem, "Info Perangkat Dasar", self.viewmodel.show_basic_info, 2
        )
        hardware_button = ctk.CTkButton(
            self.frame_sistem,
            text="Cek Hardware Lengkap",
            font=self.font_btn,
            fg_color=self.COLOR_ORANGE,
            hover_color=self.COLOR_ORANGE_HOVER,
            command=self.viewmodel.check_hardware,
        )
        hardware_button.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        self._create_action_btn(
            self.frame_sistem, "Status Baterai", self.viewmodel.show_battery_status, 4
        )
        self._create_action_btn(self.frame_sistem, "Reboot Normal", self.viewmodel.reboot_device, 5)

    def _build_app_page(self) -> None:
        self._create_section_title(self.frame_aplikasi, "Manajemen Aplikasi", 0)
        install_button = ctk.CTkButton(
            self.frame_aplikasi,
            text="Pilih & Install APK",
            font=self.font_btn,
            fg_color=self.COLOR_ORANGE,
            hover_color=self.COLOR_ORANGE_HOVER,
            command=self._install_apk,
        )
        install_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self._create_action_btn(
            self.frame_aplikasi, "List Semua Aplikasi", self.viewmodel.list_apps, 2
        )
        uninstall_button = ctk.CTkButton(
            self.frame_aplikasi,
            text="Uninstall Aplikasi (Input)",
            font=self.font_btn,
            fg_color=self.COLOR_TEXT_MAIN,
            command=self._uninstall_app,
        )
        uninstall_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    def _build_network_page(self) -> None:
        self._create_section_title(self.frame_jaringan, "Jaringan & Wireless ADB", 0)
        self._create_action_btn(
            self.frame_jaringan, "Aktifkan Port TCP/IP 5555", self.viewmodel.enable_tcpip, 1
        )
        connect_button = ctk.CTkButton(
            self.frame_jaringan,
            text="Connect ke IP HP",
            font=self.font_btn,
            fg_color=self.COLOR_ORANGE,
            hover_color=self.COLOR_ORANGE_HOVER,
            command=self._connect_wireless,
        )
        connect_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self._create_action_btn(
            self.frame_jaringan, "Disconnect Semua", self.viewmodel.disconnect_devices, 3
        )

    def _build_settings_page(self) -> None:
        self._create_section_title(self.frame_pengaturan, "Pengaturan Tampilan", 0)
        self.lbl_info = ctk.CTkLabel(
            self.frame_pengaturan,
            text="Cari dan pilih font untuk aplikasi:",
            font=self.font_normal,
            text_color=self.COLOR_TEXT_MAIN,
        )
        self.lbl_info.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        self.lbl_info.bind("<Button-1>", self._hide_font_dropdown)
        self.entry_search = ctk.CTkEntry(
            self.frame_pengaturan,
            placeholder_text="🔍 Ketik nama font di sini...",
            font=self.font_normal,
            width=300,
        )
        self.entry_search.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.entry_search.bind("<FocusIn>", self._show_font_dropdown)
        self.entry_search.bind("<KeyRelease>", self._filter_font_list)
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.frame_pengaturan, width=280, height=250, fg_color="#F7FAFC", corner_radius=10
        )
        self.is_dropdown_visible = False
        self.font_buttons: dict[str, ctk.CTkButton] = {}
        self._prebuild_font_buttons()

    def _prebuild_font_buttons(self) -> None:
        for font_name in [name for name in self.available_fonts if not name.startswith("@")][:150]:
            button = ctk.CTkButton(
                self.scroll_frame,
                text=font_name,
                fg_color="transparent",
                text_color=self.COLOR_TEXT_MAIN,
                hover_color="#E2E8F0",
                anchor="w",
                font=ctk.CTkFont(family=font_name, size=13),
                command=lambda selected=font_name: self._change_font_family(selected),
            )
            self.font_buttons[font_name] = button
            button.pack(fill="x", pady=2, padx=5)

    def _show_font_dropdown(self, event: tk.Event | None = None) -> None:
        if not self.is_dropdown_visible:
            self.scroll_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="w")
            self.is_dropdown_visible = True

    def _hide_font_dropdown(self, event: tk.Event | None = None) -> None:
        if self.is_dropdown_visible:
            self.scroll_frame.grid_forget()
            self.is_dropdown_visible = False
            self.frame_pengaturan.focus_set()

    def _filter_font_list(self, event: tk.Event | None = None) -> None:
        query = self.entry_search.get().lower()
        if query and not self.is_dropdown_visible:
            self._show_font_dropdown()
        for name, button in self.font_buttons.items():
            if query in name.lower():
                if not button.winfo_ismapped():
                    button.pack(fill="x", pady=2, padx=5)
            elif button.winfo_ismapped():
                button.pack_forget()

    def _change_font_family(self, selected_font: str) -> None:
        self.current_font_family = selected_font
        for current_font in (
            self.font_logo,
            self.font_menu,
            self.font_title,
            self.font_btn,
            self.font_normal,
        ):
            current_font.configure(family=selected_font)
        self.entry_search.configure(font=self.font_normal)
        self.entry_search.delete(0, tk.END)
        self.entry_search.insert(0, selected_font)
        self._hide_font_dropdown()
        self._filter_font_list()
        self._append_log(f"> Font diubah menjadi: {selected_font}")

    def _create_section_title(self, parent: ctk.CTkFrame, text: str, row: int) -> None:
        label = ctk.CTkLabel(
            parent, text=text, font=self.font_title, text_color=self.COLOR_TEXT_MAIN
        )
        label.grid(row=row, column=0, padx=20, pady=(20, 15), sticky="w")
        parent.grid_columnconfigure(0, weight=1)

    def _create_action_btn(
        self, parent: ctk.CTkFrame, text: str, command: Callable[[], None], row: int
    ) -> None:
        button = ctk.CTkButton(
            parent,
            text=text,
            fg_color="#EDF2F7",
            text_color=self.COLOR_TEXT_MAIN,
            hover_color="#E2E8F0",
            font=self.font_btn,
            command=command,
        )
        button.grid(row=row, column=0, padx=20, pady=8, sticky="ew")

    def _create_terminal_panel(self) -> None:
        self.terminal_frame = ctk.CTkFrame(self, fg_color=self.COLOR_BG, corner_radius=20)
        self.terminal_frame.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        self.terminal_frame.grid_rowconfigure(1, weight=1)
        self.terminal_frame.grid_columnconfigure(0, weight=1)
        self.lbl_terminal = ctk.CTkLabel(
            self.terminal_frame,
            text="Terminal Log",
            font=self.font_title,
            text_color=self.COLOR_TEXT_MAIN,
        )
        self.lbl_terminal.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.txt_output = tk.Text(
            self.terminal_frame,
            bg="#F7FAFC",
            fg="#2D3748",
            font=("Consolas", 10),
            bd=0,
            highlightthickness=1,
            highlightcolor=self.COLOR_ORANGE,
        )
        self.txt_output.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self._append_log("Terminal siap...")
        self._append_log(f"Font aktif: {self.current_font_family}")
        self._append_log("-" * 30)

    def _append_log(self, line: str) -> None:
        self.txt_output.insert(tk.END, f"{line}\n")
        self.txt_output.see(tk.END)

    def _install_apk(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Pilih File APK", filetypes=[("APK Files", "*.apk")]
        )
        if file_path:
            self.viewmodel.install_apk(file_path)

    def _uninstall_app(self) -> None:
        package_name = simpledialog.askstring("Uninstall App", "Masukkan Package Name:")
        if package_name:
            self.viewmodel.uninstall_app(package_name)

    def _connect_wireless(self) -> None:
        ip_address = simpledialog.askstring("Connect Wireless", "Masukkan IP HP:")
        if ip_address:
            self.viewmodel.connect_wireless(ip_address)
