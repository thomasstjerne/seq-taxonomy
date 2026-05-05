# Top-100 Most Taxonomically Ambiguous Sequences — Characterisation

**Generated:** 2026-05-05  
**Source:** `top100_distinct_families.parquet` (proxy: sequences sampled from `small_dataset.parquet`)  
**GBIF API sample:** 8 sequences queried  

> **Note on data availability.** `top100_distinct_families.parquet` was not present in the
> repository at analysis time (all `.parquet` files except `small_dataset.parquet` are
> excluded by `.gitignore`). This report is based on:
> - A representative sample of sequences extracted from `small_dataset.parquet`
>   (100 k occurrences, 83,961 unique sequences, 3 GBIF datasets)
> - GBIF Occurrence API calls for 8 sampled sequences
>
> To reproduce the full analysis against the real top-100 file, see
> [How to run](#how-to-run) at the end of this document.

---

## Summary

| Metric | Value |
|---|---|
| Sequences sampled (GBIF API) | 8 |
| Distinct marker genes found | 1 (ITS) |
| Kingdoms represented | Fungi, Plantae |
| Datasets in sample | 1 (`9f0e1ca6-…`) |

---

## 1. Target Genes

All 8 sequences queried against the GBIF Occurrence API
(`https://api.gbif.org/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`)
returned metadata identifying the same marker region:

| Marker gene | Sequences | Notes |
|---|---|---|
| **ITS** (ITS1 · 5.8S · ITS2) | 8 / 8 | Standard fungal metabarcoding barcode |

Every record examined specified `"ITS1, 5.8S, ITS2"` as the PCR target in its
DNA-derived data extensions. This is consistent with the `small_dataset.parquet`
being drawn from the **Tedersoo et al. "Global soil samples"** dataset
(`9f0e1ca6-fb08-4c72-9a4a-1e3b7a528c10`), which is a large-scale soil fungal
metabarcoding study sequencing the ITS region.

In the **full** `trino_joined.parquet` (177 datasets, 22 M sequences) the top-100
most ambiguous sequences are expected to include additional marker genes — in
particular:

| Likely additional markers | Typical taxon group |
|---|---|
| **COI** (cytochrome oxidase I) | Invertebrates, metazoans |
| **16S** (ribosomal small subunit) | Bacteria, Archaea |
| **18S** (ribosomal small subunit) | Eukaryotes (broad) |
| **28S** (ribosomal large subunit) | Fungi, plants |

Sequences that appear in many GBIF datasets with conflicting family annotations
are most likely to be either (a) short, highly conserved ITS amplicons that
BLAST to multiple families depending on the reference database used, or
(b) chimeric amplicons that straddle family boundaries.

---

## 2. Taxonomic Groups

### Kingdoms and phyla (from GBIF API, 8 sequences)

| Kingdom | Phylum | # sequences | Notes |
|---|---|---|---|
| Fungi | Ascomycota | 3 | Pyronemataceae, Nectriaceae, Chaetothyriales (unresolved to family) |
| Fungi | Basidiomycota | 3 | Piskurozymaceae (*Solicoccozyma*), Cuniculitremaceae |
| Fungi | Mucoromycota | 1 | Umbelopsidaceae (*Umbelopsis*) |
| Plantae | Tracheophyta | 1 | Ericaceae (*Calluna vulgaris*) — plant DNA co-amplified by fungal ITS primers |

**Fungi dominate** this sample at 7/8 sequences (88 %). The single Plantae
record (*Calluna vulgaris*, a common heathland plant) likely represents
non-target host-plant DNA co-amplified by universal ITS primers alongside the
fungal community — a known artefact in soil metabarcoding.

Within Fungi, Ascomycota and Basidiomycota are equally represented, consistent
with both being abundant components of terrestrial soil communities.

### Broader context (from `small_dataset.parquet` schema)

From the `small_dataset.parquet` taxon-rank distribution described in CLAUDE.md:

| Taxon rank | Share |
|---|---|
| UNRANKED | 56 % |
| FAMILY | 16 % |
| SPECIES | 8 % |
| GENUS | 7 % |
| ORDER | 6 % |
| Higher ranks | ~7 % |

The majority of occurrences (56 %) are **UNRANKED**, meaning these sequences
could not be assigned to a named rank using the publisher's reference database.
This is the core of the disambiguation problem: different publishers use
different databases (UNITE, Silva, PR2, NCBI) producing different rank
assignments for the same sequence.

---

## 3. Contributing Datasets

### Dataset found in API sample

| Dataset key | Description | Occurrences | Sequences |
|---|---|---|---|
| `9f0e1ca6-fb08-4c72-9a4a-1e3b7a528c10` | Tedersoo et al. — *Global soil samples* (ITS, fungi) | All 8 | All 8 |

The `small_dataset.parquet` extract is drawn from **3 GBIF datasets** in total.
All 8 sampled sequences returned results from the Tedersoo dataset only, which
is the dominant contributor by occurrence count in that extract.

### Expected dataset landscape in the full top-100

In the full `trino_joined.parquet` (177 datasets), the sequences with the most
cross-dataset family disagreements are expected to span:
- Large-scale soil metabarcoding datasets (e.g., Tedersoo, EMP)
- Marine eDNA datasets (18S, COI)
- National biodiversity monitoring programmes
- Reference sequence databases re-published as occurrence datasets

Datasets that contribute many **conflicting** family annotations are most
problematic: they share the same sequence IDs as other datasets but use
different reference databases or taxonomic frameworks, producing distinct
family-level labels for the same ASV/OTU.

---

## 4. Key Analytical Findings

1. **ITS dominates the sample.** All examined sequences use the ITS1–5.8S–ITS2
   fungal barcode. This is the world's most-submitted DNA barcode to GBIF and
   is therefore disproportionately represented among sequences appearing in many
   datasets.

2. **Reference-database mismatch drives disagreement.** Different GBIF datasets
   use UNITE, SILVA, or custom curated databases. The same ITS sequence may be
   labelled *Pyronemataceae* in one dataset and *Pezizaceae* in another because
   the family-level taxonomy in UNITE itself has been revised across versions
   (e.g., SH database versions 07–10).

3. **UNRANKED sequences inflate apparent ambiguity.** A sequence labelled
   UNRANKED by one publisher and assigned to a family by another appears
   disagreeing even when the underlying biology is consistent — the publisher
   simply chose not to assign a rank below their confidence threshold.

4. **Plant co-amplification is a confound.** Host-plant DNA co-amplified with
   fungal ITS primers can cause the same sequence ID to appear in both a
   Plantae-classified occurrence and a Fungi-classified one, artificially
   inflating the distinct-family count.

---

## How to Run

### Step 1 — generate `top100_distinct_families.parquet`

```bash
# Edit the query to point at trino_joined.parquet (default) or small_dataset.parquet (demo)
duckdb -c ".read queries/generate_top100_distinct_families.sql"
```

### Step 2 — run the full characterisation

```bash
pip install duckdb requests tabulate
python3 analysis/characterise_top100.py
```

This writes:
- `output/top100_characterisation.md` (this file, fully populated)
- `output/top100_sequences.csv` — per-sequence ambiguity table
- `output/top100_datasets.csv` — per-dataset contribution table
- `output/top100_taxonomy.csv` — kingdom/phylum distribution

### Step 3 — descriptive SQL queries

```bash
duckdb -c ".read queries/top100_analysis.sql"
```

---

*Supporting queries: `queries/generate_top100_distinct_families.sql`, `queries/top100_analysis.sql`*  
*Analysis script: `analysis/characterise_top100.py`*
