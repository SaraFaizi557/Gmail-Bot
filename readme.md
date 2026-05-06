# 🧱 1. Create Project (clean way)

```bash
python -m venv venv
```
```bash
venv\Scripts\activate
```
```bash
pip install django psycopg2-binary pillow python-dotenv stripe
```
```bash
python -m django startproject pixelmind
```
```bash
cd pixelmind
```  

## 📁 2. Project Structure (important to understand)

**After creation:**

```
pixelmind/
 ├── manage.py
 └── pixelmind/
     ├── __init__.py
     ├── settings.py
     ├── urls.py
     ├── asgi.py
     └── wsgi.py
```

## ⚙️ 3. Create App (real projects use apps)

```bash
python manage.py startapp core
```

**Add it in `settings.py`:**

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    ...
    'core',
]
```

## 🗄️ 4. Database Setup (PostgreSQL)

*Install PostgreSQL and then update:*

**`.env` file (create in root)**

```.env
DB_NAME=pixelmind
DB_USER=pixelmind_user
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```

**Install dotenv support in `settings.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()
```

**Replace DATABASES:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
```

**Open psql as postgres user:**

```bash
psql -U postgres
```

**Then run these SQL commands:**

1. Create Database
```bash
CREATE DATABASE myproject_db;
```
2. Create User with proper privileges
```bash
CREATE USER myproject_user WITH PASSWORD 'strong_password_here';
```
3. Make the user owner of the database (Best practice)
```bash
ALTER DATABASE myproject_db OWNER TO myproject_user;
```
4. Grant all privileges
```bash
GRANT ALL PRIVILEGES ON DATABASE myproject_db TO myproject_user;
```

## 🔐 5. Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## 👤 6. Create Admin User

```bash
python manage.py createsuperuser
```

## ▶️ 7. Run Server

```bash
python manage.py runserver
```

**Open:**

```bash
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/
```

## 🎨 8. Static & Media Setup

**In `settings.py`:**

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

**In `urls.py`:**

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 🧠 9. Basic App Logic Example

`core/views.py`

```python
from django.http import HttpResponse

def home(request):
    return HttpResponse("Hey world 🚀")
```

## 🧱 Step 10: Create `urls.py` inside core app

`core/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
]
```

**Connect in main `urls.py`**

```python
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
]
```

## 💳 11. Stripe Setup (basic)

**In `.env`:**

```bash
STRIPE_SECRET_KEY=your_key
```

**Example usage:**

```python
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
```

## 🖼️ 12. Image Upload (Pillow)

**`models.py`**

```python
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='products/')
```

**Then:**

```bash
python manage.py makemigrations
python manage.py migrate
```
