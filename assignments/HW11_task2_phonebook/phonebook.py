import json
import sys

def load_phonebook(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Помилка: файл не знайдено.")
        sys.exit(1)

def save_phonebook(filename, book):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=4)

def add_entry(book, filename):
    name = input("Ім'я: ")
    lastname = input("Прізвище: ")
    phone = input("Телефон: ")
    city = input("Місто: ")
    oblast = input("Область: ")
    book.append({"name": name, "lastname": lastname, "phone": phone, "city": city, "oblast": oblast})
    save_phonebook(filename, book)

def search(book, key, value):
    return [entry for entry in book if entry.get(key, "").lower() == value.lower()]

def delete_entry(book, phone):
    book[:] = [entry for entry in book if entry["phone"] != phone]

def update_entry(book, phone):
    for entry in book:
        if entry["phone"] == phone:
            print("Знайдено:", entry)
            entry["name"] = input("Нове ім'я: ")
            entry["lastname"] = input("Нове прізвище: ")
            entry["city"] = input("Нове місто: ")
            entry["oblast"] = input("Нова область: ")
            