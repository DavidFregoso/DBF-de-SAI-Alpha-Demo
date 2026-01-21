from pathlib import Path

from dbfread import DBF


def inspect_dbf(path: Path) -> None:
    table = DBF(path, load=True, char_decode_errors="ignore")
    print(f"\nTabla: {path.name}")
    print("Campos:")
    for field in table.fields:
        print(f"  - {field.name} ({field.type})")
    print("Ejemplos:")
    for idx, record in enumerate(table, start=1):
        print(f"  {idx:02d}: {record}")
        if idx >= 3:
            break


if __name__ == "__main__":
    dbf_dir = Path("dbf")
    if not dbf_dir.exists():
        print("No se encontró la carpeta dbf. Ejecuta generate_mock_dbf.py primero.")
        raise SystemExit(1)

    for dbf_path in sorted(dbf_dir.glob("*.DBF")):
        inspect_dbf(dbf_path)
