def oops():
    # Викликаємо виняток IndexError
    raise IndexError("Це штучно створений IndexError")

def handle_error():
    try:
        oops()
    except IndexError as e:
        print("Перехоплено помилку:", e)

# Запуск
if __name__ == "__main__":
    handle_error()
