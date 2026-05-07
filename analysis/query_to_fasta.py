"""
Query trino_joined.parquet and write matching sequences to a FASTA file.

The WHERE clause filters trino_joined.parquet; distinct nucleotidesequenceids
are then joined to trino_normalised_sequences.parquet to retrieve sequences.

Usage:
    python3 analysis/query_to_fasta.py <output_name> --where "<SQL condition>"

Examples:
    python3 analysis/query_to_fasta.py musca --where "genus = 'Musca'"
    python3 analysis/query_to_fasta.py diptera_families --where "\"order\" = 'Diptera' AND family IS NOT NULL"
"""

import argparse
from pathlib import Path

import duckdb

JOINED    = Path("trino_joined.parquet")
SEQUENCES = Path("trino_normalised_sequences.parquet")
OUTPUT_DIR = Path("tests/input")


def main():
    parser = argparse.ArgumentParser(description="Write a FASTA from trino_joined + trino_normalised_sequences")
    parser.add_argument("name",    help="Output filename stem (written to tests/input/<name>.fasta)")
    parser.add_argument("--where", required=True, help="SQL WHERE clause to filter trino_joined.parquet")
    args = parser.parse_args()

    for p in (JOINED, SEQUENCES):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{args.name}.fasta"

    con = duckdb.connect()
    rows = con.execute(f"""
        SELECT DISTINCT s.nucleotidesequenceid, s.sequence
        FROM '{JOINED}' j
        JOIN '{SEQUENCES}' s USING (nucleotidesequenceid)
        WHERE {args.where}
    """).fetchall()

    if not rows:
        print(f"No sequences matched: {args.where}")
        return

    with open(output_path, "w") as f:
        for seq_id, sequence in rows:
            f.write(f">{seq_id}\n{sequence}\n")

    print(f"Done — {len(rows):,} sequences written to {output_path}")


if __name__ == "__main__":
    main()
