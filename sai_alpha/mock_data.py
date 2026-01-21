from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import dbf

BRANDS = ["Andes", "Pacifica", "Sierra", "Aurora", "Delta"]
CATEGORIES = ["Bebidas", "Limpieza", "Snacks", "Hogar", "Cuidado Personal"]
CHANNELS = ["Retail", "Mayorista", "E-commerce", "Conveniencia"]
REGIONS = ["Norte", "Centro", "Sur", "Occidente", "Oriente"]

PRODUCT_NAMES = {
    "Bebidas": ["Agua Mineral", "Jugo Natural", "Refresco Cola", "Té Frío"],
    "Limpieza": ["Detergente", "Limpiador Multiuso", "Desinfectante", "Jabón Líquido"],
    "Snacks": ["Papas", "Galletas", "Barra Cereal", "Frutos Secos"],
    "Hogar": ["Toalla", "Papel Higiénico", "Velas", "Ambientador"],
    "Cuidado Personal": ["Shampoo", "Crema Corporal", "Jabón de Manos", "Desodorante"],
}

FIRST_NAMES = [
    "Ana",
    "Luis",
    "María",
    "Carlos",
    "Jorge",
    "Sofía",
    "Elena",
    "Camila",
    "Mateo",
    "Diego",
    "Lucía",
    "Valentina",
]

LAST_NAMES = ["Gómez", "López", "Rodríguez", "Pérez", "Martínez", "Santos", "Vega", "Ramírez"]

COMPANY_PREFIX = ["Alimentos", "Distribuciones", "Comercial", "Servicios", "Grupo"]
COMPANY_SUFFIX = ["Andina", "del Pacífico", "Latam", "Sur", "Global", "Norte"]


random.seed(42)


def _random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _random_company() -> str:
    return f"{random.choice(COMPANY_PREFIX)} {random.choice(COMPANY_SUFFIX)}"


def _date_range(days: int) -> Iterable[date]:
    today = date.today()
    for delta in range(days):
        yield today - timedelta(days=delta)


def generate_products(count: int = 60) -> list[dict]:
    products = []
    for idx in range(1, count + 1):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)
        name = random.choice(PRODUCT_NAMES[category])
        price = round(random.uniform(5, 120), 2)
        products.append(
            {
                "PRODUCT_ID": idx,
                "SKU": f"SKU{idx:04d}",
                "PRODUCT_NAME": f"{name} {brand}",
                "CATEGORY": category,
                "BRAND": brand,
                "BASE_PRICE": price,
            }
        )
    return products


def generate_clients(count: int = 45) -> list[dict]:
    clients = []
    for idx in range(1, count + 1):
        clients.append(
            {
                "CLIENT_ID": idx,
                "CLIENT_NAME": _random_company(),
                "REGION": random.choice(REGIONS),
                "CHANNEL": random.choice(CHANNELS),
                "CONTACT": _random_name(),
            }
        )
    return clients


def generate_vendors(count: int = 12) -> list[dict]:
    vendors = []
    for idx in range(1, count + 1):
        vendors.append(
            {
                "VENDOR_ID": idx,
                "VENDOR_NAME": _random_name(),
                "REGION": random.choice(REGIONS),
                "TEAM": random.choice(["A", "B", "C"]),
            }
        )
    return vendors


def generate_sales(
    products: list[dict],
    clients: list[dict],
    vendors: list[dict],
    days: int = 180,
    max_daily_sales: int = 40,
) -> list[dict]:
    sales = []
    sale_id = 1
    for sale_date in _date_range(days):
        daily_sales = random.randint(10, max_daily_sales)
        for _ in range(daily_sales):
            product = random.choice(products)
            client = random.choice(clients)
            vendor = random.choice(vendors)
            quantity = random.randint(1, 12)
            unit_price = round(product["BASE_PRICE"] * random.uniform(0.9, 1.2), 2)
            revenue = round(quantity * unit_price, 2)
            sales.append(
                {
                    "SALE_ID": sale_id,
                    "SALE_DATE": sale_date,
                    "PRODUCT_ID": product["PRODUCT_ID"],
                    "CLIENT_ID": client["CLIENT_ID"],
                    "VENDOR_ID": vendor["VENDOR_ID"],
                    "BRAND": product["BRAND"],
                    "CATEGORY": product["CATEGORY"],
                    "CHANNEL": client["CHANNEL"],
                    "REGION": client["REGION"],
                    "QUANTITY": quantity,
                    "UNIT_PRICE": unit_price,
                    "REVENUE": revenue,
                }
            )
            sale_id += 1
    return sales


def _write_dbf(path: Path, schema: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    table = dbf.Table(str(path), schema)
    table.open(mode=dbf.READ_WRITE)
    for row in rows:
        table.append(row)
    table.close()


def generate_dbf_dataset(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    products = generate_products()
    clients = generate_clients()
    vendors = generate_vendors()
    sales = generate_sales(products, clients, vendors)

    _write_dbf(
        output_dir / "productos.dbf",
        "PRODUCT_ID N(6,0); SKU C(10); PRODUCT_NAME C(60); CATEGORY C(30); BRAND C(30); BASE_PRICE N(10,2)",
        products,
    )
    _write_dbf(
        output_dir / "clientes.dbf",
        "CLIENT_ID N(6,0); CLIENT_NAME C(60); REGION C(20); CHANNEL C(20); CONTACT C(40)",
        clients,
    )
    _write_dbf(
        output_dir / "vendedores.dbf",
        "VENDOR_ID N(6,0); VENDOR_NAME C(40); REGION C(20); TEAM C(5)",
        vendors,
    )
    _write_dbf(
        output_dir / "ventas.dbf",
        "SALE_ID N(8,0); SALE_DATE D; PRODUCT_ID N(6,0); CLIENT_ID N(6,0); VENDOR_ID N(6,0); BRAND C(30); CATEGORY C(30); CHANNEL C(20); REGION C(20); QUANTITY N(6,0); UNIT_PRICE N(10,2); REVENUE N(12,2)",
        sales,
    )

    return {
        "productos": output_dir / "productos.dbf",
        "clientes": output_dir / "clientes.dbf",
        "vendedores": output_dir / "vendedores.dbf",
        "ventas": output_dir / "ventas.dbf",
    }
