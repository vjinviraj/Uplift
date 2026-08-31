from sqlmodel import Session, select

from apps.api.database import engine, create_db_and_tables
from apps.api.models import CompatibilityMap, Product


PRODUCTS = [
    # Games
    {
        "id": "GAME-001",
        "name": "Genshin Impact - Digital Edition",
        "category": "Games",
        "price_paise": 0,
        "currency": "INR",
        "in_stock": True,
        "description": (
            "Open-world action RPG from HoYoverse. "
            "Free-to-play with gacha mechanics."
        ),
    },
    {
        "id": "GAME-002",
        "name": "EA Sports FC 24",
        "category": "Games",
        "price_paise": 449900,
        "currency": "INR",
        "in_stock": True,
        "description": "Football game featuring HyperMotionV technology.",
    },
    {
        "id": "GAME-003",
        "name": "Grand Theft Auto V",
        "category": "Games",
        "price_paise": 249900,
        "currency": "INR",
        "in_stock": True,
        "description": "Open-world action game from Rockstar Games. Includes GTA Online.",
    },
    {
        "id": "GAME-004",
        "name": "Minecraft",
        "category": "Games",
        "price_paise": 199900,
        "currency": "INR",
        "in_stock": True,
        "description": "Sandbox game focused on survival, exploration, and creativity.",
    },
    {
        "id": "GAME-005",
        "name": "Call of Duty: Modern Warfare III",
        "category": "Games",
        "price_paise": 549900,
        "currency": "INR",
        "in_stock": True,
        "description": "Action shooter featuring campaign, multiplayer, and zombies.",
    },
    {
        "id": "GAME-006",
        "name": "The Legend of Zelda: Tears of the Kingdom",
        "category": "Games",
        "price_paise": 499900,
        "currency": "INR",
        "in_stock": True,
        "description": "Open-air adventure game set in the world of Hyrule.",
    },
    {
        "id": "GAME-007",
        "name": "Elden Ring",
        "category": "Games",
        "price_paise": 399900,
        "currency": "INR",
        "in_stock": True,
        "description": "Open-world action RPG with challenging combat and exploration.",
    },
    {
        "id": "GAME-008",
        "name": "God of War Ragnarök",
        "category": "Games",
        "price_paise": 399900,
        "currency": "INR",
        "in_stock": True,
        "description": "Action adventure following Kratos and Atreus through Norse mythology.",
    },
    {
        "id": "GAME-009",
        "name": "Hogwarts Legacy",
        "category": "Games",
        "price_paise": 449900,
        "currency": "INR",
        "in_stock": True,
        "description": "Open-world action RPG set in the wizarding world.",
    },
    {
        "id": "GAME-010",
        "name": "Final Fantasy XVI",
        "category": "Games",
        "price_paise": 479900,
        "currency": "INR",
        "in_stock": True,
        "description": "Action-focused RPG following Clive Rosfield.",
    },

    # Consoles / Hardware
    {
        "id": "CON-001",
        "name": "PlayStation 5 Console",
        "category": "Consoles / Hardware",
        "price_paise": 5499000,
        "currency": "INR",
        "in_stock": True,
        "description": "Disc edition PlayStation 5 console with DualSense controller.",
    },
    {
        "id": "CON-002",
        "name": "Xbox Series X Console",
        "category": "Consoles / Hardware",
        "price_paise": 5599000,
        "currency": "INR",
        "in_stock": True,
        "description": "High-performance Xbox console with 1TB SSD.",
    },
    {
        "id": "CON-003",
        "name": "Nintendo Switch OLED",
        "category": "Consoles / Hardware",
        "price_paise": 3599900,
        "currency": "INR",
        "in_stock": True,
        "description": "Nintendo Switch with a 7-inch OLED display and 64GB storage.",
    },
    {
        "id": "CON-004",
        "name": "Steam Deck 512GB",
        "category": "Consoles / Hardware",
        "price_paise": 4899900,
        "currency": "INR",
        "in_stock": True,
        "description": "Portable PC gaming device with a 512GB NVMe SSD.",
    },
    {
        "id": "CON-005",
        "name": "PlayStation 5 Digital Edition",
        "category": "Consoles / Hardware",
        "price_paise": 4499000,
        "currency": "INR",
        "in_stock": True,
        "description": "Digital-only PlayStation 5 console.",
    },

    # Controllers / Peripherals
    {
        "id": "PER-001",
        "name": "DualSense Wireless Controller",
        "category": "Controllers / Peripherals",
        "price_paise": 599000,
        "currency": "INR",
        "in_stock": True,
        "description": "Wireless PlayStation controller with haptic feedback and adaptive triggers.",
    },
    {
        "id": "PER-002",
        "name": "Xbox Elite Wireless Controller Series 2",
        "category": "Controllers / Peripherals",
        "price_paise": 1599000,
        "currency": "INR",
        "in_stock": True,
        "description": "Premium Xbox controller with adjustable-tension thumbsticks.",
    },
    {
        "id": "PER-003",
        "name": "Nintendo Switch Pro Controller",
        "category": "Controllers / Peripherals",
        "price_paise": 499000,
        "currency": "INR",
        "in_stock": True,
        "description": "Ergonomic Nintendo Switch controller with motion controls and NFC.",
    },
    {
        "id": "PER-004",
        "name": "Razer BlackShark V2 Pro Headset",
        "category": "Controllers / Peripherals",
        "price_paise": 1799900,
        "currency": "INR",
        "in_stock": True,
        "description": "Wireless gaming headset designed for competitive gaming.",
    },
    {
        "id": "PER-005",
        "name": "Logitech G502 X Plus Gaming Mouse",
        "category": "Controllers / Peripherals",
        "price_paise": 1299500,
        "currency": "INR",
        "in_stock": True,
        "description": "Wireless gaming mouse with high-resolution sensor and RGB lighting.",
    },

    # Accessories
    {
        "id": "ACC-001",
        "name": "PS5 DualSense Charging Station",
        "category": "Accessories",
        "price_paise": 259000,
        "currency": "INR",
        "in_stock": True,
        "description": "Charging station designed for two DualSense controllers.",
    },
    {
        "id": "ACC-002",
        "name": "Xbox Rechargeable Battery Pack",
        "category": "Accessories",
        "price_paise": 219900,
        "currency": "INR",
        "in_stock": True,
        "description": "Rechargeable play-and-charge battery accessory for Xbox controllers.",
    },
    {
        "id": "ACC-003",
        "name": "Nintendo Switch Carrying Case",
        "category": "Accessories",
        "price_paise": 179900,
        "currency": "INR",
        "in_stock": True,
        "description": "Protective carrying case for Nintendo Switch with game-card storage.",
    },
    {
        "id": "ACC-004",
        "name": "4K HDMI 2.1 Cable (2m)",
        "category": "Accessories",
        "price_paise": 149900,
        "currency": "INR",
        "in_stock": True,
        "description": "Ultra high-speed HDMI cable for modern gaming displays.",
    },

    # Gaming Merchandise
    {
        "id": "MER-001",
        "name": "Genshin Impact Paimon Plush (30cm)",
        "category": "Gaming Merchandise",
        "price_paise": 249900,
        "currency": "INR",
        "in_stock": True,
        "description": "Genshin Impact Paimon character plush.",
    },
    {
        "id": "MER-002",
        "name": "Genshin Impact Vision Keychain - Pyro Edition",
        "category": "Gaming Merchandise",
        "price_paise": 89900,
        "currency": "INR",
        "in_stock": True,
        "description": "Metal keychain inspired by a Pyro Vision.",
    },
    {
        "id": "MER-003",
        "name": "Genshin Impact Archon War Mousepad (XL)",
        "category": "Gaming Merchandise",
        "price_paise": 149900,
        "currency": "INR",
        "in_stock": True,
        "description": "Large gaming desk mat featuring Genshin Impact-inspired artwork.",
    },

    # Collectibles
    {
        "id": "COL-001",
        "name": "Genshin Impact Raiden Shogun Figure (1/7 Scale)",
        "category": "Collectibles",
        "price_paise": 1899900,
        "currency": "INR",
        "in_stock": True,
        "description": "High-detail collectible figure of Raiden Shogun.",
    },
    {
        "id": "COL-002",
        "name": "Genshin Impact Wanderer Nendoroid",
        "category": "Collectibles",
        "price_paise": 549900,
        "currency": "INR",
        "in_stock": True,
        "description": "Posable collectible figure inspired by Wanderer.",
    },
    {
        "id": "COL-003",
        "name": "Genshin Impact Elemental Burst Art Book",
        "category": "Collectibles",
        "price_paise": 399900,
        "currency": "INR",
        "in_stock": True,
        "description": "Illustrated art book featuring character designs and game artwork.",
    },
]


def relationship(
    product_id: str,
    upsell_product_id: str,
    reason_code: str,
    max_autonomous: bool = False,
) -> dict:
    return {
        "product_id": product_id,
        "upsell_product_id": upsell_product_id,
        "reason_code": reason_code,
        "max_autonomous": max_autonomous,
    }


COMPATIBILITY_MAP = [
    # PS5
    relationship("CON-001", "PER-001", "compatible_with"),
    relationship("CON-001", "ACC-001", "compatible_with"),
    relationship("CON-001", "ACC-004", "compatible_with"),
    relationship("CON-001", "PER-004", "compatible_with"),
    relationship("CON-001", "GAME-008", "frequently_bought_with"),
    relationship("CON-001", "GAME-007", "frequently_bought_with"),
    relationship("CON-001", "GAME-002", "frequently_bought_with"),
    relationship("CON-001", "GAME-003", "frequently_bought_with"),
    relationship("CON-001", "GAME-009", "frequently_bought_with"),

    # PS5 Digital
    relationship("CON-005", "PER-001", "compatible_with"),
    relationship("CON-005", "ACC-001", "compatible_with"),
    relationship("CON-005", "ACC-004", "compatible_with"),
    relationship("CON-005", "PER-004", "compatible_with"),
    relationship("CON-005", "GAME-002", "frequently_bought_with"),
    relationship("CON-005", "GAME-007", "frequently_bought_with"),
    relationship("CON-005", "GAME-008", "frequently_bought_with"),

    # Xbox Series X
    relationship("CON-002", "PER-002", "compatible_with"),
    relationship("CON-002", "PER-004", "compatible_with"),
    relationship("CON-002", "ACC-002", "compatible_with"),
    relationship("CON-002", "ACC-004", "compatible_with"),
    relationship("CON-002", "GAME-002", "frequently_bought_with"),
    relationship("CON-002", "GAME-003", "frequently_bought_with"),
    relationship("CON-002", "GAME-004", "frequently_bought_with"),
    relationship("CON-002", "GAME-005", "frequently_bought_with"),
    relationship("CON-002", "GAME-007", "frequently_bought_with"),
    relationship("CON-002", "GAME-009", "frequently_bought_with"),
    relationship("CON-002", "PER-004", "frequently_bought_with"),

    # Nintendo Switch OLED
    relationship("CON-003", "GAME-006", "compatible_with"),
    relationship("CON-003", "GAME-001", "compatible_with"),
    relationship("CON-003", "PER-003", "compatible_with"),
    relationship("CON-003", "ACC-003", "compatible_with"),
    relationship("CON-003", "PER-004", "compatible_with"),
    relationship("CON-003", "GAME-006", "frequently_bought_with"),
    relationship("CON-003", "GAME-001", "frequently_bought_with"),
    relationship("CON-003", "PER-003", "frequently_bought_with"),
    relationship("CON-003", "ACC-003", "frequently_bought_with"),

    # Steam Deck
    relationship("CON-004", "GAME-003", "compatible_with"),
    relationship("CON-004", "GAME-004", "compatible_with"),
    relationship("CON-004", "GAME-007", "compatible_with"),
    relationship("CON-004", "GAME-009", "compatible_with"),
    relationship("CON-004", "PER-004", "compatible_with"),
    relationship("CON-004", "PER-005", "compatible_with"),
    relationship("CON-004", "ACC-004", "compatible_with"),

    # Genshin
    relationship("GAME-001", "MER-001", "frequently_bought_with"),
    relationship("GAME-001", "MER-002", "frequently_bought_with", True),
    relationship("GAME-001", "MER-003", "frequently_bought_with"),
    relationship("GAME-001", "COL-001", "frequently_bought_with"),
    relationship("GAME-001", "COL-002", "frequently_bought_with"),
    relationship("GAME-001", "COL-003", "frequently_bought_with"),
    relationship("GAME-001", "CON-003", "frequently_bought_with"),

    # Genshin merchandise ecosystem
    relationship("MER-001", "COL-001", "frequently_bought_with"),
    relationship("MER-001", "COL-002", "frequently_bought_with"),
    relationship("MER-001", "MER-002", "frequently_bought_with", True),
    relationship("MER-001", "COL-003", "frequently_bought_with"),
    relationship("MER-002", "MER-001", "frequently_bought_with"),
    relationship("MER-002", "MER-003", "frequently_bought_with"),
    relationship("MER-003", "COL-003", "frequently_bought_with"),
    relationship("MER-003", "MER-001", "frequently_bought_with"),
    relationship("COL-001", "COL-003", "frequently_bought_with"),
    relationship("COL-002", "COL-003", "frequently_bought_with"),

    # Zelda
    relationship("GAME-006", "CON-003", "compatible_with"),
    relationship("GAME-006", "PER-003", "compatible_with"),
    relationship("GAME-006", "CON-003", "frequently_bought_with"),
    relationship("GAME-006", "PER-003", "frequently_bought_with"),
    relationship("GAME-006", "ACC-003", "frequently_bought_with"),

    # EA Sports FC
    relationship("GAME-002", "PER-001", "frequently_bought_with"),
    relationship("GAME-002", "PER-002", "frequently_bought_with"),
    relationship("GAME-002", "PER-004", "frequently_bought_with"),
    relationship("GAME-002", "CON-001", "frequently_bought_with"),
    relationship("GAME-002", "CON-002", "frequently_bought_with"),

    # Call of Duty
    relationship("GAME-005", "PER-004", "frequently_bought_with"),
    relationship("GAME-005", "PER-002", "frequently_bought_with"),
    relationship("GAME-005", "CON-001", "frequently_bought_with"),
    relationship("GAME-005", "CON-002", "frequently_bought_with"),

    # Elden Ring
    relationship("GAME-007", "PER-004", "frequently_bought_with"),
    relationship("GAME-007", "PER-001", "frequently_bought_with"),
    relationship("GAME-007", "CON-001", "frequently_bought_with"),
    relationship("GAME-007", "CON-004", "frequently_bought_with"),
    relationship("GAME-007", "CON-005", "frequently_bought_with"),

    # GTA V
    relationship("GAME-003", "CON-001", "frequently_bought_with"),
    relationship("GAME-003", "CON-002", "frequently_bought_with"),
    relationship("GAME-003", "CON-004", "frequently_bought_with"),
    relationship("GAME-003", "PER-004", "frequently_bought_with"),

    # Minecraft
    relationship("GAME-004", "CON-001", "frequently_bought_with"),
    relationship("GAME-004", "CON-002", "frequently_bought_with"),
    relationship("GAME-004", "CON-004", "frequently_bought_with"),
    relationship("GAME-004", "PER-004", "frequently_bought_with"),

    # Hogwarts Legacy
    relationship("GAME-009", "CON-001", "frequently_bought_with"),
    relationship("GAME-009", "CON-002", "frequently_bought_with"),
    relationship("GAME-009", "CON-004", "frequently_bought_with"),
    relationship("GAME-009", "PER-004", "frequently_bought_with"),

    # God of War
    relationship("GAME-008", "CON-001", "frequently_bought_with"),
    relationship("GAME-008", "CON-005", "frequently_bought_with"),
    relationship("GAME-008", "PER-001", "frequently_bought_with"),
    relationship("GAME-008", "ACC-001", "frequently_bought_with"),
    relationship("GAME-008", "PER-004", "frequently_bought_with"),

    # Final Fantasy XVI
    relationship("GAME-010", "CON-001", "frequently_bought_with"),
    relationship("GAME-010", "CON-005", "frequently_bought_with"),
    relationship("GAME-010", "PER-001", "frequently_bought_with"),
    relationship("GAME-010", "PER-004", "frequently_bought_with"),

    # DualSense
    relationship("PER-001", "ACC-001", "frequently_bought_with"),
    relationship("PER-001", "GAME-008", "frequently_bought_with"),
    relationship("PER-001", "GAME-007", "frequently_bought_with"),
    relationship("PER-001", "GAME-002", "frequently_bought_with"),

    # Xbox Elite Controller
    relationship("PER-002", "GAME-002", "frequently_bought_with"),
    relationship("PER-002", "GAME-005", "frequently_bought_with"),
    relationship("PER-002", "GAME-003", "frequently_bought_with"),

    # Switch Pro Controller
    relationship("PER-003", "GAME-006", "frequently_bought_with"),
    relationship("PER-003", "GAME-001", "frequently_bought_with"),

    # Headset
    relationship("PER-004", "GAME-005", "frequently_bought_with"),
    relationship("PER-004", "GAME-007", "frequently_bought_with"),
    relationship("PER-004", "GAME-002", "frequently_bought_with"),
    relationship("PER-004", "GAME-003", "frequently_bought_with"),
    relationship("PER-004", "GAME-009", "frequently_bought_with"),

    # Gaming mouse
    relationship("PER-005", "GAME-004", "frequently_bought_with"),
    relationship("PER-005", "GAME-009", "frequently_bought_with"),

    # Accessories
    relationship("ACC-001", "PER-001", "compatible_with"),
    relationship("ACC-001", "GAME-008", "frequently_bought_with"),
    relationship("ACC-002", "CON-002", "compatible_with"),
    relationship("ACC-002", "PER-002", "compatible_with"),
    relationship("ACC-003", "CON-003", "compatible_with"),
    relationship("ACC-003", "GAME-006", "frequently_bought_with"),
    relationship("ACC-003", "GAME-001", "frequently_bought_with"),
    relationship("ACC-004", "CON-001", "compatible_with"),
    relationship("ACC-004", "CON-002", "compatible_with"),
    relationship("ACC-004", "CON-003", "compatible_with"),
    relationship("ACC-004", "CON-004", "compatible_with"),
    relationship("ACC-004", "CON-005", "compatible_with"),
]


VALID_REASON_CODES = {"compatible_with", "frequently_bought_with"}
AUTONOMOUS_UPSELL_MAX_PAISE = 100_000


def seed_catalog() -> None:
    create_db_and_tables()

    product_ids = {product["id"] for product in PRODUCTS}

    # Validate seed data before touching the database.
    if len(PRODUCTS) != 30:
        raise ValueError(f"Expected exactly 30 products, found {len(PRODUCTS)}")

    if len(product_ids) != len(PRODUCTS):
        raise ValueError("Duplicate product IDs found in catalog")

    for item in PRODUCTS:
        if item["price_paise"] < 0:
            raise ValueError(f"Negative price found for {item['id']}")

    for mapping in COMPATIBILITY_MAP:
        if mapping["product_id"] not in product_ids:
            raise ValueError(
                f"Unknown source product: {mapping['product_id']}"
            )

        if mapping["upsell_product_id"] not in product_ids:
            raise ValueError(
                f"Unknown target product: {mapping['upsell_product_id']}"
            )

        if mapping["reason_code"] not in VALID_REASON_CODES:
            raise ValueError(
                f"Invalid reason code: {mapping['reason_code']}"
            )

        if mapping["max_autonomous"]:
            target = next(
                product
                for product in PRODUCTS
                if product["id"] == mapping["upsell_product_id"]
            )

            if target["price_paise"] > AUTONOMOUS_UPSELL_MAX_PAISE:
                raise ValueError(
                    f"Autonomous upsell exceeds ₹1,000: "
                    f"{target['id']} = {target['price_paise']} paise"
                )

    with Session(engine) as session:
        # Upsert products by stable product ID.
        existing_products = {
            product.id: product
            for product in session.exec(select(Product)).all()
        }

        for product_data in PRODUCTS:
            product_id = product_data["id"]

            if product_id in existing_products:
                product = existing_products[product_id]

                for field, value in product_data.items():
                    setattr(product, field, value)

                session.add(product)
            else:
                session.add(Product(**product_data))

        session.commit()

        # CompatibilityMap represents the catalog's deterministic graph.
        # Rebuild it from the version-controlled source of truth.
        existing_mappings = session.exec(
            select(CompatibilityMap)
        ).all()

        for mapping in existing_mappings:
            session.delete(mapping)

        session.commit()

        for mapping_data in COMPATIBILITY_MAP:
            session.add(CompatibilityMap(**mapping_data))

        session.commit()

        product_count = len(session.exec(select(Product)).all())
        mapping_count = len(session.exec(select(CompatibilityMap)).all())

    print(
        f"Catalog seeded successfully: "
        f"{product_count} products, {mapping_count} compatibility mappings."
    )


if __name__ == "__main__":
    seed_catalog()