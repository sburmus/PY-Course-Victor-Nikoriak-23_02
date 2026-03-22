def import_tax(amount: float) -> float:
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




    
