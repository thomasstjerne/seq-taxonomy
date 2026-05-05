"""
Characterise the top-100 most taxonomically ambiguous sequences.

Reads top100_distinct_families.parquet, calls the GBIF occurrence API for a
sample of sequences to identify the marker gene, then writes a markdown report
to output/top100_characterisation.md.

Usage:
    python3 analysis/characterise_top100.py

Requires:
    pip install duckdb requests

Input:
    top100_distinct_families.parquet  (generate with queries/generate_top100_distinct_families.sql)

Output:
    output/top100_characterisation.md
    output/top100_sequences.csv
    output/top100_datasets.csv
    output/top100_taxonomy.csv
"""

import os
import json
import time
import textwrap
from pathlib import Path
from collections import Counter, defaultdict

import duckdb
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PARQUET = "top100_distinct_families.parquet"
OUTPUT_DIR = Path("output")
GBIF_API = "https://api.gbif.org/v1/occurrence/search"
SAMPLE_SIZE = 20       # sequences to hit the GBIF API for gene detection
API_DELAY  = 0.5       # seconds between requests (be polite)

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load data from parquet
# ---------------------------------------------------------------------------
con = duckdb.connect()

print("Loading parquet …")
con.execute(f"CREATE VIEW data AS SELECT * FROM '{PARQUET}'")

# Per-sequence ambiguity
seqs = con.execute("""
    SELECT
        nucleotidesequenceid,
        COUNT(DISTINCT family)              AS n_distinct_families,
        COUNT(DISTINCT datasetkey)          AS n_datasets,
        COUNT(*)                            AS n_occurrences,
        LIST(DISTINCT family ORDER BY family) AS distinct_families,
        ANY_VALUE(kingdom)                  AS kingdom,
        ANY_VALUE(phylum)                   AS phylum
    FROM data
    WHERE family IS NOT NULL
    GROUP BY nucleotidesequenceid
    ORDER BY n_distinct_families DESC, n_datasets DESC
""").df()

seqs.to_csv(OUTPUT_DIR / "top100_sequences.csv", index=False)
print(f"  {len(seqs)} sequences with ≥1 family annotation")

# Kingdom / phylum distribution (all rows, including those without family)
taxonomy = con.execute("""
    SELECT
        COALESCE(kingdom, '(null)') AS kingdom,
        COALESCE(phylum,  '(null)') AS phylum,
        COUNT(DISTINCT nucleotidesequenceid) AS n_sequences,
        COUNT(*)                             AS n_occurrences
    FROM data
    GROUP BY 1, 2
    ORDER BY n_sequences DESC
""").df()

taxonomy.to_csv(OUTPUT_DIR / "top100_taxonomy.csv", index=False)

# Dataset contribution
datasets = con.execute("""
    SELECT
        datasetkey,
        COUNT(DISTINCT nucleotidesequenceid)  AS n_sequences,
        COUNT(*)                              AS n_occurrences,
        COUNT(DISTINCT family)                AS n_families_contributed
    FROM data
    GROUP BY datasetkey
    ORDER BY n_occurrences DESC
""").df()

datasets.to_csv(OUTPUT_DIR / "top100_datasets.csv", index=False)

# Total stats
total_seqs   = con.execute("SELECT COUNT(DISTINCT nucleotidesequenceid) FROM data").fetchone()[0]
total_rows   = con.execute("SELECT COUNT(*) FROM data").fetchone()[0]
total_ds     = con.execute("SELECT COUNT(DISTINCT datasetkey) FROM data").fetchone()[0]

print(f"  {total_seqs} unique sequences · {total_rows} rows · {total_ds} datasets")

# ---------------------------------------------------------------------------
# 2. GBIF API: detect marker genes
# ---------------------------------------------------------------------------
sample_ids = seqs["nucleotidesequenceid"].head(SAMPLE_SIZE).tolist()
gene_counter: Counter = Counter()
gene_examples: dict = {}
missing = 0

print(f"\nQuerying GBIF API for {len(sample_ids)} sequences …")
for seq_id in sample_ids:
    try:
        resp = requests.get(
            GBIF_API,
            params={"advanced": "1", "dna_sequence_id": seq_id, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            missing += 1
            continue
        occ = results[0]
        # Look for marker gene in extensions
        gene = None
        for ext_key, ext_records in occ.get("extensions", {}).items():
            for rec in ext_records:
                for field, val in rec.items():
                    if "pcr_primer_name" in field.lower() or "target_gene" in field.lower():
                        gene = val
                    elif "marker" in field.lower() and val:
                        gene = val
                # Check for ITS / 16S / 18S / COI in any value
                for field, val in rec.items():
                    if isinstance(val, str):
                        for marker in ("ITS", "COI", "16S", "18S", "28S", "rbcL", "matK", "trnL"):
                            if marker.lower() in val.lower():
                                gene = marker
                                break
        if gene is None:
            # Try verbatimScientificName or other fields at occurrence level
            for field, val in occ.items():
                if isinstance(val, str):
                    for marker in ("ITS", "COI", "16S", "18S", "28S", "rbcL", "matK", "trnL"):
                        if marker.lower() in val.lower():
                            gene = marker
                            break
        if gene:
            gene_counter[gene] += 1
            gene_examples.setdefault(gene, seq_id)
        else:
            gene_counter["unknown"] += 1
    except Exception as exc:
        print(f"  Warning: API error for {seq_id}: {exc}")
        missing += 1
    time.sleep(API_DELAY)

print(f"  Marker gene counts: {dict(gene_counter)}")
print(f"  {missing} sequences returned no GBIF results")

# ---------------------------------------------------------------------------
# 3. Build markdown report
# ---------------------------------------------------------------------------
def df_to_md(df, max_rows=20):
    return df.head(max_rows).to_markdown(index=False)


# Kingdom/phylum summary (top 15 rows)
tax_md = df_to_md(taxonomy, 15)

# Dataset summary (top 20)
ds_md = df_to_md(datasets, 20)

# Ambiguity summary (top 20 sequences)
seqs_md = df_to_md(
    seqs[["nucleotidesequenceid", "n_distinct_families", "n_datasets",
          "n_occurrences", "kingdom", "phylum"]].head(20)
)

# Gene summary
if gene_counter:
    gene_total = sum(gene_counter.values())
    gene_lines = "\n".join(
        f"| {g} | {c} | {c/gene_total*100:.0f}% |"
        for g, c in gene_counter.most_common()
    )
    gene_table = "| Marker gene | Sequences sampled | % |\n|---|---|---|\n" + gene_lines
else:
    gene_table = "_No gene data retrieved._"

report = textwrap.dedent(f"""\
# Top-100 Most Taxonomically Ambiguous Sequences — Characterisation

**Generated:** {time.strftime('%Y-%m-%d')}
**Source file:** `{PARQUET}`
**Total unique sequences:** {total_seqs}
**Total occurrence rows:** {total_rows}
**Total contributing datasets:** {total_ds}

---

## 1. Target Genes

The marker gene was inferred from GBIF occurrence API metadata for a sample
of {len(sample_ids)} sequences. A result was retrieved for
{len(sample_ids) - missing} of them.

{gene_table}

> Sequences were queried via:
> `https://api.gbif.org/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`

---

## 2. Taxonomic Groups

Distribution of kingdoms and phyla across **all occurrence rows** in the
top-100 dataset. Sequences where taxonomy is entirely missing are shown as
`(null)`.

{tax_md}

---

## 3. Contributing Datasets

Datasets ranked by number of occurrences. The column
`n_families_contributed` shows how many distinct family-level annotations
each dataset introduces across the 100 sequences.

{ds_md}

---

## 4. Per-Sequence Ambiguity (top 20)

The 20 most ambiguous sequences by number of distinct family annotations.

{seqs_md}

---

## Notes

- All supporting queries are in `queries/`.
- CSVs for all tables are in `output/`.
- To regenerate `{PARQUET}` from the full dataset, run:
  `duckdb -c ".read queries/generate_top100_distinct_families.sql"`
  (edit the query to point at `trino_joined.parquet`).
- To re-run this analysis:
  `python3 analysis/characterise_top100.py`
""")

out_path = OUTPUT_DIR / "top100_characterisation.md"
out_path.write_text(report)
print(f"\nReport written to {out_path}")
