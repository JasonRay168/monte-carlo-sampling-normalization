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
    table_5 = generate_table(5)
    table_6 = generate_table(6)
    table_8 = generate_table(8)

    print("Count of rows in table_5:", len(table_5))
    print("Count of rows in table_6:", len(table_6))
    print("Count of rows in table_8:", len(table_8))
    
    with open("tables.json", 'w') as f:
        json.dump({"table_5": table_5,
        "table_6": table_6,
        "table_8": table_8}, f)

if __name__ == "__main__":
    store_table()