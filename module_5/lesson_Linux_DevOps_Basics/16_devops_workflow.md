# 16. DevOps workflow

## Навіщо це потрібно

Ти написав код. Натиснув `git push`. Через 5 хвилин зміни вже на production — автоматично. Без ручного SSH, без копіювання файлів, без "я щойно задеплоїв, перевіряйте". Це і є **DevOps workflow**.

---

## Що таке DevOps

> DevOps — це не посада і не набір інструментів. Це культура і набір практик, які допомагають командам швидко і безпечно доставляти зміни від ноутбука розробника до production-сервера.

**DevOps = Development + Operations.**

Раніше: розробники писали код, а окрема команда (operations) деплоїла і підтримувала. Між ними — "стіна" і постійні конфлікти.

Сьогодні: команди разом відповідають за весь шлях коду — від написання до моніторингу в production.

---

## Ключові концепції

| Концепція | Що означає |
|---|---|
| **CI** (Continuous Integration) | Автоматична перевірка коду при кожному push |
| **CD** (Continuous Delivery) | Автоматична підготовка до деплою |
| **CD** (Continuous Deployment) | Автоматичний деплой на production |
| **Pipeline** | Послідовність кроків від коду до production |
| **Staging** | Тестовий сервер, що імітує production |
| **Production** | Реальний сервер для кінцевих користувачів |
| **Rollback** | Відкат до попередньої робочої версії |
| **IaC** | Infrastructure as Code — сервери описані як код |

---

## Шлях коду від ноутбука до production

```mermaid
flowchart LR
    Dev["1. Розробник\nпише код"] --> Push["2. git push\nна GitHub"]
    Push --> CI["3. CI:\nтести + лінтер"]
    CI -->|"провалились"| Notify["Сповіщення\nрозробнику"]
    CI -->|"пройшли"| Build["4. Build:\ndocker build"]
    Build --> Registry["5. Push image\nдо Registry"]
    Registry --> Staging["6. Deploy\nна Staging"]
    Staging --> ManualQA{Ручне QA\n(або auto E2E)}
    ManualQA -->|"OK"| Production["7. Deploy\nна Production"]
    Production --> Monitor["8. Monitoring\nлоги, метрики"]
    Monitor -->|"є проблеми"| Rollback["Rollback\nдо попередньої версії"]
    Monitor --> Dev
```

---

## CI — Continuous Integration

CI автоматично запускається при кожному push в репозиторій і виконує:

1. `ruff check .` — лінтер
2. `pytest` — тести
3. Можливо: `safety check` — перевірка вразливостей

Якщо щось провалилося — pull request не можна змерджити. Код з поламаними тестами не потрапить у main.

### GitHub Actions — приклад CI для Django

```yaml
# .github/workflows/ci.yml
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      db:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run linter
        run: ruff check .

      - name: Run tests
        env:
          DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
          DEBUG: "True"
          SECRET_KEY: "ci-test-secret-key"
        run: pytest --tb=short
```

---

## CD — Continuous Deployment

Після успішного CI — автоматичний деплой:

```yaml
# .github/workflows/deploy.yml (частина)
  deploy:
    needs: test            # тільки якщо тести пройшли
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/myapp
            git pull origin main
            source .venv/bin/activate
            pip install -r requirements.txt
            python manage.py migrate --noinput
            python manage.py collectstatic --noinput
            sudo systemctl restart myapp
```

---

## Staging і Production

> Staging — це дзеркало production. Ти деплоїш туди спочатку, перевіряєш що все працює, і тільки потім — на production.

```text
[Developer] → [Git] → [CI] → [Staging] → [Manual/Auto QA] → [Production]
```

На staging:
- Реальна база (копія або тест-дані)
- Реальний Docker, Nginx, Gunicorn
- Але доступ обмежений (не публічний)

Переваги:
- Баги знаходяться до того як побачать користувачі
- Можна протестувати міграції
- Команда QA може перевірити нові фічі

---

## Rollback

Якщо після деплою щось зламалося — треба швидко повернутися назад.

### Варіант 1: Git rollback

```bash
git log --oneline -5           # знайти попередній коміт
git checkout HEAD~1            # або конкретний SHA
sudo systemctl restart myapp
```

### Варіант 2: Docker image tags

```bash
# Попередній image ще в registry
docker pull myapp:v1.2.3
docker compose up -d           # з попередньою версією
```

### Варіант 3: Через CI/CD

Більшість CI/CD систем мають кнопку "Redeploy previous build".

---

## Infrastructure as Code (IaC)

> Якщо конфігурацію сервера описати в коді — її можна версіонувати, відтворити, переглянути зміни, і розгорнути знову після катастрофи.

Замість того щоб вручну налаштовувати Nginx, PostgreSQL, firewall — це описується в файлах (Terraform, Ansible, Pulumi) і запускається автоматично.

Для початківця: достатньо `docker-compose.yml` і Bash-скриптів. Terraform і Ansible — наступний рівень.

---

## Типові помилки початківців

**Помилка 1:** Деплоїти вручну без скрипта
> Одного разу забудеш `collectstatic` або `migrate` і сайт зламається.

**Помилка 2:** Деплоїти без тестів
> Без CI тести не запускаються автоматично і баги потрапляють на production.

**Помилка 3:** Немає staging
> Перший раз бачиш поведінку на production. Немає можливості відтворити проблему.

---

## Практичне завдання

### Завдання 1
Намалюй pipeline для свого Django-проєкту: від `git push` до живого сайту. Які кроки? Що автоматично, що вручну?

### Завдання 2
Додай `.github/workflows/ci.yml` у свій проєкт з кроками: install, ruff, pytest. Перевір що він запускається при push.

### Завдання 3
Напиши `deploy.sh` — скрипт деплою на сервер, який виконує git pull, migrate, collectstatic, restart.

---

## Самоперевірка

- [ ] Я можу пояснити що таке CI/CD
- [ ] Я розумію навіщо потрібен Staging
- [ ] Я знаю, що таке rollback і як його зробити
- [ ] Я можу написати базовий GitHub Actions workflow для Django
- [ ] Я розумію шлях коду від push до production

---

## Короткий підсумок

DevOps — практики для швидкої і безпечної доставки коду. CI перевіряє тести при кожному push. CD автоматизує деплой. Staging — безпечне місце для тестування перед production. Rollback — план відступу. Наступний крок — Kubernetes overview.
