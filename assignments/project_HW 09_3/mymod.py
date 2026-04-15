def count_lines(name: str) -> int:
    """Підраховує кількість рядків у файлі."""
    with open(name, encoding="utf-8") as f:
        return len(f.readlines())


def count_chars(name: str) -> int:
    """Підраховує кількість символів у файлі."""
    with open(name, encoding="utf-8") as f:
        return len(f.read())


def test(name: str):
    """Викликає обидві функції для заданого файлу."""
    lines = count_lines(name)
    chars = count_chars(name)
    print(f"Файл: {name}")
    print(f"Рядків: {lines}")
    print(f"Символів: {chars}")
