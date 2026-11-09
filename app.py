# app.py
# Inisialisasi Flask dan semua route AkademikKu.
# Prinsip: route hanya "mengatur lalu lintas".
#   cek input         -> validasi.py
#   hitungan          -> logika.py
#   simpan/ambil data -> database.py / SQL berparameter

import csv
import io
import sqlite3

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import database
import konfigurasi
import logika
import validasi
from validasi import DataTidakValidError

app = Flask(__name__)
app.secret_key = konfigurasi.KUNCI_RAHASIA

# Membuat tabel saat aplikasi dimulai (aman, memakai IF NOT EXISTS)
database.buat_tabel()


# ============================================================
# BAGIAN 1: FUNGSI BANTU LOGIN DAN PENGGUNA
# ============================================================

def ambil_user_id():
    """Mengembalikan id pengguna yang sedang login, atau None."""
    return session.get("user_id")


def alihkan_ke_login():
    flash("Silakan login terlebih dahulu.", "error")
    return redirect(url_for("login"))


def ambil_user(user_id):
    koneksi = database.buka_koneksi()
    user = koneksi.execute(
        "SELECT id, nama, email, paket FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    koneksi.close()
    return user


def simpan_user(nama, email, hash_password):
    """Menyimpan user baru + pengaturan defaultnya dalam SATU transaksi."""
    koneksi = database.buka_koneksi()
    try:
        cursor = koneksi.execute(
            "INSERT INTO users (nama, email, password_hash, paket) VALUES (?, ?, ?, ?)",
            (nama, email, hash_password, konfigurasi.PAKET_FREE),
        )
        user_id = cursor.lastrowid
        database.buat_pengaturan_default(koneksi, user_id)
        koneksi.commit()
        return user_id
    # MATERI: Eksepsi (email UNIQUE dilanggar -> IntegrityError)
    except sqlite3.IntegrityError:
        raise DataTidakValidError("Email sudah terdaftar. Silakan login.")
    finally:
        koneksi.close()


def proses_register(form):
    """Memvalidasi form register lalu menyimpannya. Mengembalikan (user_id, nama)."""
    # MATERI: String (.strip, .title, .lower lewat fungsi validasi)
    nama = validasi.bersihkan_nama(form.get("nama", ""))
    email = validasi.validasi_email(form.get("email", ""))
    password = validasi.validasi_password(form.get("password", ""))

    if password != form.get("konfirmasi", ""):
        raise DataTidakValidError("Konfirmasi password tidak sama.")

    hash_password = generate_password_hash(password)
    user_id = simpan_user(nama, email, hash_password)
    return user_id, nama


def proses_login(form):
    """Memeriksa email + password. Mengembalikan baris user, atau melempar error."""
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    koneksi = database.buka_koneksi()
    user = koneksi.execute(
        "SELECT id, nama, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    koneksi.close()

    # MATERI: Seleksi kondisi (satu pesan yang sama untuk dua kemungkinan salah)
    if user is None or not check_password_hash(user["password_hash"], password):
        raise DataTidakValidError("Email atau password salah.")
    return user


def mulai_session(user_id, nama):
    session.clear()
    session["user_id"] = user_id
    session["nama"] = nama


# ============================================================
# BAGIAN 2: FUNGSI BANTU KEPEMILIKAN DATA
# Setiap data dicek lewat JOIN sampai ke semester.user_id.
# Bukan milik pengguna yang login -> 404 (seolah tidak ada).
# ============================================================

def ambil_semester_milik(koneksi, semester_id, user_id):
    semester = koneksi.execute(
        "SELECT id, nama FROM semester WHERE id = ? AND user_id = ?",
        (semester_id, user_id),
    ).fetchone()
    if semester is None:
        abort(404)
    return semester


def ambil_matkul_milik(koneksi, matkul_id, user_id):
    matkul = koneksi.execute(
        "SELECT m.* FROM matkul m "
        "JOIN semester s ON m.semester_id = s.id "
        "WHERE m.id = ? AND s.user_id = ?",
        (matkul_id, user_id),
    ).fetchone()
    if matkul is None:
        abort(404)
    return matkul


def ambil_komponen_milik(koneksi, komponen_id, user_id):
    komponen = koneksi.execute(
        "SELECT k.* FROM komponen k "
        "JOIN matkul m ON k.matkul_id = m.id "
        "JOIN semester s ON m.semester_id = s.id "
        "WHERE k.id = ? AND s.user_id = ?",
        (komponen_id, user_id),
    ).fetchone()
    if komponen is None:
        abort(404)
    return komponen


# ============================================================
# BAGIAN 3: FUNGSI BANTU PENGOLAHAN DATA
# ============================================================

def hitung_jumlah(koneksi, sql, parameter):
    """Menjalankan query COUNT(*) dan mengembalikan angkanya."""
    return koneksi.execute(sql, parameter).fetchone()[0]


def ambil_komponen_matkul(koneksi, matkul_id):
    return koneksi.execute(
        "SELECT id, nama, bobot, nilai FROM komponen WHERE matkul_id = ? ORDER BY id",
        (matkul_id,),
    ).fetchall()


def ubah_ke_tuple(baris_komponen):
    """Baris database -> list of tuple (nama, bobot, nilai) untuk logika.py."""
    # MATERI: List dan tuple (list comprehension sederhana)
    return [(k["nama"], k["bobot"], k["nilai"]) for k in baris_komponen]


def ringkas_matkul(koneksi, matkul, skala):
    """Menghitung nilai dan grade satu matkul. Hasil berupa dictionary."""
    daftar = ubah_ke_tuple(ambil_komponen_matkul(koneksi, matkul["id"]))
    poin, bobot_terisi = logika.hitung_nilai_akhir(daftar)
    huruf, bobot_grade = logika.tentukan_grade(poin, skala)
    return {
        "matkul": matkul,
        "nilai": poin,
        "huruf": huruf,
        "bobot_grade": bobot_grade,
        "warna": logika.tentukan_warna_grade(bobot_grade),
        "bobot_terisi": bobot_terisi,
        "final": round(bobot_terisi, 2) == 100,  # semua komponen sudah bernilai
    }


def kumpulkan_data_semester(koneksi, user_id, skala):
    """Mengembalikan list of tuple (semester, daftar_ringkasan_matkul)."""
    data = []
    daftar_semester = koneksi.execute(
        "SELECT id, nama FROM semester WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    # MATERI: Perulangan for + list dan tuple
    for semester in daftar_semester:
        daftar_matkul = koneksi.execute(
            "SELECT * FROM matkul WHERE semester_id = ? ORDER BY id", (semester["id"],)
        ).fetchall()
        ringkasan = [ringkas_matkul(koneksi, m, skala) for m in daftar_matkul]
        data.append((semester, ringkasan))
    return data


def cek_nama_komponen_unik(daftar, nama):
    """Nama komponen tidak boleh kembar dalam satu matkul."""
    for nama_ada, bobot, nilai in daftar:
        if nama_ada.lower() == nama.lower():
            raise DataTidakValidError(f"Komponen {nama} sudah ada di mata kuliah ini.")


def cek_total_pertemuan_baru(koneksi, matkul_id, total_baru):
    """Total pertemuan tidak boleh lebih kecil dari pertemuan yang sudah dicatat."""
    terbesar = koneksi.execute(
        "SELECT MAX(pertemuan_ke) AS maks FROM kehadiran WHERE matkul_id = ?",
        (matkul_id,),
    ).fetchone()["maks"]
    if terbesar is not None and total_baru < terbesar:
        raise DataTidakValidError(
            f"Kehadiran sudah tercatat sampai pertemuan ke-{terbesar}. "
            "Total pertemuan tidak boleh lebih kecil."
        )


# ============================================================
# BAGIAN 4: ROUTE LANDING DAN AUTENTIKASI
# ============================================================

@app.route("/")
def landing():
    if ambil_user_id() is not None:
        return redirect(url_for("dashboard"))
    return render_template(
        "landing.html",
        batas_semester=konfigurasi.BATAS_FREE_SEMESTER,
        batas_matkul=konfigurasi.BATAS_FREE_MATKUL,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if ambil_user_id() is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        # MATERI: Eksepsi (try/except menangkap error ramah dari validasi)
        try:
            user_id, nama = proses_register(request.form)
            mulai_session(user_id, nama)
            flash(f"Akun berhasil dibuat. Selamat datang, {nama}!", "sukses")
            return redirect(url_for("dashboard"))
        except DataTidakValidError as error:
            flash(str(error), "error")
            return render_template("register.html", isian=request.form)

    return render_template("register.html", isian={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if ambil_user_id() is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        try:
            user = proses_login(request.form)
            mulai_session(user["id"], user["nama"])
            flash(f"Selamat datang kembali, {user['nama']}!", "sukses")
            return redirect(url_for("dashboard"))
        except DataTidakValidError as error:
            flash(str(error), "error")
            return render_template("login.html", isian=request.form)

    return render_template("login.html", isian={})


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda sudah keluar. Sampai jumpa!", "sukses")
    return redirect(url_for("landing"))


# ===== BAGIAN 2 DITEMPEL TEPAT DI BAWAH GARIS INI =====

# ============================================================
# BAGIAN 5: FUNGSI BANTU SIMULASI TARGET
# ============================================================

def hitung_komponen_belum_keluar(daftar, nama_target):
    """Berapa komponen LAIN yang nilainya belum keluar (dihitung 0 oleh rumus)."""
    jumlah = 0
    for nama, bobot, nilai in daftar:
        if nama != nama_target and nilai is None:
            jumlah += 1
    return jumlah


def buat_tabel_target(daftar, skala, nama_target):
    """Nilai minimal untuk SETIAP grade. Hasil: list of tuple (huruf, batas, perlu)."""
    baris = []
    # MATERI: Perulangan for + list of tuple
    for huruf, batas, bobot_grade in skala:
        perlu, pesan = logika.nilai_minimal_komponen(daftar, batas, nama_target)
        baris.append((huruf, batas, perlu))
    return baris


def proses_simulasi(koneksi, matkul, skala, form):
    """Menghitung simulasi, menyimpan target_grade, mengembalikan dictionary."""
    daftar = ubah_ke_tuple(ambil_komponen_matkul(koneksi, matkul["id"]))
    validasi.validasi_total_bobot(daftar)  # simulasi hanya masuk akal jika bobot = 100%

    nama_target = form.get("komponen", "")
    huruf = form.get("grade", "")
    batas = logika.cari_batas_grade(huruf, skala)
    nilai_perlu, pesan = logika.nilai_minimal_komponen(daftar, batas, nama_target)

    koneksi.execute("UPDATE matkul SET target_grade = ? WHERE id = ?", (huruf, matkul["id"]))
    koneksi.commit()
    return {
        "nama_target": nama_target, "huruf": huruf, "batas": batas,
        "nilai_perlu": nilai_perlu, "pesan": pesan,
        "tabel": buat_tabel_target(daftar, skala, nama_target),
        "belum_keluar": hitung_komponen_belum_keluar(daftar, nama_target),
    }


# ============================================================
# BAGIAN 6: FUNGSI BANTU KEHADIRAN
# ============================================================

def ambil_catatan_kehadiran(koneksi, matkul_id):
    return koneksi.execute(
        "SELECT pertemuan_ke, status FROM kehadiran "
        "WHERE matkul_id = ? ORDER BY pertemuan_ke",
        (matkul_id,),
    ).fetchall()


def ringkas_kehadiran(koneksi, matkul, batas_hadir):
    """Semua angka kehadiran satu matkul, dikemas dalam dictionary."""
    catatan = ambil_catatan_kehadiran(koneksi, matkul["id"])
    # MATERI: List (list comprehension sederhana)
    daftar_status = [c["status"] for c in catatan]
    # MATERI: Fungsi yang mengembalikan tuple (tuple unpacking)
    hadir, izin, sakit, alpa = logika.rekap_kehadiran(daftar_status)
    tercatat = len(daftar_status)
    persen = logika.hitung_persen_hadir(hadir, tercatat)
    status = logika.status_kehadiran(persen, batas_hadir)
    sisa, jatah = logika.hitung_sisa_jatah_absen(
        matkul["total_pertemuan"], batas_hadir, tercatat - hadir
    )
    return {
        "catatan": catatan, "hadir": hadir, "izin": izin, "sakit": sakit,
        "alpa": alpa, "tercatat": tercatat, "persen": persen, "status": status,
        "warna": logika.warna_status(status),
        "pesan": logika.pesan_peringatan(status, sisa),
        "sisa": sisa, "jatah": jatah,
        "boleh_uas": logika.boleh_ikut_uas(persen, batas_hadir),
    }


def tambah_info_hadir(koneksi, data, batas_hadir):
    """Menempelkan info kehadiran ke setiap ringkasan matkul (untuk dashboard)."""
    # MATERI: Perulangan bersarang (semester -> matkul)
    for semester, ringkasan in data:
        for r in ringkasan:
            r["kehadiran"] = ringkas_kehadiran(koneksi, r["matkul"], batas_hadir)


# ============================================================
# BAGIAN 7: FUNGSI BANTU IPS / IPK DAN DASHBOARD
# ============================================================

def ambil_sks_grade(ringkasan):
    """Daftar tuple (sks, bobot_grade) dari matkul yang sudah FINAL saja."""
    hasil = []
    for r in ringkasan:
        if r["final"]:
            hasil.append((r["matkul"]["sks"], r["bobot_grade"]))
    return hasil


def cari_ips_terakhir(kartu_semester):
    """IPS dari semester terakhir yang punya matkul final."""
    ips_terakhir = 0.0
    nama = "-"
    for semester, ringkasan, ips, jumlah in kartu_semester:
        if jumlah > 0:
            ips_terakhir = ips
            nama = semester["nama"]
    return ips_terakhir, nama


def hitung_tren_ipk(kartu_semester, semua_semester):
    """IPK kumulatif setelah tiap semester (untuk grafik)."""
    label = []
    nilai = []
    for i in range(len(kartu_semester)):
        semester, ringkasan, ips, jumlah = kartu_semester[i]
        if jumlah > 0:
            label.append(semester["nama"])
            # MATERI: List slicing. [:i + 1] = semester pertama sampai ke-i
            nilai.append(logika.hitung_ipk(semua_semester[:i + 1]))
    return label, nilai


def susun_dashboard(data):
    """data: list of (semester, ringkasan). Mengembalikan dictionary untuk template."""
    kartu_semester = []
    semua_semester = []
    jumlah_final = 0
    for semester, ringkasan in data:
        daftar = ambil_sks_grade(ringkasan)
        semua_semester.append(daftar)
        jumlah_final += len(daftar)
        ips = logika.hitung_ips(daftar)
        kartu_semester.append((semester, ringkasan, ips, len(daftar)))

    ips_terakhir, nama_ips = cari_ips_terakhir(kartu_semester)
    tren_label, tren_nilai = hitung_tren_ipk(kartu_semester, semua_semester)
    return {
        "ipk": logika.hitung_ipk(semua_semester), "ips_terakhir": ips_terakhir,
        "nama_ips": nama_ips, "jumlah_final": jumlah_final,
        "kartu_semester": kartu_semester,
        "tren_label": tren_label, "tren_nilai": tren_nilai,
    }


def kumpulkan_peringatan(data):
    """Matkul yang kehadirannya Waspada atau Terancam."""
    daftar = []
    for semester, ringkasan in data:
        for r in ringkasan:
            k = r["kehadiran"]
            if k["status"] != "Aman" and k["tercatat"] > 0:
                daftar.append((r["matkul"]["nama"], r["matkul"]["id"], k))
    return daftar


# ============================================================
# BAGIAN 8: ROUTE DASHBOARD (hanya satu di seluruh file)
# ============================================================

@app.route("/dashboard")
def dashboard():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    user = ambil_user(user_id)
    if user is None:  # akun sudah tidak ada di database
        session.clear()
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        data = kumpulkan_data_semester(koneksi, user_id, skala)
        tambah_info_hadir(koneksi, data, batas_hadir)
    finally:
        koneksi.close()

    return render_template(
        "dashboard.html", user=user, d=susun_dashboard(data),
        peringatan=kumpulkan_peringatan(data),
        # MATERI: Tipe data bool
        premium=(user["paket"] == konfigurasi.PAKET_PREMIUM),
    )


# ============================================================
# BAGIAN 9: ROUTE SEMESTER
# ============================================================

@app.route("/semester")
def halaman_semester():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        data = kumpulkan_data_semester(koneksi, user_id, skala)
    finally:
        koneksi.close()
    return render_template(
        "semester.html", data=data, user=ambil_user(user_id),
        batas_semester=konfigurasi.BATAS_FREE_SEMESTER,
        batas_matkul=konfigurasi.BATAS_FREE_MATKUL,
    )


@app.route("/semester/tambah", methods=["POST"])
def semester_tambah():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        nama = validasi.bersihkan_teks(request.form.get("nama", ""), "Nama semester")
        jumlah = hitung_jumlah(
            koneksi, "SELECT COUNT(*) FROM semester WHERE user_id = ?", (user_id,)
        )
        # Batas paket Free diperiksa di BACKEND, bukan hanya disembunyikan di HTML
        validasi.validasi_batas_paket(
            jumlah, konfigurasi.BATAS_FREE_SEMESTER, "semester", ambil_user(user_id)["paket"]
        )
        koneksi.execute("INSERT INTO semester (user_id, nama) VALUES (?, ?)", (user_id, nama))
        koneksi.commit()
        flash(f"{nama} berhasil ditambahkan.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_semester"))


@app.route("/semester/<int:semester_id>/ubah", methods=["POST"])
def semester_ubah(semester_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_semester_milik(koneksi, semester_id, user_id)
        nama = validasi.bersihkan_teks(request.form.get("nama", ""), "Nama semester")
        koneksi.execute("UPDATE semester SET nama = ? WHERE id = ?", (nama, semester_id))
        koneksi.commit()
        flash("Nama semester diperbarui.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_semester"))


@app.route("/semester/<int:semester_id>/hapus", methods=["POST"])
def semester_hapus(semester_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_semester_milik(koneksi, semester_id, user_id)
        # ON DELETE CASCADE: matkul, komponen, dan kehadiran ikut terhapus
        koneksi.execute("DELETE FROM semester WHERE id = ?", (semester_id,))
        koneksi.commit()
        flash("Semester beserta isinya sudah dihapus.", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_semester"))


# ============================================================
# BAGIAN 10: ROUTE MATA KULIAH
# ============================================================

@app.route("/semester/<int:semester_id>/matkul/tambah", methods=["POST"])
def matkul_tambah(semester_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_semester_milik(koneksi, semester_id, user_id)
        nama = validasi.bersihkan_teks(request.form.get("nama", ""), "Nama mata kuliah")
        sks = validasi.validasi_bilangan_bulat(request.form.get("sks", ""), "SKS")
        pertemuan = validasi.validasi_bilangan_bulat(
            request.form.get("total_pertemuan", ""), "Total pertemuan"
        )
        jumlah = hitung_jumlah(
            koneksi, "SELECT COUNT(*) FROM matkul WHERE semester_id = ?", (semester_id,)
        )
        validasi.validasi_batas_paket(
            jumlah, konfigurasi.BATAS_FREE_MATKUL, "mata kuliah per semester",
            ambil_user(user_id)["paket"],
        )
        koneksi.execute(
            "INSERT INTO matkul (semester_id, nama, sks, total_pertemuan) VALUES (?, ?, ?, ?)",
            (semester_id, nama, sks, pertemuan),
        )
        koneksi.commit()
        flash(f"Mata kuliah {nama} ditambahkan.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_semester"))


@app.route("/matkul/<int:matkul_id>")
def matkul_detail(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        matkul = ambil_matkul_milik(koneksi, matkul_id, user_id)
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        komponen = ambil_komponen_matkul(koneksi, matkul_id)
        ringkasan = ringkas_matkul(koneksi, matkul, skala)
        total_bobot = logika.hitung_total_bobot(ubah_ke_tuple(komponen))
    finally:
        koneksi.close()
    return render_template(
        "matkul_detail.html",
        matkul=matkul, komponen=komponen, r=ringkasan, total_bobot=total_bobot,
    )


@app.route("/matkul/<int:matkul_id>/ubah", methods=["POST"])
def matkul_ubah(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_matkul_milik(koneksi, matkul_id, user_id)
        nama = validasi.bersihkan_teks(request.form.get("nama", ""), "Nama mata kuliah")
        sks = validasi.validasi_bilangan_bulat(request.form.get("sks", ""), "SKS")
        pertemuan = validasi.validasi_bilangan_bulat(
            request.form.get("total_pertemuan", ""), "Total pertemuan"
        )
        cek_total_pertemuan_baru(koneksi, matkul_id, pertemuan)
        koneksi.execute(
            "UPDATE matkul SET nama = ?, sks = ?, total_pertemuan = ? WHERE id = ?",
            (nama, sks, pertemuan, matkul_id),
        )
        koneksi.commit()
        flash("Data mata kuliah diperbarui.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("matkul_detail", matkul_id=matkul_id))


@app.route("/matkul/<int:matkul_id>/hapus", methods=["POST"])
def matkul_hapus(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_matkul_milik(koneksi, matkul_id, user_id)
        koneksi.execute("DELETE FROM matkul WHERE id = ?", (matkul_id,))
        koneksi.commit()
        flash("Mata kuliah dihapus.", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_semester"))


# ============================================================
# BAGIAN 11: ROUTE KOMPONEN NILAI
# ============================================================

@app.route("/matkul/<int:matkul_id>/komponen/tambah", methods=["POST"])
def komponen_tambah(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_matkul_milik(koneksi, matkul_id, user_id)
        nama = validasi.bersihkan_teks(request.form.get("nama", ""), "Nama komponen")
        bobot = validasi.validasi_bobot(request.form.get("bobot", ""))
        nilai = validasi.validasi_nilai_opsional(request.form.get("nilai", ""))

        daftar = ubah_ke_tuple(ambil_komponen_matkul(koneksi, matkul_id))
        cek_nama_komponen_unik(daftar, nama)
        validasi.validasi_bobot_tidak_lebih(logika.hitung_total_bobot(daftar) + bobot)

        koneksi.execute(
            "INSERT INTO komponen (matkul_id, nama, bobot, nilai) VALUES (?, ?, ?, ?)",
            (matkul_id, nama, bobot, nilai),
        )
        koneksi.commit()
        flash(f"Komponen {nama} ditambahkan.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("matkul_detail", matkul_id=matkul_id))


@app.route("/komponen/<int:komponen_id>/ubah", methods=["POST"])
def komponen_ubah(komponen_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        komponen = ambil_komponen_milik(koneksi, komponen_id, user_id)
        matkul_id = komponen["matkul_id"]
        try:
            bobot = validasi.validasi_bobot(request.form.get("bobot", ""))
            nilai = validasi.validasi_nilai_opsional(request.form.get("nilai", ""))

            daftar = ubah_ke_tuple(ambil_komponen_matkul(koneksi, matkul_id))
            # total semua - bobot lama + bobot baru
            total_baru = logika.hitung_total_bobot(daftar) - komponen["bobot"] + bobot
            validasi.validasi_bobot_tidak_lebih(total_baru)

            koneksi.execute(
                "UPDATE komponen SET bobot = ?, nilai = ? WHERE id = ?",
                (bobot, nilai, komponen_id),
            )
            koneksi.commit()
            flash(f"Komponen {komponen['nama']} diperbarui.", "sukses")
        except DataTidakValidError as error:
            flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("matkul_detail", matkul_id=matkul_id))


@app.route("/komponen/<int:komponen_id>/hapus", methods=["POST"])
def komponen_hapus(komponen_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        komponen = ambil_komponen_milik(koneksi, komponen_id, user_id)
        koneksi.execute("DELETE FROM komponen WHERE id = ?", (komponen_id,))
        koneksi.commit()
        flash("Komponen dihapus.", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("matkul_detail", matkul_id=komponen["matkul_id"]))


# ============================================================
# BAGIAN 12: ROUTE SIMULASI TARGET
# ============================================================

@app.route("/matkul/<int:matkul_id>/simulasi", methods=["GET", "POST"])
def simulasi(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        matkul = ambil_matkul_milik(koneksi, matkul_id, user_id)
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        komponen = ambil_komponen_matkul(koneksi, matkul_id)
        hasil = None
        if request.method == "POST":
            hasil = proses_simulasi(koneksi, matkul, skala, request.form)
            matkul = ambil_matkul_milik(koneksi, matkul_id, user_id)  # muat ulang target
        return render_template(
            "simulasi.html", matkul=matkul, komponen=komponen, skala=skala, hasil=hasil
        )
    except DataTidakValidError as error:
        flash(str(error), "error")
        return redirect(url_for("matkul_detail", matkul_id=matkul_id))
    finally:
        koneksi.close()


# ============================================================
# BAGIAN 13: ROUTE KEHADIRAN
# ============================================================

@app.route("/matkul/<int:matkul_id>/kehadiran")
def halaman_kehadiran(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        matkul = ambil_matkul_milik(koneksi, matkul_id, user_id)
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        k = ringkas_kehadiran(koneksi, matkul, batas_hadir)
    finally:
        koneksi.close()

    # Isian otomatis: pertemuan setelah catatan terakhir (maksimal total pertemuan)
    terakhir = 0
    if k["catatan"]:
        terakhir = k["catatan"][-1]["pertemuan_ke"]
    berikutnya = min(terakhir + 1, matkul["total_pertemuan"])
    return render_template(
        "kehadiran.html", matkul=matkul, k=k, batas_hadir=batas_hadir,
        berikutnya=berikutnya, daftar_status=konfigurasi.DAFTAR_STATUS_HADIR,
    )


@app.route("/matkul/<int:matkul_id>/kehadiran/catat", methods=["POST"])
def kehadiran_catat(matkul_id):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        matkul = ambil_matkul_milik(koneksi, matkul_id, user_id)
        pertemuan_ke = validasi.validasi_bilangan_bulat(
            request.form.get("pertemuan_ke", ""), "Pertemuan ke"
        )
        validasi.validasi_pertemuan(pertemuan_ke, matkul["total_pertemuan"])
        status = validasi.validasi_status_hadir(request.form.get("status", ""))
        # UPSERT: pertemuan yang sudah ada diperbarui, berkat UNIQUE (matkul_id, pertemuan_ke)
        koneksi.execute(
            "INSERT INTO kehadiran (matkul_id, pertemuan_ke, status) VALUES (?, ?, ?) "
            "ON CONFLICT (matkul_id, pertemuan_ke) DO UPDATE SET status = excluded.status",
            (matkul_id, pertemuan_ke, status),
        )
        koneksi.commit()
        flash(f"Pertemuan ke-{pertemuan_ke} dicatat: {status}.", "sukses")
    except DataTidakValidError as error:
        flash(str(error), "error")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_kehadiran", matkul_id=matkul_id))


@app.route("/matkul/<int:matkul_id>/kehadiran/<int:pertemuan_ke>/hapus", methods=["POST"])
def kehadiran_hapus(matkul_id, pertemuan_ke):
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        ambil_matkul_milik(koneksi, matkul_id, user_id)
        koneksi.execute(
            "DELETE FROM kehadiran WHERE matkul_id = ? AND pertemuan_ke = ?",
            (matkul_id, pertemuan_ke),
        )
        koneksi.commit()
        flash(f"Catatan pertemuan ke-{pertemuan_ke} dihapus.", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("halaman_kehadiran", matkul_id=matkul_id))


# ============================================================
# BAGIAN 14: ROUTE PENGATURAN
# ============================================================

def baca_skala_dari_form(form):
    """Form mengirim tiga daftar sejajar: huruf, batas, bobot_grade.
    Hasil: list of tuple (huruf, batas, bobot_grade)."""
    skala = []
    # zip menggabungkan tiga daftar menjadi satu perulangan
    for huruf, batas, bobot in zip(
        form.getlist("huruf"), form.getlist("batas"), form.getlist("bobot_grade")
    ):
        huruf = huruf.strip().upper()
        if huruf == "":
            continue  # kolom grade kosong = baris dihapus/diabaikan
        skala.append((huruf, validasi.validasi_nilai(batas),
                      validasi.validasi_bobot_grade(bobot)))
    return skala


def proses_simpan_pengaturan(koneksi, user_id, form):
    """Memvalidasi form pengaturan lalu menyimpannya."""
    skala_baru = logika.urutkan_skala(baca_skala_dari_form(form))
    validasi.validasi_skala_grade(skala_baru)
    batas_baru = validasi.validasi_batas_hadir(form.get("batas_hadir", ""))
    database.simpan_pengaturan(koneksi, user_id, batas_baru, skala_baru)


@app.route("/pengaturan", methods=["GET", "POST"])
def pengaturan():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        if request.method == "POST":
            try:
                proses_simpan_pengaturan(koneksi, user_id, request.form)
                flash("Pengaturan disimpan.", "sukses")
                return redirect(url_for("pengaturan"))
            except DataTidakValidError as error:
                flash(str(error), "error")
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
    finally:
        koneksi.close()
    return render_template("pengaturan.html", skala=skala, batas_hadir=batas_hadir)


@app.route("/pengaturan/reset", methods=["POST"])
def pengaturan_reset():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        database.simpan_pengaturan(
            koneksi, user_id, konfigurasi.BATAS_HADIR_DEFAULT, konfigurasi.SKALA_GRADE_DEFAULT
        )
        flash("Pengaturan dikembalikan ke nilai default.", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("pengaturan"))


# ============================================================
# BAGIAN 15: ROUTE PAKET DAN EKSPOR
# ============================================================

@app.route("/paket")
def paket():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    koneksi = database.buka_koneksi()
    try:
        jumlah_semester = hitung_jumlah(
            koneksi, "SELECT COUNT(*) FROM semester WHERE user_id = ?", (user_id,)
        )
    finally:
        koneksi.close()
    return render_template(
        "paket.html", user=ambil_user(user_id), jumlah_semester=jumlah_semester,
        batas_semester=konfigurasi.BATAS_FREE_SEMESTER,
        batas_matkul=konfigurasi.BATAS_FREE_MATKUL,
    )


@app.route("/paket/ubah", methods=["POST"])
def paket_ubah():
    """HANYA UNTUK DEMO. Di aplikasi nyata, ini diganti alur pembayaran."""
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    paket_baru = request.form.get("paket", "")
    if paket_baru not in (konfigurasi.PAKET_FREE, konfigurasi.PAKET_PREMIUM):
        flash("Paket tidak dikenal.", "error")
        return redirect(url_for("paket"))

    koneksi = database.buka_koneksi()
    try:
        koneksi.execute("UPDATE users SET paket = ? WHERE id = ?", (paket_baru, user_id))
        koneksi.commit()
        flash(f"Paket sekarang: {paket_baru.title()} (mode demo).", "sukses")
    finally:
        koneksi.close()
    return redirect(url_for("paket"))


@app.route("/ekspor")
def ekspor():
    user_id = ambil_user_id()
    if user_id is None:
        return alihkan_ke_login()

    # Batas fitur Premium diperiksa di BACKEND
    if ambil_user(user_id)["paket"] != konfigurasi.PAKET_PREMIUM:
        flash("Ekspor ringkasan hanya tersedia di paket Premium.", "error")
        return redirect(url_for("paket"))

    koneksi = database.buka_koneksi()
    try:
        skala, batas_hadir = database.baca_pengaturan(koneksi, user_id)
        data = kumpulkan_data_semester(koneksi, user_id, skala)
    finally:
        koneksi.close()

    # csv.writer (modul bawaan) menangani tanda kutip dan koma dengan benar
    keluaran = io.StringIO()
    penulis = csv.writer(keluaran)
    penulis.writerow(["Semester", "Mata Kuliah", "SKS", "Nilai", "Grade", "Status"])
    for semester, ringkasan in data:
        for r in ringkasan:
            status = "Final" if r["final"] else "Sementara"
            penulis.writerow([semester["nama"], r["matkul"]["nama"], r["matkul"]["sks"],
                            r["nilai"], r["huruf"], status])
    penulis.writerow([])
    penulis.writerow(["IPK", susun_dashboard(data)["ipk"]])
    return Response(
        keluaran.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ringkasan_akademikku.csv"},
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )