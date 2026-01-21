# MVP DEMO - Dashboard Ejecutivo y Operativo SAI Alpha (DBF)

## Objetivo
Construir un demo local en Python que simule un flujo completo con DBF (xBase):
1. Generar datos mock realistas en archivos DBF.
2. Ejecutar ETL a DataFrames y calcular KPIs.
3. Mostrar un dashboard Streamlit multi-página con filtros y exportación.

## Estructura del proyecto
```
.
├── data/
│   ├── dbf/              # DBFs generados
│   └── exports/          # Exportaciones CSV/Excel
├── pages/                # Páginas Streamlit
├── sai_alpha/            # Módulos de negocio (ETL, KPIs, utilidades)
├── dbf_inspector.py      # Inspector de DBF
├── generate_dbfs.py      # Generador de datos mock DBF
├── run_demo.bat          # Lanzador en Windows
├── streamlit_app.py      # Entrada principal de Streamlit
└── README_DEMO.md
```

## Ejecución en Windows (paso a paso)
1. Abre una consola en la carpeta del proyecto.
2. Ejecuta:
   ```bat
   run_demo.bat
   ```
3. Abre el navegador en [http://localhost:8501](http://localhost:8501).

## Scripts principales
- `generate_dbfs.py`: crea DBFs con ventas, productos, clientes y vendedores.
- `dbf_inspector.py`: lista tablas, campos, tipos y muestras para mapear un Alpha real.
- `streamlit_app.py`: dashboard ejecutivo principal.

## Criterios de “Done”
- El demo levanta correctamente en **http://localhost:8501**.
- Se muestran las páginas:
  - Resumen
  - Clientes
  - Vendedores
  - Productos
- Filtros por fecha, marca y vendedor disponibles.
- Exportación CSV/Excel disponible para tablas relevantes.
