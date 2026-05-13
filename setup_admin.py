import os
import django

# Setup environment Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bahasaku.settings')
django.setup()

from authentication.models import User # Sesuaikan dengan path model Anda

def create_admin():
    email = os.getenv('ADMIN_EMAIL', 'admin@bahasaku.com')
    password = os.getenv('ADMIN_PASSWORD', 'admin12345')
    name = 'Super Admin'

    # Cek apakah user dengan email tersebut sudah ada
    if not User.objects.filter(email=email).exists():
        print(f"Creating superuser for {email}...")
        # Sesuaikan dengan method manager Anda
        User.objects.create_superuser(email=email, name=name, password=password)
        print("Superuser created successfully!")
    else:
        print("Superuser already exists.")

if __name__ == '__main__':
    create_admin()