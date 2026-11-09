# seed.py
# Mengisi data contoh untuk demo presentasi.
# Jalankan: python seed.py
# Login demo: demo@akademikku.id / demo123

from werkzeug.security import generate_password_hash

import database
import konfigurasi

EMAIL_DEMO = "demo@akademikku.id"
PASSWORD_DEMO = "demo123"


def komponen_standar(tugas, uts, uas):
    """Tiga komponen umum: Tugas 30%, UTS 30%, UAS 40%.
    Nilai None berarti belum keluar."""
    # MATERI: List dan tuple (list of tuple)
    return [("Tugas", 30, tugas), ("UTS", 30, uts), ("UAS", 40, uas)]


# Format tiap mata kuliah:
# (nama, sks, total_pertemuan, target_grade, daftar_komponen, daftar_kehadiran)
SEMESTER_1 = [
    ("Dasar Pemrograman", 3, 16, None, komponen_standar(90, 85, 88), []),
    ("Matematika Diskrit", 3, 16, None, komponen_standar(75, 70, 72), []),
    ("Bahasa Inggris", 2, 16, None, komponen_standar(80, 78, 82), []),
    ("Pengantar TI", 2, 16, None, komponen_standar(60, 55, 58), []),
]

SEMESTER_2 = [
    # Aman: 7 hadir, 1 alpa dari 8 pertemuan (87.5%). Target B -> UAS minimal 62.5
    ("Algoritma", 3, 16, "B", komponen_standar(80, 70, None),
     ["hadir"] * 7 + ["alpa"]),
    # Waspada: 6 hadir, 2 alpa (75%), sisa jatah absen 1
    ("Basis Data", 3, 14, None, komponen_standar(90, 85, None),
     ["hadir"] * 6 + ["alpa"] * 2),
    # Terancam: 4 hadir dari 8 (50%)
    ("Statistika", 2, 16, None, komponen_standar(70, 60, None),
     ["hadir"] * 4 + ["izin", "sakit", "alpa", "alpa"]),
    # Target A mustahil -> "Target tidak tercapai"
    ("Jaringan Komputer", 3, 16, "A", komponen_standar(50, 50, None),
     ["hadir"] * 4),
    # Sudah final (semua nilai terisi), supaya IPS semester 2 muncul
    ("Pendidikan Pancasila", 2, 16, None, komponen_standar(85, 80, 90), []),
]


def hapus_demo_lama(koneksi):
    # ON DELETE CASCADE: semua data turunan akun demo ikut terhapus
    koneksi.execute("DELETE FROM users WHERE email = ?", (EMAIL_DEMO,))


def buat_user_demo(koneksi):
    hash_password = generate_password_hash(PASSWORD_DEMO)
    cursor = koneksi.execute(
        "INSERT INTO users (nama, email, password_hash, paket) VALUES (?, ?, ?, ?)",
        ("Budi Santoso", EMAIL_DEMO, hash_password, konfigurasi.PAKET_FREE),
    )
    user_id = cursor.lastrowid
    database.buat_pengaturan_default(koneksi, user_id)
    return user_id


def simpan_matkul(koneksi, semester_id, data_matkul):
    nama, sks, pertemuan, target, daftar_komponen, daftar_hadir = data_matkul
    cursor = koneksi.execute(
        "INSERT INTO matkul (semester_id, nama, sks, total_pertemuan, target_grade) "
        "VALUES (?, ?, ?, ?, ?)",
        (semester_id, nama, sks, pertemuan, target),
    )
    matkul_id = cursor.lastrowid

    # MATERI: Perulangan for + tuple unpacking
    for nama_komponen, bobot, nilai in daftar_komponen:
        koneksi.execute(
            "INSERT INTO komponen (matkul_id, nama, bobot, nilai) VALUES (?, ?, ?, ?)",
            (matkul_id, nama_komponen, bobot, nilai),
        )

    # enumerate memberi nomor urut mulai dari 1 (= pertemuan ke-1, ke-2, dst.)
    for pertemuan_ke, status in enumerate(daftar_hadir, start=1):
        koneksi.execute(
            "INSERT INTO kehadiran (matkul_id, pertemuan_ke, status) VALUES (?, ?, ?)",
            (matkul_id, pertemuan_ke, status),
        )


def simpan_semester(koneksi, user_id, nama_semester, daftar_matkul):
    cursor = koneksi.execute(
        "INSERT INTO semester (user_id, nama) VALUES (?, ?)", (user_id, nama_semester)
    )
    for data_matkul in daftar_matkul:
        simpan_matkul(koneksi, cursor.lastrowid, data_matkul)


def isi_data_demo():
    database.buat_tabel()
    koneksi = database.buka_koneksi()
    try:
        hapus_demo_lama(koneksi)
        user_id = buat_user_demo(koneksi)
        simpan_semester(koneksi, user_id, "Semester 1", SEMESTER_1)
        simpan_semester(koneksi, user_id, "Semester 2", SEMESTER_2)
        koneksi.commit()  # semua tersimpan bersamaan, atau tidak sama sekali
    finally:
        koneksi.close()
    print("Data demo siap.")
    print("Login:", EMAIL_DEMO, "/", PASSWORD_DEMO)


if __name__ == "__main__":
    isi_data_demo()