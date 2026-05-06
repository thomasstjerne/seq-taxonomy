"""
Convert a Darwin Core archive to a normalised FASTA file.

Reads dna.tsv and occurrence.tsv from an extracted DwC archive and writes a
FASTA file whose headers contain the fields defined in tsvHeaders.js plus
dataset shortname and target gene.

Header format (pipe-separated):
  ID | accessionNumber | scientificName | decimalLatitude | decimalLongitude |
  typeStatus | catalogueNumber | identifiedBy | taxonRank | country | locality |
  basisOfRecord | higherClassification | dataset | targetGene

Usage:
    python3 analysis/dwc_to_fasta.py <dwc_dir> <dataset_shortname> --target-gene 12s

Example:
    python3 analysis/dwc_to_fasta.py source-data/nbdl/extracted nbdl_12s --target-gene 12s
"""

import argparse
import csv
import re
import unicodedata
from pathlib import Path

OUTPUT_DIR = Path("output/fasta")

DNA_ID       = 0
DNA_GENE     = 1
DNA_SEQUENCE = 2


def sanitize(value: str) -> str:
    """ASCII-safe, whitespace→underscore, for BLAST/vsearch header compatibility."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", ascii_only).strip("_")


def get_taxon_rank(row: dict) -> str:
    genus    = row.get("genus", "").strip()
    specific = row.get("specificEpiphet", "").strip()
    if genus and specific:
        return "species"
    if genus:
        return "genus"
    if row.get("family", "").strip():
        return "family"
    if row.get("order", "").strip():
        return "order"
    if row.get("class", "").strip():
        return "class"
    if row.get("phylum", "").strip():
        return "phylum"
    if row.get("kingdom", "").strip():
        return "kingdom"
    return ""


def build_higher_classification(row: dict) -> str:
    """Semicolon-separated taxonomy from kingdom down to species binomial."""
    parts = []
    for rank in ("kingdom", "phylum", "class", "order", "family", "genus"):
        val = row.get(rank, "").strip()
        if val:
            parts.append(val)
    genus    = row.get("genus", "").strip()
    specific = row.get("specificEpiphet", "").strip()
    if genus and specific:
        parts.append(f"{genus}_{specific}")
    return ";".join(parts)


def load_sequences(dna_path: Path, target_gene: str) -> dict[str, str]:
    sequences: dict[str, str] = {}
    with open(dna_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue
            if row[DNA_GENE].strip().lower() == target_gene.lower():
                sequences[row[DNA_ID].strip()] = row[DNA_SEQUENCE].strip().upper()
    return sequences


def load_occurrences(occ_path: Path) -> dict[str, dict]:
    occurrences: dict[str, dict] = {}
    with open(occ_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            occ_id = row.get("occurrenceId", "").strip()
            if occ_id:
                occurrences[occ_id] = row
    return occurrences


def build_header(occ: dict, seq_id: str, dataset: str, target_gene: str) -> str:
    fields = [
        seq_id,
        sanitize(occ.get("otherCatalogNumbers", "")),
        sanitize(occ.get("scientificName", "")),
        sanitize(occ.get("decimalLatitude", "")),
        sanitize(occ.get("decimalLongitude", "")),
        sanitize(occ.get("typeStatus", "")),
        sanitize(occ.get("catalogNumber", "")),
        sanitize(occ.get("identifiedBy", "")),
        get_taxon_rank(occ),
        sanitize(occ.get("country", "")),
        sanitize(occ.get("locality", "")),
        sanitize(occ.get("basisOfRecord", "")),  # blank in NBDL
        sanitize(build_higher_classification(occ)),
        dataset,
        target_gene,
    ]
    return "|".join(fields)


def main():
    parser = argparse.ArgumentParser(description="Convert a DwC archive to a normalised FASTA")
    parser.add_argument("dwc_dir",  help="Path to extracted DwC archive directory")
    parser.add_argument("dataset",  help="Short dataset name for FASTA headers (e.g. nbdl_12s)")
    parser.add_argument("--target-gene", required=True, help="Target gene to extract (e.g. 12s)")
    args = parser.parse_args()

    target_gene = args.target_gene.lower()
    dwc_dir     = Path(args.dwc_dir)
    output_path = OUTPUT_DIR / f"{args.dataset}.fasta"

    dna_path = dwc_dir / "dna.tsv"
    occ_path = dwc_dir / "occurrence.tsv"

    for p in (dna_path, occ_path):
        if not p.exists():
            raise FileNotFoundError(f"Expected file not found: {p}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"Loading sequences (target gene: {target_gene}) …")
    sequences = load_sequences(dna_path, target_gene)
    print(f"  {len(sequences):,} sequences found")

    print("Loading occurrences …")
    occurrences = load_occurrences(occ_path)
    print(f"  {len(occurrences):,} occurrence records")

    print(f"Writing {output_path} …")
    written = missing = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for seq_id, sequence in sequences.items():
            occ = occurrences.get(seq_id)
            if not occ:
                print(f"  Warning: no occurrence record for {seq_id}")
                missing += 1
                continue
            header = build_header(occ, seq_id, args.dataset, target_gene)
            out.write(f">{header}\n{sequence}\n")
            written += 1

    print(f"\nDone — {written:,} sequences written to {output_path}")
    if missing:
        print(f"  {missing} sequences skipped (no occurrence record)")


if __name__ == "__main__":
    main()
