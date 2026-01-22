from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import dbf

CATEGORIES = ["Abarrotes", "Bebidas", "Botanas", "Lácteos"]
BRANDS_BY_CATEGORY = {
    "Abarrotes": ["Bimbo", "Gamesa", "La Costeña", "Kellogg's", "Nestlé"],
    "Bebidas": ["Coca-Cola", "Pepsi", "Jumex", "Bonafont", "Topo Chico"],
    "Botanas": ["Sabritas", "Barcel", "Doritos", "Cheetos", "Pringles"],
    "Lácteos": ["Lala", "Alpura", "Danone", "Nestlé", "Yoplait"],
}
PRODUCT_NAMES = {
    "Abarrotes": ["Pan de caja", "Galletas surtidas", "Cereal", "Atún", "Arroz", "Pasta"],
    "Bebidas": ["Refresco cola", "Jugo natural", "Agua mineral", "Té frío", "Bebida energética"],
    "Botanas": ["Papas clásicas", "Nachos", "Palomitas", "Botana picosa", "Chips de maíz"],
    "Lácteos": ["Leche entera", "Yogurt natural", "Queso panela", "Crema", "Mantequilla"],
}
PRESENTATIONS = ["250 ml", "355 ml", "500 ml", "1 L", "2 L", "90 g", "200 g", "500 g", "1 kg", "Caja 12"]

REGIONS = ["Norte", "Centro", "Sur", "Occidente", "Oriente"]
CLIENT_ORIGINS = ["Recomendación", "Google", "Facebook", "Volante", "Walk-in", "Marketplace", "Campaña"]
SALE_ORIGINS = ["Mostrador", "Página web", "WhatsApp", "Marketplace", "Teléfono", "App", "Distribuidor"]
RECOMM_SOURCES = [
    "Encuesta NPS",
    "Encuesta post-compra",
    "Recomendación cliente",
    "Google Reviews",
    "Facebook",
    "Sin encuesta",
]

INVOICE_TYPES = ["Factura", "Ticket", "Nota"]
ORDER_TYPES = ["Entrega", "Pickup", "Envío"]
INVOICE_STATUS = ["Emitida", "Cancelada", "Pendiente"]
CREDIT_NOTE_REASONS = ["Devolución", "Descuento", "Producto dañado", "Ajuste comercial"]

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

COMPANY_PREFIX = ["Abarrotes", "Super", "Comercial", "Distribuciones", "Grupo", "Minisúper"]
COMPANY_SUFFIX = ["Central", "del Centro", "Norte", "Express", "Premium", "Metropolitano"]


@dataclass
class ExchangeRateSeries:
    rates: dict[date, float]

    def for_date(self, value: date) -> float:
        return self.rates[value]


def _rng(seed: int = 2024) -> random.Random:
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
    month_factor = 1 + 0.22 * math.sin(2 * math.pi * (current.month - 1) / 12)
    if current.month in (11, 12):
        month_factor *= 1.35
    weekday_factor = 1.05 if current.weekday() < 4 else 0.85
    return month_factor * weekday_factor


def _generate_exchange_rates(start: date, end: date, rng: random.Random) -> ExchangeRateSeries:
    rates: dict[date, float] = {}
    current_rate = 17.8
    for current in _date_range(start, end):
        drift = rng.uniform(-0.06, 0.06)
        current_rate = max(16.2, min(20.4, current_rate + drift))
        rates[current] = round(current_rate, 4)
    return ExchangeRateSeries(rates=rates)


def generate_products(rng: random.Random, count: int = 320) -> list[dict]:
    products = []
    price_ranges = {
        "Abarrotes": (18, 120),
        "Bebidas": (12, 80),
        "Botanas": (10, 70),
        "Lácteos": (15, 95),
    }
    for idx in range(1, count + 1):
        category = rng.choice(CATEGORIES)
        brand = rng.choice(BRANDS_BY_CATEGORY[category])
        name = rng.choice(PRODUCT_NAMES[category])
        presentation = rng.choice(PRESENTATIONS)
        low, high = price_ranges[category]
        price = round(rng.uniform(low, high), 2)
        cost = round(price * rng.uniform(0.55, 0.75), 2)
        products.append(
            {
                "PRODUCT_ID": idx,
                "SKU": f"SKU{idx:05d}",
                "PRODUCT_NAME": f"{name} {presentation} {brand}",
                "CATEGORY": category,
                "BRAND": brand,
                "COST_MXN": cost,
                "PRICE_MXN": price,
                "STOCK_QTY": 0,
                "MIN_STK": 0,
                "MAX_STK": 0,
            }
        )
    return products


def generate_clients(rng: random.Random, count: int = 420) -> list[dict]:
    clients = []
    for idx in range(1, count + 1):
        clients.append(
            {
                "CLIENT_ID": idx,
                "CLNT_NAME": _random_company(rng),
                "REGION": rng.choice(REGIONS),
                "ORIGEN_CLI": rng.choice(CLIENT_ORIGINS),
                "RECOM_SRC": rng.choice(RECOMM_SOURCES),
                "CONTACT": _random_name(rng),
                "STATUS": rng.choice(["Activo", "Inactivo"]),
                "LAST_PCH": None,
            }
        )
    return clients


def generate_vendors(rng: random.Random, count: int = 10) -> list[dict]:
    vendors = []
    for idx in range(1, count + 1):
        name = _random_name(rng)
        vendors.append(
            {
                "SELLER_ID": idx,
                "SELLER_NM": name,
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
) -> tuple[list[dict], list[dict]]:
    sales: list[dict] = []
    facturas: list[dict] = []
    sale_id = 1
    factura_id = 100000
    product_weights = [rng.uniform(0.8, 1.2) for _ in products]
    client_weights = [rng.uniform(0.6, 1.8) for _ in clients]
    vendor_weights = [rng.uniform(0.9, 1.4) for _ in vendors]

    for sale_date in _date_range(start, end):
        seasonality = _seasonality_factor(sale_date)
        base_invoices = 40
        invoice_noise = rng.gauss(0, 5)
        daily_invoices = max(15, int(base_invoices * seasonality + invoice_noise))
        for _ in range(daily_invoices):
            client = rng.choices(clients, weights=client_weights, k=1)[0]
            vendor = rng.choices(vendors, weights=vendor_weights, k=1)[0]
            rate = exchange_rates.for_date(sale_date)
            currency = "USD" if rng.random() < 0.15 else "MXN"
            status = rng.choices(INVOICE_STATUS, weights=[0.8, 0.08, 0.12], k=1)[0]
            invoice_type = rng.choice(INVOICE_TYPES)
            order_type = rng.choice(ORDER_TYPES)
            origin = rng.choice(SALE_ORIGINS)
            recomm = rng.choice(RECOMM_SOURCES)
            line_count = rng.randint(1, 5)
            subtotal_mxn = 0.0

            for _ in range(line_count):
                product = rng.choices(products, weights=product_weights, k=1)[0]
                quantity = rng.randint(1, 14)
                unit_price = round(product["PRICE_MXN"] * rng.uniform(0.85, 1.18), 2)
                amount_mxn = round(quantity * unit_price, 2)
                amount_usd = round(amount_mxn / rate, 2)
                sales.append(
                    {
                        "SALE_ID": sale_id,
                        "FACT_ID": factura_id,
                        "SALE_DATE": sale_date,
                        "PRODUCT_ID": product["PRODUCT_ID"],
                        "PRODUCT_NAME": product["PRODUCT_NAME"],
                        "BRAND": product["BRAND"],
                        "CATEGORY": product["CATEGORY"],
                        "CLIENT_ID": client["CLIENT_ID"],
                        "CLNT_NAME": client["CLNT_NAME"],
                        "CLNT_ORIG": client["ORIGEN_CLI"],
                        "SELLER_ID": vendor["SELLER_ID"],
                        "SELLER_NM": vendor["SELLER_NM"],
                        "ORIGEN_VT": origin,
                        "RECOM_SRC": recomm,
                        "TIPO_FACT": invoice_type,
                        "TIPO_ORDN": order_type,
                        "STATUS": status,
                        "QTY": quantity,
                        "UNIT_MXN": unit_price,
                        "AMT_MXN": amount_mxn,
                        "AMT_USD": amount_usd,
                        "MONEDA": currency,
                        "USD_MXN": rate,
                    }
                )
                sale_id += 1
                subtotal_mxn += amount_mxn

            facturas.append(
                {
                    "FACT_ID": factura_id,
                    "FECHA": sale_date,
                    "CLIENT_ID": client["CLIENT_ID"],
                    "CLNT_NAME": client["CLNT_NAME"],
                    "SELLER_ID": vendor["SELLER_ID"],
                    "SELLER_NM": vendor["SELLER_NM"],
                    "STATUS": status,
                    "TIPO_FACT": invoice_type,
                    "TIPO_ORDN": order_type,
                    "ORIGEN_VT": origin,
                    "RECOM_SRC": recomm,
                    "MONEDA": currency,
                    "SUBT_MXN": round(subtotal_mxn, 2),
                    "TOTAL_MXN": round(subtotal_mxn * 1.16, 2),
                    "AMT_USD": round(subtotal_mxn / rate, 2),
                    "USD_MXN": rate,
                }
            )
            factura_id += 1
    return sales, facturas


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
        daily_orders = max(6, int(rng.gauss(12, 4)))
        for _ in range(daily_orders):
            product = rng.choice(products)
            client = rng.choice(clients)
            vendor = rng.choice(vendors)
            qty_order = rng.randint(1, 20)
            status = rng.choices(["Surtido", "Parcial", "Pendiente", "Cancelado"], weights=[0.55, 0.2, 0.2, 0.05], k=1)[0]
            qty_pending = qty_order if status == "Pendiente" else rng.randint(0, max(0, qty_order - 1))
            pedidos.append(
                {
                    "ORDER_ID": order_id,
                    "ORDER_DATE": order_date,
                    "CLIENT_ID": client["CLIENT_ID"],
                    "CLNT_NAME": client["CLNT_NAME"],
                    "SELLER_ID": vendor["SELLER_ID"],
                    "SELLER_NM": vendor["SELLER_NM"],
                    "PRODUCT_ID": product["PRODUCT_ID"],
                    "PRODUCT_NAME": product["PRODUCT_NAME"],
                    "QTY_ORDER": qty_order,
                    "QTY_PEND": qty_pending,
                    "STATUS": status,
                    "ORIGEN_VT": rng.choice(SALE_ORIGINS),
                    "TIPO_ORDN": rng.choice(ORDER_TYPES),
                }
            )
            order_id += 1
    return pedidos


def generate_notas_credito(
    rng: random.Random,
    facturas: list[dict],
    start: date,
    end: date,
) -> list[dict]:
    notes = []
    note_id = 5000
    eligible = [invoice for invoice in facturas if invoice["STATUS"] == "Emitida"]
    sample = rng.sample(eligible, k=max(1, int(len(eligible) * 0.04)))
    for invoice in sample:
        note_date = invoice["FECHA"] + timedelta(days=rng.randint(1, 18))
        if note_date > end:
            note_date = end
        notes.append(
            {
                "NOTA_ID": note_id,
                "FACT_ID": invoice["FACT_ID"],
                "FECHA": note_date,
                "CLIENT_ID": invoice["CLIENT_ID"],
                "MONTO_MXN": round(invoice["SUBT_MXN"] * rng.uniform(0.05, 0.2), 2),
                "MOTIVO": rng.choice(CREDIT_NOTE_REASONS),
            }
        )
        note_id += 1
    return notes


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
        sold_by_product[sale["PRODUCT_ID"]] = sold_by_product.get(sale["PRODUCT_ID"], 0) + sale["QTY"]
    for product in products:
        sold_units = sold_by_product.get(product["PRODUCT_ID"], 0)
        base_stock = max(20, int(sold_units * rng.uniform(0.8, 1.6) + rng.randint(30, 200)))
        min_stock = max(8, int(base_stock * rng.uniform(0.15, 0.25)))
        max_stock = int(base_stock * rng.uniform(1.3, 1.8))
        product["STOCK_QTY"] = base_stock
        product["MIN_STK"] = min_stock
        product["MAX_STK"] = max_stock


def _assign_client_last_purchase(rng: random.Random, clients: list[dict], sales: list[dict], end: date) -> None:
    last_purchase: dict[int, date] = {}
    for sale in sales:
        client_id = sale["CLIENT_ID"]
        sale_date = sale["SALE_DATE"]
        if client_id not in last_purchase or sale_date > last_purchase[client_id]:
            last_purchase[client_id] = sale_date
    for client in clients:
        client["LAST_PCH"] = last_purchase.get(client["CLIENT_ID"], end - timedelta(days=rng.randint(120, 900)))


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
    end_date = date(2026, 1, 31)
    start_date = end_date - timedelta(days=365 * 4)

    products = generate_products(rng)
    clients = generate_clients(rng)
    vendors = generate_vendors(rng)
    exchange_rates = _generate_exchange_rates(start_date, end_date, rng)
    sales, facturas = generate_sales(rng, products, clients, vendors, start_date, end_date, exchange_rates)
    pedidos = generate_pedidos(rng, products, clients, vendors, end_date - timedelta(days=120), end_date)
    notas_credito = generate_notas_credito(rng, facturas, start_date, end_date)

    _assign_stock(rng, products, sales, end_date)
    _assign_client_last_purchase(rng, clients, sales, end_date)

    _write_dbf(
        output_dir / "productos.dbf",
        "PRODUCT_ID N(6,0); SKU C(12); PRODUCT_NAME C(70); CATEGORY C(20); BRAND C(20); "
        "COST_MXN N(10,2); PRICE_MXN N(10,2); STOCK_QTY N(8,0); MIN_STK N(6,0); MAX_STK N(6,0)",
        products,
    )
    _write_dbf(
        output_dir / "clientes.dbf",
        "CLIENT_ID N(6,0); CLNT_NAME C(60); REGION C(20); ORIGEN_CLI C(25); "
        "RECOM_SRC C(30); CONTACT C(40); STATUS C(12); LAST_PCH D",
        clients,
    )
    _write_dbf(
        output_dir / "vendedores.dbf",
        "SELLER_ID N(6,0); SELLER_NM C(40); REGION C(20); TEAM C(5)",
        vendors,
    )
    _write_dbf(
        output_dir / "ventas.dbf",
        "SALE_ID N(10,0); FACT_ID N(10,0); SALE_DATE D; PRODUCT_ID N(6,0); "
        "PRODUCT_NAME C(70); BRAND C(20); CATEGORY C(20); CLIENT_ID N(6,0); "
        "CLNT_NAME C(60); CLNT_ORIG C(25); SELLER_ID N(6,0); SELLER_NM C(40); "
        "ORIGEN_VT C(20); RECOM_SRC C(30); TIPO_FACT C(12); TIPO_ORDN C(12); "
        "STATUS C(12); QTY N(6,0); UNIT_MXN N(10,2); AMT_MXN N(12,2); "
        "AMT_USD N(12,2); MONEDA C(3); USD_MXN N(8,4)",
        sales,
    )
    _write_dbf(
        output_dir / "tipo_cambio.dbf",
        "DATE D; USD_MXN N(8,4)",
        [{"DATE": k, "USD_MXN": v} for k, v in exchange_rates.rates.items()],
    )
    _write_dbf(
        output_dir / "facturas.dbf",
        "FACT_ID N(10,0); FECHA D; CLIENT_ID N(6,0); CLNT_NAME C(60); "
        "SELLER_ID N(6,0); SELLER_NM C(40); STATUS C(12); TIPO_FACT C(12); "
        "TIPO_ORDN C(12); ORIGEN_VT C(20); RECOM_SRC C(30); MONEDA C(3); "
        "SUBT_MXN N(12,2); TOTAL_MXN N(12,2); AMT_USD N(12,2); USD_MXN N(8,4)",
        facturas,
    )
    _write_dbf(
        output_dir / "notas_credito.dbf",
        "NOTA_ID N(10,0); FACT_ID N(10,0); FECHA D; CLIENT_ID N(6,0); MONTO_MXN N(12,2); "
        "MOTIVO C(30)",
        notas_credito,
    )
    _write_dbf(
        output_dir / "pedidos.dbf",
        "ORDER_ID N(10,0); ORDER_DATE D; CLIENT_ID N(6,0); CLNT_NAME C(60); "
        "SELLER_ID N(6,0); SELLER_NM C(40); PRODUCT_ID N(6,0); PRODUCT_NAME C(70); "
        "QTY_ORDER N(6,0); QTY_PEND N(6,0); STATUS C(12); ORIGEN_VT C(20); TIPO_ORDN C(12)",
        pedidos,
    )

    return {
        "productos": output_dir / "productos.dbf",
        "clientes": output_dir / "clientes.dbf",
        "vendedores": output_dir / "vendedores.dbf",
        "ventas": output_dir / "ventas.dbf",
        "tipo_cambio": output_dir / "tipo_cambio.dbf",
        "facturas": output_dir / "facturas.dbf",
        "notas_credito": output_dir / "notas_credito.dbf",
        "pedidos": output_dir / "pedidos.dbf",
    }
