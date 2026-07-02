"""Pipeline orchestrator: ingest -> dbt build -> export marts.

Usage:
    python main.py            # live run
    python main.py --sample   # offline run with synthetic data
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> None:
    print(f"\n=== {' '.join(cmd)} ===")
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    # DuckDB won't create missing parent directories, and data/warehouse/
    # is gitignored (the file is derivable), so ensure it exists.
    (REPO_ROOT / "data" / "warehouse").mkdir(parents=True, exist_ok=True)

    ingest_cmd = [sys.executable, "-m", "ingestion.ingest"]
    if args.sample:
        ingest_cmd.append("--sample")

    run(ingest_cmd)
    run(["dbt", "deps", "--profiles-dir", "."], cwd=REPO_ROOT / "dbt")
    run(["dbt", "build", "--profiles-dir", "."], cwd=REPO_ROOT / "dbt")
    run([sys.executable, "-m", "ingestion.export_marts"])
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
