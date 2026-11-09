# validasi.py
# Fungsi pengecekan input + custom exception.
# Prinsip: fungsi validasi MELEMPAR error bila data salah,
# lalu route di app.py MENANGKAPNYA dengan try/except.

import konfigurasi


# MATERI: Modul dan eksepsi (custom exception)
class DataTidakValidError(Exception):
    """Error khusus AkademikKu. Isinya pesan ramah untuk pengguna."""
    pass


def bersihkan_nama(teks, nama_isian="Nama"):
    """Merapikan teks nama: buang spasi berlebih dan huruf awal kapital."""
    # MATERI: String (.strip, .title, f-string)
    bersih = teks.strip().title()
    if bersih == "":
        raise DataTidakValidError(f"{nama_isian} tidak boleh kosong.")
    return bersih


def validasi_email(teks):
    """Email dibuat huruf kecil dan dicek bentuk dasarnya."""
    email = teks.strip().lower()
    if "@" not in email or "." not in email:
        raise DataTidakValidError("Format email tidak valid.")
    return email


def validasi_password(teks):
    if len(teks) < 6:
        raise DataTidakValidError("Password minimal 6 karakter.")
    return teks


def ubah_ke_angka(teks, nama_isian="Nilai"):
    """Mengubah teks menjadi float; gagal jika bukan angka."""
    # MATERI: Eksepsi (try/except ValueError)
    try:
        return float(str(teks).strip().replace(",", "."))
    except ValueError:
        raise DataTidakValidError(f"{nama_isian} harus berupa angka.")


def validasi_nilai(teks):
    """Nilai harus angka 0-100."""
    nilai = ubah_ke_angka(teks, "Nilai")
    if nilai < 0 or nilai > 100:
        raise DataTidakValidError("Nilai harus di antara 0 sampai 100.")
    return nilai


def validasi_nilai_opsional(teks):
    """Nilai boleh dikosongkan (belum keluar). Kosong -> None."""
    if teks is None or str(teks).strip() == "":
        return None
    return validasi_nilai(teks)


def validasi_bobot(teks):
    """Bobot harus lebih dari 0 dan maksimal 100."""
    bobot = ubah_ke_angka(teks, "Bobot")
    if bobot <= 0 or bobot > 100:
        raise DataTidakValidError("Bobot harus lebih dari 0 dan maksimal 100.")
    return bobot


def validasi_bilangan_bulat(teks, nama_isian):
    """Untuk SKS dan total pertemuan: harus bilangan bulat > 0."""
    try:
        angka = int(str(teks).strip())
    except ValueError:
        raise DataTidakValidError(f"{nama_isian} harus berupa bilangan bulat.")
    if angka <= 0:
        raise DataTidakValidError(f"{nama_isian} harus lebih dari 0.")
    return angka


def validasi_total_bobot(daftar_komponen):
    """Total bobot semua komponen harus tepat 100%."""
    total = 0
    # MATERI: Perulangan for + tuple unpacking
    for nama, bobot, nilai in daftar_komponen:
        total += bobot
    if round(total, 2) != 100:
        raise DataTidakValidError(
            f"Total bobot komponen harus 100%, saat ini {total:g}%."
        )
    return total


def validasi_pertemuan(pertemuan_ke, total_pertemuan):
    """Pertemuan ke-N tidak boleh melebihi total pertemuan."""
    if pertemuan_ke < 1 or pertemuan_ke > total_pertemuan:
        raise DataTidakValidError(
            f"Pertemuan ke-{pertemuan_ke} tidak ada. "
            f"Mata kuliah ini hanya {total_pertemuan} pertemuan."
        )
    return pertemuan_ke


def validasi_status_hadir(status):
    if status not in konfigurasi.DAFTAR_STATUS_HADIR:
        raise DataTidakValidError("Status kehadiran tidak dikenal.")
    return status


def validasi_batas_paket(jumlah_sekarang, batas, nama_item, paket):
    """Paket Free dibatasi; Premium bebas."""
    if paket == konfigurasi.PAKET_PREMIUM:
        return True
    if jumlah_sekarang >= batas:
        raise DataTidakValidError(
            f"Paket Free hanya boleh {batas} {nama_item}. "
            "Upgrade ke Premium untuk menambah lebih banyak."
        )
    return True


def bagi_aman(pembilang, penyebut, nama_penyebut="Pembagi"):
    """Pembagian yang aman dari pembagian dengan nol."""
    try:
        return pembilang / penyebut
    except ZeroDivisionError:
        raise DataTidakValidError(f"{nama_penyebut} tidak boleh nol.")

def bersihkan_teks(teks, nama_isian="Isian"):
    """Hanya membuang spasi di pinggir. Huruf besar/kecil dibiarkan
    (agar 'UAS' tidak berubah menjadi 'Uas')."""
    # MATERI: String (.strip, f-string)
    bersih = teks.strip()
    if bersih == "":
        raise DataTidakValidError(f"{nama_isian} tidak boleh kosong.")
    return bersih


def validasi_bobot_tidak_lebih(total_bobot):
    """Saat menambah/mengubah komponen, total bobot tidak boleh melewati 100%."""
    if round(total_bobot, 2) > 100:
        raise DataTidakValidError(
            f"Total bobot menjadi {total_bobot:g}%, tidak boleh lebih dari 100%."
        )
    return total_bobot

def validasi_batas_hadir(teks):
    """Batas kehadiran: bilangan bulat 1-100."""
    batas = validasi_bilangan_bulat(teks, "Batas kehadiran")
    if batas > 100:
        raise DataTidakValidError("Batas kehadiran maksimal 100%.")
    return batas


def validasi_bobot_grade(teks):
    """Bobot grade (misal 4.0) antara 0 sampai batas di konfigurasi."""
    bobot = ubah_ke_angka(teks, "Bobot grade")
    if bobot < 0 or bobot > konfigurasi.BOBOT_GRADE_MAKSIMAL:
        raise DataTidakValidError(
            f"Bobot grade harus antara 0 sampai {konfigurasi.BOBOT_GRADE_MAKSIMAL:g}."
        )
    return bobot


def validasi_skala_grade(skala):
    """skala: list of tuple (huruf, batas, bobot_grade)."""
    if len(skala) < 2:
        raise DataTidakValidError("Skala grade minimal terdiri dari 2 grade.")
    daftar_huruf = []
    daftar_batas = []
    # MATERI: Perulangan for + list + tuple unpacking
    for huruf, batas, bobot_grade in skala:
        if huruf in daftar_huruf:
            raise DataTidakValidError(f"Grade {huruf} muncul dua kali.")
        if batas in daftar_batas:
            raise DataTidakValidError(f"Batas nilai {batas:g} dipakai dua grade.")
        daftar_huruf.append(huruf)
        daftar_batas.append(batas)
    if 0 not in daftar_batas:
        raise DataTidakValidError("Harus ada satu grade dengan batas nilai 0.")
    return skala