from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from dbfread import DBF


def describe_fields(table: DBF) -> List[Dict[str, Any]]:
    fields: List[Dict[str, Any]] = []
    for field in table.fields:
        fields.append(
            {
                "name": field.name,
                "type": field.type,
                "length": field.length,
                "decimal_count": field.decimal_count,
            }
        )
    return fields


def inspect_dbf(path: Path, sample_size: int = 5) -> Dict[str, Any]:
    table = DBF(path, load=True, char_decode_errors="ignore")
    print(f"\nTabla: {path.name}")
    print("Campos:")
    for field in table.fields:
        print(f"  - {field.name} ({field.type})")
    print(f"Ejemplos ({sample_size} filas):")
    examples: List[Dict[str, Any]] = []
    for idx, record in enumerate(table, start=1):
        examples.append(dict(record))
        print(f"  {idx:02d}: {record}")
        if idx >= sample_size:
            break

    return {
        "name": path.name,
        "path": str(path.resolve()),
        "fields": describe_fields(table),
        "sample_rows": examples,
    }


def list_dbf_files(dbf_dir: Path) -> List[Path]:
    return sorted(
        path
        for path in dbf_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".dbf"
    )


def export_schema(output_path: Path, dbf_data: List[Dict[str, Any]]) -> None:
    payload = {
        "generated_from": "dbf_inspector.py",
        "files": dbf_data,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspecciona archivos DBF y muestra campos/ejemplos."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="./dbf",
        help="Carpeta con archivos DBF (por defecto ./dbf).",
    )
    parser.add_argument(
        "--export-schema",
        metavar="schema.json",
        help="Exporta el esquema detectado a un archivo JSON.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dbf_dir = Path(args.folder)
    if not dbf_dir.exists():
        print(f"No se encontró la carpeta {dbf_dir}.")
        raise SystemExit(1)

    dbf_files = list_dbf_files(dbf_dir)
    if not dbf_files:
        print(f"No se encontraron archivos DBF en {dbf_dir}.")
        raise SystemExit(1)

    print("Archivos DBF encontrados:")
    for dbf_path in dbf_files:
        print(f"  - {dbf_path.name}")

    dbf_data: List[Dict[str, Any]] = []
    for dbf_path in dbf_files:
        dbf_data.append(inspect_dbf(dbf_path))

    if args.export_schema:
        output_path = Path(args.export_schema)
        export_schema(output_path, dbf_data)
        print(f"\nEsquema exportado a: {output_path}")


if __name__ == "__main__":
    main()
