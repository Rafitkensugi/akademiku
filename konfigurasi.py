# konfigurasi.py
# Berisi semua konstanta default aplikasi.
# Alasan dipisah: aturan tiap kampus berbeda, jadi angka tidak boleh
# tersebar di banyak file. Cukup ubah di sini.

# MATERI: Tipe data dan variabel (str, int, bool, list, tuple)
NAMA_DATABASE = "akademikku.db"       # str
KUNCI_RAHASIA = "ganti-dengan-kunci-rahasia-anda"  # str, untuk session Flask
MODE_DEBUG = True                     # bool

# MATERI: List dan tuple
# Skala grade = list of tuple: (huruf, batas_nilai_minimal, bobot_grade)
# Urutan dari grade tertinggi ke terendah (penting untuk if/elif nanti).
SKALA_GRADE_DEFAULT = [
    ("A", 85, 4.0),
    ("B", 70, 3.0),
    ("C", 55, 2.0),
    ("D", 40, 1.0),
    ("E", 0, 0.0),
]

# Batas minimal kehadiran (persen) agar boleh ikut UAS
BATAS_HADIR_DEFAULT = 75              # int

# Batas paket Free
BATAS_FREE_SEMESTER = 2               # int
BATAS_FREE_MATKUL = 6                 # int per semester

# Nilai yang boleh dipakai di tabel kehadiran
DAFTAR_STATUS_HADIR = ("hadir", "izin", "sakit", "alpa")  # tuple (tidak boleh berubah)

# Nama paket
PAKET_FREE = "free"
PAKET_PREMIUM = "premium"

# Bobot grade tertinggi yang boleh diisi di Pengaturan (skala 4.0)
BOBOT_GRADE_MAKSIMAL = 4.0            # float