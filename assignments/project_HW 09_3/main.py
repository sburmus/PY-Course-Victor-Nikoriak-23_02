import mymod

def main():
    filename = "sample.txt"   
    mymod.test(filename)

if __name__ == "__main__":
 main()

print(mymod.count_lines("sample.txt"))
print(mymod.count_chars("sample.txt"))
mymod.test("sample.txt")