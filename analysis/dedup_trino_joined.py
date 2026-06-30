"""
Deduplicate trino_joined.parquet on (nucleotidesequenceid, gbifid).

When duplicates exist, keep the row with the most non-NULL taxonomy columns.
Ties are broken arbitrarily (any row is equally valid).

Usage:
    python3 analysis/dedup_trino_joined.py
    python3 analysis/dedup_trino_joined.py --input trino_joined.parquet --output output/trino_joined_nonredundant.parquet
    python3 analysis/dedup_trino_joined.py --temp-dir /tmp/duckdb_spill
"""

import argparse
from pathlib import Path

import duckdb

TAXONOMY_COLS = ["kingdom", "phylum", "class", "order", "family", "genus", "species", "scientificname", "taxonrank"]

DEFAULT_INPUT  = Path("trino_joined.parquet")
DEFAULT_OUTPUT = Path("output/trino_joined_nonredundant.parquet")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",    default=str(DEFAULT_INPUT))
    parser.add_argument("--output",   default=str(DEFAULT_OUTPUT))
    parser.add_argument("--temp-dir", default=None)
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    if args.temp_dir:
        con.execute(f"SET temp_directory = '{args.temp_dir}'")

    non_null_expr = " + ".join(
        f'(CASE WHEN "{col}" IS NOT NULL THEN 1 ELSE 0 END)' for col in TAXONOMY_COLS
    )

    print(f"Reading {input_path} ...")
    print(f"Writing deduplicated output to {output_path} ...")

    con.execute(f"""
        COPY (
            SELECT
                nucleotidesequenceid,
                gbifid,
                datasetkey,
                kingdom, phylum, class, "order", family, genus, species,
                scientificname, taxonrank
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY nucleotidesequenceid, gbifid
                        ORDER BY ({non_null_expr}) DESC
                    ) AS rn
                FROM '{input_path}'
                WHERE nucleotidesequenceid IS NOT NULL AND gbifid IS NOT NULL
            )
            WHERE rn = 1
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    result = con.execute(f"SELECT count(*) FROM '{output_path}'").fetchone()[0]
    print(f"Done — {result:,} rows written.")


if __name__ == "__main__":
    main()
