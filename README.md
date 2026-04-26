---
title: BahasaKu Backend
emoji: 🇮🇩
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# BahasaKu Backend API

Django REST API for BahasaKu — adaptive Indonesian language learning platform for international students at UIII.

# BahasaKu — Backend API

Platform latihan Bahasa Indonesia adaptif untuk mahasiswa asing UIII.  
Dibangun dengan Django REST Framework + JWT Authentication.

---

## Daftar Isi

- [Tech Stack](#tech-stack)
- [Setup Project](#setup-project)
- [Struktur Folder](#struktur-folder)
- [Cara Baca Kode](#cara-baca-kode)
- [Alur Proses](#alur-proses)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)

---

## Tech Stack

| Komponen              | Teknologi                     |
| --------------------- | ----------------------------- |
| Language              | Python 3.10                   |
| Framework             | Django 4.2 LTS                |
| REST API              | Django REST Framework         |
| Auth                  | djangorestframework-simplejwt |
| Database (lokal)      | SQLite                        |
| Database (production) | PostgreSQL via Supabase       |
| API Docs              | drf-spectacular (Swagger UI)  |
| Package manager       | pipenv                        |

---

## Setup Project

### Prasyarat

Pastikan sudah terinstall di komputer:

- Python 3.10 ([download](https://www.python.org/downloads/release/python-3100/))
- pipenv — install dengan perintah:
  ```bash
  pip install pipenv
  ```

### Langkah-langkah

**1. Clone repository**

```bash
git clone <url-repo>
cd backend
```

**2. Buat file `.env`**

Salin dari contoh yang sudah ada:

```bash
cp .env.example .env
```

Isi nilai `SECRET_KEY` di file `.env`:

```
SECRET_KEY=isi-dengan-string-acak-panjang
DEBUG=True
USE_SQLITE=True
```

> Untuk generate SECRET_KEY, jalankan:
>
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

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

**6. Buat akun superuser (untuk Django Admin)**

```bash
python manage.py createsuperuser
```

Ikuti instruksi: masukkan email, name, dan password.

**7. Jalankan server**

```bash
python manage.py runserver
```

Server berjalan di `http://localhost:8000`

### Verifikasi instalasi

Buka URL berikut di browser — semua harus bisa diakses:

| URL                                            | Yang diharapkan      |
| ---------------------------------------------- | -------------------- |
| `http://localhost:8000/health/`                | `{"status": "ok"}`   |
| `http://localhost:8000/api/schema/swagger-ui/` | Halaman Swagger UI   |
| `http://localhost:8000/admin/`                 | Halaman Django Admin |

---

## Struktur Folder

```
backend/
├── bahasaku/               → konfigurasi project Django
│   ├── settings.py         → semua settings (database, JWT, CORS, dll.)
│   ├── urls.py             → routing utama (entry point semua URL)
│   └── wsgi.py             → untuk deploy production
│
├── authentication/         → app untuk fitur auth
│   ├── models.py           → struktur tabel User dan RefreshToken
│   ├── serializers.py      → validasi input dari request
│   ├── services.py         → business logic (register, login, logout, dll.)
│   ├── views.py            → terima request, panggil service, kirim response
│   ├── urls.py             → routing untuk /api/auth/...
│   ├── admin.py            → konfigurasi tampilan Django Admin
│   └── migrations/         → file migrasi database (auto-generated)
│
├── manage.py               → CLI Django (migrate, runserver, dll.)
├── Pipfile                 → daftar dependencies
├── .env                    → konfigurasi lokal (tidak di-commit ke Git)
├── .env.example            → template .env (aman di-commit)
└── .gitignore              → file yang diabaikan Git
```

---

## Cara Baca Kode

### Prinsip arsitektur

Project ini menggunakan **3-layer architecture**. Setiap layer punya satu tanggung jawab:

```
Request masuk
     ↓
serializers.py   → "Apakah input-nya valid?"
     ↓
services.py      → "Apa yang harus dilakukan?"
     ↓
models.py        → "Simpan/ambil data dari database"
     ↓
views.py         → "Kirim response apa ke client?"
```

### Kalau ada bug, cari di sini

| Masalah                                          | File yang diperiksa |
| ------------------------------------------------ | ------------------- |
| Format request/response salah                    | `views.py`          |
| Validasi input gagal (email, password, dll.)     | `serializers.py`    |
| Logic bisnis salah (token tidak tersimpan, dll.) | `services.py`       |
| Struktur data/kolom database                     | `models.py`         |
| URL tidak ditemukan (404)                        | `urls.py`           |
| Setting database, CORS, JWT                      | `settings.py`       |

### Contoh membaca satu fitur dari ujung ke ujung

Ambil contoh **Login**. Urutannya:

1. `authentication/urls.py` → cari path `login/`, mengarah ke `LoginView`
2. `authentication/views.py` → buka `LoginView.post()`, lihat apa yang dilakukan
3. `authentication/serializers.py` → buka `LoginSerializer`, lihat field apa yang divalidasi
4. `authentication/services.py` → buka `login_user()`, lihat logic autentikasi dan penyimpanan token

---

## Alur Proses

### Registrasi

```
Client                          Server
  |                               |
  |  POST /api/auth/register/     |
  |  { name, email, password,     |
  |    password_confirm }         |
  |------------------------------>|
  |                               | 1. Validasi input (serializer)
  |                               |    - email belum terdaftar?
  |                               |    - password == password_confirm?
  |                               | 2. Buat user baru (services)
  |                               |    - password di-hash otomatis
  |                               |    - role default: 'user'
  |                               |    - is_onboarded: false
  |  201 { message, user }        |
  |<------------------------------|
```

### Login

```
Client                          Server
  |                               |
  |  POST /api/auth/login/        |
  |  { email, password }          |
  |------------------------------>|
  |                               | 1. Cek email & password (services)
  |                               | 2. Generate access token (60 menit)
  |                               |    + refresh token (7 hari)
  |                               | 3. Simpan refresh token ke tabel
  |                               |    RefreshToken di database
  |  200 { access, refresh, user }|
  |<------------------------------|
```

### Akses endpoint yang butuh autentikasi

```
Client                          Server
  |                               |
  |  GET /api/...                 |
  |  Header:                      |
  |  Authorization: Bearer <token>|
  |------------------------------>|
  |                               | 1. Validasi JWT token
  |                               |    - signature valid?
  |                               |    - belum expired?
  |  200 { data }                 |
  |<------------------------------|
  |                               |
  |  (kalau token expired)        |
  |  401 { message }              |
  |<------------------------------|
```

### Refresh Token

```
Client                          Server
  |                               |
  |  POST /api/auth/token/refresh/|
  |  { refresh }                  |
  |------------------------------>|
  |                               | 1. Cek refresh token di database
  |                               |    - ada? belum di-revoke?
  |                               | 2. Validasi JWT refresh token
  |                               |    - signature valid? belum expired?
  |                               | 3. Generate access token baru
  |  200 { access }               |
  |<------------------------------|
```

### Logout

```
Client                          Server
  |                               |
  |  POST /api/auth/logout/       |
  |  Header: Authorization: Bearer|
  |  { refresh }                  |
  |------------------------------>|
  |                               | 1. Verifikasi Bearer token di header
  |                               | 2. Set is_revoked = True pada
  |                               |    refresh token di database
  |  200 { message }              |
  |<------------------------------|
  |                               |
  |  (refresh token lama dicoba)  |
  |  POST /api/auth/token/refresh/|
  |  { refresh }                  |
  |------------------------------>|
  |  401 { message }              | ← ditolak karena sudah di-revoke
  |<------------------------------|
```

---

## API Endpoints

Base URL lokal: `http://localhost:8000`

| Method | Endpoint                   | Auth          | Deskripsi                    |
| ------ | -------------------------- | ------------- | ---------------------------- |
| GET    | `/health/`                 | Tidak         | Health check                 |
| POST   | `/api/auth/register/`      | Tidak         | Registrasi akun              |
| POST   | `/api/auth/login/`         | Tidak         | Login, dapat JWT token       |
| POST   | `/api/auth/token/refresh/` | Tidak         | Perbarui access token        |
| POST   | `/api/auth/logout/`        | Ya            | Logout, revoke refresh token |
| GET    | `/api/schema/swagger-ui/`  | Tidak         | Dokumentasi Swagger UI       |
| GET    | `/admin/`                  | Ya (is_staff) | Django Admin                 |

---

## Environment Variables

| Variable      | Default | Keterangan                                  |
| ------------- | ------- | ------------------------------------------- |
| `SECRET_KEY`  | —       | Wajib diisi. Key enkripsi Django            |
| `DEBUG`       | `True`  | `False` di production                       |
| `USE_SQLITE`  | `True`  | `True` = SQLite lokal, `False` = PostgreSQL |
| `DB_NAME`     | —       | Nama database PostgreSQL (production)       |
| `DB_USER`     | —       | Username PostgreSQL                         |
| `DB_PASSWORD` | —       | Password PostgreSQL                         |
| `DB_HOST`     | —       | Host PostgreSQL (dari Supabase)             |
| `DB_PORT`     | `5432`  | Port PostgreSQL                             |

> File `.env` tidak pernah di-commit ke Git. Lihat `.env.example` untuk template.
