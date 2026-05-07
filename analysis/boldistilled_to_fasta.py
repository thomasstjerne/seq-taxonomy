"""
Convert BOLDistilled FASTA + taxonomy TSV to the normalised FASTA header format.

BOLDistilled FASTA header format:  >sampleID|BIN
Taxonomy TSV is indexed by BIN with columns:
  bin, kingdom, phylum, class, order, family, subfamily, tribe,
  genus, species, subspecies, concordant_rank, discordant_rank

Output header format (pipe-separated, same field order as all other conversion scripts):
  ID | accessionNumber | scientificName | decimalLatitude | decimalLongitude |
  typeStatus | catalogueNumber | identifiedBy | taxonRank | country | locality |
  basisOfRecord | higherClassification | dataset | targetGene

Usage:
    python3 analysis/boldistilled_to_fasta.py <fasta_file> <taxonomy_tsv> <dataset_shortname> --target-gene coi

Example:
    python3 analysis/boldistilled_to_fasta.py \\
        source-data/BOLDistilled/BOLDistilled_COI_Apr2026_SEQUENCES.fasta \\
        source-data/BOLDistilled/BOLDistilled_COI_Apr2026_TAXONOMY.tsv \\
        boldistilled_coi --target-gene coi
"""

import argparse
import csv
import re
import unicodedata
from pathlib import Path

OUTPUT_DIR = Path("output/fasta")

TAXON_FIELDS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]


def sanitize(value) -> str:
    if not value or value in ("", "None", "nan"):
        return ""
    normalized = unicodedata.normalize("NFD", str(value))
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", ascii_only).strip("_")


def get_scientific_name(row: dict, taxon_rank: str) -> str:
    """Return the name at the concordant rank, falling back down the hierarchy."""
    if taxon_rank and taxon_rank != "None":
        val = row.get(taxon_rank, "")
        if val and val != "None":
            return sanitize(val)
    # Fall back to lowest non-empty standard rank
    for field in reversed(TAXON_FIELDS):
        val = row.get(field, "")
        if val and val != "None":
            return sanitize(val)
    return ""


def get_higher_classification(row: dict) -> str:
    parts = []
    for field in TAXON_FIELDS:
        val = row.get(field, "")
        if val and val != "None":
            parts.append(sanitize(val))
    return ";".join(parts)


def load_taxonomy(tsv_path: Path) -> dict[str, dict]:
    taxonomy: dict[str, dict] = {}
    with open(tsv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            bin_id = row.get("bin", "").strip()
            if bin_id:
                taxonomy[bin_id] = row
    return taxonomy


def build_header(sample_id: str, bin_id: str, tax: dict, dataset: str, target_gene: str) -> str:
    taxon_rank    = tax.get("concordant_rank", "")
    if taxon_rank == "None":
        taxon_rank = ""
    scientific_name        = get_scientific_name(tax, taxon_rank)
    higher_classification  = get_higher_classification(tax)

    def rank(field: str) -> str:
        val = tax.get(field, "")
        return sanitize(val) if val and val != "None" else ""

    fields = [
        sample_id,
        sample_id,
        scientific_name,
        "",                          # decimalLatitude
        "",                          # decimalLongitude
        "",                          # typeStatus
        "",                          # catalogueNumber
        "",                          # identifiedBy
        taxon_rank,
        "",                          # country
        "",                          # locality
        "",                          # basisOfRecord
        higher_classification,
        dataset,
        target_gene,
        "",                          # domain
        rank("kingdom"),
        rank("phylum"),
        rank("class"),
        rank("order"),
        rank("family"),
        rank("genus"),
        rank("species"),
    ]
    return "|".join(fields)


def main():
    parser = argparse.ArgumentParser(description="Convert BOLDistilled to normalised FASTA format")
    parser.add_argument("fasta_file",    help="Path to BOLDistilled sequences FASTA")
    parser.add_argument("taxonomy_tsv",  help="Path to BOLDistilled taxonomy TSV")
    parser.add_argument("dataset",       help="Short dataset name for headers (e.g. boldistilled_coi)")
    parser.add_argument("--target-gene", required=True, help="Target gene label (e.g. coi)")
    args = parser.parse_args()

    fasta_path  = Path(args.fasta_file)
    tsv_path    = Path(args.taxonomy_tsv)
    target_gene = args.target_gene.lower()
    output_path = OUTPUT_DIR / f"{args.dataset}.fasta"

    for p in (fasta_path, tsv_path):
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading taxonomy …")
    taxonomy = load_taxonomy(tsv_path)
    print(f"  {len(taxonomy):,} BIN records loaded")

    print(f"Streaming {fasta_path.name} …")
    written = missing = 0

    with open(fasta_path, encoding="utf-8") as inp, \
         open(output_path, "w", encoding="utf-8") as out:

        sample_id = bin_id = ""
        seq_lines = []

        def flush():
            nonlocal written, missing
            if not sample_id:
                return
            tax = taxonomy.get(bin_id)
            if not tax:
                nonlocal missing
                missing += 1
                return
            header = build_header(sample_id, bin_id, tax, args.dataset, target_gene)
            out.write(f">{header}\n{''.join(seq_lines).upper()}\n")
            written += 1

        for line in inp:
            line = line.rstrip("\n")
            if line.startswith(">"):
                flush()
                seq_lines = []
                raw = line[1:].split()[0]          # e.g. BLPAA17045-20|BOLD:AAA0017
                parts = raw.split("|", 1)
                sample_id = parts[0]
                bin_id    = parts[1] if len(parts) > 1 else ""
            else:
                seq_lines.append(line.strip())

        flush()

    print(f"\nDone — {written:,} sequences written to {output_path}")
    if missing:
        print(f"  {missing:,} skipped (BIN not found in taxonomy TSV)")


if __name__ == "__main__":
    main()
