from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import dbf

BRANDS = ["Andes", "Pacifica", "Sierra", "Aurora", "Delta"]
CATEGORIES = ["Bebidas", "Limpieza", "Snacks", "Hogar", "Cuidado Personal"]
CLIENT_ORIGINS = ["Tradicional", "Moderno", "Digital", "Mayoreo"]

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


def _currency_fx(usd_ratio: float) -> tuple[str, float]:
    if random.random() < usd_ratio:
        return "USD", round(random.uniform(16.5, 18.8), 2)
    return "MXN", 1.0


def _write_dbf(path: Path, schema: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    table = dbf.Table(str(path), schema)
    table.open(mode=dbf.READ_WRITE)
    for row in rows:
        table.append(row)
    table.close()


def generate_products(count: int = 300) -> list[dict]:
    productos = []
    for idx in range(1, count + 1):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)
        name = random.choice(PRODUCT_NAMES[category])
        price = round(random.uniform(8, 150), 2)
        productos.append(
            {
                "PROD_ID": idx,
                "PROD_NAME": f"{name} {brand}",
                "BRAND": brand,
                "CATEGORY": category,
                "PRICE": price,
            }
        )
    return productos


def generate_clients(count: int = 150) -> list[dict]:
    clientes = []
    for idx in range(1, count + 1):
        clientes.append(
            {
                "CL_ID": idx,
                "CL_NAME": _random_company(),
                "ORIGIN": random.choice(CLIENT_ORIGINS),
            }
        )
    return clientes


def generate_sellers(count: int = 10) -> list[dict]:
    vendedores = []
    for idx in range(1, count + 1):
        vendedores.append(
            {
                "SELLER_ID": idx,
                "SELLER_NAME": _random_name(),
            }
        )
    return vendedores


def generate_stock(productos: list[dict]) -> list[dict]:
    stock = []
    for producto in productos:
        stock.append({"PROD_ID": producto["PROD_ID"], "ON_HAND": random.randint(15, 600)})
    return stock


def generate_invoices(
    productos: list[dict],
    clientes: list[dict],
    vendedores: list[dict],
    count: int = 1000,
    days: int = 120,
    usd_ratio: float = 0.2,
) -> tuple[list[dict], list[dict], dict[int, float]]:
    invoices = []
    invoice_lines = []
    totals_by_invoice: dict[int, float] = {}
    dates = _date_range(days)

    for inv_id in range(1, count + 1):
        inv_date = random.choice(dates)
        client = random.choice(clientes)
        seller = random.choice(vendedores)
        currency, fx = _currency_fx(usd_ratio)
        invoices.append(
            {
                "INV_ID": inv_id,
                "INV_DATE": inv_date,
                "CL_ID": client["CL_ID"],
                "SELLER_ID": seller["SELLER_ID"],
                "CURRENCY": currency,
                "FX": fx,
            }
        )

        line_count = random.randint(1, 6)
        total = 0.0
        for _ in range(line_count):
            product = random.choice(productos)
            qty = random.randint(1, 20)
            unit_price = round(product["PRICE"] * random.uniform(0.9, 1.15), 2)
            invoice_lines.append(
                {
                    "INV_ID": inv_id,
                    "PROD_ID": product["PROD_ID"],
                    "QTY": qty,
                    "UNIT_PRICE": unit_price,
                }
            )
            total += qty * unit_price
        totals_by_invoice[inv_id] = round(total, 2)

    return invoices, invoice_lines, totals_by_invoice


def _estimate_order_total(
    productos: list[dict],
    line_count: int,
) -> float:
    total = 0.0
    for _ in range(line_count):
        product = random.choice(productos)
        qty = random.randint(1, 15)
        unit_price = round(product["PRICE"] * random.uniform(0.9, 1.1), 2)
        total += qty * unit_price
    return round(total, 2)


def generate_orders(
    productos: list[dict],
    invoices: list[dict],
    invoice_totals: dict[int, float],
    count: int = 1200,
    days: int = 120,
    usd_ratio: float = 0.2,
) -> list[dict]:
    orders = []
    dates = _date_range(days)
    surtir_target = random.randint(int(count * 0.10), int(count * 0.25))
    statuses = ["SURTIR"] * surtir_target + ["FACTURADO"] * (count - surtir_target)
    random.shuffle(statuses)

    for ord_id, status in enumerate(statuses, start=1):

        if status == "FACTURADO":
            invoice = random.choice(invoices)
            inv_date = invoice["INV_DATE"]
            ord_date = inv_date - timedelta(days=random.randint(0, 3))
            currency = invoice["CURRENCY"]
            fx = invoice["FX"]
            total_estimado = invoice_totals.get(invoice["INV_ID"], 0.0)
            cl_id = invoice["CL_ID"]
            seller_id = invoice["SELLER_ID"]
        else:
            ord_date = random.choice(dates)
            currency, fx = _currency_fx(usd_ratio)
            total_estimado = _estimate_order_total(productos, random.randint(1, 5))
            cl_id = random.choice(invoices)["CL_ID"]
            seller_id = random.choice(invoices)["SELLER_ID"]

        orders.append(
            {
                "ORD_ID": ord_id,
                "ORD_DATE": ord_date,
                "CL_ID": cl_id,
                "SELLER_ID": seller_id,
                "STATUS": status,
                "CURRENCY": currency,
                "FX": fx,
                "TOTAL_ESTIMADO": total_estimado,
            }
        )

    return orders


def generate_dataset(output_dir: Path) -> list[tuple[str, int]]:
    productos = generate_products()
    clientes = generate_clients()
    vendedores = generate_sellers()
    stock = generate_stock(productos)
    invoices, invoice_lines, invoice_totals = generate_invoices(productos, clientes, vendedores)
    pedidos = generate_orders(productos, invoices, invoice_totals)

    _write_dbf(
        output_dir / "PRODUCTS.DBF",
        "PROD_ID N(6,0); PROD_NAME C(60); BRAND C(20); CATEGORY C(30); PRICE N(12,2)",
        productos,
    )
    _write_dbf(
        output_dir / "CLIENTS.DBF",
        "CL_ID N(6,0); CL_NAME C(60); ORIGIN C(20)",
        clientes,
    )
    _write_dbf(
        output_dir / "SELLERS.DBF",
        "SELLER_ID N(6,0); SELLER_NAME C(40)",
        vendedores,
    )
    _write_dbf(
        output_dir / "STOCK.DBF",
        "PROD_ID N(6,0); ON_HAND N(8,0)",
        stock,
    )
    _write_dbf(
        output_dir / "INVOICES.DBF",
        "INV_ID N(8,0); INV_DATE D; CL_ID N(6,0); SELLER_ID N(6,0); CURRENCY C(3); FX N(6,2)",
        invoices,
    )
    _write_dbf(
        output_dir / "INVOICE_LINES.DBF",
        "INV_ID N(8,0); PROD_ID N(6,0); QTY N(6,0); UNIT_PRICE N(12,2)",
        invoice_lines,
    )
    _write_dbf(
        output_dir / "PEDIDOS.DBF",
        "ORD_ID N(8,0); ORD_DATE D; CL_ID N(6,0); SELLER_ID N(6,0); STATUS C(12); CURRENCY C(3); FX N(6,2); TOTAL_ESTIMADO N(12,2)",
        pedidos,
    )

    return [
        ("PRODUCTS.DBF", len(productos)),
        ("CLIENTS.DBF", len(clientes)),
        ("SELLERS.DBF", len(vendedores)),
        ("STOCK.DBF", len(stock)),
        ("INVOICES.DBF", len(invoices)),
        ("INVOICE_LINES.DBF", len(invoice_lines)),
        ("PEDIDOS.DBF", len(pedidos)),
    ]


if __name__ == "__main__":
    dbf_dir = Path("dbf")
    summary = generate_dataset(dbf_dir)
    print(f"DBF mock generado en: {dbf_dir.resolve()}")
    print("Resumen de archivos generados:")
    for name, count in summary:
        print(f"- {name}: {count} registros")
