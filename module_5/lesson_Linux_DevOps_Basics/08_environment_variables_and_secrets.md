# 08. Environment Variables і секрети

## Навіщо це потрібно

У Django-проєкті є речі, які **не можна зберігати в коді**: паролі до бази даних, `SECRET_KEY`, API-ключі, токени. Якщо вони потраплять у Git — їх побачить весь світ (або зловмисники).

Environment variables (змінні оточення) — це спосіб передати конфіденційні дані програмі без записування їх у код.

---

## Просте пояснення

> Уяви, що твій Django-проєкт — це рецепт торта. Код — це рецепт (можна ділитися). Паролі до бази і SECRET_KEY — це секретний інгредієнт, який ти не пишеш у рецепті, а передаєш окремо, усно.

Environment variables — це "усна" частина. Вони живуть в операційній системі або у файлі `.env`, але **не в коді**.

---

## Що таке environment variable

Environment variable (змінна оточення) — це пара `КЛЮЧ=значення`, яка існує в середовищі запуску процесу.

```bash
echo $HOME          # /home/student
echo $USER          # student
echo $PATH          # /usr/bin:/usr/local/bin:...
printenv            # всі змінні оточення
```

`PATH` — одна з найважливіших змінних. Linux шукає програми в директоріях, перерахованих у `PATH`. Саме тому ти можеш написати `python` замість `/usr/bin/python3`.

---

## Керування змінними в shell

### Встановити змінну в поточній сесії

```bash
export DEBUG=True
export DATABASE_URL=postgres://user:pass@localhost/mydb
```

### Переглянути значення

```bash
echo $DEBUG
echo $DATABASE_URL
printenv DEBUG
```

### Видалити змінну

```bash
unset DEBUG
```

> Змінна, встановлена через `export`, існує тільки в поточній сесії терміналу. Після закриття терміналу — зникає.

---

## Файл .env

Щоб не вводити змінні кожного разу вручну, їх зберігають у файлі `.env`:

```env
DEBUG=True
SECRET_KEY=your-very-secret-key-change-me-in-production
DATABASE_URL=postgres://app_user:app_password@localhost:5432/app_db
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=yourmail@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
REDIS_URL=redis://localhost:6379/0
```

`.env` — це просто текстовий файл. Формат: `КЛЮЧ=значення`, по одному на рядок. Без пробілів навколо `=`.

### .env і .gitignore

`.env` завжди додається в `.gitignore`:

```bash
# .gitignore
.env
.env.local
.env.production
.venv/
__pycache__/
*.pyc
```

Замість `.env` у Git зберігають `.env.example` — шаблон без реальних значень:

```env
# .env.example
DEBUG=True
SECRET_KEY=change-me
DATABASE_URL=postgres://user:password@localhost:5432/dbname
ALLOWED_HOSTS=localhost
```

---

## Django і environment variables

### Пакет python-decouple

```bash
pip install python-decouple
```

```python
# settings.py
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
DATABASE_URL = config('DATABASE_URL')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')
```

### Пакет django-environ

```bash
pip install django-environ
```

```python
# settings.py
import environ

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env('.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASES = {'default': env.db()}
```

### Або os.environ напряму

```python
import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-only-for-dev')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

---

## Передача змінних через systemd

Якщо Django запущений як systemd-сервіс, змінні передаються через `EnvironmentFile`:

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Django App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/myapp
EnvironmentFile=/var/www/myapp/.env
ExecStart=/var/www/myapp/.venv/bin/gunicorn myapp.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Файл `.env` при цьому читає systemd, а не bash:
```bash
sudo chmod 600 /var/www/myapp/.env
sudo chown www-data:www-data /var/www/myapp/.env
```

---

## Передача змінних у Docker

```yaml
# docker-compose.yml
services:
  web:
    build: .
    env_file:
      - .env
    environment:
      - DEBUG=False
```

або через окремий файл:
```bash
docker run --env-file .env django-app
```

---

## Правила безпеки

```text
✓ Зберігай всі секрети в .env
✓ Додавай .env у .gitignore ПЕРЕД першим комітом
✓ Зберігай .env.example у Git (без реальних значень)
✓ Права на .env — 600 (тільки власник читає)
✓ На production: різні значення, ніж на dev

✗ Не зберігай SECRET_KEY або паролі в settings.py
✗ Не комить .env у Git
✗ Не надсилай .env по email або Slack
✗ Не використовуй однаковий SECRET_KEY на dev і production
```

---

## Типові помилки початківців

**Помилка 1:** Закомітив `.env` з реальними паролями
> Негайно зміни всі паролі і ключі. Видали з Git history: `git filter-branch` або `git-filter-repo`. Вважай, що вони скомпрометовані.

**Помилка 2:** `KeyError: 'SECRET_KEY'` при запуску Django
> Змінна не встановлена. Перевір: чи є `.env` файл? Чи правильно читається?

**Помилка 3:** Різні значення DEBUG на різних серверах не відрізняються
> На production завжди `DEBUG=False`. Якщо `DEBUG=True` на production — Django показує stack traces всім користувачам.

---

## Практичне завдання

### Завдання 1
```bash
export MY_NAME="Linux Student"
echo "Hello, $MY_NAME!"
printenv MY_NAME
```

### Завдання 2
Створи Django-проєкт і перенеси `SECRET_KEY` у `.env`:
```bash
django-admin startproject config .
pip install python-decouple
```
У `settings.py` замін `SECRET_KEY = '...'` на читання з `.env`.

### Завдання 3
Переконайся, що `.gitignore` містить `.env`. Зроби `git status` і перевір, що `.env` не з'являється в списку файлів для коміту.

---

## Самоперевірка

- [ ] Я розумію, що таке environment variable і навіщо вона потрібна
- [ ] Я можу встановити змінну через `export` і прочитати через `echo $VAR`
- [ ] Я знаю формат файлу `.env`
- [ ] Я розумію, чому `.env` не можна комітити в Git
- [ ] Я вмію читати змінні в Django через `python-decouple` або `os.environ`

---

## Короткий підсумок

Environment variables — спосіб зберігати секрети окремо від коду. Django читає `SECRET_KEY`, паролі до бази, налаштування email — з `.env` або зі змінних оточення. `.env` завжди в `.gitignore`. Наступний крок — Bash-скрипти для автоматизації.
