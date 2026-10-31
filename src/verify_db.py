import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "cold_chain.db"


def main():
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}"
        )

    with sqlite3.connect(DATABASE_FILE) as connection:
        products = connection.execute("""
            SELECT product_id, product_name, product_category,
                   min_temperature, max_temperature,
                   min_humidity, max_humidity
            FROM Product
            ORDER BY product_id
        """).fetchall()

        print("=" * 75)
        print("YOTTAFLEX COLD CHAIN - PRODUCT VERIFICATION")
        print("=" * 75)
        print(f"\nTotal products: {len(products)}\n")

        for product in products:
            product_id, name, category, min_t, max_t, min_h, max_h = product

            print(f"Product ID  : {product_id}")
            print(f"Product     : {name}")
            print(f"Category    : {category}")
            print(f"Temperature : {min_t}°C to {max_t}°C")
            print(f"Humidity    : {min_h}% to {max_h}%")
            print("-" * 75)

        if len(products) != 5:
            print("WARNING: Expected 5 products.")
        else:
            print("PRODUCT VERIFICATION: PASSED")


if __name__ == "__main__":
    main()
