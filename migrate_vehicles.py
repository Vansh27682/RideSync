
import sqlite3
from contextlib import closing

from database import get_db_connection

LOCAL_DATABASE = "ridesync.db"


def migrate_vehicles():
    source = sqlite3.connect(LOCAL_DATABASE)
    source.row_factory = sqlite3.Row

    vehicles = source.execute("""
        SELECT name, type, brand, model, registration_number,
               price_per_hour, status, image
        FROM vehicles
    """).fetchall()

    source.close()

    if not vehicles:
        print("No vehicles found in local database.")
        return

    with closing(get_db_connection()) as destination:
        for vehicle in vehicles:
            destination.execute("""
                INSERT INTO vehicles
                    (name, type, brand, model, registration_number,
                     price_per_hour, status, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (registration_number) DO NOTHING
            """, tuple(vehicle))

        destination.commit()

        count = destination.execute(
            "SELECT COUNT(*) AS total FROM vehicles"
        ).fetchone()["total"]

    print(f"Migration completed.")
    print(f"Local vehicles read: {len(vehicles)}")
    print(f"Vehicles now in destination database: {count}")


if __name__ == "__main__":
    migrate_vehicles()
