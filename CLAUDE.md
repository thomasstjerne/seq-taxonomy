# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Build an approach for unified taxonomic annotation of DNA sequences shared to GBIF, resolving disagreements across datasets where the same sequence variant has been annotated differently by different publishers.

The approach has two tracks:
1. **Reference database pipeline** — compile a multi-gene reference database from public sources, normalise to a common format, and build a vsearch UDB index for taxonomic assignment
2. **GBIF annotation analysis** — query the full GBIF DNA occurrence dataset to characterise annotation disagreement and develop consensus rules

## Reference database pipeline

### Configuration

All sources are defined in `datasets.yaml` (repo root). Each entry has: `short_name`, `version`, `target_gene`, `taxonomic_scope`, `citation`, `endpoints`, optional `curl_flags`/`prepare_cmd`/`prepare_sentinel`, `convert_cmd`, and optional `postprocess_cmd`/`postprocess_fasta`.

If `postprocess_cmd` is set, the pipeline runs it after conversion (with `output/fasta/` → `$OUTPUT_DIR/` substitution). If `postprocess_fasta` is also set, the combined FASTA uses that file instead of the raw conversion output.

The `target_gene` value must be a concept name from the GBIF target_gene vocabulary:
- Browse: https://registry.gbif.org/vocabulary/target_gene/concepts
- API: https://api.gbif.org/v1/vocabularies/target_gene/concepts?limit=100

Current mappings in use: `SSU_rRNA_12S_mitochondrial`, `SSU_rRNA_18S_eukaryotic`, `SSU_rRNA_16S_prokaryotic`, `COI`, `ITS_region`, `ITS2`, `rbcL`, `matK`, and the mitochondrial set from MIDORI (`CytB`, `COII`, `COIII`, `ND1`–`ND6`, `ND4L`, `atp6`, `atp8`, `LSU_rRNA_16S_mitochondrial`). Coverage is chosen to match the leaf target genes that actually carry data in GBIF (facet on `nucleotideSequence.targetGene`).

Conversion scripts that filter source data by gene name (e.g. `dwc_to_fasta.py`) accept a separate `--filter-gene` argument for the value used to match records in the source file (e.g. `12s`, `16s`, `its`), keeping `--target-gene` strictly for the output FASTA header.

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
bash analysis/download_and_convert.sh --source-dir /path/to/storage                   # store source data outside the repo (e.g. external drive)
bash analysis/download_and_convert.sh --output-dir /path/to/storage                   # write FASTAs and UDB outside the repo
```

Requires: `yq` (**mikefarah v4** — not the Python jq-wrapper `yq`; the script checks this and fails fast), `vsearch` (only for the UDB build), `curl`, `python3` (≥3.9), `duckdb`, `pandas`, `openpyxl`. The script is cross-platform (Linux/macOS). Secrets (e.g. `NCBI_API_KEY` for the matK fetch) go in a gitignored `.env` — copy `.env.example` and fill it in.

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
| `midori2_to_fasta.py` | FASTA with `accession###rank_taxid;...` headers | midori2 (12S) + 13 per-gene mito entries (`midori2_cytb`, `midori2_co2/co3`, `midori2_nd1`–`nd6`/`nd4l`, `midori2_atp6/atp8`, `midori2_16s`) |
| `pr2_to_fasta.py` | Excel (xlsx) via pandas | pr2 |
| `boldistilled_to_fasta.py` | FASTA + taxonomy TSV, BIN-keyed | boldistilled |
| `unite_to_fasta.py` | FASTA with `k__/p__/.../s__` rank prefixes | unite |
| `gtdb_to_fasta.py` | Gzipped FASTA + taxonomy TSV, `d__/p__/.../s__` rank prefixes | gtdb |
| `its2_global_to_fasta.py` | FASTA with `>ID;tax=k:V,p:V,...,s:V;` headers | its2_global |
| `bell_brosi_rbcl_to_fasta.py` | FASTA with `k__/p__/.../s__` DADA2 headers + numeric taxid suffixes | bell_brosi_rbcl |
| `ncbi_matk_to_fasta.py` | **Live NCBI Entrez query** (no static file): esearch→efetch + taxonomy lookup | ncbi_matk |

`ncbi_matk_to_fasta.py` is the exception to the "one source file" rule — it downloads from NCBI at convert time (its `datasets.yaml` entry has `endpoints: []`). It reads `NCBI_API_KEY`/`NCBI_EMAIL` from `.env` if present (recommended — raises the rate limit 3→10 req/s) and runs without one otherwise, printing a notice. Raw downloads are cached under `--raw-dir`. It generalises to other NCBI genes via `--query`/`--target-gene`.

### Post-processing: within-species deduplication

Several databases contain many exact within-species duplicates (multiple accessions for the same species with identical sequence). The dedup step is run automatically by `download_and_convert.sh` via `postprocess_cmd` in `datasets.yaml`. It can also be run manually:

```bash
python3 analysis/duplicate_analysis.py --fasta output/fasta/its2_global.fasta \
    --write-deduped output/fasta/its2_global_deduped.fasta
python3 analysis/duplicate_analysis.py --fasta output/fasta/mitofish_12s.fasta \
    --write-deduped output/fasta/mitofish_12s_deduped.fasta
```

**Dedup rule**: collapse by `(sequence, species)` — only within-species duplicates are removed. Sequences that are identical across different species are kept once per species, because their cross-species presence is meaningful signal for `pickBestMatch`: when vsearch returns the same sequence under multiple species names, the selector knows it can only assign to genus level with confidence.

| Dataset | Before | After | Removed |
|---|---|---|---|
| its2_global | 307,976 | 258,218 | 49,758 |
| mitofish_12s | 43,870 | 37,145 | 6,725 |
| pr2_18s | 223,357 | 196,218 | 27,139 |

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
# CACHE selects the cache backend: dragonfly (default), hbase, or none (no cache).
#   CACHE=none sends every query straight to vsearch — no cache server needed.
# LOG_TOP_MATCHES=N prints the top N matches per queried sequence to the console
#   as a TSV block (rank, identity, qcovs, scientificName, taxonRank, dataset,
#   targetGene) — a debugging/inspection aid, off by default. e.g.:
#   LOG_TOP_MATCHES=5 npm start
# LOG_TOP_MATCHES_FILE=path appends the top N rows to a flat TSV file (with a
#   queryId column) instead of the console — better for large multi-request
#   tests. Truncated fresh each server start. N defaults to 5 if only the file
#   path is given. e.g.:
#   LOG_TOP_MATCHES=10 LOG_TOP_MATCHES_FILE=output/top_matches.tsv npm start
# LOG_RAW_MATCHES_FILE=path appends the top N RAW vsearch blast6out lines per
#   query (unparsed, in vsearch's own order) to a file. Same shared N. Useful
#   for inspecting exactly what vsearch returned before parsing/selection. e.g.:
#   LOG_TOP_MATCHES=10 LOG_RAW_MATCHES_FILE=output/raw_matches.tsv npm start
```

The proxy exposes three endpoints:

| Endpoint | Body | Response |
|---|---|---|
| `POST /search/batch` | FASTA (text/plain) | `{ [queryId]: topMatches[] }` — up to 5 ranked matches per sequence |
| `POST /occurrence/classify` | Single occurrence (JSON) | `DnaClassification` or 204 |
| `POST /occurrence/classify/batch` | `occurrence[]` (JSON) | `{ gbifID, classification }[]` — one entry per input occurrence |

Query params for `/search/batch`: `outfmt=blast6out|alnout` (default `blast6out`), `selector=<name>` (default `pickBestMatch`).

**`/occurrence/classify/batch`** deduplicates sequences across all occurrences before querying vsearch (a single round-trip regardless of how many occurrences share the same sequence), then fans the cached results back to each `assignTaxonomyToOccurrence` call.

**`pickBestMatch` return type**: all selector functions return `object[]` (up to 5 matches, best first). `topMatches[0]` is the primary classification; the remaining matches are available to `assignTaxonomyToOccurrence` for cases where the top match alone is insufficient (e.g. disambiguating cross-species sequences).

**`pickBestMatch` ranking rule**: sort by `identity` descending, then `qcovs` descending as tiebreaker. This ensures that when two hits share the same identity, the one covering more of the query sequence is preferred.

### 3. Create a query FASTA

Extract sequences from the GBIF dataset by filtering `trino_joined.parquet` and joining to `trino_normalised_sequences.parquet`:

```bash
python3 analysis/query_to_fasta.py <name> --where "<SQL condition>"

# Examples:
python3 analysis/query_to_fasta.py musca --where "genus = 'Musca'"
python3 analysis/query_to_fasta.py diptera --where "\"order\" = 'Diptera'"

# For large queries, add --temp-dir to allow DuckDB to spill to disk:
python3 analysis/query_to_fasta.py diptera --where "\"order\" = 'Diptera'" --temp-dir /tmp/duckdb_spill
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
#   --selector pickBestMatch2   # use an alternate pickBestMatch function (see node-server/)
```

The `--selector` value must match both a file `node-server/<selector>.mjs` and a named export `<selector>` within it. The server validates the name and caches loaded modules across requests. The default selector is `pickBestMatch`.

The output Parquet has 35 columns: `queryId` + all 23 reference header fields + `identity`, `alignmentLength`, `mismatches`, `gapOpenings`, `qstart`, `qend`, `sstart`, `send`, `evalue`, `bitScore`, `qcovs`.

### 5. Batch-classify occurrences and compare taxonomy

To test `/occurrence/classify/batch` against real GBIF occurrences:

```bash
# Generate test data: 500 occurrences with 2–4 sequences each
python3 analysis/generate_test_occurrences.py
# → node-server/test-data/multi_seq_occurrences.json

# Classify and write a TSV comparing publisher vs assigned taxonomy
python3 analysis/batch_classify_occurrences.py node-server/test-data/multi_seq_occurrences.json
# → output/multi_seq_occurrences_classified.tsv

# Options for both scripts:
#   --output   path to output file
#   --limit    number of occurrences to generate (default 500)
#   --server   proxy base URL (default http://localhost:3000)
#   --batch-size  occurrences per request (default 25)
```

The TSV has one row per occurrence with `in_*` columns (publisher taxonomy) and `out_*` columns (assigned taxonomy), plus a `remarks` field recording which sequences matched, at what identity/qcovs, and from which reference dataset.

### Unit tests for matching logic

`pickBestMatch` and `assignTaxonomyToOccurrence` have a unit test suite that runs without vsearch or any live server. Tests use minimal synthetic match objects and mocked `searchSequences` functions — no real data required.

```bash
cd node-server && npm test
```

Tests live in `node-server/test/`. **Add a test for every new ranking rule before implementing it.** Each test should cover exactly one rule with the smallest data that demonstrates it.

Current rules under test:
- `pickBestMatch`: sort by `identity` desc, `qcovs` desc as tiebreaker
- `assignTaxonomyToOccurrence`: null on no sequences / no matches; highest-identity sequence wins when multiple sequences present; invalid sequences excluded before querying

## GBIF annotation data

**`trino_joined.parquet`** — main working dataset (full join from Trino/GBIF). Not committed to git.
144,906,122 rows · 22,036,768 unique sequences · 177 datasets · 1,186,295 unique scientific names.
(Deduplicated 2026-06-29: 26.9M exact duplicate rows — identical on every column, a download artifact — were removed from the original 171,809,965-row file. Unique-sequence/dataset/name counts are unaffected.)
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
