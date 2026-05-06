"""
Convert a MIDORI2 BLAST/UNIQ FASTA to the normalised header format.

MIDORI2 header format:
  >accession.version.start.end###root_1;Taxon_taxid;...;Genus_species_taxid

Output header format (pipe-separated, same field order as dwc_to_fasta.py):
  ID | accessionNumber | scientificName | decimalLatitude | decimalLongitude |
  typeStatus | catalogueNumber | identifiedBy | taxonRank | country | locality |
  basisOfRecord | higherClassification | dataset | targetGene

Fields absent from MIDORI2 (lat/lon, typeStatus, etc.) are left empty.

Usage:
    python3 analysis/midori2_to_fasta.py <fasta_file> <dataset_shortname> --target-gene 12s

Example:
    python3 analysis/midori2_to_fasta.py \\
        source-data/midori2/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta \\
        midori2_12s --target-gene 12s
"""

import argparse
import re
from pathlib import Path

OUTPUT_DIR = Path("output/fasta")

RANK_PREFIXES = {"kingdom", "phylum", "class", "order", "family", "genus", "suborder",
                 "subclass", "subfamily", "superfamily", "tribe", "subtribe", "infraorder"}


def parse_node(node: str) -> tuple[str, str, str]:
    """
    Parse a single taxonomy node into (rank, name, taxid).

    Examples:
      'Eukaryota_2759'              → ('', 'Eukaryota', '2759')
      'order_Carcharhiniformes_3639' → ('order', 'Carcharhiniformes', '3639')
      'Paravannella_minima_1443144'  → ('', 'Paravannella minima', '1443144')
    """
    parts = node.split("_")

    # Strip trailing numeric taxid
    if parts and parts[-1].isdigit():
        taxid = parts.pop()
    else:
        taxid = ""

    # Strip leading rank prefix
    rank = ""
    if parts and parts[0].lower() in RANK_PREFIXES:
        rank = parts.pop(0).lower()

    name = " ".join(parts)
    return rank, name, taxid


def infer_rank(rank_prefix: str, name: str) -> str:
    """Infer taxon rank from the rank prefix or the number of words in the name."""
    if rank_prefix:
        return rank_prefix
    if len(name.split()) == 2:
        return "species"
    return ""


def parse_taxonomy(taxonomy_str: str) -> tuple[str, str, str]:
    """
    Parse the MIDORI2 taxonomy string (after ###) into:
      - scientificName  (name of the lowest node)
      - taxonRank       (inferred rank of the lowest node)
      - higherClassification  (semicolon-separated names, root excluded)
    """
    nodes = [n for n in taxonomy_str.split(";") if n and not n.startswith("root_")]
    if not nodes:
        return "", "", ""

    names = []
    for node in nodes:
        rank_prefix, name, _ = parse_node(node)
        if name:
            names.append(name)

    if not names:
        return "", "", ""

    scientific_name = names[-1]
    last_rank_prefix, _, _ = parse_node(nodes[-1])
    taxon_rank = infer_rank(last_rank_prefix, scientific_name)
    higher_classification = ";".join(names)

    return scientific_name, taxon_rank, higher_classification


def parse_header(header_line: str) -> tuple[str, str, str, str, str]:
    """
    Parse a MIDORI2 FASTA header line into:
      seq_id, accession_number, scientific_name, taxon_rank, higher_classification
    """
    raw = header_line.lstrip(">").strip()

    if "###" in raw:
        seq_id, taxonomy_str = raw.split("###", 1)
    else:
        seq_id = raw
        taxonomy_str = ""

    # GenBank accession is the first two dot-separated components (e.g. MH910097.1)
    acc_parts = seq_id.split(".")
    accession_number = ".".join(acc_parts[:2]) if len(acc_parts) >= 2 else seq_id

    scientific_name, taxon_rank, higher_classification = parse_taxonomy(taxonomy_str)

    return seq_id, accession_number, scientific_name, taxon_rank, higher_classification


def build_header(seq_id, accession_number, scientific_name, taxon_rank,
                 higher_classification, dataset, target_gene) -> str:
    def s(v):
        return v.replace(" ", "_") if v else ""

    fields = [
        seq_id,
        accession_number,
        s(scientific_name),
        "",   # decimalLatitude
        "",   # decimalLongitude
        "",   # typeStatus
        "",   # catalogueNumber
        "",   # identifiedBy
        taxon_rank,
        "",   # country
        "",   # locality
        "",   # basisOfRecord
        s(higher_classification),
        dataset,
        target_gene,
    ]
    return "|".join(fields)


def main():
    parser = argparse.ArgumentParser(description="Convert MIDORI2 FASTA to normalised header format")
    parser.add_argument("fasta_file", help="Path to MIDORI2 FASTA file")
    parser.add_argument("dataset",    help="Short dataset name for headers (e.g. midori2_12s)")
    parser.add_argument("--target-gene", required=True, help="Target gene label (e.g. 12s)")
    args = parser.parse_args()

    fasta_path  = Path(args.fasta_file)
    target_gene = args.target_gene.lower()
    output_path = OUTPUT_DIR / f"{args.dataset}.fasta"

    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA file not found: {fasta_path}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"Converting {fasta_path.name} …")
    written = 0

    with open(fasta_path, encoding="utf-8") as inp, \
         open(output_path, "w", encoding="utf-8") as out:

        seq_id = accession_number = scientific_name = taxon_rank = higher_classification = ""
        sequence_lines = []

        def flush():
            nonlocal written
            if seq_id and sequence_lines:
                header = build_header(seq_id, accession_number, scientific_name,
                                      taxon_rank, higher_classification,
                                      args.dataset, target_gene)
                out.write(f">{header}\n{''.join(sequence_lines).upper()}\n")
                written += 1

        for line in inp:
            line = line.rstrip("\n")
            if line.startswith(">"):
                flush()
                sequence_lines = []
                seq_id, accession_number, scientific_name, taxon_rank, higher_classification = \
                    parse_header(line)
            else:
                sequence_lines.append(line.strip())

        flush()  # last record

    print(f"Done — {written:,} sequences written to {output_path}")


if __name__ == "__main__":
    main()
