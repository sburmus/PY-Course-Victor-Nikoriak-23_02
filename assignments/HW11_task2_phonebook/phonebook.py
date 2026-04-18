import json
import sys
import os

def load_phonebook(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Файл {filename} не знайдено")
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_phonebook(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_entry(phonebook):
    name = input("Ім'я: ")
    surname = input("Прізвище: ")
    phone = input("Телефон: ")
    city = input("Місто: ")
    state = input("Штат: ")
    phonebook[phone] = {
        "name": name,
        "surname": surname,
        "city": city,
        "state": state
    }

def search(phonebook, key, value):
    results = [entry for entry in phonebook.values() if entry.get(key) == value]
    return results

def delete_entry(phonebook, phone):
    if phone in phonebook:
        del phonebook[phone]

def update_entry(phonebook, phone):
    if phone in phonebook:
        print("Оновлення запису:")
        phonebook[phone]["name"] = input("Нове ім'я: ")
        phonebook[phone]["surname"] = input("Нове прізвище: ")
        phonebook[phone]["city"] = input("Нове місто: ")
        phonebook[phone]["state"] = input("Новий штат: ")

def main():
    if len(sys.argv) < 2:
        print("Використання: python phonebook.py <назва_файлу.json>")
        return

    filename = sys.argv[1]
    try:
        phonebook = load_phonebook(filename)
    except FileNotFoundError:
        print("Файл не знайдено. Створіть його перед запуском.")
        return

    while True:
        print("\nМеню:")
        print("1. Додати запис")
        print("2. Пошук за ім'ям")
        print("3. Пошук за прізвищем")
        print("4. Пошук за повним ім'ям")
        print("5. Пошук за телефоном")
        print("6. Пошук за містом")
        print("7. Видалити запис")
        print("8. Оновити запис")
        print("9. Вихід")

        choice = input("Ваш вибір: ")

        if choice == "1":
            add_entry(phonebook)
        elif choice == "2":
            name = input("Ім'я: ")
            print(search(phonebook, "name", name))
        elif choice == "3":
            surname = input("Прізвище: ")
            print(search(phonebook, "surname", surname))
        elif choice == "4":
            name = input("Ім'я: ")
            surname = input("Прізвище: ")
            results = [entry for entry in phonebook.values() if entry["name"] == name and entry["surname"] == surname]
            print(results)
        elif choice == "5":
            phone = input("Телефон: ")
            print(phonebook.get(phone))
        elif choice == "6":
            city = input("Місто: ")
            print(search(phonebook, "city", city))
        elif choice == "7":
            phone = input("Телефон для видалення: ")
            delete_entry(phonebook, phone)
        elif choice == "8":
            phone = input("Телефон для оновлення: ")
            update_entry(phonebook, phone)
        elif choice == "9":
            save_phonebook(filename, phonebook)
            print("Зміни збережено. Вихід.")
            break
        else:
            print("Невірний вибір.")

if __name__ == "__main__":
    main()
