import json

def generate_table(n):
    values = [0, 1, -1]
    num_rows = 3 ** n
    table = []
    for i in range(num_rows):
        row = []
        tmp = i
        for _ in range(n):
            row.append(values[tmp % 3])
            tmp //= 3
        if row.count(1) > 0 and row.count(-1) == 1:
            table.append(row)
    return table

def store_table():
    table_4 = generate_table(4)
    table_5 = generate_table(5)
    table_6 = generate_table(6)
    table_7 = generate_table(7)
    table_8 = generate_table(8)
    table_9 = generate_table(9)
    table_10 = generate_table(10)

    print("Count of rows in table_4:", len(table_4))
    print("Count of rows in table_5:", len(table_5))
    print("Count of rows in table_6:", len(table_6))
    print("Count of rows in table_7:", len(table_7))
    print("Count of rows in table_8:", len(table_8))
    print("Count of rows in table_9:", len(table_9))
    print("Count of rows in table_10:", len(table_10))

    with open("tables.json", 'w') as f:
        json.dump({
            "table_4": table_4,
            "table_5": table_5,
            "table_6": table_6,
            "table_7": table_7,
            "table_8": table_8,
            "table_9": table_9,
            "table_10": table_10
        }, f)

if __name__ == "__main__":
    store_table()