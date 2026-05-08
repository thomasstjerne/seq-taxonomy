"""
Send a FASTA to the vsearch proxy server and write annotated results as Excel (xlsx).

Usage:
    python3 analysis/annotate_sequences_xlsx.py <fasta_file> [options]

Examples:
    python3 analysis/annotate_sequences_xlsx.py tests/input/musca.fasta
    python3 analysis/annotate_sequences_xlsx.py tests/input/musca.fasta \
        --output output/musca_annotated.xlsx --batch-size 50
"""

import argparse
import json
import urllib.request
from pathlib import Path

import pandas as pd

DEFAULT_SERVER     = "http://localhost:3000"
DEFAULT_BATCH_SIZE = 100


def parse_fasta(path: Path):
    with open(path) as f:
        seq_id = None
        bases = []
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if seq_id is not None:
                    yield seq_id, "".join(bases)
                seq_id = line[1:].strip()
                bases = []
            else:
                bases.append(line)
        if seq_id is not None:
            yield seq_id, "".join(bases)


def chunked(iterable, size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def to_fasta_text(seqs):
    return "\n".join(f">{seq_id}\n{seq}" for seq_id, seq in seqs)


def send_batch(server_url: str, fasta_text: str) -> dict:
    url = f"{server_url}/search/batch?outfmt=blast6out"
    req = urllib.request.Request(
        url,
        data=fasta_text.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(
        description="Annotate sequences via vsearch proxy and write Excel (xlsx)"
    )
    parser.add_argument("fasta_file",   help="Input FASTA file")
    parser.add_argument("--output",     help="Output xlsx path (default: output/<stem>_annotated.xlsx)")
    parser.add_argument("--server",     default=DEFAULT_SERVER,
                        help=f"Proxy server base URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Sequences per batch (default: {DEFAULT_BATCH_SIZE})")
    args = parser.parse_args()

    fasta_path = Path(args.fasta_file)
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA not found: {fasta_path}")

    output_path = Path(args.output) if args.output \
        else Path("output") / f"{fasta_path.stem}_annotated.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sequences = list(parse_fasta(fasta_path))
    total     = len(sequences)
    n_batches = (total + args.batch_size - 1) // args.batch_size
    print(f"{total:,} sequences → {n_batches} batches of up to {args.batch_size}")

    rows   = []
    no_hit = 0

    for i, batch in enumerate(chunked(sequences, args.batch_size), 1):
        print(f"  Batch {i}/{n_batches} …", end="\r", flush=True)
        results = send_batch(args.server, to_fasta_text(batch))

        batch_ids = {seq_id for seq_id, _ in batch}
        no_hit += len(batch_ids - results.keys())

        for query_id, match in results.items():
            if match:
                rows.append({"queryId": query_id, **match})

    print(f"\nMatched:   {len(rows):,}")
    if no_hit:
        print(f"No hit:    {no_hit:,}")

    pd.DataFrame(rows).to_excel(output_path, index=False)
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
