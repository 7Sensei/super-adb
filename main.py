import customtkinter as ctk
from gui.main_window import AppWindow

def main():
    # Mengatur tema dasar (Putih/Terang) sesuai desain
    ctk.set_appearance_mode("Light")
    
    # PENTING: Gunakan ctk.CTk(), BUKAN tk.Tk()
    root = ctk.CTk()
    
    # Memanggil kelas AppWindow dari folder gui
    AppWindow(root)
    
    # Menjalankan loop utama aplikasi
    root.mainloop()

if __name__ == "__main__":
    main()