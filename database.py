# database.py
# Mengurus koneksi SQLite dan pembuatan tabel.
# Memakai modul bawaan sqlite3 (tanpa ORM) agar SQL-nya terlihat jelas.

import json
import sqlite3

import konfigurasi


def buka_koneksi():
    """Membuka koneksi ke database dan mengembalikannya."""
    koneksi = sqlite3.connect(konfigurasi.NAMA_DATABASE)
    # row_factory membuat hasil query bisa dibaca per nama kolom: baris["nama"]
    koneksi.row_factory = sqlite3.Row
    # SQLite secara bawaan MEMATIKAN foreign key, jadi kita nyalakan manual
    koneksi.execute("PRAGMA foreign_keys = ON")
    return koneksi


def buat_tabel():
    """Membuat semua tabel jika belum ada."""
    koneksi = buka_koneksi()
    koneksi.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            paket TEXT NOT NULL DEFAULT 'free'
        );

        CREATE TABLE IF NOT EXISTS pengaturan (
            user_id INTEGER PRIMARY KEY,
            batas_hadir_persen INTEGER NOT NULL,
            skala_grade_json TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS semester (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nama TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS matkul (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester_id INTEGER NOT NULL,
            nama TEXT NOT NULL,
            sks INTEGER NOT NULL,
            total_pertemuan INTEGER NOT NULL,
            target_grade TEXT,
            FOREIGN KEY (semester_id) REFERENCES semester(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS komponen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matkul_id INTEGER NOT NULL,
            nama TEXT NOT NULL,
            bobot REAL NOT NULL,
            nilai REAL,
            FOREIGN KEY (matkul_id) REFERENCES matkul(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kehadiran (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matkul_id INTEGER NOT NULL,
            pertemuan_ke INTEGER NOT NULL,
            status TEXT NOT NULL,
            UNIQUE (matkul_id, pertemuan_ke),
            FOREIGN KEY (matkul_id) REFERENCES matkul(id) ON DELETE CASCADE
        );
    """)
    koneksi.commit()
    koneksi.close()


def buat_pengaturan_default(koneksi, user_id):
    """Dipanggil saat register: mengisi pengaturan awal pengguna baru."""
    skala_json = json.dumps(konfigurasi.SKALA_GRADE_DEFAULT)
    koneksi.execute(
        "INSERT INTO pengaturan (user_id, batas_hadir_persen, skala_grade_json) "
        "VALUES (?, ?, ?)",
        (user_id, konfigurasi.BATAS_HADIR_DEFAULT, skala_json),
    )


def baca_pengaturan(koneksi, user_id):
    """Mengembalikan tuple (skala_grade, batas_hadir) milik pengguna."""
    baris = koneksi.execute(
        "SELECT batas_hadir_persen, skala_grade_json FROM pengaturan "
        "WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    # JSON mengubah tuple menjadi list, jadi kita ubah lagi ke tuple
    skala = [tuple(item) for item in json.loads(baris["skala_grade_json"])]
    return skala, baris["batas_hadir_persen"]

def simpan_pengaturan(koneksi, user_id, batas_hadir, skala):
    """Menyimpan pengaturan pengguna (skala diubah menjadi teks JSON)."""
    koneksi.execute(
        "UPDATE pengaturan SET batas_hadir_persen = ?, skala_grade_json = ? "
        "WHERE user_id = ?",
        (batas_hadir, json.dumps(skala), user_id),
    )
    koneksi.commit()

if __name__ == "__main__":
    buat_tabel()
    print("Tabel berhasil dibuat di", konfigurasi.NAMA_DATABASE)