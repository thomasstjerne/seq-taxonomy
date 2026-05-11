"""
Two-panel plot:
  Left:  histogram — how many distinct species names each unique sequence has
  Right: rank abundance — how many sequences each species name covers

Usage:
    python3 analysis/plot_species_sequence_distributions.py
    python3 analysis/plot_species_sequence_distributions.py --parquet trino_joined.parquet
    python3 analysis/plot_species_sequence_distributions.py --output output/species_distributions.png
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

DEFAULT_PARQUET = "small_dataset.parquet"
DEFAULT_OUTPUT_DISAGREEMENT = "output/species_disagreement.png"
DEFAULT_OUTPUT_COVERAGE     = "output/species_coverage.png"
DEFAULT_OUTPUT_AMBIGUITY    = "output/species_ambiguity.png"
DEFAULT_OUTPUT_TAXONOMY     = "output/ambiguous_sequences_by_family_genus.xlsx"


def load_data(parquet: str):
    con = duckdb.connect()

    # Species names per sequence — only sequences with genuine disagreement (>1 distinct name)
    species_per_seq = con.execute(f"""
        SELECT nucleotidesequenceid, COUNT(DISTINCT species) AS n_species
        FROM '{parquet}'
        WHERE taxonrank = 'SPECIES' AND species IS NOT NULL
        GROUP BY nucleotidesequenceid
        HAVING COUNT(DISTINCT species) >= 2
    """).df()

    # Sequences per species name
    seqs_per_species = con.execute(f"""
        SELECT species, COUNT(DISTINCT nucleotidesequenceid) AS n_sequences
        FROM '{parquet}'
        WHERE taxonrank = 'SPECIES' AND species IS NOT NULL
        GROUP BY species
        ORDER BY n_sequences DESC
    """).df()

    # Ambiguity bar chart: sequences in >1 GBIF record, split by 1 vs ≥2 species names
    ambiguity = con.execute(f"""
        WITH multi AS (
            SELECT nucleotidesequenceid
            FROM '{parquet}'
            GROUP BY nucleotidesequenceid
            HAVING COUNT(*) > 1
        )
        SELECT
            CASE WHEN COUNT(DISTINCT t.species) = 1
                 THEN 'Exactly one species name'
                 ELSE 'Two or more species names' END AS category,
            COUNT(*) AS n_sequences
        FROM '{parquet}' t
        JOIN multi USING (nucleotidesequenceid)
        WHERE t.taxonrank = 'SPECIES' AND t.species IS NOT NULL
        GROUP BY nucleotidesequenceid
    """).df()

    ambiguity = ambiguity.groupby("category")["n_sequences"].count().reset_index()
    ambiguity.columns = ["category", "n_sequences"]

    # Family/genus breakdown of the ambiguous sequences (in >1 record, ≥2 species names)
    ambiguous_taxonomy = con.execute(f"""
        WITH multi AS (
            SELECT nucleotidesequenceid
            FROM '{parquet}'
            GROUP BY nucleotidesequenceid
            HAVING COUNT(*) > 1
        ),
        ambiguous AS (
            SELECT nucleotidesequenceid
            FROM '{parquet}' t
            JOIN multi USING (nucleotidesequenceid)
            WHERE t.taxonrank = 'SPECIES' AND t.species IS NOT NULL
            GROUP BY nucleotidesequenceid
            HAVING COUNT(DISTINCT t.species) >= 2
        )
        SELECT
            t.family,
            t.genus,
            COUNT(DISTINCT t.nucleotidesequenceid) AS n_sequences
        FROM '{parquet}' t
        JOIN ambiguous USING (nucleotidesequenceid)
        WHERE t.family IS NOT NULL OR t.genus IS NOT NULL
        GROUP BY t.family, t.genus
        ORDER BY n_sequences DESC
    """).df()

    return species_per_seq, seqs_per_species, ambiguity, ambiguous_taxonomy


def plot(species_per_seq, seqs_per_species, ambiguity, ambiguous_taxonomy, parquet: str,
         output_disagreement: str, output_coverage: str, output_ambiguity: str,
         output_taxonomy: str):
    stem = Path(parquet).name

    # ── Plot 1: rank plot — sequences with ≥2 distinct species names ──────────
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    counts = species_per_seq["n_species"].sort_values(ascending=False).reset_index(drop=True)
    seq_ranks = np.arange(1, len(counts) + 1)
    ax1.plot(seq_ranks, counts.values, color="steelblue", linewidth=1)
    ax1.set_yscale("log")
    ax1.set_xlabel("Sequence rank (most → fewest distinct species names)")
    ax1.set_ylabel("Distinct species names (log scale)")
    ax1.set_title(f"Annotation disagreement — {stem}\n(sequences with ≥2 distinct species names)")
    ax1.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig1.tight_layout()
    Path(output_disagreement).parent.mkdir(parents=True, exist_ok=True)
    fig1.savefig(output_disagreement, dpi=150)
    print(f"Saved to {output_disagreement}")

    # ── Plot 2: rank abundance — sequences per species name ───────────────────
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    sp_ranks = np.arange(1, len(seqs_per_species) + 1)
    ax2.plot(sp_ranks, seqs_per_species["n_sequences"].values, color="darkorange", linewidth=1)
    ax2.set_yscale("log")
    ax2.set_xlabel("Species rank (most → fewest sequences)")
    ax2.set_ylabel("Number of sequences (log scale)")
    ax2.set_title(f"Sequence coverage per species name — {stem}")
    ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    fig2.tight_layout()
    Path(output_coverage).parent.mkdir(parents=True, exist_ok=True)
    fig2.savefig(output_coverage, dpi=150)
    print(f"Saved to {output_coverage}")

    # ── Plot 3: bar chart — taxonomic ambiguity ───────────────────────────────
    fig3, ax3 = plt.subplots(figsize=(6, 5))
    ordered = ["Exactly one species name", "Two or more species names"]
    colors  = ["steelblue", "tomato"]
    values  = [ambiguity.set_index("category")["n_sequences"].get(cat, 0) for cat in ordered]
    bars = ax3.bar(ordered, values, color=colors, edgecolor="white", width=0.5)
    ax3.bar_label(bars, labels=[f"{v:,}" for v in values], padding=4, fontsize=10)
    ax3.set_ylabel("Number of unique sequences")
    ax3.set_title(f"Taxonomic ambiguity — {stem}\n(sequences in >1 GBIF record, with species-level annotation)")
    ax3.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax3.set_ylim(0, max(values) * 1.12)
    fig3.tight_layout()
    Path(output_ambiguity).parent.mkdir(parents=True, exist_ok=True)
    fig3.savefig(output_ambiguity, dpi=150)
    print(f"Saved to {output_ambiguity}")

    # ── Table: family/genus breakdown of ambiguous sequences ─────────────────
    Path(output_taxonomy).parent.mkdir(parents=True, exist_ok=True)
    ambiguous_taxonomy.to_excel(output_taxonomy, index=False)
    print(f"Saved to {output_taxonomy}")

    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", default=DEFAULT_PARQUET, help="Parquet file to query")
    parser.add_argument("--output-disagreement", default=DEFAULT_OUTPUT_DISAGREEMENT,
                        help="Output path for disagreement plot")
    parser.add_argument("--output-coverage",     default=DEFAULT_OUTPUT_COVERAGE,
                        help="Output path for coverage plot")
    parser.add_argument("--output-ambiguity",    default=DEFAULT_OUTPUT_AMBIGUITY,
                        help="Output path for ambiguity bar chart")
    parser.add_argument("--output-taxonomy",     default=DEFAULT_OUTPUT_TAXONOMY,
                        help="Output path for family/genus breakdown xlsx")
    args = parser.parse_args()

    if not Path(args.parquet).exists():
        raise FileNotFoundError(f"Parquet file not found: {args.parquet}")

    print(f"Loading data from {args.parquet} …")
    species_per_seq, seqs_per_species, ambiguity, ambiguous_taxonomy = load_data(args.parquet)
    print(f"  {len(species_per_seq):,} sequences with ≥2 distinct species names")
    print(f"  {len(seqs_per_species):,} distinct species names")
    print(f"  {len(ambiguous_taxonomy):,} family/genus groups in ambiguous sequences")
    plot(species_per_seq, seqs_per_species, ambiguity, ambiguous_taxonomy, args.parquet,
         args.output_disagreement, args.output_coverage, args.output_ambiguity,
         args.output_taxonomy)


if __name__ == "__main__":
    main()
