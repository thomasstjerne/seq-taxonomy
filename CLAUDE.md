# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Build an approach for unified taxonomic annotation of DNA sequences shared to GBIF, resolving disagreements across datasets where the same sequence variant has been annotated differently by different publishers.

The approach has two tracks:
1. **Reference database pipeline** — compile a multi-gene reference database from public sources, normalise to a common format, and build a vsearch UDB index for taxonomic assignment
2. **GBIF annotation analysis** — query the full GBIF DNA occurrence dataset to characterise annotation disagreement and develop consensus rules

## Reference database pipeline

### Configuration

All sources are defined in `datasets.yaml` (repo root). Each entry has: `short_name`, `version`, `target_gene`, `taxonomic_scope`, `citation`, `endpoints`, optional `curl_flags`/`prepare_cmd`/`prepare_sentinel`, and `convert_cmd`.

### Running

```bash
bash analysis/download_and_convert.sh                                        # full pipeline
bash analysis/download_and_convert.sh --download-only                        # fetch only
bash analysis/download_and_convert.sh --convert-only                         # convert + index only
bash analysis/download_and_convert.sh gtdb pr2                               # selected datasets
bash analysis/download_and_convert.sh --list                                 # show available datasets
bash analysis/download_and_convert.sh --config small12s.yaml                 # use a custom config file
bash analysis/download_and_convert.sh --output-name small_12s                # set output FASTA/UDB base name
bash analysis/download_and_convert.sh --config small12s.yaml --output-name small_12s  # combine both
```

Requires: `yq` (v4), `vsearch`, `curl`, `python3`, `duckdb`, `pandas`, `openpyxl`.

### Output

- `output/fasta/<dataset>.fasta` — per-dataset normalised FASTA
- `output/fasta/gbif_dna_taxonomy_annotation.fasta` — combined (2.2 GB, ~2.6M sequences)
- `output/fasta/gbif_dna_taxonomy_annotation.udb` — vsearch UDB index (9 GB)

### Normalised FASTA header format

All conversion scripts produce the same 23-field pipe-separated header:

```
>ID|accessionNumber|scientificName|decimalLatitude|decimalLongitude|typeStatus|catalogueNumber|identifiedBy|taxonRank|country|locality|basisOfRecord|higherClassification|dataset|targetGene|domain|kingdom|phylum|class|order|family|genus|species
```

### Conversion scripts

Each script in `analysis/` handles one source format:

| Script | Source format | Datasets |
|---|---|---|
| `dwc_to_fasta.py` | Darwin Core archive (named or positional headers) | nbdl, refSeq_* |
| `mitofish_to_fasta.py` | Gzipped FASTA + DuckDB parquet tables | mitofish |
| `midori2_to_fasta.py` | FASTA with `accession###rank_taxid;...` headers | midori2 |
| `pr2_to_fasta.py` | Excel (xlsx) via pandas | pr2 |
| `boldistilled_to_fasta.py` | FASTA + taxonomy TSV, BIN-keyed | boldistilled |
| `unite_to_fasta.py` | FASTA with `k__/p__/.../s__` rank prefixes | unite |
| `gtdb_to_fasta.py` | Gzipped FASTA + taxonomy TSV, `d__/p__/.../s__` rank prefixes | gtdb |

### Known issues / TODOs

- UNITE official URL is blocked behind a user-agreement popup; a temporary mirror is in use — see comment in `datasets.yaml`
- `refseq_its` version is unrecorded

## Taxonomic annotation pipeline

This pipeline queries the GBIF sequence data, runs it against the reference UDB, and produces annotated Parquet output for analysis.

### 1. Start the vsearch server

vsearch must be running in server mode before any annotation work:

```bash
vsearch --threads 8 --usearch_global_server \
  --db output/fasta/gbif_dna_taxonomy_annotation.udb \
  --id 0.9 --query_cov 0.5 \
  --maxaccepts 1000 --maxrejects 1000 --maxhits 100 \
  --port 8000 --temp_file_path ~/temp-vsearch
```

### 2. Start the Node.js proxy server

The proxy parses vsearch output and returns structured JSON:

```bash
cd node-server && npm start
# Listens on http://localhost:3000 by default
# Override with PORT=XXXX or VSEARCH_URL=http://... environment variables
```

The proxy exposes `POST /search/batch?outfmt=blast6out|alnout` — accepts a FASTA body, forwards to vsearch, parses the 23-field headers, and returns one best-match object per query ID (selected by `pickBestMatch.mjs`).

### 3. Create a query FASTA

Extract sequences from the GBIF dataset by filtering `trino_joined.parquet` and joining to `trino_normalised_sequences.parquet`:

```bash
python3 analysis/query_to_fasta.py <name> --where "<SQL condition>"

# Examples:
python3 analysis/query_to_fasta.py musca --where "genus = 'Musca'"
python3 analysis/query_to_fasta.py diptera --where "\"order\" = 'Diptera'"
```

Output: `tests/input/<name>.fasta`

### 4. Annotate and write Parquet

Send the FASTA to the proxy in batches of 100, collect best matches, and write results:

```bash
python3 analysis/annotate_sequences.py tests/input/<name>.fasta
# Output: output/<name>_annotated.parquet

# Options:
#   --output path/to/output.parquet
#   --server http://localhost:3000
#   --batch-size 100
```

The output Parquet has 35 columns: `queryId` + all 23 reference header fields + `identity`, `alignmentLength`, `mismatches`, `gapOpenings`, `qstart`, `qend`, `sstart`, `send`, `evalue`, `bitScore`, `qcovs`.

## GBIF annotation data

**`trino_joined.parquet`** — main working dataset (full join from Trino/GBIF). Not committed to git.
171,809,965 rows · 22,036,768 unique sequences · 177 datasets · 1,186,295 unique scientific names.
Taxon rank distribution: `GENUS` (30%), `SPECIES` (18%), `FAMILY` (18%), `UNRANKED` (15%), `ORDER` (7%), `KINGDOM` (5%), `CLASS` (4%), `PHYLUM` (2%), and minor ranks.

**`small_dataset.parquet`** — 100,000 occurrence rows (subset for exploration), with 83,961 unique sequences from 3 GBIF datasets.

**`top100_distinct_families.parquet`** — top 100 nucleotidesequenceids by number of distinct families.

Schema:
| Column | Type | Notes |
|---|---|---|
| `nucleotidesequenceid` | VARCHAR | MD5 hash identifying the exact sequence variant (ASV/OTU) |
| `gbifid` | BIGINT | GBIF occurrence key |
| `datasetkey` | VARCHAR | UUID of the publishing dataset |
| `kingdom` … `species` | VARCHAR | Publisher-assigned taxonomy (may be NULL) |
| `scientificname` | VARCHAR | Publisher-assigned name at the identified rank |
| `taxonrank` | VARCHAR | Rank of the identification |

The key analytical unit is `nucleotidesequenceid`: the same sequence can appear multiple times (once per dataset that contains it), potentially with different taxonomic annotations.

## Tooling

- **DuckDB** — primary tool for all data analysis; use the CLI (`duckdb`) or in-process via Python (`import duckdb`)
- Parquet files are queried directly — no import step needed
- Run a one-off query: `duckdb -c "SELECT ... FROM 'small_dataset.parquet' ..."`
- Run a SQL file: `duckdb -c ".read queries/foo.sql"`
- `.gitignore` excludes all `*.parquet` except `small_dataset.parquet` and `top100_distinct_families.parquet`

## Conventions

- Query files go in `queries/` (`.sql` extension)
- Analysis scripts go in `analysis/` (Python preferred)
- Results/outputs go in `output/` (CSV or Parquet); FASTA outputs in `output/fasta/`
- Keep queries self-contained and runnable from the repo root
- `source-data/` is gitignored (large downloads); `source-data/README.md` is tracked

## Key analytical questions

1. For sequences annotated by multiple datasets, how often do the taxonomic annotations agree?
2. What is the distribution of annotation depth (rank reached) per sequence?
3. Can we define a consensus or "best" annotation for each unique sequence, and by what rules?
