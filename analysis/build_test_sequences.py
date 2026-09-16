"""
Build a representative test FASTA for performance benchmarking.

Replaces the single-gene musca.fasta with a sample that reflects the real
production workload. Two modes, answering different questions:

  proportional  strata allocated by each gene's share of UNIQUE sequences —
                use this to extrapolate wall-clock for the full 23.9M job
  per-gene      equal N per gene — use this to build a per-gene cost model,
                since proportional sampling yields too few matK/rbcL/12S to
                measure them

Sampling notes:
  - Sampled by UNIQUE sequence, not occurrence. The occurrence-level gene
    distribution is badly skewed by metabarcoding datasets (~22 occurrences per
    sequence for Ribosomal_RNA vs ~2 for COI), and the job processes each unique
    sequence once.
  - Within each gene, sequences are drawn evenly across length deciles so the
    per-gene length distribution is preserved rather than approximated by its
    mean. Query cost scales with length.
  - Sequences longer than --max-length (default 2048) are excluded: the vsearch
    server rejects them, so they are not annotated. This drops 0.52% of unique
    sequences overall, but ~29% of the (null)-targetGene stratum — so the filter
    is applied BEFORE allocation, not after.
  - Sequences with no hits are NOT filtered out. They are fast, they exist in
    production, and excluding them would inflate throughput estimates.
  - ~3% of sequence ids in the derived-data dump have no bases in the sequence
    dump (different snapshots). Each stratum is oversampled by --oversample to
    absorb that, then trimmed back to the exact target.

Usage:
    python3 analysis/build_test_sequences.py mixed_prod \\
        --temp-dir /Volumes/Samsung_T5/duckdb_tmp

    python3 analysis/build_test_sequences.py per_gene --mode per-gene \\
        --per-gene-n 200 --temp-dir /Volumes/Samsung_T5/duckdb_tmp

Outputs tests/input/<name>.fasta plus tests/input/<name>_manifest.csv, which
records gene, length and decile per sequence so benchmark results can be sliced
by stratum afterwards.
"""

import argparse
import csv
from pathlib import Path

import duckdb

DERIVED   = Path("/Volumes/Samsung_T5/occurrence_dna_derived_data_deduped.parquet")
SEQUENCES = Path("trino_normalised_sequences.parquet")
OUTPUT_DIR = Path("tests/input")

N_DECILES = 10


def parse_args():
    p = argparse.ArgumentParser(description="Build a representative test FASTA")
    p.add_argument("name", help="Output filename stem (written to tests/input/<name>.fasta)")
    p.add_argument("--mode", choices=("proportional", "per-gene"), default="proportional")
    p.add_argument("--n", type=int, default=5000,
                   help="Total sequences for proportional mode (default 5000)")
    p.add_argument("--per-gene-n", type=int, default=200,
                   help="Sequences per gene for per-gene mode (default 200)")
    p.add_argument("--max-length", type=int, default=2048,
                   help="Drop sequences longer than this (default 2048, the server's cap)")
    p.add_argument("--min-pool", type=int, default=5000,
                   help="Ignore genes with fewer than this many unique sequences (default 5000)")
    p.add_argument("--oversample", type=float, default=1.6,
                   help="Draw this multiple per stratum to absorb sequence-dump misses (default 1.6)")
    p.add_argument("--seed", default="0", help="Sampling seed (default 0)")
    p.add_argument("--derived", default=str(DERIVED))
    p.add_argument("--sequences", default=str(SEQUENCES))
    p.add_argument("--temp-dir", default=None,
                   help="DuckDB temp directory for spilling to disk")
    return p.parse_args()


def largest_remainder(shares, total):
    """Allocate `total` across `shares` (dict name -> weight) without drift."""
    raw = {k: total * w for k, w in shares.items()}
    alloc = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(alloc.values())
    for k, _ in sorted(raw.items(), key=lambda kv: kv[1] - int(kv[1]), reverse=True)[:remainder]:
        alloc[k] += 1
    return {k: v for k, v in alloc.items() if v > 0}


def spread(n, buckets):
    """Split n as evenly as possible across `buckets`, returning a list."""
    base, extra = divmod(n, buckets)
    return [base + (1 if i < extra else 0) for i in range(buckets)]


def main():
    args = parse_args()

    for path in (Path(args.derived), Path(args.sequences)):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fasta_path    = OUTPUT_DIR / f"{args.name}.fasta"
    manifest_path = OUTPUT_DIR / f"{args.name}_manifest.csv"

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute("SET memory_limit = '12GB'")
    if args.temp_dir:
        con.execute(f"SET temp_directory = '{args.temp_dir}'")
        con.execute("SET max_temp_directory_size = '60GB'")

    # One row per unique sequence. A sequence can carry more than one targetGene
    # (~1.8k cases, all iBOL); min() picks one deterministically.
    print("Building candidate pool …", flush=True)
    con.execute(f"""
        CREATE TEMP TABLE pool AS
        SELECT nucleotidesequenceid AS id,
               min(gene) AS gene,
               min(sequencelength) AS len
        FROM (
            SELECT nucleotidesequenceid,
                   coalesce(regexp_extract(targetgene, 'concept=([^,}}]+)', 1), '(null)') AS gene,
                   sequencelength
            FROM '{args.derived}'
            WHERE sequencelength IS NOT NULL
              AND sequencelength <= {args.max_length}
        )
        GROUP BY nucleotidesequenceid
    """)

    sizes = con.execute(f"""
        SELECT gene, count(*) AS n FROM pool
        GROUP BY gene HAVING count(*) >= {args.min_pool} ORDER BY n DESC
    """).fetchall()
    if not sizes:
        raise SystemExit("No gene stratum met --min-pool")

    total_pool = sum(n for _, n in sizes)
    print(f"Pool: {total_pool:,} unique sequences across {len(sizes)} genes "
          f"(<= {args.max_length} bp)")

    if args.mode == "proportional":
        shares = {g: n / total_pool for g, n in sizes}
        per_gene = largest_remainder(shares, args.n)
    else:
        per_gene = {g: min(args.per_gene_n, n) for g, n in sizes}

    # Even allocation across length deciles within each gene.
    alloc_rows = []
    for gene, n_gene in per_gene.items():
        for decile, n_dec in enumerate(spread(n_gene, N_DECILES), start=1):
            if n_dec:
                alloc_rows.append((gene, decile, n_dec,
                                   max(n_dec, int(n_dec * args.oversample) + 1)))
    con.execute("CREATE TEMP TABLE alloc (gene VARCHAR, decile INT, n_target INT, n_draw INT)")
    con.executemany("INSERT INTO alloc VALUES (?, ?, ?, ?)", alloc_rows)

    target_total = sum(r[2] for r in alloc_rows)
    print(f"Target: {target_total:,} sequences across {len(per_gene)} genes "
          f"({args.mode} allocation)")

    # Deterministic draw: rank by hash(id || seed) within (gene, decile), take
    # the oversampled count, join to bases, then trim to the exact target.
    print("Sampling and joining to sequence bases …", flush=True)
    rows = con.execute(f"""
        WITH deciled AS (
            SELECT id, gene, len,
                   ntile({N_DECILES}) OVER (PARTITION BY gene ORDER BY len, id) AS decile
            FROM pool
            WHERE gene IN (SELECT DISTINCT gene FROM alloc)
        ),
        drawn AS (
            SELECT d.id, d.gene, d.len, d.decile,
                   row_number() OVER (PARTITION BY d.gene, d.decile
                                      ORDER BY hash(d.id || '{args.seed}')) AS rn
            FROM deciled d
            JOIN alloc a ON a.gene = d.gene AND a.decile = d.decile
            QUALIFY rn <= a.n_draw
        ),
        withseq AS (
            SELECT d.id, d.gene, d.len, d.decile, s.sequence,
                   row_number() OVER (PARTITION BY d.gene, d.decile ORDER BY d.rn) AS keep_rn
            FROM drawn d
            JOIN '{args.sequences}' s ON s.nucleotidesequenceid = d.id
        )
        SELECT w.id, w.gene, w.len, w.decile, w.sequence
        FROM withseq w
        JOIN alloc a ON a.gene = w.gene AND a.decile = w.decile
        WHERE w.keep_rn <= a.n_target
        ORDER BY w.gene, w.decile, w.id
    """).fetchall()

    if not rows:
        raise SystemExit("Sampling produced no rows")

    with open(fasta_path, "w") as f:
        for seq_id, _, _, _, sequence in rows:
            f.write(f">{seq_id}\n{sequence}\n")

    with open(manifest_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nucleotidesequenceid", "targetGene", "sequenceLength", "lengthDecile"])
        for seq_id, gene, length, decile, _ in rows:
            w.writerow([seq_id, gene, length, decile])

    print(f"\nDone — {len(rows):,} sequences written to {fasta_path}")
    print(f"        manifest written to {manifest_path}")
    if len(rows) < target_total:
        short = target_total - len(rows)
        print(f"\nNOTE: {short:,} short of target ({100*short/target_total:.1f}%) — some strata "
              f"ran out of sequences present in {args.sequences}. Raise --oversample to compensate.")

    print("\nRealised composition:")
    by_gene = {}
    for _, gene, length, _, _ in rows:
        g = by_gene.setdefault(gene, [])
        g.append(length)
    print(f"  {'gene':<30}{'n':>7}{'pct':>8}{'len p50':>10}{'len max':>10}")
    for gene, lengths in sorted(by_gene.items(), key=lambda kv: -len(kv[1])):
        lengths.sort()
        print(f"  {gene:<30}{len(lengths):>7}{100*len(lengths)/len(rows):>7.2f}%"
              f"{lengths[len(lengths)//2]:>10}{lengths[-1]:>10}")


if __name__ == "__main__":
    main()
