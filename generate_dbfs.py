from pathlib import Path

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.mock_data import generate_dbf_dataset


if __name__ == "__main__":
    output_dir = resolve_dbf_dir(Path.cwd() / "data" / "dbf")
    paths = generate_dbf_dataset(output_dir)
    print("DBF mock data generated:")
    for name, path in paths.items():
        print(f"- {name}: {path}")
