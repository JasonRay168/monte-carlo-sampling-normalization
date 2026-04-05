import json


def generate_table(n):
    values = [0, 1, -1]
    num_rows = 3**n
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
    tables = {}
    for i in range(3, 10):
        table_num = i + 1
        table = generate_table(table_num)
        print(f"Count of rows in table_{table_num}:", len(table))
        tables[f"table_{table_num}"] = table

    with open("tables.json", "w") as f:
        json.dump(tables, f)


if __name__ == "__main__":
    store_table()
