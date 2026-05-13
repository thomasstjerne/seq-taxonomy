"""
Convert a Greengenes2 FASTA + taxonomy TSV to the normalised FASTA header format.

Greengenes2 distributes:
  <release>.backbone.full-length.fna.qza   — QIIME2 artifact (zip); unzip to get data/dna-sequences.fasta
  <release>.taxonomy.id.tsv.gz             — gzipped TSV; columns: Feature ID <TAB> Taxon

The .qza file must be extracted before running this script (see prepare_cmd in the yaml config).
Expected filename after extraction: <release>.backbone.full-length.fna

Taxonomy string format (GTDB-compatible rank prefixes, spaces after semicolons):
  d__Bacteria; p__Proteobacteria; c__Gammaproteobacteria; o__...; f__...; g__...; s__...

The TSV file has a header row ("Feature ID\tTaxon").

Output header format (pipe-separated, same 23-field order as all other scripts):
  ID | accessionNumber | scientificName | decimalLatitude | decimalLongitude |
  typeStatus | catalogueNumber | identifiedBy | taxonRank | country | locality |
  basisOfRecord | higherClassification | dataset | targetGene |
  domain | kingdom | phylum | class | order | family | genus | species

Usage:
    python3 analysis/greengenes2_to_fasta.py <gg2_dir> <dataset_shortname> --target-gene SSU_rRNA_16S_prokaryotic

Example:
    python3 analysis/greengenes2_to_fasta.py source-data/greengenes2 greengenes2_16s --target-gene SSU_rRNA_16S_prokaryotic
"""

import argparse
import gzip
import re
import unicodedata
from pathlib import Path

OUTPUT_DIR = Path("output/fasta")

RANK_PREFIXES = {
    "d__": "domain",
    "p__": "phylum",
    "c__": "class",
    "o__": "order",
    "f__": "family",
    "g__": "genus",
    "s__": "species",
}

RANK_ORDER = ["domain", "phylum", "class", "order", "family", "genus", "species"]

UNRESOLVED = re.compile(r"^[a-z]__$")


def sanitize(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", ascii_only).strip("_")


def parse_taxonomy(tax_str: str) -> dict:
    ranks = {}
    for node in tax_str.split(";"):
        node = node.strip()
        for prefix, rank in RANK_PREFIXES.items():
            if node.startswith(prefix):
                name = node[len(prefix):]
                if name and not UNRESOLVED.match(node):
                    ranks[rank] = name
                break
    return ranks


def get_scientific_name_and_rank(ranks: dict) -> tuple:
    for rank in reversed(RANK_ORDER):
        if rank in ranks:
            return sanitize(ranks[rank]), rank
    return "", ""


def get_higher_classification(ranks: dict) -> str:
    return ";".join(sanitize(ranks[r]) for r in RANK_ORDER if r in ranks)


def load_taxonomy(tsv_path: Path) -> dict:
    taxonomy = {}
    opener = gzip.open if tsv_path.suffix == ".gz" else open
    with opener(tsv_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("Feature ID"):
                continue
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            seq_id, tax_str = parts[0].strip(), parts[1].strip()
            taxonomy[seq_id] = parse_taxonomy(tax_str)
    return taxonomy


def build_header(seq_id: str, ranks: dict, dataset: str, target_gene: str) -> str:
    scientific_name, taxon_rank = get_scientific_name_and_rank(ranks)
    higher_classification       = get_higher_classification(ranks)

    def r(rank: str) -> str:
        return sanitize(ranks.get(rank, ""))

    fields = [
        seq_id,
        seq_id,   # accessionNumber — GG2 has no separate accession
        scientific_name,
        "",   # decimalLatitude
        "",   # decimalLongitude
        "",   # typeStatus
        "",   # catalogueNumber
        "",   # identifiedBy
        taxon_rank,
        "",   # country
        "",   # locality
        "",   # basisOfRecord
        higher_classification,
        dataset,
        target_gene,
        r("domain"),
        "",           # kingdom (not in GG2)
        r("phylum"),
        r("class"),
        r("order"),
        r("family"),
        r("genus"),
        r("species"),
    ]
    return "|".join(fields)


def convert(fasta_path: Path, taxonomy: dict, dataset: str, target_gene: str,
            out, stats: dict) -> None:
    seq_id = ""
    seq_lines = []

    def flush():
        if not seq_id or not seq_lines:
            return
        ranks = taxonomy.get(seq_id)
        if not ranks:
            stats["missing"] += 1
            return
        header = build_header(seq_id, ranks, dataset, target_gene)
        out.write(f">{header}\n{''.join(seq_lines).upper()}\n")
        stats["written"] += 1

    opener = gzip.open if fasta_path.suffix == ".gz" else open
    with opener(fasta_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                flush()
                seq_lines = []
                seq_id = line.lstrip(">").split()[0]
            else:
                seq_lines.append(line.strip())
        flush()


def find_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching '{pattern}' found in {directory}")
    if len(matches) > 1:
        raise FileNotFoundError(f"Multiple files matching '{pattern}' in {directory}: {[m.name for m in matches]}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description="Convert Greengenes2 FASTA + taxonomy TSV to normalised header format")
    parser.add_argument("gg2_dir",      help="Directory containing Greengenes2 backbone.full-length.fna and taxonomy.id.tsv.gz")
    parser.add_argument("dataset",      help="Short dataset name for headers (e.g. greengenes2_16s)")
    parser.add_argument("--target-gene", required=True, help="Vocabulary term for output FASTA headers (e.g. SSU_rRNA_16S_prokaryotic)")
    parser.add_argument("--output-dir",  default=None, help="Directory to write output FASTA (default: output/fasta)")
    args = parser.parse_args()

    OUTPUT_DIR  = Path(args.output_dir) if args.output_dir else Path("output/fasta")
    gg2_dir     = Path(args.gg2_dir)
    target_gene = args.target_gene
    output_path = OUTPUT_DIR / f"{args.dataset}.fasta"

    fasta_path = find_file(gg2_dir, "*.backbone.full-length.fna")
    tax_path   = find_file(gg2_dir, "*.taxonomy.id.tsv.gz")

    print(f"FASTA    : {fasta_path.name}")
    print(f"Taxonomy : {tax_path.name}")

    print("Loading taxonomy …")
    taxonomy = load_taxonomy(tax_path)
    print(f"  {len(taxonomy):,} records loaded")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"written": 0, "missing": 0}

    print(f"Writing {output_path} …")
    with open(output_path, "w", encoding="utf-8") as out:
        convert(fasta_path, taxonomy, args.dataset, target_gene, out, stats)

    print(f"\nDone — {stats['written']:,} sequences written to {output_path}")
    if stats["missing"]:
        print(f"  {stats['missing']:,} skipped (sequence ID not found in taxonomy)")


if __name__ == "__main__":
    main()
