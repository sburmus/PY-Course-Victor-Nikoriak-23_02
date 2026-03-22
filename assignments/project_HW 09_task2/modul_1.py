def calculate():
    try:
        a = float(input("Введіть число a: "))
        b = float(input("Введіть число b: "))
        
        result = (a ** 2) / b
        print(f"Результат: {result}")
        return result

    except ValueError:
        print("Помилка: потрібно вводити лише числа.")
    except ZeroDivisionError:
        print("Помилка: не можна ділити на нуль.")

calculate()
