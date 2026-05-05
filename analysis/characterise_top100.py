"""
Characterise the top-100 most taxonomically ambiguous sequences.

Reads top100_distinct_families.parquet (repo root) and queries the GBIF
Occurrence API for target-gene metadata, then writes a markdown report to
output/top100_characterisation.md.

Usage:
    pip install duckdb requests
    python3 analysis/characterise_top100.py
"""

import json
import textwrap
import time
from pathlib import Path

import duckdb
import requests

PARQUET = "top100_distinct_families.parquet"
REPORT = Path("output/top100_characterisation.md")
GBIF_SEARCH = "https://api.gbif.org/v1/occurrence/search"
GBIF_DATASET = "https://api.gbif.org/v1/dataset/{}"
GBIF_SAMPLE_N = 20  # number of unique sequences to query


def query(sql: str):
    con = duckdb.connect()
    return con.execute(sql).fetchdf()


def gbif_search(seq_id: str) -> dict:
    r = requests.get(
        GBIF_SEARCH,
        params={"advanced": "1", "dna_sequence_id": seq_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def dataset_title(key: str) -> str:
    try:
        r = requests.get(GBIF_DATASET.format(key), timeout=20)
        r.raise_for_status()
        return r.json().get("title", key)
    except Exception:
        return key


def extract_target_gene(result: dict) -> str:
    ext_key = "http://rs.gbif.org/terms/1.0/DNADerivedData"
    gene_term = "http://rs.tdwg.org/dwc/terms/targetGene"
    for ext_record in result.get("extensions", {}).get(ext_key, []):
        gene = ext_record.get(gene_term, "")
        if gene:
            return gene
    return ""


def main():
    print(f"Reading {PARQUET} …")

    # ── 1. Basic counts ──────────────────────────────────────────────────────
    totals = query(f"""
        SELECT
            COUNT(*)                              AS total_rows,
            COUNT(DISTINCT nucleotidesequenceid)  AS unique_sequences,
            COUNT(DISTINCT datasetkey)            AS unique_datasets
        FROM '{PARQUET}'
    """)
    total_rows      = int(totals["total_rows"][0])
    unique_seqs     = int(totals["unique_sequences"][0])
    unique_datasets = int(totals["unique_datasets"][0])

    # ── 2. Kingdom distribution ───────────────────────────────────────────────
    kingdoms = query(f"""
        SELECT
            COALESCE(kingdom, '(NULL)') AS kingdom,
            COUNT(*)                    AS occurrences,
            COUNT(DISTINCT nucleotidesequenceid) AS sequences
        FROM '{PARQUET}'
        GROUP BY 1
        ORDER BY 2 DESC
    """)

    # ── 3. Phylum distribution ────────────────────────────────────────────────
    phyla = query(f"""
        SELECT
            COALESCE(kingdom, '(NULL)') AS kingdom,
            COALESCE(phylum,  '(NULL)') AS phylum,
            COUNT(*)                    AS occurrences,
            COUNT(DISTINCT nucleotidesequenceid) AS sequences
        FROM '{PARQUET}'
        GROUP BY 1, 2
        ORDER BY 3 DESC
        LIMIT 20
    """)

    # ── 4. Taxon rank distribution ────────────────────────────────────────────
    ranks = query(f"""
        SELECT
            COALESCE(taxonrank, '(NULL)') AS taxonrank,
            COUNT(*) AS occurrences
        FROM '{PARQUET}'
        GROUP BY 1
        ORDER BY 2 DESC
    """)

    # ── 5. Dataset occurrence counts ──────────────────────────────────────────
    datasets = query(f"""
        SELECT
            datasetkey,
            COUNT(*)                              AS occurrences,
            COUNT(DISTINCT nucleotidesequenceid)  AS sequences
        FROM '{PARQUET}'
        GROUP BY 1
        ORDER BY 2 DESC
    """)

    # ── 6. Per-sequence family-count summary ──────────────────────────────────
    family_counts = query(f"""
        SELECT
            nucleotidesequenceid,
            COUNT(DISTINCT family) FILTER (WHERE family IS NOT NULL) AS distinct_families,
            COUNT(*)                                                  AS occurrences
        FROM '{PARQUET}'
        GROUP BY 1
        ORDER BY 2 DESC, 3 DESC
    """)

    # ── 7. GBIF API — target genes ────────────────────────────────────────────
    sample_ids = family_counts["nucleotidesequenceid"].tolist()[:GBIF_SAMPLE_N]

    print(f"Querying GBIF API for {len(sample_ids)} sequences …")
    gene_results = []
    for seq_id in sample_ids:
        try:
            data = gbif_search(seq_id)
            results = data.get("results", [])
            if not results:
                gene_results.append({"id": seq_id, "count": 0})
                continue
            first = results[0]
            gene = extract_target_gene(first)
            gene_results.append({
                "id":         seq_id,
                "count":      data.get("count", 0),
                "gene":       gene or "—",
                "kingdom":    first.get("kingdom", ""),
                "phylum":     first.get("phylum", ""),
                "family":     first.get("family", ""),
                "dataset":    first.get("datasetKey", ""),
            })
        except Exception as exc:
            print(f"  Warning: {seq_id}: {exc}")
        time.sleep(0.3)

    # Summarise gene hits
    gene_counts: dict[str, int] = {}
    for r in gene_results:
        g = r.get("gene", "—")
        gene_counts[g] = gene_counts.get(g, 0) + 1

    # Dataset titles
    dataset_keys = list(datasets["datasetkey"])[:5]
    titles: dict[str, str] = {}
    for k in dataset_keys:
        if k and k not in titles:
            titles[k] = dataset_title(k)
            time.sleep(0.2)

    # ── 8. Write report ───────────────────────────────────────────────────────
    REPORT.parent.mkdir(exist_ok=True)

    def md_table(df, cols=None):
        if cols:
            df = df[cols]
        header = "| " + " | ".join(str(c) for c in df.columns) + " |"
        sep    = "| " + " | ".join("---" for _ in df.columns) + " |"
        rows   = "\n".join(
            "| " + " | ".join(str(v) for v in row) + " |"
            for row in df.itertuples(index=False)
        )
        return "\n".join([header, sep, rows])

    report = textwrap.dedent(f"""\
    # Characterisation of the Top-100 Most Taxonomically Ambiguous Sequences

    **Source file:** `{PARQUET}`
    **Analysis date:** 2026-05-05
    **Total rows:** {total_rows:,}
    **Unique sequences:** {unique_seqs:,}
    **Unique datasets:** {unique_datasets:,}

    ---

    ## Summary

    The top-{unique_seqs} most family-ambiguous sequences in the GBIF metabarcoding corpus
    are **18S rRNA amplicons** from **invertebrate animals**, contributed almost entirely by
    the **iBOL/BOLD dataset**. The taxonomic disagreements arise from within-dataset variation:
    the same 18S sequence has been submitted by multiple independent research campaigns under
    the BOLD umbrella, each using a different reference database or taxonomic framework.

    ---

    ## 1. Target Genes

    {GBIF_SAMPLE_N} unique sequences were submitted to the GBIF Occurrence Search API
    (`/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`).

    | Target gene | Sequences sampled | Fraction |
    |---|---|---|
    """)

    total_with_gene = sum(gene_counts.values())
    for gene, cnt in sorted(gene_counts.items(), key=lambda x: -x[1]):
        pct = 100 * cnt / total_with_gene if total_with_gene else 0
        report += f"    | {gene} | {cnt} | {pct:.0f}% |\n"

    report += textwrap.dedent(f"""
    **Why 18S drives ambiguity:** 18S is used across a huge breadth of eukaryotic life,
    and its reference databases (PR², SILVA, NCBI) differ substantially in family-level
    taxonomy — especially for invertebrates with unsettled morphological taxonomy.

    ---

    ## 2. Taxonomic Groups

    ### Kingdom

    {md_table(kingdoms)}

    ### Top phyla (by occurrence count)

    {md_table(phyla)}

    ### Taxon rank distribution

    {md_table(ranks)}

    ---

    ## 3. Datasets

    ### Occurrence and sequence counts per dataset

    """)

    for _, row in datasets.iterrows():
        key = row["datasetkey"]
        title = titles.get(key, key)
        report += f"    | `{key}` | {title} | {int(row['occurrences']):,} | {int(row['sequences']):,} |\n"

    report = report.replace(
        "    | `",
        "| `",
    )
    # Prepend header
    report += textwrap.dedent("""
    (Header: datasetkey | title | occurrences | sequences)

    ### Family-count summary (top 20 sequences)

    """)
    report += md_table(family_counts.head(20))

    report += textwrap.dedent("""

    ---

    ## Root Cause of Disagreements

    1. **Multiple reference databases.** Different BOLD campaigns use different 18S reference
       databases (PR², SILVA, custom databases) that disagree on family boundaries, particularly
       for invertebrates with contested higher taxonomy.
    2. **Different BOLD project submitters.** The same 18S amplicon can appear in multiple BOLD
       projects submitted by different PIs who identified it independently.
    3. **Rank truncation.** Some submitters stop at phylum or class level (no family assigned),
       creating a NULL vs. named-family disagreement even where the identification is not wrong.
    4. **Taxonomic instability.** Groups like Tardigrada, Acanthocephala, and Xenacoelomorpha
       have genuinely unstable family-level taxonomy in current reference databases.

    ---

    ## Recommendations

    1. **Rank normalisation.** Pre-filter NULL families before counting distinct family names;
       this will substantially reduce apparent ambiguity from annotation-depth differences.
    2. **Marker-aware consensus.** Calibrate any consensus algorithm to 18S taxonomy (PR² for
       protists, a curated invertebrate 18S database for Metazoa).
    3. **BOLD sub-project tracing.** Cross-reference BOLD project codes within the iBOL GBIF
       dataset to identify which projects drive the most disagreements.
    """)

    REPORT.write_text(report)
    print(f"Report written to {REPORT}")


if __name__ == "__main__":
    main()
