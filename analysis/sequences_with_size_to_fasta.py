"""
Write all distinct GBIF sequences to FASTA with vsearch-style ;size= abundance annotations.

The size value reflects the number of distinct occurrences (gbifid) each sequence
is associated with in the non-redundant trino_joined parquet.

Usage:
    python3 analysis/sequences_with_size_to_fasta.py
    python3 analysis/sequences_with_size_to_fasta.py --output output/fasta/gbif_sequences_with_size.fasta
    python3 analysis/sequences_with_size_to_fasta.py --temp-dir /tmp/duckdb_spill
"""

import argparse
from pathlib import Path

import duckdb

JOINED_NR = Path("output/trino_joined_nonredundant.parquet")
SEQUENCES  = Path("trino_normalised_sequences.parquet")
DEFAULT_OUTPUT = Path("output/fasta/gbif_sequences_with_size.fasta")


def main():
    parser = argparse.ArgumentParser(description="Write GBIF sequences to FASTA with ;size= abundance")
    parser.add_argument("--output",   default=str(DEFAULT_OUTPUT), help="Output FASTA path")
    parser.add_argument("--temp-dir", default=None, help="DuckDB temp directory for spilling to disk")
    args = parser.parse_args()

    for p in (JOINED_NR, SEQUENCES):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    if args.temp_dir:
        con.execute(f"SET temp_directory = '{args.temp_dir}'")

    print("Counting occurrences per sequence...")
    cursor = con.execute(f"""
        SELECT s.nucleotidesequenceid, s.sequence, counts.n_occurrences
        FROM '{SEQUENCES}' s
        JOIN (
            SELECT nucleotidesequenceid, COUNT(gbifid) AS n_occurrences
            FROM '{JOINED_NR}'
            GROUP BY nucleotidesequenceid
        ) counts USING (nucleotidesequenceid)
        ORDER BY counts.n_occurrences DESC
    """)

    print(f"Writing to {output_path}...")
    n = 0
    with open(output_path, "w") as f:
        while True:
            batch = cursor.fetchmany(100_000)
            if not batch:
                break
            for seq_id, sequence, size in batch:
                f.write(f">{seq_id};size={size}\n{sequence}\n")
            n += len(batch)
            print(f"  {n:,} sequences written", end="\r")

    print(f"\nDone — {n:,} sequences written to {output_path}")


if __name__ == "__main__":
    main()
