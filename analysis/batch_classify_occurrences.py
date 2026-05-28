"""
Send occurrences from a JSON file to /occurrence/classify/batch and write
a TSV comparing input (publisher) taxonomy against the assigned taxonomy.

Usage:
    python3 analysis/batch_classify_occurrences.py node-server/test-data/multi_seq_occurrences.json
    python3 analysis/batch_classify_occurrences.py node-server/test-data/multi_seq_occurrences.json \\
        --output output/batch_classify_results.tsv --batch-size 25
"""

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

DEFAULT_SERVER     = "http://localhost:3000"
DEFAULT_BATCH_SIZE = 25

TAXONOMY_RANKS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]

INPUT_COLS  = ["gbifID", "n_seqs", "in_scientificName", "in_taxonRank"] + [f"in_{r}" for r in TAXONOMY_RANKS]
OUTPUT_COLS = ["out_scientificName", "out_taxonRank"] + [f"out_{r}" for r in TAXONOMY_RANKS] + ["remarks"]


def send_batch(server_url, occurrences):
    url = f"{server_url}/occurrence/classify/batch"
    req = urllib.request.Request(
        url,
        data=json.dumps(occurrences).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def main():
    parser = argparse.ArgumentParser(description="Batch classify occurrences and write TSV")
    parser.add_argument("input",        help="JSON file of occurrences")
    parser.add_argument("--output",     help="Output TSV path (default: output/<stem>_classified.tsv)")
    parser.add_argument("--server",     default=DEFAULT_SERVER)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    output_path = Path(args.output) if args.output \
        else Path("output") / f"{input_path.stem}_classified.tsv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    occurrences = json.loads(input_path.read_text())
    total     = len(occurrences)
    n_batches = (total + args.batch_size - 1) // args.batch_size
    print(f"{total} occurrences → {n_batches} batches of up to {args.batch_size}")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INPUT_COLS + OUTPUT_COLS, delimiter="\t")
        writer.writeheader()

        matched = no_match = errors = 0

        for i, batch in enumerate(chunked(occurrences, args.batch_size), 1):
            print(f"  Batch {i}/{n_batches} …", end="\r", flush=True)
            try:
                results = send_batch(args.server, batch)
            except Exception as e:
                print(f"\n  Batch {i} failed: {e}", file=sys.stderr)
                errors += len(batch)
                continue

            occ_by_gbifid = {str(o["gbifID"]): o for o in batch}

            for result in results:
                gbif_id    = str(result.get("gbifID") or "")
                occ        = occ_by_gbifid.get(gbif_id, {})
                cls        = result.get("classification")

                row = {
                    "gbifID":          gbif_id,
                    "n_seqs":          len(occ.get("nucleotideSequence", [])),
                    "in_scientificName": occ.get("scientificName", ""),
                    "in_taxonRank":    occ.get("taxonRank", ""),
                    **{f"in_{r}":  occ.get(r, "") or "" for r in TAXONOMY_RANKS},
                }

                if cls:
                    matched += 1
                    row.update({
                        "out_scientificName": cls.get("scientificName", ""),
                        "out_taxonRank":      cls.get("taxonRank", ""),
                        **{f"out_{r}": cls.get(r, "") or "" for r in TAXONOMY_RANKS},
                        "remarks": cls.get("remarks", ""),
                    })
                else:
                    no_match += 1
                    row.update({c: "" for c in OUTPUT_COLS})

                writer.writerow(row)

    print(f"\nMatched:  {matched}")
    print(f"No match: {no_match}")
    if errors:
        print(f"Errors:   {errors}")
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
