from contextlib import closing

from app import DEFAULT_VEHICLES, get_db_connection, init_db


def seed_vehicles():
    init_db()
    with closing(get_db_connection()) as connection:
        connection.executemany("""
            INSERT OR IGNORE INTO vehicles
                (name, type, brand, model, registration_number,
                 price_per_hour, status, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, DEFAULT_VEHICLES)
        connection.commit()

        vehicles = connection.execute("""
            SELECT id, name, type, price_per_hour, status
            FROM vehicles
            ORDER BY id
        """).fetchall()

    print("\n--- RideSync Vehicle Database ---")
    for vehicle in vehicles:
        print(
            f"ID: {vehicle['id']} | {vehicle['name']} | {vehicle['type']} | "
            f"Rs.{vehicle['price_per_hour']}/hr | {vehicle['status']}"
        )
    print(f"\nTotal vehicles: {len(vehicles)}")


if __name__ == "__main__":
    seed_vehicles()
