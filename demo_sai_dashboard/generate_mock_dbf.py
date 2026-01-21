from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import dbf

BRANDS = ["Andes", "Pacifica", "Sierra", "Aurora", "Delta"]
CATEGORIES = ["Bebidas", "Limpieza", "Snacks", "Hogar", "Cuidado Personal"]
CLIENT_ORIGINS = ["Tradicional", "Moderno", "Digital", "Mayoreo"]
REGIONS = ["Norte", "Centro", "Sur", "Occidente", "Oriente"]

PRODUCT_NAMES = {
    "Bebidas": ["Agua Mineral", "Jugo Natural", "Refresco Cola", "Té Frío"],
    "Limpieza": ["Detergente", "Limpiador", "Desinfectante", "Jabón Líquido"],
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


def _date_range(days: int) -> list[date]:
    today = date.today()
    return [today - timedelta(days=delta) for delta in range(days)]


def _write_dbf(path: Path, schema: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    table = dbf.Table(str(path), schema)
    table.open(mode=dbf.READ_WRITE)
    for row in rows:
        table.append(row)
    table.close()


def generate_productos(count: int = 80) -> list[dict]:
    productos = []
    for idx in range(1, count + 1):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)
        name = random.choice(PRODUCT_NAMES[category])
        base_price = round(random.uniform(8, 150), 2)
        stock_units = random.randint(50, 400)
        productos.append(
            {
                "PRODUCT_ID": idx,
                "SKU": f"SKU{idx:05d}",
                "PRODUCT_NAME": f"{name} {brand}",
                "CATEGORY": category,
                "BRAND": brand,
                "BASE_PRICE": base_price,
                "STOCK_UNITS": stock_units,
            }
        )
    return productos


def generate_clientes(count: int = 60) -> list[dict]:
    clientes = []
    for idx in range(1, count + 1):
        clientes.append(
            {
                "CLIENT_ID": idx,
                "CLIENT_NAME": _random_company(),
                "ORIGIN": random.choice(CLIENT_ORIGINS),
                "REGION": random.choice(REGIONS),
                "CONTACT": _random_name(),
            }
        )
    return clientes


def generate_vendedores(count: int = 14) -> list[dict]:
    vendedores = []
    for idx in range(1, count + 1):
        vendedores.append(
            {
                "VENDOR_ID": idx,
                "VENDOR_NAME": _random_name(),
                "REGION": random.choice(REGIONS),
                "TEAM": random.choice(["A", "B", "C"]),
            }
        )
    return vendedores


def generate_ventas(
    productos: list[dict],
    clientes: list[dict],
    vendedores: list[dict],
    days: int = 200,
    max_daily_sales: int = 45,
) -> list[dict]:
    ventas = []
    sale_id = 1
    for sale_date in _date_range(days):
        daily_sales = random.randint(12, max_daily_sales)
        for _ in range(daily_sales):
            product = random.choice(productos)
            client = random.choice(clientes)
            vendor = random.choice(vendedores)
            quantity = random.randint(1, 14)
            currency = random.choice(["MXN", "USD"])
            fx_rate = 17.5 if currency == "USD" else 1.0
            unit_price = round(product["BASE_PRICE"] * random.uniform(0.9, 1.2), 2)
            total_mxn = round(quantity * unit_price * fx_rate, 2)
            total_usd = round(total_mxn / 17.5, 2)
            ventas.append(
                {
                    "SALE_ID": sale_id,
                    "SALE_DATE": sale_date,
                    "PRODUCT_ID": product["PRODUCT_ID"],
                    "CLIENT_ID": client["CLIENT_ID"],
                    "VENDOR_ID": vendor["VENDOR_ID"],
                    "BRAND": product["BRAND"],
                    "CATEGORY": product["CATEGORY"],
                    "ORIGIN": client["ORIGIN"],
                    "QUANTITY": quantity,
                    "CURRENCY": currency,
                    "TOTAL_MXN": total_mxn,
                    "TOTAL_USD": total_usd,
                }
            )
            sale_id += 1
    return ventas


def generate_pedidos(ventas: list[dict]) -> list[dict]:
    pedidos = []
    pedido_id = 1
    for venta in random.sample(ventas, k=min(len(ventas), 300)):
        status = random.choice(["PENDIENTE", "PARCIAL", "SURTIDO"])
        if status == "SURTIDO":
            continue
        pedidos.append(
            {
                "PEDIDO_ID": pedido_id,
                "SALE_ID": venta["SALE_ID"],
                "CLIENT_ID": venta["CLIENT_ID"],
                "VENDOR_ID": venta["VENDOR_ID"],
                "PEDIDO_DATE": venta["SALE_DATE"],
                "STATUS": status,
                "TOTAL_MXN": venta["TOTAL_MXN"],
            }
        )
        pedido_id += 1
    return pedidos


def generate_dataset(output_dir: Path) -> None:
    productos = generate_productos()
    clientes = generate_clientes()
    vendedores = generate_vendedores()
    ventas = generate_ventas(productos, clientes, vendedores)
    pedidos = generate_pedidos(ventas)

    _write_dbf(
        output_dir / "PRODUCTOS.DBF",
        "PRODUCT_ID N(6,0); SKU C(12); PRODUCT_NAME C(60); CATEGORY C(30); BRAND C(20); BASE_PRICE N(10,2); STOCK_UNITS N(8,0)",
        productos,
    )
    _write_dbf(
        output_dir / "CLIENTES.DBF",
        "CLIENT_ID N(6,0); CLIENT_NAME C(60); ORIGIN C(20); REGION C(20); CONTACT C(40)",
        clientes,
    )
    _write_dbf(
        output_dir / "VENDEDORES.DBF",
        "VENDOR_ID N(6,0); VENDOR_NAME C(40); REGION C(20); TEAM C(5)",
        vendedores,
    )
    _write_dbf(
        output_dir / "VENTAS.DBF",
        "SALE_ID N(8,0); SALE_DATE D; PRODUCT_ID N(6,0); CLIENT_ID N(6,0); VENDOR_ID N(6,0); BRAND C(20); CATEGORY C(30); ORIGIN C(20); QUANTITY N(6,0); CURRENCY C(5); TOTAL_MXN N(12,2); TOTAL_USD N(12,2)",
        ventas,
    )
    _write_dbf(
        output_dir / "PEDIDOS.DBF",
        "PEDIDO_ID N(8,0); SALE_ID N(8,0); CLIENT_ID N(6,0); VENDOR_ID N(6,0); PEDIDO_DATE D; STATUS C(12); TOTAL_MXN N(12,2)",
        pedidos,
    )


if __name__ == "__main__":
    dbf_dir = Path("dbf")
    generate_dataset(dbf_dir)
    print(f"DBF mock generado en: {dbf_dir.resolve()}")
