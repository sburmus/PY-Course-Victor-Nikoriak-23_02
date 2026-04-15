import sys

# Подивитися стандартні шляхи пошуку модулів
print("Початковий sys.path:")
print(sys.path)

# Додати новий шлях до каталогу з нашим модулем
sys.path.append("practice_sys_path")

print("\nОновлений sys.path:")
print(sys.path)

# Імпортувати модуль із доданого шляху
import modul_1_task2

print(modul_1_task2.hello())


    
