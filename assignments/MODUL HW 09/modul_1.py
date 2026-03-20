def ask_name():
    user_name = input("Як ваше ім'я? ")
    return user_name

print(f"Hello, {ask_name()}!")

def import_tax(country: str, amount: float) -> float:
    """
    Обчислює податок на ввіз товару.
    Якщо сума > 150 євро, податок = 20%.
    Інакше податок = 0.
    """
    if amount > 150:
        tax_rate = 0.20
    else:
        tax_rate = 0.0

    return amount * tax_rate

