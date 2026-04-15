import tax_09  

def ask_name():
    user_name = input("Як ваше ім'я? ")
    return user_name

def total_price():
    user_amount = float(input("Яка сума покупки (€)? "))
    return user_amount

def main():
    name = ask_name()
    amount = total_price()
    tax_amount = tax_09.import_tax(amount)
    final_amount = amount + tax_amount

    print(f"Hello, {name}!")
    print(f"{name}, ваша сума покупки: {amount:.2f} €")
    print(f"Податок: {tax_amount:.2f} €")
    print(f"Сума з податком: {final_amount:.2f} €")

if __name__ == "__main__":
    main()
