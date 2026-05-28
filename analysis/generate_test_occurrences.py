"""
Generate a JSON array of GBIF occurrences with multiple sequences for testing
the /occurrence/classify/batch endpoint.

Queries trino_joined.parquet and trino_normalised_sequences.parquet, groups by
gbifid, and emits one JSON object per occurrence containing the publisher's
original taxonomy fields and a nucleotideSequence array.

Only occurrences with 2–4 sequences are included (high-count metabarcoding
occurrences are excluded as they represent a different use case).

Output format matches the shape expected by assignTaxonomyToOccurrence.mjs:
  {
    "gbifID": 12345,
    "kingdom": "...", ..., "scientificName": "...", "taxonRank": "...",
    "nucleotideSequence": [
      { "nucleotideSequenceID": "abc...", "sequence": "ATCG..." },
      ...
    ]
  }

Usage:
    python3 analysis/generate_test_occurrences.py
    python3 analysis/generate_test_occurrences.py --output node-server/test-data/occurrences.json --limit 200
"""

import argparse
import json
from pathlib import Path

import duckdb


def main():
    parser = argparse.ArgumentParser(description="Generate multi-sequence occurrence test data")
    parser.add_argument("--output",    default="node-server/test-data/multi_seq_occurrences.json")
    parser.add_argument("--limit",     type=int, default=500)
    parser.add_argument("--joined",    default="trino_joined.parquet")
    parser.add_argument("--sequences", default="trino_normalised_sequences.parquet")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    print("Querying …", flush=True)
    rows = con.execute(f"""
        WITH multi AS (
            SELECT gbifid
            FROM '{args.joined}'
            GROUP BY gbifid
            HAVING COUNT(DISTINCT nucleotidesequenceid) BETWEEN 2 AND 4
            ORDER BY gbifid
            LIMIT {args.limit}
        ),
        joined AS (
            SELECT
                j.gbifid,
                ANY_VALUE(j.kingdom)        AS kingdom,
                ANY_VALUE(j.phylum)         AS phylum,
                ANY_VALUE(j.class)          AS class,
                ANY_VALUE(j.order)          AS order,
                ANY_VALUE(j.family)         AS family,
                ANY_VALUE(j.genus)          AS genus,
                ANY_VALUE(j.species)        AS species,
                ANY_VALUE(j.scientificname) AS scientificName,
                ANY_VALUE(j.taxonrank)      AS taxonRank,
                LIST(DISTINCT j.nucleotidesequenceid) AS seq_ids
            FROM multi m
            JOIN '{args.joined}' j USING (gbifid)
            GROUP BY j.gbifid
        )
        SELECT
            o.gbifid,
            o.kingdom, o.phylum, o.class, o.order, o.family,
            o.genus, o.species, o.scientificName, o.taxonRank,
            LIST({{'nucleotideSequenceID': s.nucleotidesequenceid, 'sequence': s.sequence}})
                AS nucleotideSequence
        FROM joined o
        JOIN '{args.sequences}' s ON list_contains(o.seq_ids, s.nucleotidesequenceid)
        GROUP BY
            o.gbifid, o.kingdom, o.phylum, o.class, o.order, o.family,
            o.genus, o.species, o.scientificName, o.taxonRank
        ORDER BY o.gbifid
    """).fetchall()

    col_names = [d[0] for d in con.description]
    print(f"Building JSON for {len(rows)} occurrences …", flush=True)

    occurrences = []
    for row in rows:
        record = dict(zip(col_names, row))
        record["gbifID"] = record.pop("gbifid")
        occurrences.append(record)

    output_path.write_text(json.dumps(occurrences, indent=2))
    seq_counts = [len(o["nucleotideSequence"]) for o in occurrences]
    print(f"Written {len(occurrences)} occurrences to {output_path}")
    print(f"Sequences per occurrence: min={min(seq_counts)} max={max(seq_counts)} "
          f"avg={sum(seq_counts)/len(seq_counts):.1f}")


if __name__ == "__main__":
    main()
