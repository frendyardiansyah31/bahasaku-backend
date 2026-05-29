# BahasaKu

Backend API untuk platform latihan Bahasa Indonesia adaptif bagi mahasiswa asing di UIII (Universitas Islam Internasional Indonesia). Dibangun dengan Django REST Framework.

---

## Problem yang Diselesaikan

Mahasiswa asing di UIII kesulitan mempelajari Bahasa Indonesia secara mandiri karena tidak ada platform latihan yang:

- Menyesuaikan materi dengan kemampuan individu masing-masing pengguna
- Melacak perkembangan skill secara spesifik per topik
- Memberikan rekomendasi latihan berdasarkan kelemahan dan kebiasaan belajar

BahasaKu hadir sebagai solusi dengan sistem kuis adaptif yang secara otomatis menyesuaikan rekomendasi topik berdasarkan performa historis pengguna.

---

## Fitur Utama

**Autentikasi**

- Registrasi dan login dengan JWT (access token + refresh token)
- Logout dengan revoke refresh token
- Manajemen profil dan onboarding pengguna

**Kuis Adaptif**

- Daftar topik pembelajaran yang dapat difilter per kategori atau dicari dengan kata kunci
- Sesi kuis per topik dengan soal pilihan ganda
- Submit jawaban per soal dengan feedback langsung (benar/salah + penjelasan)
- Selesaikan sesi kuis dan dapatkan skor, XP, serta streak harian

**Adaptive Learning**

- Pelacakan skill pengguna per topik secara otomatis setelah setiap sesi kuis
- Kalkulasi tingkat kelemahan berdasarkan akurasi jawaban, frekuensi error, dan jarak hari terakhir latihan
- Rekomendasi topik harian berdasarkan algoritma prioritas: `(weakness × 0.5) + (days_idle × 0.3) + (error_freq × 0.2)`

---

## Cara Install dan Menjalankan

### Prasyarat

- Python 3.10
- pipenv — install dengan: `pip install pipenv`

### Langkah-langkah

**1. Clone repository**

```bash
git clone <url-repo>
cd backend
```

**2. Buat file `.env`**

Jika bash (Linux / Mac)

```bash
cp .env.example .env
```

atau bisa copy paste lalu rename untuk pengguna Windows

Isi file `.env`:

```
SECRET_KEY=isi-dengan-string-acak-panjang
DEBUG=True
USE_SQLITE=True
```

Cara membuat secret key menggunakan python :

> Generate SECRET_KEY:
>
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

Lalu copy paste hasil generate secret key ke file .env sebelumnya

**3. Install dependencies**

```bash
pipenv install
```

**4. Aktifkan virtual environment**

```bash
pipenv shell
```

**5. Jalankan migrasi database**

```bash
python manage.py migrate
```

**6. Buat akun superuser untuk Django Admin**

```bash
python manage.py createsuperuser
```

**7. Jalankan server**

```bash
python manage.py runserver
```

Server berjalan di `http://localhost:8000`

### Verifikasi

| URL                                            | Yang diharapkan                |
| ---------------------------------------------- | ------------------------------ |
| `http://localhost:8000/health/`                | `{"status": "ok"}`             |
| `http://localhost:8000/api/schema/swagger-ui/` | Halaman dokumentasi Swagger UI |
| `http://localhost:8000/admin/`                 | Halaman Django Admin           |

---

## Tech Stack

| Komponen              | Teknologi                              |
| --------------------- | -------------------------------------- |
| Language              | Python 3.10                            |
| Framework             | Django 4.2 LTS + Django REST Framework |
| Auth                  | JWT via djangorestframework-simplejwt  |
| Database (lokal)      | SQLite                                 |
| Database (production) | PostgreSQL via Supabase                |
| API Docs              | drf-spectacular (Swagger UI)           |
| Package manager       | pipenv                                 |

---

## Environment Variables

| Variable      | Keterangan                                         |
| ------------- | -------------------------------------------------- |
| `SECRET_KEY`  | Wajib. Key enkripsi Django                         |
| `DEBUG`       | `True` untuk development, `False` untuk production |
| `USE_SQLITE`  | `True` = SQLite lokal, `False` = PostgreSQL        |
| `DB_NAME`     | Nama database PostgreSQL                           |
| `DB_USER`     | Username PostgreSQL                                |
| `DB_PASSWORD` | Password PostgreSQL                                |
| `DB_HOST`     | Host PostgreSQL (dari Supabase)                    |
| `DB_PORT`     | Port PostgreSQL (default: `5432`)                  |

> File `.env` tidak pernah di-commit ke Git. Lihat `.env.example` untuk template lengkap.
