# Demo SAI Alpha - Dashboard Ejecutivo y Operativo

## Objetivo
Demo local (sin internet) que simula un flujo con DBF (xBase):
- Generación de DBF mock realistas.
- ETL a DataFrames con KPIs.
- Dashboard Streamlit con filtros, exportación y gráficas Plotly.

## Estructura
```
demo_sai_dashboard/
  dbf/
  exports/
  app.py
  etl.py
  generate_mock_dbf.py
  dbf_inspector.py
  requirements.txt
  run_demo.bat
  README_DEMO.md
```

## Ejecución en Windows
1. Doble click a `run_demo.bat`.
2. Abre el navegador en [http://localhost:8501](http://localhost:8501).

## Troubleshooting
- **Falta Python**: instalar Python 3.10+ desde el instalador oficial.
- **Error de dependencias**: verifica que tienes acceso a PyPI y reintenta `pip install -r requirements.txt`.
- **DBF faltantes**: ejecuta `python generate_mock_dbf.py` dentro de la carpeta `demo_sai_dashboard`.

## Scripts clave
- `generate_mock_dbf.py`: genera `VENTAS.DBF`, `CLIENTES.DBF`, `PRODUCTOS.DBF`, `VENDEDORES.DBF`, `PEDIDOS.DBF`.
- `dbf_inspector.py`: lista tablas, campos, tipos y ejemplos para mapear un Alpha real.
- `app.py`: dashboard principal (Ventas, Clientes, Productos).

## Done
- El demo abre en **http://localhost:8501**.
- Navegación y filtros funcionan: Marcas, Vendedor, Rango de fechas, Semana del año.
- Exportaciones CSV/Excel disponibles sin errores.
