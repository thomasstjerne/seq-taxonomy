"""
Benchmark vsearch throughput across batch size and client concurrency.

Submits a fixed pool of real sequences directly to the raw vsearch HTTP server
(no Node proxy, no cache) and measures how throughput responds to:

  - batch size   B : sequences per HTTP request
  - concurrency  C : requests in flight at once (how full we keep vsearch's queue)

Thread count is NOT swept here: restart vsearch at each --threads value and
re-run this script with --threads-label N. The label is stamped on every output
row so per-thread CSVs can be concatenated for the cross-thread comparison.

The same shuffled pool is reused for every (B, C) cell, so timings are directly
comparable (vsearch has no result cache). A warmup pass loads the UDB into the OS
page cache before timing. Each cell is repeated and config order is randomised per
repeat to spread out background drift.

Usage:
    # vsearch started with --threads 8, already serving on :8000
    python3 analysis/vsearch_batch_benchmark.py --threads-label 8 --plot

    # quick pass
    python3 analysis/vsearch_batch_benchmark.py --threads-label 8 \\
        --n 300 --batch-sizes 1,10,100 --concurrency 1,4 --repeats 1
"""

import argparse
import csv
import random
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_FASTA       = "tests/input/musca.fasta"
DEFAULT_VSEARCH_URL = "http://127.0.0.1:8000/search/batch"
DEFAULT_BATCH_SIZES = "1,5,10,25,50,100,200,500,1000"
DEFAULT_CONCURRENCY = "1,2,4,8"
SHUFFLE_SEED        = 0

CSV_FIELDS = [
    "threads", "batch_size", "concurrency", "repeat", "n_seqs",
    "wall_seconds", "throughput", "lat_mean", "lat_p50", "lat_p95",
    "lat_max", "queries_with_hits",
]


def parse_fasta(path: Path):
    """Return a list of (seq_id, sequence) pairs from a FASTA file."""
    seqs = []
    with open(path) as f:
        seq_id, bases = None, []
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if seq_id is not None:
                    seqs.append((seq_id, "".join(bases)))
                seq_id, bases = line[1:].strip(), []
            else:
                bases.append(line)
        if seq_id is not None:
            seqs.append((seq_id, "".join(bases)))
    return seqs


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def to_fasta_text(seqs):
    return "\n".join(f">{sid}\n{seq}" for sid, seq in seqs)


def send_batch(url: str, fasta_text: str):
    """POST one FASTA batch; return (elapsed_seconds, n_query_ids_with_hits)."""
    req = urllib.request.Request(
        f"{url}?outfmt=blast6out",
        data=fasta_text.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = resp.read().decode("utf-8")
    elapsed = time.perf_counter() - start
    hit_ids = {line.split("\t", 1)[0] for line in body.splitlines() if line.strip()}
    return elapsed, len(hit_ids)


def run_cell(url, pool, batch_size, concurrency):
    """Process the whole pool at one (batch_size, concurrency) setting.

    Returns dict of metrics for this cell.
    """
    batches = list(chunked(pool, batch_size))
    fasta_texts = [to_fasta_text(b) for b in batches]

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool_exec:
        results = list(pool_exec.map(lambda ft: send_batch(url, ft), fasta_texts))
    wall = time.perf_counter() - wall_start

    latencies = [r[0] for r in results]
    queries_with_hits = sum(r[1] for r in results)
    n = len(pool)

    def pct(values, p):
        s = sorted(values)
        k = max(0, min(len(s) - 1, int(round((p / 100) * (len(s) - 1)))))
        return s[k]

    return {
        "n_seqs": n,
        "wall_seconds": round(wall, 4),
        "throughput": round(n / wall, 2) if wall > 0 else 0,
        "lat_mean": round(statistics.fmean(latencies), 4),
        "lat_p50": round(pct(latencies, 50), 4),
        "lat_p95": round(pct(latencies, 95), 4),
        "lat_max": round(max(latencies), 4),
        "queries_with_hits": queries_with_hits,
    }


def print_pivot(rows, batch_sizes, concurrencies, threads):
    """Print mean-throughput grid: rows = batch size, cols = concurrency."""
    agg = {}  # (B, C) -> [throughput, ...]
    for r in rows:
        agg.setdefault((r["batch_size"], r["concurrency"]), []).append(r["throughput"])

    col_w = 11
    header = "batch \\ conc".ljust(14) + "".join(f"{c:>{col_w}}" for c in concurrencies)
    print(f"\nThroughput (seqs/sec), mean over repeats — threads={threads}")
    print(header)
    print("-" * len(header))
    best = max(
        ((b, c) for b in batch_sizes for c in concurrencies if (b, c) in agg),
        key=lambda bc: statistics.fmean(agg[bc]),
        default=None,
    )
    for b in batch_sizes:
        cells = []
        for c in concurrencies:
            vals = agg.get((b, c))
            if vals is None:
                cells.append(f"{'-':>{col_w}}")
            else:
                mark = "*" if (b, c) == best else " "
                cells.append(f"{statistics.fmean(vals):>{col_w-1}.1f}{mark}")
        print(f"{b:<14}" + "".join(cells))
    if best:
        print(f"\nBest cell: batch_size={best[0]}, concurrency={best[1]} "
              f"({statistics.fmean(agg[best]):.1f} seqs/sec)  [marked *]")


def maybe_plot(rows, batch_sizes, concurrencies, threads, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plot")
        return

    agg = {}
    for r in rows:
        agg.setdefault((r["batch_size"], r["concurrency"]), []).append(r["throughput"])

    fig, ax = plt.subplots(figsize=(8, 5))
    for c in concurrencies:
        xs = [b for b in batch_sizes if (b, c) in agg]
        ys = [statistics.fmean(agg[(b, c)]) for b in xs]
        ax.plot(xs, ys, marker="o", label=f"concurrency={c}")
    ax.set_xscale("log")
    ax.set_xlabel("batch size (sequences per request, log scale)")
    ax.set_ylabel("throughput (seqs/sec)")
    ax.set_title(f"vsearch throughput vs batch size — threads={threads}")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    print(f"Plot written to {out_png}")


def main():
    p = argparse.ArgumentParser(description="Benchmark vsearch batch size × concurrency")
    p.add_argument("--threads-label", required=True,
                   help="vsearch --threads value this run was served with (stamped on output)")
    p.add_argument("--fasta", default=DEFAULT_FASTA)
    p.add_argument("--n", type=int, default=1000, help="pool size (sequences)")
    p.add_argument("--batch-sizes", default=DEFAULT_BATCH_SIZES)
    p.add_argument("--concurrency", default=DEFAULT_CONCURRENCY)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--vsearch-url", default=DEFAULT_VSEARCH_URL)
    p.add_argument("--warmup", dest="warmup", action="store_true", default=True)
    p.add_argument("--no-warmup", dest="warmup", action="store_false")
    p.add_argument("--plot", action="store_true")
    p.add_argument("--output", default=None)
    args = p.parse_args()

    batch_sizes   = [int(x) for x in args.batch_sizes.split(",") if x.strip()]
    concurrencies = [int(x) for x in args.concurrency.split(",") if x.strip()]

    fasta_path = Path(args.fasta)
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA not found: {fasta_path}")

    all_seqs = parse_fasta(fasta_path)
    random.Random(SHUFFLE_SEED).shuffle(all_seqs)
    pool = all_seqs[:args.n]
    if len(pool) < args.n:
        print(f"WARNING: requested --n {args.n} but pool only has {len(pool)} sequences")

    print(f"Pool: {len(pool):,} sequences from {fasta_path}")
    print(f"Grid: batch_sizes={batch_sizes} × concurrency={concurrencies} × repeats={args.repeats}")
    print(f"vsearch: {args.vsearch_url}  (threads label: {args.threads_label})")

    if args.warmup:
        print("Warmup pass …", end=" ", flush=True)
        t0 = time.perf_counter()
        for batch in chunked(pool, 100):
            send_batch(args.vsearch_url, to_fasta_text(batch))
        print(f"done ({time.perf_counter() - t0:.1f}s)")

    cells = [(b, c) for b in batch_sizes for c in concurrencies]
    rows = []
    total = len(cells) * args.repeats
    done = 0
    for rep in range(1, args.repeats + 1):
        order = cells[:]
        random.Random(rep).shuffle(order)  # randomise config order per repeat
        for (b, c) in order:
            done += 1
            print(f"  [{done}/{total}] rep {rep}  batch={b:<5} conc={c} …",
                  end=" ", flush=True)
            m = run_cell(args.vsearch_url, pool, b, c)
            row = {"threads": args.threads_label, "batch_size": b,
                   "concurrency": c, "repeat": rep, **m}
            rows.append(row)
            print(f"{m['throughput']:.1f} seqs/s  ({m['wall_seconds']:.1f}s)")

    out_path = Path(args.output) if args.output \
        else Path("output") / f"vsearch_batch_benchmark_t{args.threads_label}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists()
    with open(out_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} rows written to {out_path}")

    print_pivot(rows, batch_sizes, concurrencies, args.threads_label)

    # Sanity: queries_with_hits should be constant across the grid
    hit_counts = {r["queries_with_hits"] for r in rows}
    if len(hit_counts) > 1:
        print(f"\nWARNING: queries_with_hits varies across cells {sorted(hit_counts)} "
              f"— batch size should not change which queries match.")

    if args.plot:
        out_png = out_path.with_suffix(".png")
        maybe_plot(rows, batch_sizes, concurrencies, args.threads_label, out_png)


if __name__ == "__main__":
    main()
