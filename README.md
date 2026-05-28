# seq-taxonomy

Build a combined multi-gene reference database from public sequence sources, and use it to assign unified taxonomic annotations to DNA sequences shared to GBIF.

## Overview

Many DNA sequences in GBIF carry inconsistent or missing taxonomic annotations because different publishers have annotated the same sequence variant differently. This project:

1. Compiles a combined reference database from multiple curated sources (MitoFish, NBDL, MIDORI2, PR2, BOLDistilled, UNITE, RefSeq, GTDB)
2. Normalises all sources into a common pipe-separated FASTA header format
3. Builds a vsearch UDB index for fast taxonomic assignment
4. Analyses annotation agreement across GBIF datasets to develop consensus rules

## Requirements

```bash
brew install yq node
pip install duckdb pandas openpyxl
cd node-server && npm install
```

**vsearch (GBIF fork with web server support):**

The pipeline requires the GBIF fork of vsearch on the `batch-requests` branch, which adds HTTP server mode. Build from source:

```bash
git clone --branch batch-requests https://github.com/gbif/vsearch.git
cd vsearch
./autogen.sh
./configure
make
sudo make install
```

## Building the reference database

All sources are configured in `datasets.yaml`. A single script downloads, extracts, converts, and indexes everything:

```bash
bash analysis/download_and_convert.sh
```

This will:
1. Create `source-data/<dataset>/` for each source and download all files
2. Extract archives where needed
3. Convert each source to the normalised FASTA format → `output/fasta/<dataset>.fasta`
4. Concatenate all FASTAs → `output/fasta/gbif_dna_taxonomy_annotation.fasta`
5. Build a vsearch UDB index → `output/fasta/gbif_dna_taxonomy_annotation.udb`

### Partial runs

```bash
bash analysis/download_and_convert.sh --download-only                                  # fetch files only
bash analysis/download_and_convert.sh --convert-only                                   # skip download, re-convert
bash analysis/download_and_convert.sh gtdb pr2                                         # selected datasets only
bash analysis/download_and_convert.sh --convert-only gtdb pr2                          # flags and filters combine
bash analysis/download_and_convert.sh --list                                           # show all datasets
bash analysis/download_and_convert.sh --config small12s.yaml                           # use a custom config file
bash analysis/download_and_convert.sh --output-name small_12s                          # set output FASTA/UDB base name
bash analysis/download_and_convert.sh --config small12s.yaml --output-name small_12s  # combine both
```

### Datasets

| Short name | Gene | Scope | Version |
|---|---|---|---|
| mitofish | 12S | Fish (Actinopterygii, Chondrichthyes) | 2026-04 |
| nbdl | 12S | Australian fauna | 2024 |
| midori2 | 12S | Vertebrates (GenBank-derived) | GB269 |
| pr2 | 18S | Protists and algae | 5.1.0 |
| boldistilled | COI | Animals (BOLD BIN clusters) | Apr2026 |
| unite | ITS | Fungi and other eukaryotes | 10.0 |
| refSeq_arc_16s | 16S | Archaea (NCBI RefSeq) | 2026-05-01 |
| refSeq_bac_16s | 16S | Bacteria (NCBI RefSeq) | 2026-05-01 |
| refseq_its | ITS | Fungi and land plants (NCBI RefSeq) | — |
| gtdb | 16S | Bacteria and Archaea | v232 |
| its2_global | ITS2 | Vascular plants | 2023-01-17 |
| bell_brosi_rbcl | rbcL | Land plants | 2021-07 |

See `source-data/README.md` for download URLs and file descriptions for each source.

### Normalised FASTA header format

All output FASTAs share the same 23-field pipe-separated header:

```
>ID|accessionNumber|scientificName|decimalLatitude|decimalLongitude|typeStatus|catalogueNumber|identifiedBy|taxonRank|country|locality|basisOfRecord|higherClassification|dataset|targetGene|domain|kingdom|phylum|class|order|family|genus|species
```

Fields unavailable in a given source are left empty; pipe delimiters are always present so columns stay aligned across sources.

### Within-species deduplication

Several databases contain many exact within-species duplicates. The pipeline runs deduplication automatically for these datasets via `postprocess_cmd` in `datasets.yaml`, and the deduped FASTA is what goes into the combined output. To run it manually:

```bash
python3 analysis/duplicate_analysis.py \
    --fasta output/fasta/its2_global.fasta \
    --write-deduped output/fasta/its2_global_deduped.fasta

python3 analysis/duplicate_analysis.py \
    --fasta output/fasta/mitofish_12s.fasta \
    --write-deduped output/fasta/mitofish_12s_deduped.fasta
```

This collapses entries with the same sequence **and** the same species, but keeps sequences that appear under multiple species. Those cross-species duplicates are preserved intentionally — `pickBestMatch` uses them as a signal that the sequence cannot be identified below genus level.

| Dataset | Before | After | Removed |
|---|---|---|---|
| its2_global | 307,976 | 258,218 | 49,758 |
| mitofish_12s | 43,870 | 37,145 | 6,725 |
| pr2_18s | 223,357 | 196,218 | 27,139 |

## Annotating GBIF sequences against the reference database

With the reference UDB built, you can annotate sequences from the GBIF dataset in three steps.

### 1. Start the servers

```bash
# vsearch search server
vsearch --threads 8 --usearch_global_server \
  --db output/fasta/gbif_dna_taxonomy_annotation.udb \
  --id 0.9 --query_cov 0.5 \
  --maxaccepts 1000 --maxrejects 1000 --maxhits 100 \
  --port 8000 --temp_file_path ~/temp-vsearch

# Node.js proxy (parses vsearch output → JSON)
cd node-server && npm start
```

### 2. Create a query FASTA

Filter `trino_joined.parquet` by any SQL condition and write matching sequences to a FASTA:

```bash
python3 analysis/query_to_fasta.py musca --where "genus = 'Musca'"
# → tests/input/musca.fasta  (7,356 sequences)

# For large queries, add --temp-dir to allow DuckDB to spill to disk:
python3 analysis/query_to_fasta.py diptera --where "\"order\" = 'Diptera'" --temp-dir /tmp/duckdb_spill
```

### 3. Annotate and write Parquet

```bash
python3 analysis/annotate_sequences.py tests/input/musca.fasta
# → output/musca_annotated.parquet

# Options:
#   --output path/to/output.parquet
#   --server http://localhost:3000
#   --batch-size 100
#   --selector pickBestMatch2   # use an alternate best-match selector (see node-server/)
```

The output has 35 columns: `queryId` + all 23 reference header fields (taxonomy, dataset, gene) + alignment stats (`identity`, `alignmentLength`, `mismatches`, `qcovs`, …).

To experiment with different selection strategies, add a file `node-server/pickBestMatchFoo.mjs` that exports a function `pickBestMatchFoo`, then pass `--selector pickBestMatchFoo`.

## Analysing GBIF sequence annotations

The main working dataset is `trino_joined.parquet` — a full join from Trino/GBIF with 171M rows and 22M unique sequences. It is not committed to git; collaborators keep their own copy.

```bash
# One-off query
duckdb -c "SELECT taxonrank, COUNT(*) FROM 'trino_joined.parquet' GROUP BY 1 ORDER BY 2 DESC"

# Run a SQL file
duckdb -c ".read queries/foo.sql"
```

A 100k-row exploration subset is committed as `small_dataset.parquet`.

### Schema

| Column | Type | Notes |
|---|---|---|
| `nucleotidesequenceid` | VARCHAR | MD5 hash identifying the exact sequence variant |
| `gbifid` | BIGINT | GBIF occurrence key |
| `datasetkey` | VARCHAR | UUID of the publishing dataset |
| `kingdom` … `species` | VARCHAR | Publisher-assigned taxonomy (may be NULL) |
| `scientificname` | VARCHAR | Publisher-assigned name at the identified rank |
| `taxonrank` | VARCHAR | Rank of the identification |

The key analytical unit is `nucleotidesequenceid` — the same sequence can appear in multiple datasets with different annotations.

## Repository layout

```
datasets.yaml                   # master config: sources, versions, download URLs
analysis/
  download_and_convert.sh       # reference database pipeline script
  dwc_to_fasta.py               # Darwin Core archive → normalised FASTA
  mitofish_to_fasta.py          # MitoFish → normalised FASTA
  midori2_to_fasta.py           # MIDORI2 → normalised FASTA
  pr2_to_fasta.py               # PR2 xlsx → normalised FASTA
  boldistilled_to_fasta.py      # BOLDistilled → normalised FASTA
  unite_to_fasta.py             # UNITE → normalised FASTA
  gtdb_to_fasta.py              # GTDB SSU → normalised FASTA
  its2_global_to_fasta.py       # ITS2 Global FASTA → normalised FASTA
  bell_brosi_rbcl_to_fasta.py   # Bell & Brosi rbcL DADA2 FASTA → normalised FASTA
  duplicate_analysis.py    # analyse/remove within-species duplicate sequences
  query_to_fasta.py             # filter GBIF parquet → query FASTA
  annotate_sequences.py         # send FASTA to proxy → annotated Parquet
  annotate_sequences_xlsx.py    # send FASTA to proxy → annotated Excel (xlsx)
node-server/
  index.mjs                     # Express proxy: forwards to vsearch, parses results
  pickBestMatch.mjs             # default best-match selector
  pickBestMatch2.mjs            # alternate selector (pass --selector pickBestMatch2)
queries/                        # DuckDB SQL files
output/
  fasta/                        # per-dataset and combined FASTAs + UDB index
  *_annotated.parquet           # annotation results (not committed)
tests/
  input/                        # query FASTAs generated by query_to_fasta.py
  vsearch-output/               # example raw vsearch output (blast6out, alnout)
source-data/                    # downloaded source files (not committed)
  README.md                     # download instructions for each source
small_dataset.parquet           # 100k-row GBIF subset (committed)
```
