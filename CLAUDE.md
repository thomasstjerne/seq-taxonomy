# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Build an approach for unified taxonomic annotation of DNA sequences shared to GBIF, resolving disagreements across datasets where the same sequence variant has been annotated differently by different publishers.

## Data

**`trino_joined.parquet`** — main working dataset (full join from Trino/GBIF). Not committed to git.
171,809,965 rows · 22,036,768 unique sequences · 177 datasets · 1,186,295 unique scientific names.
Taxon rank distribution: `GENUS` (30%), `SPECIES` (18%), `FAMILY` (18%), `UNRANKED` (15%), `ORDER` (7%), `KINGDOM` (5%), `CLASS` (4%), `PHYLUM` (2%), and minor ranks.

**`small_dataset.parquet`** — 100,000 occurrence rows (subset for exploration), with 83,961 unique sequences from 3 GBIF datasets.
Taxon rank distribution: `UNRANKED` (56%), `FAMILY` (16%), `SPECIES` (8%), `GENUS` (7%), `ORDER` (6%), and higher ranks.

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
- `.gitignore` excludes all `*.parquet` except `small_dataset.parquet` — larger datasets should not be committed

## Conventions

- Query files go in `queries/` (`.sql` extension)
- Analysis scripts go in `analysis/` (Python preferred)
- Results/outputs go in `output/` (CSV or Parquet)
- Keep queries self-contained and runnable from the repo root

## Key analytical questions

1. For sequences annotated by multiple datasets, how often do the taxonomic annotations agree?
2. What is the distribution of annotation depth (rank reached) per sequence?
3. Can we define a consensus or "best" annotation for each unique sequence, and by what rules?
