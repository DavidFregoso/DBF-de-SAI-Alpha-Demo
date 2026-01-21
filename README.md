SAI Alpha DBF Dashboard Demo

See demo_sai_dashboard/README_DEMO.md for setup and execution steps.
See README_DEMO.md for setup and execution steps.

## Demo portable (sin Python instalado)
La demo de fase 1 se puede construir como staging portable (incluye Python embeddable, dependencias y app).

### Paso 1: Construir staging
Ejecuta desde PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_staging.ps1
```

### Paso 2: Ejecutar demo
```powershell
.\build\staging\StartDemo.cmd
```

La app se levanta con Streamlit y muestra la URL local y la URL LAN. Desde otra PC en la misma red abre:
```
http://IP_DEL_SERVIDOR:PUERTO
```

### Opcional: ZIP portable
Para generar un ZIP portable con todo el staging:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```
Salida: `dist\DBF-SAI-Alpha-Demo-Portable.zip`.
