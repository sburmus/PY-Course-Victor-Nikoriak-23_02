# 11. Деплой Django на Linux

## Навіщо це потрібно

Ти написав Django-проєкт. Він працює на ноутбуці. Тепер треба зробити так, щоб його побачили реальні користувачі — через інтернет, 24/7. Це і є **деплой**.

Цей файл — покрокова інструкція: від `git clone` до працюючого сайту.

---

## Що таке деплой

Деплой — це процес переносу коду з локального середовища розробки на сервер, де він буде доступний користувачам.

```mermaid
flowchart TD
    Local["Local Django project\n(ноутбук, DEBUG=True)"] --> Git["Push to Git\n(GitHub/GitLab)"]
    Git --> Server["Pull on Linux server\n(Ubuntu)"]
    Server --> Venv["Створити virtualenv\nВстановити залежності"]
    Venv --> Env["Налаштувати .env\n(DEBUG=False, DB credentials)"]
    Env --> Migrate["python manage.py migrate"]
    Migrate --> Static["python manage.py collectstatic"]
    Static --> AppServer["Запустити Gunicorn/Uvicorn"]
    AppServer --> Nginx["Nginx приймає запити\nі проксує до app server"]
    Nginx --> Users["Користувачі"]
```

---

## Підготовка сервера

```bash
# Підключитися до сервера
ssh ubuntu@your_server_ip

# Оновити систему
sudo apt update && sudo apt upgrade -y

# Встановити необхідні пакети
sudo apt install python3 python3-venv python3-pip git nginx -y

# Встановити PostgreSQL (якщо використовуєш)
sudo apt install postgresql postgresql-contrib -y
```

---

## Налаштування PostgreSQL на сервері

```bash
sudo -u postgres psql

-- Всередині psql:
CREATE DATABASE myapp_db;
CREATE USER myapp_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE myapp_db TO myapp_user;
\q
```

---

## Клонування і налаштування проєкту

```bash
# Перейти в директорію для веб-проєктів
cd /var/www/

# Клонувати репозиторій
sudo git clone https://github.com/you/myproject.git myapp
sudo chown -R $USER:$USER /var/www/myapp
cd /var/www/myapp

# Створити virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Встановити залежності
pip install -r requirements.txt

# Встановити Gunicorn (якщо немає в requirements.txt)
pip install gunicorn
```

---

## Файл .env на сервері

```bash
nano /var/www/myapp/.env
```

```env
DEBUG=False
SECRET_KEY=your-production-secret-key-very-long-and-random
DATABASE_URL=postgres://myapp_user:strong_password_here@localhost:5432/myapp_db
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your_server_ip
STATIC_ROOT=/var/www/myapp/staticfiles
MEDIA_ROOT=/var/www/myapp/media
```

```bash
chmod 600 /var/www/myapp/.env
```

> `DEBUG=False` на production — обов'язково. Інакше Django показує stack traces з даними бази.

---

## Міграції і статика

```bash
source /var/www/myapp/.venv/bin/activate
cd /var/www/myapp

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # якщо потрібен адмін
```

`collectstatic` збирає всі статичні файли (CSS, JS, images) в одну директорію `STATIC_ROOT`. Звідти Nginx роздає їх напряму, не чіпаючи Django.

---

## Перевірка що Django запускається

```bash
# Тест — запустити і подивитися чи є помилки
python manage.py check --deploy

# Запустити Gunicorn вручну (для перевірки)
gunicorn myapp.wsgi:application --bind 0.0.0.0:8000
```

Якщо відкрити `http://your_server_ip:8000` в браузері — має відкритися сайт (без CSS, бо Nginx ще не налаштований).

Зупини Gunicorn: `Ctrl+C`

---

## Systemd service для Django

Створи файл сервісу:

```bash
sudo nano /etc/systemd/system/myapp.service
```

```ini
[Unit]
Description=Django Application - myapp
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/myapp
EnvironmentFile=/var/www/myapp/.env
ExecStart=/var/www/myapp/.venv/bin/gunicorn \
    myapp.wsgi:application \
    --workers 3 \
    --bind unix:/run/myapp.sock \
    --log-file /var/log/myapp/gunicorn.log \
    --access-logfile /var/log/myapp/access.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Створити директорію для логів
sudo mkdir -p /var/log/myapp
sudo chown www-data:www-data /var/log/myapp

# Передати права на проєкт www-data
sudo chown -R www-data:www-data /var/www/myapp

# Запустити і увімкнути автостарт
sudo systemctl daemon-reload
sudo systemctl start myapp
sudo systemctl enable myapp
sudo systemctl status myapp
```

> `--bind unix:/run/myapp.sock` — Gunicorn слухає на Unix socket замість TCP-порту. Це швидше і безпечніше для local-комунікації з Nginx.

---

## Nginx конфігурація

```bash
sudo nano /etc/nginx/sites-available/myapp
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location /static/ {
        alias /var/www/myapp/staticfiles/;
    }

    location /media/ {
        alias /var/www/myapp/media/;
    }

    location / {
        proxy_pass http://unix:/run/myapp.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Активувати конфіг
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t              # перевірити синтаксис
sudo systemctl restart nginx
```

---

## Чому не можна використовувати runserver на production

| `runserver` | Gunicorn |
|---|---|
| Однопотоковий | Кілька workers (паралельні запити) |
| Розроблений для debug | Оптимізований для production |
| Не підтримує Unix sockets | Підтримує |
| Повільний | Швидкий |
| Без SSL | Nginx додає SSL |

---

## Типові помилки при деплої

**Помилка 1:** `DisallowedHost at /`
> Додай домен і IP до `ALLOWED_HOSTS` у `.env`

**Помилка 2:** CSS/JS не завантажуються
> Виконай `python manage.py collectstatic`. Перевір шлях `STATIC_ROOT` і конфіг Nginx.

**Помилка 3:** `502 Bad Gateway`
> Gunicorn не запущений або не може підключитися до сокета. `systemctl status myapp`

**Помилка 4:** Помилки з базою даних
> Перевір `DATABASE_URL` у `.env`. Чи є доступ від `www-data` до PostgreSQL?

---

## Практичне завдання

### Завдання 1
Підготуй `requirements.txt` для production: додай `gunicorn`, `psycopg2-binary`, `python-decouple`.

### Завдання 2
Запусти Gunicorn вручну і перевір що сайт відкривається:
```bash
gunicorn myapp.wsgi:application --bind 0.0.0.0:8000 --log-level debug
```

### Завдання 3
Напиши systemd unit file для свого проєкту і поясни кожен рядок.

---

## Самоперевірка

- [ ] Я можу пояснити всі кроки деплою Django від git clone до запущеного сайту
- [ ] Я знаю, що `DEBUG=False` обов'язковий на production
- [ ] Я розумію навіщо `collectstatic` і що таке `STATIC_ROOT`
- [ ] Я вмію написати systemd unit file для Django
- [ ] Я знаю, чому `runserver` не можна використовувати на production

---

## Короткий підсумок

Деплой Django — це: клонувати код, налаштувати `.env`, створити virtualenv, встановити залежності, виконати міграції і collectstatic, запустити Gunicorn через systemd, налаштувати Nginx. Далі розберемо Nginx і Gunicorn детальніше.
