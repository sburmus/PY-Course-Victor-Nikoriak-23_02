# 09. Bash-скрипти

## Навіщо це потрібно

Уяви, що кожен раз при деплої ти вводиш 15 команд вручну: `git pull`, `source .venv/bin/activate`, `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py collectstatic`, `sudo systemctl restart myapp`... Це повільно і ти неодмінно щось пропустиш або наберешь помилку.

Bash-скрипт — це файл, де записані всі ці команди по порядку. Запускаєш один файл — він все робить сам.

---

## Просте пояснення

> Bash-скрипт — це список команд, записаних у файл. Замість того щоб вводити їх вручну одну за одною — ти запускаєш один файл і він все робить за тебе.

---

## Shebang — перший рядок скрипта

```bash
#!/usr/bin/env bash
```

Перший рядок скрипта завжди починається з `#!` (shebang). Він вказує, якою програмою виконувати файл.

`/usr/bin/env bash` — знайти bash через `env` (надійніший варіант, ніж `#!/bin/bash`, бо bash може бути в різних місцях).

---

## Перший скрипт

```bash
#!/usr/bin/env bash

echo "Починаємо налаштування Django проєкту..."

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

echo "Готово!"
```

Зберегти у файл `setup.sh`, зробити виконуваним і запустити:

```bash
chmod +x setup.sh
./setup.sh
```

---

## Змінні

```bash
#!/usr/bin/env bash

PROJECT_DIR="/var/www/myapp"
VENV_DIR="$PROJECT_DIR/.venv"
APP_USER="www-data"

echo "Проєкт: $PROJECT_DIR"
echo "Virtualenv: $VENV_DIR"
```

Правила змінних у Bash:
- Без пробілів: `NAME="value"` ✓, `NAME = "value"` ✗
- Читати через `$`: `$NAME` або `${NAME}`
- Лапки важливі: `"$NAME"` збереже пробіли

---

## Умови (if/else)

```bash
#!/usr/bin/env bash

if [ -f ".env" ]; then
    echo ".env файл знайдено"
else
    echo "ПОМИЛКА: .env файл відсутній"
    exit 1
fi
```

Корисні перевірки:

| Умова | Що перевіряє |
|---|---|
| `[ -f file ]` | файл існує |
| `[ -d dir ]` | директорія існує |
| `[ -z "$VAR" ]` | змінна порожня |
| `[ "$A" = "$B" ]` | рядки рівні |
| `[ $N -gt 0 ]` | число більше за 0 |

---

## Exit codes у скриптах

```bash
#!/usr/bin/env bash

# Зупинитися при першій помилці
set -e

git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate

echo "Деплой успішний!"
```

`set -e` — дуже корисна опція: якщо будь-яка команда повернула ненульовий exit code — скрипт зупиниться. Без цього скрипт продовжить виконання навіть після помилки.

---

## Цикли

```bash
#!/usr/bin/env bash

# Виконати команду для кожного аргументу
for app in users notes tags; do
    echo "Запускаємо міграції для $app..."
    python manage.py migrate $app
done

# Перебрати файли
for file in *.py; do
    echo "Файл: $file"
done
```

---

## Аргументи командного рядка

```bash
#!/usr/bin/env bash

ENVIRONMENT=${1:-development}   # $1 — перший аргумент, за замовчуванням development

echo "Деплой у середовище: $ENVIRONMENT"

if [ "$ENVIRONMENT" = "production" ]; then
    echo "Увага: деплой на production!"
fi
```

Запуск:
```bash
./deploy.sh production
./deploy.sh            # використає development
```

---

## Реальний скрипт деплою

```bash
#!/usr/bin/env bash
set -e

echo "=== Деплой Django-проєкту ==="

# Змінні
APP_DIR="/var/www/myapp"
VENV="$APP_DIR/.venv"
SERVICE_NAME="myapp"

# Оновити код
cd "$APP_DIR"
git pull origin main

# Оновити залежності
source "$VENV/bin/activate"
pip install -r requirements.txt --quiet

# Застосувати міграції
python manage.py migrate --noinput

# Зібрати статику
python manage.py collectstatic --noinput

# Перезапустити сервіс
sudo systemctl restart "$SERVICE_NAME"

echo "=== Деплой завершено! ==="
echo "Статус сервісу:"
systemctl status "$SERVICE_NAME" --no-pager
```

---

## Debugging скрипта

```bash
bash -x script.sh         # виконати з трасуванням (показує кожну команду)
set -x                    # увімкнути трасування всередині скрипта
set +x                    # вимкнути трасування
```

---

## Типові помилки початківців

**Помилка 1:** `Permission denied` при запуску скрипта
> Забув `chmod +x script.sh`

**Помилка 2:** `./script.sh: line 1: $'\r': command not found`
> Файл збережений у Windows-форматі (CRLF). Виправ: `sed -i 's/\r//' script.sh`

**Помилка 3:** Скрипт продовжується після помилки і ламає сервер
> Додай `set -e` на початку скрипта

**Помилка 4:** Пробіли навколо `=` у змінних
> `NAME="value"` ✓, `NAME = "value"` ✗ — Bash сприйме `NAME` як команду

---

## Практичне завдання

### Завдання 1
Напиши `setup.sh` для Django-проєкту:
1. Перевіряє наявність `.env`
2. Створює virtualenv (якщо не існує)
3. Встановлює залежності
4. Виконує міграції

### Завдання 2
Напиши `deploy.sh`:
1. `git pull`
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py collectstatic --noinput`
5. Перевіряє exit code кожного кроку

### Завдання 3
```bash
bash -x setup.sh 2>&1 | head -30
```
Запусти скрипт з трасуванням і проаналізуй вивід.

---

## Самоперевірка

- [ ] Я розумію, що таке shebang і навіщо він потрібен
- [ ] Я можу написати скрипт з змінними, умовами і циклами
- [ ] Я знаю, що `set -e` зупиняє скрипт при помилці
- [ ] Я вмію зробити скрипт виконуваним через `chmod +x`
- [ ] Я можу написати простий деплой-скрипт для Django

---

## Короткий підсумок

Bash-скрипт — набір команд у файлі. Shebang вказує інтерпретатор. `set -e` — зупинка при помилці. Реальний деплой починається з написання скрипта, який автоматизує всі ручні кроки. Наступний крок — Makefile, ще один спосіб організувати команди.
