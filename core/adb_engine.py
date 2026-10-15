import subprocess
import threading
import tkinter as tk

class ADBEngine:
    @staticmethod
    def run_command(command, text_widget):
        # Menampilkan teks perintah yang sedang dijalankan
        text_widget.insert(tk.END, f"\n> Menjalankan: {' '.join(command)}\n")
        text_widget.see(tk.END) # Otomatis scroll ke paling bawah
        
        try:
            # subprocess.run untuk mengeksekusi ADB
            # creationflags=0x08000000 mencegah munculnya jendela CMD hitam di Windows
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=15,
                creationflags=0x08000000 
            )
            
            # Menampilkan hasil output
            if result.stdout:
                text_widget.insert(tk.END, result.stdout)
            if result.stderr:
                text_widget.insert(tk.END, f"Pesan:\n{result.stderr}")
                
        except FileNotFoundError:
            text_widget.insert(tk.END, "Error: ADB tidak ditemukan! Pastikan sudah install ADB dan masuk ke PATH Windows.\n")
        except subprocess.TimeoutExpired:
            text_widget.insert(tk.END, "Error: Proses terlalu lama (Timeout).\n")
        except Exception as e:
            text_widget.insert(tk.END, f"Terjadi kesalahan sistem: {e}\n")
            
        text_widget.insert(tk.END, "-"*50 + "\n")
        text_widget.see(tk.END)

    @staticmethod
    def execute_in_thread(command, text_widget):
        # Membungkus proses di Thread terpisah agar GUI tidak "Not Responding"
        thread = threading.Thread(target=ADBEngine.run_command, args=(command, text_widget))
        thread.daemon = True # Thread mati saat aplikasi ditutup
        thread.start()