Demo Tienda – Dashboard Ejecutivo (DBF + Streamlit)

## One-click run (Windows)
1. Doble click en `run_demo.bat` (crea venv, instala dependencias, genera DBFs y lanza Streamlit).
2. Si usas el staging portable, ejecuta directamente `build\staging\StartDemo.cmd`.

La app mostrará la URL local y la URL LAN para compartir el demo.

## Binary-free (sin archivos binarios en git)
- Los DBFs se generan localmente en el primer arranque y están ignorados por git.
- No se versionan binarios (`.dbf`, `.png`, `.zip`, `.exe`, etc.). Solo archivos de texto.
- Si necesitas limpiar datos locales, borra `data/dbf` y vuelve a ejecutar el demo.

### Troubleshooting
- Si faltan datos, ejecuta `python generate_dbfs.py` para regenerar DBFs.
- Si hay errores de dependencias, elimina `.venv` y vuelve a correr `run_demo.bat`.

## Mock Dataset (4 años, determinista)
El generador de DBF (`generate_dbfs.py`) crea un set determinista con 4 años de datos diarios
terminando en 2026-01-31:

- 300+ SKU con marca, categoría, costo, precio y stock.
- 400+ clientes con origen y recomendación/encuesta.
- 10 vendedores estables.
- Ventas diarias con estacionalidad (picos Nov-Dic).
- Tipo de cambio diario USD/MXN.

Para verificar rápidamente el dataset generado:
```bash
python verify_dbfs.py
```

## DBFs generados y schema breve
Los archivos se generan en `data/dbf` (o `app/data/dbf` en staging):

- `ventas.dbf` (líneas de venta)
  - SALE_ID, FACTURA_ID, SALE_DATE
  - PRODUCT_ID, PRODUCT_NAME, BRAND, CATEGORY
  - CLIENT_ID, CLIENT_NAME, CLIENT_ORIGIN
  - SELLER_ID, SELLER_NAME
  - ORIGEN_VENTA, RECOMM_SOURCE
  - TIPO_FACTURA, TIPO_ORDEN, STATUS
  - QTY, UNIT_PRICE_MXN, AMOUNT_MXN, AMOUNT_USD, CURRENCY, USD_MXN_RATE
- `facturas.dbf` (cabeceras)
  - FACTURA_ID, FECHA, CLIENT_ID/NAME, SELLER_ID/NAME
  - STATUS, TIPO_FACTURA, TIPO_ORDEN, ORIGEN_VENTA, RECOMM_SOURCE
  - SUBTOTAL_MXN, TOTAL_MXN, AMOUNT_USD, CURRENCY, USD_MXN_RATE
- `productos.dbf`
  - PRODUCT_ID, SKU, PRODUCT_NAME, BRAND, CATEGORY
  - COST_MXN, PRICE_MXN, STOCK_QTY, MIN_STOCK, MAX_STOCK
- `clientes.dbf`
  - CLIENT_ID, CLIENT_NAME, CLIENT_ORIGIN, RECOMM_SOURCE, REGION, CONTACT, STATUS, LAST_PURCHASE
- `vendedores.dbf`
  - SELLER_ID, SELLER_NAME, REGION, TEAM
- `tipo_cambio.dbf`
  - DATE, USD_MXN
- `notas_credito.dbf`
  - NOTA_ID, FACTURA_ID, FECHA, CLIENT_ID, MONTO_MXN, MOTIVO
- `pedidos.dbf`
  - ORDER_ID, ORDER_DATE, CLIENT_ID/NAME, SELLER_ID/NAME, PRODUCT_ID/NAME
  - QTY_ORDER, QTY_PENDING, STATUS, ORIGEN_VENTA, TIPO_ORDEN

## Moneda MXN/USD
El toggle “Vista moneda” permite ver métricas en MXN o USD. La conversión se hace con
`tipo_cambio.dbf` usando la tasa por fecha de venta. En el Resumen Ejecutivo se muestra
el FX promedio del periodo filtrado.

## Demo portable (sin Python instalado)
La demo se puede construir como staging portable (incluye Python embeddable, dependencias y app).

### Checklist rápido (rebuild)
1. Ejecuta `.\scripts\build_staging.ps1`
2. Ejecuta `.\build\staging\StartDemo.cmd`

### Paso 1: Construir staging
Ejecuta desde PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_staging.ps1
```

### Paso 2: Ejecutar demo
```powershell
.\build\staging\StartDemo.cmd
```

### Opcional: ZIP portable
Para generar un ZIP portable con todo el staging:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```
Salida: `dist\DBF-SAI-Alpha-Demo-Portable.zip`.
