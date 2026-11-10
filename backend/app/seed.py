import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product


DEMO_PRODUCTS = [
    ("AeroBook 14", "Laptops", "Acer", "Lightweight laptop for coding and campus work.", "549.00", 12, {"processor": "Intel Core i5-1335U", "memory": "16 GB", "storage": "512 GB SSD", "display": "14-inch FHD"}),
    ("ThinkPad E14 Gen 5", "Laptops", "Lenovo", "Durable business laptop with a comfortable keyboard.", "699.00", 9, {"processor": "AMD Ryzen 5 7530U", "memory": "16 GB", "storage": "512 GB SSD", "display": "14-inch WUXGA"}),
    ("IdeaPad Slim 5", "Laptops", "Lenovo", "Thin everyday laptop for study and productivity.", "629.00", 15, {"processor": "AMD Ryzen 7 7730U", "memory": "16 GB", "storage": "1 TB SSD", "display": "14-inch OLED"}),
    ("MacBook Air 13", "Laptops", "Apple", "Fanless laptop with long battery life for development.", "1099.00", 7, {"processor": "Apple M3", "memory": "8 GB", "storage": "256 GB SSD", "display": "13.6-inch Retina"}),
    ("VivoBook 15", "Laptops", "ASUS", "Value-focused laptop for classwork and everyday coding.", "479.00", 14, {"processor": "AMD Ryzen 5 7520U", "memory": "16 GB", "storage": "512 GB SSD", "display": "15.6-inch FHD"}),
    ("Pavilion Plus 14", "Laptops", "HP", "OLED laptop with strong performance for creative workloads.", "799.00", 6, {"processor": "Intel Core i7-1355U", "memory": "16 GB", "storage": "1 TB SSD", "display": "14-inch OLED"}),
    ("Galaxy S24", "Phones", "Samsung", "Compact flagship smartphone with a versatile camera.", "799.00", 11, {"processor": "Snapdragon 8 Gen 3", "memory": "8 GB", "storage": "256 GB", "camera": "50 MP"}),
    ("Pixel 8a", "Phones", "Google", "Smartphone with clean Android and computational photography.", "499.00", 13, {"processor": "Google Tensor G3", "memory": "8 GB", "storage": "128 GB", "camera": "64 MP"}),
    ("iPhone 15", "Phones", "Apple", "Reliable smartphone with a bright display and capable cameras.", "799.00", 8, {"processor": "A16 Bionic", "memory": "6 GB", "storage": "128 GB", "camera": "48 MP"}),
    ("Nord 4", "Phones", "OnePlus", "Fast-charging smartphone with a vivid AMOLED display.", "449.00", 10, {"processor": "Snapdragon 7+ Gen 3", "memory": "12 GB", "storage": "256 GB", "camera": "50 MP"}),
    ("QuietComfort Ultra", "Audio", "Bose", "Over-ear headphones with adjustable noise cancellation.", "429.00", 5, {"type": "Over-ear", "noise_cancellation": "Adaptive ANC", "battery": "24 hours", "connectivity": "Bluetooth"}),
    ("WH-1000XM5", "Audio", "Sony", "Premium headphones with detailed sound and noise cancellation.", "349.00", 8, {"type": "Over-ear", "noise_cancellation": "Active ANC", "battery": "30 hours", "connectivity": "Bluetooth"}),
    ("AirPods Pro 2", "Audio", "Apple", "Compact earbuds with noise cancellation and transparency mode.", "249.00", 16, {"type": "In-ear", "noise_cancellation": "Active ANC", "battery": "6 hours", "connectivity": "Bluetooth"}),
    ("Soundcore Space One", "Audio", "Anker", "Affordable wireless headphones for work and travel.", "99.00", 20, {"type": "Over-ear", "noise_cancellation": "Hybrid ANC", "battery": "40 hours", "connectivity": "Bluetooth"}),
    ("iPad Air 11", "Tablets", "Apple", "Versatile tablet for notes, reading and creative projects.", "599.00", 7, {"processor": "Apple M2", "memory": "8 GB", "storage": "128 GB", "display": "11-inch Liquid Retina"}),
    ("Galaxy Tab S9 FE", "Tablets", "Samsung", "Water-resistant tablet with included S Pen.", "449.00", 10, {"processor": "Exynos 1380", "memory": "6 GB", "storage": "128 GB", "display": "10.9-inch LCD"}),
    ("Kindle Paperwhite", "Tablets", "Amazon", "Waterproof e-reader with a glare-free display.", "149.00", 24, {"display": "6.8-inch e-ink", "storage": "16 GB", "battery": "Up to 10 weeks", "waterproof": "IPX8"}),
    ("MX Master 3S", "Accessories", "Logitech", "Ergonomic wireless mouse with precise scrolling.", "99.00", 18, {"type": "Wireless mouse", "connectivity": "Bluetooth / USB receiver", "battery": "Up to 70 days"}),
    ("Keychron K2 Pro", "Accessories", "Keychron", "Compact mechanical keyboard with customizable keys.", "109.00", 12, {"type": "Mechanical keyboard", "layout": "75%", "connectivity": "Bluetooth / USB-C"}),
    ("Dell UltraSharp 27", "Monitors", "Dell", "Color-accurate QHD monitor for desks and creative work.", "429.00", 6, {"size": "27-inch", "resolution": "2560 x 1440", "panel": "IPS", "refresh_rate": "60 Hz"}),
    ("LG UltraGear 27", "Monitors", "LG", "High-refresh gaming monitor with a QHD IPS panel.", "349.00", 9, {"size": "27-inch", "resolution": "2560 x 1440", "panel": "IPS", "refresh_rate": "165 Hz"}),
    ("Anker 737 Power Bank", "Accessories", "Anker", "High-capacity USB-C power bank for laptops and phones.", "129.00", 15, {"capacity": "24000 mAh", "output": "140 W USB-C", "ports": "2 USB-C, 1 USB-A"}),
    ("EcoFlow River 2", "Accessories", "EcoFlow", "Portable power station for travel and backup.", "239.00", 5, {"capacity": "256 Wh", "output": "300 W AC", "charging": "USB-C / AC / solar"}),
    ("Fitbit Charge 6", "Wearables", "Google", "Fitness tracker with heart rate and activity insights.", "159.00", 17, {"display": "AMOLED", "battery": "Up to 7 days", "water_resistance": "5 ATM"}),
]


def seed_products(db: Session) -> None:
    if db.scalar(select(Product.id).limit(1)) is not None:
        return
    for index, row in enumerate(DEMO_PRODUCTS):
        name, category, brand, description, price, stock, specs = row
        db.add(
            Product(
                name=name,
                category=category,
                brand=brand,
                description=description,
                price=Decimal(price),
                stock=stock,
                image_url=f"https://placehold.co/640x480?text={name.replace(' ', '+')}",
                specs_json=json.dumps(specs),
                featured=index < 8,
            )
        )
    db.commit()
