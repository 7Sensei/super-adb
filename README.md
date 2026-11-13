# Super-ADB

**Kelola perangkat Android melalui ADB dengan antarmuka desktop yang praktis.**

Super-ADB adalah aplikasi desktop berbasis PySide6 untuk melihat perangkat yang
terhubung dan menjalankan tindakan ADB umum dari satu tempat.

## Fitur

- **Sistem:** lihat informasi perangkat, detail perangkat, baterai, dan kontrol
  reboot.
- **Aplikasi:** tampilkan daftar aplikasi serta pasang atau hapus APK/aplikasi.
- **Jaringan:** aktifkan ADB melalui TCP/IP, hubungkan perangkat lewat alamat IP,
  dan putuskan koneksi.
- **Tampilan:** pilih tema terang, gelap, atau mengikuti sistem; cari dan pilih
  font aplikasi.
- **Pemantauan:** lihat status perintah dan keluaran ADB pada panel log.

## Persyaratan

- Python 3.10 atau lebih baru.
- Android SDK Platform-Tools, termasuk `adb`, tersedia di `PATH`.
- Perangkat Android dengan USB debugging aktif, atau perangkat yang dapat
  dijangkau melalui ADB over TCP/IP.

Super-ADB akan menampilkan pesan kesalahan jika executable ADB tidak ditemukan.

## Instalasi dan menjalankan

Dari folder proyek, jalankan perintah berikut di PowerShell:

```powershell
python -m pip install -e ".[dev]"
python -m super_adb
```

Setelah instalasi, aplikasi juga dapat dijalankan menggunakan perintah:

```powershell
super-adb
```

## Pengembangan

Dependensi pengembangan—termasuk pytest dan Ruff—sudah tercakup dalam opsi
`dev`. Jalankan pemeriksaan dari root proyek:

```powershell
pytest -q
ruff check .
```

## Struktur proyek

```text
src/super_adb/
  models/       Model perangkat, pengaturan, dan log
  services/     Integrasi ADB dan penyimpanan pengaturan
  ui/           Jendela, halaman, widget, dan tema PySide6
  viewmodels/   Logika presentasi dan penghubung UI dengan layanan
tests/          Pengujian layanan, viewmodel, dan antarmuka
```
