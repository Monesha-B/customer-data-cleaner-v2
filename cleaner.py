import csv


def read_customers(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


rows = read_customers("data/customers.csv")
print(rows)