from pathlib import Path
import sys

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.mock_data import generate_dbf_dataset


if __name__ == "__main__":
    output_dir = resolve_dbf_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        paths = generate_dbf_dataset(output_dir)
    except Exception as exc:
        print(f"Error generating DBF mock data: {exc}")
        sys.exit(1)
    print("DBF mock data generated:")
    for name, path in paths.items():
        print(f"- {name}: {path}")
