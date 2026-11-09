// 1. Pesan flash hilang otomatis setelah 4 detik.
//    Hanya yang ada di .area-flash, agar peringatan permanen di halaman tidak ikut hilang.
document.querySelectorAll(".area-flash .flash").forEach(function (pesan) {
    setTimeout(function () {
        pesan.style.display = "none";
    }, 4000);
});

// 2. Form dengan atribut data-konfirmasi meminta persetujuan sebelum dikirim
document.querySelectorAll("form[data-konfirmasi]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        if (!confirm(form.dataset.konfirmasi)) {
            event.preventDefault();
        }
    });
});

// 3. Menu hamburger di layar kecil
const tombolMenu = document.getElementById("tombolMenu");
const menuNav = document.getElementById("menuNav");

if (tombolMenu && menuNav) {
    tombolMenu.addEventListener("click", function () {
        menuNav.classList.toggle("buka");
    });
}