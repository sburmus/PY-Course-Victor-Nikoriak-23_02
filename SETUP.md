# 🚀 Як працює запуск курсу

Після запуску:

start_course.bat (Windows)
або
python3 start_course.py (Mac/Linux)

ви побачите меню:

----------------------------------------
Python Course -- Select Lesson
----------------------------------------

[1] 01_variables / ...
[2] 02_conditions / ...
[3] 03_loops / ...
...

Введіть номер уроку та натисніть Enter.

Після цього:

- автоматично відкриється браузер
- запуститься вибраний notebook
- ви зможете проходити завдання або тест

---

# 🧪 Режим тестів (через launcher)

Launcher використовує Voila.

Це означає:

- системні клітинки приховані
- інтерфейс чистий
- працює як тестова система
- не потрібно нічого налаштовувати

Цей режим використовується для:
- контрольних
- тестів
- захищених завдань

---

# 📓 Звичайна робота у Jupyter

Якщо ви хочете просто редагувати ноутбук:

## Windows
1️⃣ Відкрийте папку проєкту  
2️⃣ Затисніть Shift + ПКМ  
3️⃣ "Open PowerShell here"

Виконайте:

.venv\Scripts\activate
jupyter notebook

## Mac/Linux

source .venv/bin/activate
jupyter notebook

---

Після цього відкрийте файл:

04_boolean_logic_and_control/python_lesson_bool_logic_student.ipynb

---

# 🧠 Який режим обрати?

🔹 Якщо потрібно пройти тест → використовуйте start_course  
🔹 Якщо потрібно редагувати код → використовуйте Jupyter

---

# 🔁 Повторний запуск

Windows:
двічі натиснути start_course.bat

Mac/Linux:
python3 start_course.py
