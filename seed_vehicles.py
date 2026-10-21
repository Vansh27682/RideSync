import sqlite3

DATABASE = "ridesync.db"

vehicles = [
    # Scooters
    ("Activa 6G", "Scooter", "Honda", "6G", "UK07RS1001", 40, "available", None),
    ("Jupiter", "Scooter", "TVS", "ZX", "UK07RS1002", 40, "available", None),
    ("Access 125", "Scooter", "Suzuki", "125", "UK07RS1003", 45, "available", None),
    ("Ntorq 125", "Scooter", "TVS", "Race Edition", "UK07RS1004", 50, "available", None),
    ("Dio", "Scooter", "Honda", "Standard", "UK07RS1005", 40, "available", None),
    ("Pleasure Plus", "Scooter", "Hero", "XTEC", "UK07RS1006", 40, "available", None),
    ("Destini 125", "Scooter", "Hero", "XTEC", "UK07RS1007", 45, "available", None),
    ("RayZR 125", "Scooter", "Yamaha", "Fi Hybrid", "UK07RS1008", 50, "available", None),
    ("Avenis 125", "Scooter", "Suzuki", "Standard", "UK07RS1009", 45, "available", None),
    ("Fascino 125", "Scooter", "Yamaha", "Fi Hybrid", "UK07RS1010", 45, "available", None),
    ("Activa 125", "Scooter", "Honda", "H-Smart", "UK07RS1011", 50, "available", None),
    ("Jupiter 125", "Scooter", "TVS", "Disc", "UK07RS1012", 50, "available", None),

    # Bikes
    ("Pulsar 150", "Bike", "Bajaj", "150", "UK07RS2001", 65, "available", None),
    ("Apache RTR 160", "Bike", "TVS", "160 4V", "UK07RS2002", 75, "available", None),
    ("Splendor Plus", "Bike", "Hero", "XTEC", "UK07RS2003", 55, "available", None),
    ("FZ-S", "Bike", "Yamaha", "FI V4", "UK07RS2004", 75, "available", None),
    ("Hunter 350", "Bike", "Royal Enfield", "Metro", "UK07RS2005", 100, "available", None),
    ("Classic 350", "Bike", "Royal Enfield", "Classic", "UK07RS2006", 110, "available", None),
    ("Pulsar NS200", "Bike", "Bajaj", "NS200", "UK07RS2007", 90, "available", None),
    ("Apache RTR 200", "Bike", "TVS", "4V", "UK07RS2008", 90, "available", None)
]

connection = sqlite3.connect(DATABASE)

connection.executemany("""
    INSERT OR IGNORE INTO vehicles
    (name, type, brand, model, registration_number, price_per_hour, status, image)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", vehicles)

connection.commit()

vehicles_data = connection.execute("""
    SELECT id, name, type, price_per_hour, status
    FROM vehicles
""").fetchall()

print("\n--- RideSync Vehicle Database ---")

for vehicle in vehicles_data:
    print(
        f"ID: {vehicle[0]} | "
        f"{vehicle[1]} | "
        f"{vehicle[2]} | "
        f"Rs.{vehicle[3]}/hr | "
        f"{vehicle[4]}"
    )

print(f"\nTotal vehicles: {len(vehicles_data)}")

connection.close()