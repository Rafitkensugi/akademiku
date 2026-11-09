# logika.py
# Semua fungsi perhitungan AkademikKu.
# File ini TIDAK tahu soal Flask maupun database, sehingga mudah diuji sendiri.
#
# Format data yang dipakai di seluruh file:
#   komponen = tuple (nama_komponen, bobot, nilai)   -> nilai boleh None
#   skala    = list of tuple (huruf, batas_minimal, bobot_grade)
#   matkul   = tuple (sks, bobot_grade)

import math

import validasi
from validasi import DataTidakValidError


# ============================================================
# BAGIAN 1: NILAI, GRADE, SIMULASI TARGET
# ============================================================
def hitung_total_bobot(daftar_komponen):
    """Menjumlah bobot SEMUA komponen, baik yang sudah maupun belum bernilai."""
    total = 0
    # MATERI: Perulangan for + tuple unpacking
    for nama, bobot, nilai in daftar_komponen:
        total += bobot
    return total


def tentukan_warna_grade(bobot_grade):
    """Warna badge dari bobot grade (4.0 = terbaik)."""
    # MATERI: Seleksi kondisi (if/elif/else)
    if bobot_grade >= 3.5:
        return "hijau"
    elif bobot_grade >= 2.5:
        return "biru"
    elif bobot_grade >= 1.5:
        return "kuning"
    else:
        return "merah"
    
def hitung_total_bobot(daftar_komponen):
    """Menjumlah bobot SEMUA komponen, baik yang sudah maupun belum bernilai."""
    total = 0
    # MATERI: Perulangan for + tuple unpacking
    for nama, bobot, nilai in daftar_komponen:
        total += bobot
    return total


def tentukan_warna_grade(bobot_grade):
    """Warna badge dari bobot grade (4.0 = terbaik)."""
    # MATERI: Seleksi kondisi (if/elif/else)
    if bobot_grade >= 3.5:
        return "hijau"
    elif bobot_grade >= 2.5:
        return "biru"
    elif bobot_grade >= 1.5:
        return "kuning"
    else:
        return "merah"
    
def hitung_nilai_akhir(daftar_komponen):
    """Menjumlah poin berbobot dari komponen yang SUDAH bernilai.
    Mengembalikan tuple: (total_poin, bobot_terisi)."""
    # MATERI: Tipe data dan variabel (float untuk nilai, int/float untuk bobot)
    total_poin = 0.0
    bobot_terisi = 0

    # MATERI: Perulangan for + list of tuple (tuple unpacking)
    for nama, bobot, nilai in daftar_komponen:
        # MATERI: Seleksi kondisi (lewati komponen yang belum keluar)
        if nilai is not None:
            # MATERI: Operator (rumus bobot nilai: bobot x nilai / 100)
            total_poin += bobot * nilai / 100
            bobot_terisi += bobot

    # MATERI: Fungsi dengan return lebih dari satu nilai (tuple) + pembulatan
    return round(total_poin, 2), bobot_terisi


def tentukan_grade(nilai, skala):
    """Menentukan grade dari nilai. Mengembalikan (huruf, bobot_grade)."""
    # MATERI: Seleksi kondisi (if) di dalam perulangan.
    # Skala urut dari tertinggi, jadi yang pertama cocok adalah grade-nya.
    for huruf, batas_minimal, bobot_grade in skala:
        if nilai >= batas_minimal:
            return huruf, bobot_grade
    # Cadangan jika skala tidak punya batas 0
    return skala[-1][0], skala[-1][2]


def cari_batas_grade(huruf_target, skala):
    """Mencari batas nilai minimal dari sebuah grade, misalnya 'A' -> 85."""
    for huruf, batas_minimal, bobot_grade in skala:
        if huruf == huruf_target:
            return batas_minimal
    raise DataTidakValidError(f"Grade {huruf_target} tidak ada di skala.")


def nilai_minimal_komponen(daftar_komponen, target_nilai, nama_komponen_target):
    """Rumus mundur: berapa nilai minimal komponen target (misal UAS)
    agar nilai akhir mencapai target_nilai.
    Mengembalikan tuple (nilai_minimal, pesan). Jika mustahil, nilai_minimal = None."""
    poin_lain = 0.0
    bobot_target = None

    for nama, bobot, nilai in daftar_komponen:
        if nama == nama_komponen_target:
            bobot_target = bobot
        elif nilai is not None:
            poin_lain += bobot * nilai / 100

    if bobot_target is None:
        raise DataTidakValidError(f"Komponen {nama_komponen_target} tidak ditemukan.")

    # Rumus: (target - poin_lain) / bobot_target x 100
    # MATERI: Eksepsi (pembagian aman dari nol lewat validasi.bagi_aman)
    perlu = validasi.bagi_aman(target_nilai - poin_lain, bobot_target, "Bobot") * 100
    perlu = round(max(perlu, 0), 2)  # tidak mungkin butuh nilai negatif

    # MATERI: Seleksi kondisi (status target nilai)
    if perlu > 100:
        return None, "Target tidak tercapai"
    return perlu, f"Anda butuh minimal {perlu:g} di {nama_komponen_target}."


# ============================================================
# BAGIAN 2: KEHADIRAN
# ============================================================

def rekap_kehadiran(daftar_status):
    """Menghitung jumlah tiap status. Mengembalikan (hadir, izin, sakit, alpa)."""
    hadir = 0
    izin = 0
    sakit = 0
    alpa = 0
    # MATERI: Perulangan for + if/elif/else
    for status in daftar_status:
        if status == "hadir":
            hadir += 1
        elif status == "izin":
            izin += 1
        elif status == "sakit":
            sakit += 1
        else:
            alpa += 1
    return hadir, izin, sakit, alpa


def hitung_persen_hadir(jumlah_hadir, jumlah_pertemuan):
    """Persentase hadir dari pertemuan yang sudah tercatat."""
    if jumlah_pertemuan == 0:
        return 100.0  # belum ada pertemuan, anggap aman
    persen = validasi.bagi_aman(jumlah_hadir, jumlah_pertemuan, "Jumlah pertemuan") * 100
    return round(persen, 2)


def hitung_sisa_jatah_absen(total_pertemuan, batas_persen, jumlah_tidak_hadir):
    """Berapa kali lagi boleh tidak hadir. Mengembalikan (sisa, jatah_maksimal)."""
    # math.ceil membulatkan ke atas: 10.5 pertemuan berarti harus hadir 11
    minimal_hadir = math.ceil(total_pertemuan * batas_persen / 100)
    jatah_maksimal = total_pertemuan - minimal_hadir
    sisa = max(jatah_maksimal - jumlah_tidak_hadir, 0)
    return sisa, jatah_maksimal


def status_kehadiran(persen, batas):
    """Aman / Waspada / Terancam. Waspada = kurang dari 10 poin di atas batas."""
    # MATERI: Seleksi kondisi (if/elif/else)
    if persen < batas:
        return "Terancam"
    elif persen < batas + 10:
        return "Waspada"
    else:
        return "Aman"


def boleh_ikut_uas(persen, batas):
    """Mengembalikan bool: True jika kehadiran memenuhi syarat UAS."""
    # MATERI: Tipe data bool
    return persen >= batas

def warna_status(status):
    """Status kehadiran -> warna badge."""
    # MATERI: Seleksi kondisi (if/elif/else)
    if status == "Aman":
        return "hijau"
    elif status == "Waspada":
        return "kuning"
    else:
        return "merah"


def pesan_peringatan(status, sisa):
    """Kalimat peringatan untuk pengguna."""
    # MATERI: Seleksi kondisi + f-string
    if status == "Terancam":
        return "Kehadiran di bawah batas! Kamu terancam tidak boleh ikut UAS."
    elif status == "Waspada":
        return f"Hati-hati, sisa jatah absenmu {sisa} kali lagi."
    else:
        return "Kehadiran aman. Pertahankan!"


def ambil_batas(baris_skala):
    """Mengambil batas nilai dari satu tuple skala (dipakai untuk mengurutkan)."""
    return baris_skala[1]


def urutkan_skala(skala):
    """Mengurutkan skala dari batas tertinggi ke terendah
    (syarat agar tentukan_grade bekerja benar)."""
    # MATERI: List (sort dengan key). key = fungsi yang menentukan dasar urutan.
    skala_baru = list(skala)
    skala_baru.sort(key=ambil_batas, reverse=True)
    return skala_baru


# ============================================================
# BAGIAN 3: IPS DAN IPK
# ============================================================

def hitung_ips(daftar_matkul):
    """IPS = jumlah(bobot_grade x SKS) / jumlah SKS.
    daftar_matkul: list of tuple (sks, bobot_grade)."""
    total_mutu = 0.0
    total_sks = 0
    # MATERI: Perulangan for
    for sks, bobot_grade in daftar_matkul:
        total_mutu += bobot_grade * sks
        total_sks += sks
    if total_sks == 0:
        return 0.0
    return round(validasi.bagi_aman(total_mutu, total_sks, "Total SKS"), 2)


def hitung_ipk(semua_semester):
    """IPK dari semua semester. semua_semester: list berisi daftar_matkul.
    Catatan: IPK BUKAN rata-rata IPS, karena SKS tiap semester berbeda."""
    total_mutu = 0.0
    total_sks = 0
    # MATERI: Perulangan bersarang (semester -> matkul)
    for daftar_matkul in semua_semester:
        for sks, bobot_grade in daftar_matkul:
            total_mutu += bobot_grade * sks
            total_sks += sks
    if total_sks == 0:
        return 0.0
    return round(validasi.bagi_aman(total_mutu, total_sks, "Total SKS"), 2)

def warna_status(status):
    """Status kehadiran -> warna badge."""
    # MATERI: Seleksi kondisi (if/elif/else)
    if status == "Aman":
        return "hijau"
    elif status == "Waspada":
        return "kuning"
    else:
        return "merah"


def pesan_peringatan(status, sisa):
    """Kalimat peringatan untuk pengguna."""
    # MATERI: Seleksi kondisi + f-string
    if status == "Terancam":
        return "Kehadiran di bawah batas! Kamu terancam tidak boleh ikut UAS."
    elif status == "Waspada":
        return f"Hati-hati, sisa jatah absenmu {sisa} kali lagi."
    else:
        return "Kehadiran aman. Pertahankan!"


def ambil_batas(baris_skala):
    """Mengambil batas nilai dari satu tuple skala (dipakai untuk mengurutkan)."""
    return baris_skala[1]


def urutkan_skala(skala):
    """Mengurutkan skala dari batas tertinggi ke terendah
    (syarat agar tentukan_grade bekerja benar)."""
    # MATERI: List (sort dengan key). key = fungsi yang menentukan dasar urutan.
    skala_baru = list(skala)
    skala_baru.sort(key=ambil_batas, reverse=True)
    return skala_baru


# ============================================================
# CONTOH UJI (jalankan: python logika.py)
# ============================================================

if __name__ == "__main__":
    skala = [("A", 85, 4.0), ("B", 70, 3.0), ("C", 55, 2.0), ("D", 40, 1.0), ("E", 0, 0.0)]
    komponen = [("Tugas", 30, 80.0), ("UTS", 30, 70.0), ("UAS", 40, None)]

    print("1. hitung_nilai_akhir:", hitung_nilai_akhir(komponen))
    assert hitung_nilai_akhir(komponen) == (45.0, 60)

    print("2. tentukan_grade:", tentukan_grade(88, skala), tentukan_grade(72, skala), tentukan_grade(45, skala))
    assert tentukan_grade(88, skala) == ("A", 4.0)
    assert tentukan_grade(45, skala) == ("D", 1.0)

    print("3. cari_batas_grade A:", cari_batas_grade("A", skala))
    assert cari_batas_grade("A", skala) == 85

    print("4. target B:", nilai_minimal_komponen(komponen, 70, "UAS"))
    print("   target A:", nilai_minimal_komponen(komponen, 85, "UAS"))
    assert nilai_minimal_komponen(komponen, 70, "UAS")[0] == 62.5
    kurang = [("Tugas", 30, 50.0), ("UTS", 30, 50.0), ("UAS", 40, None)]
    print("   mustahil:", nilai_minimal_komponen(kurang, 85, "UAS"))
    assert nilai_minimal_komponen(kurang, 85, "UAS")[0] is None

    print("5. rekap_kehadiran:", rekap_kehadiran(["hadir", "hadir", "izin", "alpa", "sakit", "hadir"]))
    assert rekap_kehadiran(["hadir", "hadir", "izin", "alpa", "sakit", "hadir"]) == (3, 1, 1, 1)

    print("6. hitung_persen_hadir(10, 12):", hitung_persen_hadir(10, 12))
    assert hitung_persen_hadir(10, 12) == 83.33

    print("7. hitung_sisa_jatah_absen(16, 75, 3):", hitung_sisa_jatah_absen(16, 75, 3))
    assert hitung_sisa_jatah_absen(16, 75, 3) == (1, 4)

    print("8. status_kehadiran:", status_kehadiran(90, 75), status_kehadiran(80, 75), status_kehadiran(70, 75))
    assert status_kehadiran(90, 75) == "Aman"
    assert status_kehadiran(80, 75) == "Waspada"
    assert status_kehadiran(70, 75) == "Terancam"

    print("9. boleh_ikut_uas:", boleh_ikut_uas(80, 75), boleh_ikut_uas(70, 75))

    smt1 = [(3, 4.0), (2, 3.0), (3, 2.0)]
    smt2 = [(4, 4.0)]
    print("10. hitung_ips:", hitung_ips(smt1))
    assert hitung_ips(smt1) == 3.0

    print("11. hitung_ipk:", hitung_ipk([smt1, smt2]))
    assert hitung_ipk([smt1, smt2]) == 3.33

    acak = [("C", 55, 2.0), ("A", 85, 4.0), ("B", 70, 3.0)]
    print("12. urutkan_skala:", urutkan_skala(acak))
    assert urutkan_skala(acak)[0][0] == "A"

    print("13. warna & pesan:", warna_status("Waspada"), "|", pesan_peringatan("Terancam", 0))
    assert warna_status("Aman") == "hijau"
    assert warna_status("Terancam") == "merah"
    
    print("\nSemua uji lolos!")