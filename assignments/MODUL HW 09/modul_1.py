def ask_name():
    user_name = input("Як ваше ім'я? ")
    return user_name

def total_price():
    user_amount = float(input("Яка сума покупки (€)? "))
    return user_amount

def main():
    name = ask_name()
    amount = total_price()

    print(f"Hello, {name}!")
    print(f"{name}, ваша сума покупки: {amount:.2f} €")



