from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import dbf

BRANDS = [
    "Andes",
    "Pacifica",
    "Sierra",
    "Aurora",
    "Delta",
    "Altiplano",
    "Brisa",
    "Cumbres",
    "Laguna",
    "Montaña",
    "Océano",
    "Nativo",
    "Solaria",
    "Fresca",
    "Quetzal",
    "Riviera",
    "Vértice",
    "Néctar",
    "Horizonte",
    "Tundra",
]
CATEGORIES = ["Bebidas", "Limpieza", "Snacks", "Hogar", "Cuidado Personal"]
CHANNELS = ["Retail", "Mayorista", "E-commerce", "Conveniencia", "Distribuidor"]
REGIONS = ["Norte", "Centro", "Sur", "Occidente", "Oriente"]
CLIENT_ORIGINS = ["Nuevo", "Existente", "Web", "Recomendación", "Campaña", "Mostrador", "Distribuidor"]
SALE_ORIGINS = ["Web", "Tienda", "WhatsApp", "Teléfono", "Vendedor", "Marketplace", "Recomendación"]
INVOICE_TYPES = ["Contado", "Crédito", "Nota", "Factura"]
ORDER_TYPES = ["Pedido", "Remisión", "Cotización", "Backorder"]
ORDER_STATUS = ["Surtido", "Parcial", "Pendiente", "Cancelado"]

PRODUCT_NAMES = {
    "Bebidas": ["Agua Mineral", "Jugo Natural", "Refresco Cola", "Té Frío", "Bebida Energética"],
    "Limpieza": ["Detergente", "Limpiador Multiuso", "Desinfectante", "Jabón Líquido", "Lavavajillas"],
    "Snacks": ["Papas", "Galletas", "Barra Cereal", "Frutos Secos", "Granola"],
    "Hogar": ["Toalla", "Papel Higiénico", "Velas", "Ambientador", "Servilletas"],
    "Cuidado Personal": ["Shampoo", "Crema Corporal", "Jabón de Manos", "Desodorante", "Acondicionador"],
}

PRESENTATIONS = ["250ml", "500ml", "1L", "2L", "500g", "1kg", "2kg", "Caja 12", "Caja 24"]

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
    "Regina",
    "Pablo",
    "Fernanda",
    "Iván",
]

LAST_NAMES = ["Gómez", "López", "Rodríguez", "Pérez", "Martínez", "Santos", "Vega", "Ramírez"]

COMPANY_PREFIX = ["Alimentos", "Distribuciones", "Comercial", "Servicios", "Grupo", "Mayoreo"]
COMPANY_SUFFIX = ["Andina", "del Pacífico", "Latam", "Sur", "Global", "Norte", "Metropolitano"]


@dataclass
class ExchangeRateSeries:
    rates: dict[date, float]

    def for_date(self, value: date) -> float:
        return self.rates[value]


def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def _random_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _random_company(rng: random.Random) -> str:
    return f"{rng.choice(COMPANY_PREFIX)} {rng.choice(COMPANY_SUFFIX)}"


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _seasonality_factor(current: date) -> float:
    month_factor = 1 + 0.18 * math.sin(2 * math.pi * (current.month - 1) / 12)
    weekday = current.weekday()
    weekday_factor = 1.1 if weekday in (0, 1, 2, 3) else 0.9 if weekday == 4 else 0.7
    return month_factor * weekday_factor


def _generate_exchange_rates(start: date, end: date, rng: random.Random) -> ExchangeRateSeries:
    rates: dict[date, float] = {}
    current_rate = 18.2
    for current in _date_range(start, end):
        drift = rng.uniform(-0.08, 0.08)
        current_rate = max(16.0, min(20.5, current_rate + drift))
        rates[current] = round(current_rate, 4)
    return ExchangeRateSeries(rates=rates)


def generate_products(rng: random.Random, count: int = 2000) -> list[dict]:
    products = []
    for idx in range(1, count + 1):
        category = rng.choice(CATEGORIES)
        brand = rng.choice(BRANDS)
        name = rng.choice(PRODUCT_NAMES[category])
        presentation = rng.choice(PRESENTATIONS)
        base_price = round(rng.uniform(8, 180), 2)
        products.append(
            {
                "PRODUCT_ID": idx,
                "SKU": f"SKU{idx:05d}",
                "PROD_NAME": f"{name} {presentation} {brand}",
                "CATEGORY": category,
                "BRAND": brand,
                "BASE_PRICE": base_price,
                "EXISTENCIA": 0,
                "MIN_STOCK": 0,
                "MAX_STOCK": 0,
            }
        )
    return products


def generate_clients(rng: random.Random, count: int = 650) -> list[dict]:
    clients = []
    for idx in range(1, count + 1):
        clients.append(
            {
                "CLIENT_ID": idx,
                "CLNT_NAME": _random_company(rng),
                "REGION": rng.choice(REGIONS),
                "CHANNEL": rng.choice(CHANNELS),
                "CONTACT": _random_name(rng),
                "ORIGEN_CLI": rng.choice(CLIENT_ORIGINS),
                "LAST_PURCH": None,
                "STATUS": rng.choice(["Activo", "Inactivo"]),
            }
        )
    return clients


def generate_vendors(rng: random.Random, count: int = 11) -> list[dict]:
    vendors = []
    for idx in range(1, count + 1):
        name = _random_name(rng)
        if idx == count:
            name = "VENTAS GENERALES"
        vendors.append(
            {
                "VENDOR_ID": idx,
                "VEND_NAME": name,
                "REGION": rng.choice(REGIONS),
                "TEAM": rng.choice(["A", "B", "C"]),
            }
        )
    return vendors


def generate_sales(
    rng: random.Random,
    products: list[dict],
    clients: list[dict],
    vendors: list[dict],
    start: date,
    end: date,
    exchange_rates: ExchangeRateSeries,
) -> list[dict]:
    sales = []
    sale_id = 1
    product_weights = [rng.uniform(0.8, 1.2) for _ in products]
    client_weights = [rng.uniform(0.5, 1.8) for _ in clients]
    vendor_weights = [rng.uniform(0.8, 1.4) for _ in vendors]

    for sale_date in _date_range(start, end):
        seasonality = _seasonality_factor(sale_date)
        daily_base = 65
        daily_noise = rng.gauss(0, 8)
        daily_sales = max(18, int(daily_base * seasonality + daily_noise))
        for _ in range(daily_sales):
            product = rng.choices(products, weights=product_weights, k=1)[0]
            client = rng.choices(clients, weights=client_weights, k=1)[0]
            vendor = rng.choices(vendors, weights=vendor_weights, k=1)[0]
            quantity = rng.randint(1, 14)
            unit_price = round(product["BASE_PRICE"] * rng.uniform(0.9, 1.15), 2)
            revenue_mxn = round(quantity * unit_price, 2)
            tc_rate = exchange_rates.for_date(sale_date)
            moneda = "USD" if rng.random() < 0.18 else "MXN"
            if moneda == "USD":
                revenue_usd = round(revenue_mxn / tc_rate, 2)
            else:
                revenue_usd = round(revenue_mxn / tc_rate, 2)
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
                    "ORIGEN_VTA": rng.choice(SALE_ORIGINS),
                    "TIPO_FACT": rng.choice(INVOICE_TYPES),
                    "TIPO_ORDEN": rng.choice(ORDER_TYPES),
                    "MONEDA": moneda,
                    "TC_MXN_USD": tc_rate,
                    "QUANTITY": quantity,
                    "UNIT_PRICE": unit_price,
                    "REVENUE": revenue_mxn,
                    "REV_USD": revenue_usd,
                }
            )
            sale_id += 1
    return sales


def generate_pedidos(
    rng: random.Random,
    products: list[dict],
    clients: list[dict],
    vendors: list[dict],
    start: date,
    end: date,
) -> list[dict]:
    pedidos = []
    order_id = 1
    for order_date in _date_range(start, end):
        daily_orders = max(6, int(rng.gauss(10, 3)))
        for _ in range(daily_orders):
            product = rng.choice(products)
            client = rng.choice(clients)
            vendor = rng.choice(vendors)
            qty_order = rng.randint(1, 20)
            status = rng.choices(ORDER_STATUS, weights=[0.55, 0.2, 0.2, 0.05], k=1)[0]
            if status == "Parcial":
                qty_pending = rng.randint(1, max(1, qty_order - 1))
            elif status == "Pendiente":
                qty_pending = qty_order
            else:
                qty_pending = 0
            pedidos.append(
                {
                    "ORDER_ID": order_id,
                    "ORDER_DATE": order_date,
                    "CLIENT_ID": client["CLIENT_ID"],
                    "VENDOR_ID": vendor["VENDOR_ID"],
                    "PRODUCT_ID": product["PRODUCT_ID"],
                    "QTY_ORDER": qty_order,
                    "QTY_PEND": qty_pending,
                    "STATUS": status,
                    "ORIGEN_VTA": rng.choice(SALE_ORIGINS),
                    "TIPO_ORDEN": rng.choice(ORDER_TYPES),
                }
            )
            order_id += 1
    return pedidos


def _assign_stock(
    rng: random.Random,
    products: list[dict],
    sales: list[dict],
    end: date,
) -> None:
    recent_start = end - timedelta(days=30)
    sold_by_product: dict[int, int] = {}
    for sale in sales:
        if sale["SALE_DATE"] < recent_start:
            continue
        sold_by_product[sale["PRODUCT_ID"]] = sold_by_product.get(sale["PRODUCT_ID"], 0) + sale["QUANTITY"]
    for product in products:
        sold_units = sold_by_product.get(product["PRODUCT_ID"], 0)
        base_stock = max(15, int(sold_units * rng.uniform(0.8, 1.6) + rng.randint(20, 180)))
        min_stock = max(5, int(base_stock * rng.uniform(0.15, 0.25)))
        max_stock = int(base_stock * rng.uniform(1.3, 1.8))
        product["EXISTENCIA"] = base_stock
        product["MIN_STOCK"] = min_stock
        product["MAX_STOCK"] = max_stock


def _assign_client_last_purchase(rng: random.Random, clients: list[dict], sales: list[dict], end: date) -> None:
    last_purchase: dict[int, date] = {}
    for sale in sales:
        client_id = sale["CLIENT_ID"]
        sale_date = sale["SALE_DATE"]
        if client_id not in last_purchase or sale_date > last_purchase[client_id]:
            last_purchase[client_id] = sale_date
    for client in clients:
        client["LAST_PURCH"] = last_purchase.get(
            client["CLIENT_ID"], end - timedelta(days=rng.randint(120, 900))
        )


def _write_dbf(path: Path, schema: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    table = dbf.Table(str(path), schema, dbf_type="vfp", codepage="cp1252")
    table.open(mode=dbf.READ_WRITE)
    for row in rows:
        table.append(row)
    table.close()


def generate_dbf_dataset(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = _rng()
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 4)

    products = generate_products(rng)
    clients = generate_clients(rng)
    vendors = generate_vendors(rng)
    exchange_rates = _generate_exchange_rates(start_date, end_date, rng)
    sales = generate_sales(rng, products, clients, vendors, start_date, end_date, exchange_rates)
    pedidos = generate_pedidos(rng, products, clients, vendors, end_date - timedelta(days=120), end_date)

    _assign_stock(rng, products, sales, end_date)
    _assign_client_last_purchase(rng, clients, sales, end_date)

    _write_dbf(
        output_dir / "productos.dbf",
        "PRODUCT_ID N(6,0); SKU C(12); PROD_NAME C(60); CATEGORY C(30); BRAND C(30); BASE_PRICE N(10,2); "
        "EXISTENCIA N(8,0); MIN_STOCK N(6,0); MAX_STOCK N(6,0)",
        products,
    )
    _write_dbf(
        output_dir / "clientes.dbf",
        "CLIENT_ID N(6,0); CLNT_NAME C(60); REGION C(20); CHANNEL C(20); CONTACT C(40); "
        "ORIGEN_CLI C(20); LAST_PURCH D; STATUS C(12)",
        clients,
    )
    _write_dbf(
        output_dir / "vendedores.dbf",
        "VENDOR_ID N(6,0); VEND_NAME C(40); REGION C(20); TEAM C(5)",
        vendors,
    )
    _write_dbf(
        output_dir / "ventas.dbf",
        "SALE_ID N(10,0); SALE_DATE D; PRODUCT_ID N(6,0); CLIENT_ID N(6,0); VENDOR_ID N(6,0); "
        "BRAND C(30); CATEGORY C(30); CHANNEL C(20); REGION C(20); ORIGEN_VTA C(20); "
        "TIPO_FACT C(15); TIPO_ORDEN C(15); MONEDA C(3); TC_MXN_USD N(8,4); "
        "QUANTITY N(6,0); UNIT_PRICE N(10,2); REVENUE N(12,2); REV_USD N(12,2)",
        sales,
    )
    _write_dbf(
        output_dir / "tcambio.dbf",
        "FECHA D; TC_MXN_USD N(8,4)",
        [{"FECHA": k, "TC_MXN_USD": v} for k, v in exchange_rates.rates.items()],
    )
    _write_dbf(
        output_dir / "pedidos.dbf",
        "ORDER_ID N(10,0); ORDER_DATE D; CLIENT_ID N(6,0); VENDOR_ID N(6,0); PRODUCT_ID N(6,0); "
        "QTY_ORDER N(6,0); QTY_PEND N(6,0); STATUS C(12); ORIGEN_VTA C(20); TIPO_ORDEN C(15)",
        pedidos,
    )

    return {
        "productos": output_dir / "productos.dbf",
        "clientes": output_dir / "clientes.dbf",
        "vendedores": output_dir / "vendedores.dbf",
        "ventas": output_dir / "ventas.dbf",
        "tcambio": output_dir / "tcambio.dbf",
        "pedidos": output_dir / "pedidos.dbf",
    }
