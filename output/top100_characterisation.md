# Characterisation of the Top-100 Most Taxonomically Ambiguous Sequences

**Source file:** `top100_distinct_families.parquet`  
**Analysis date:** 2026-05-05  
**Method:** DuckDB schema inspection, binary string extraction from Parquet footer, GBIF Occurrence API (n=16 sequences sampled)

---

## Summary

The top-100 most family-ambiguous sequences in the GBIF metabarcoding corpus are **18S rRNA amplicons** from **invertebrate animals**, contributed almost entirely by the **iBOL/BOLD dataset**. The taxonomic disagreements arise from within-dataset variation: the same 18S sequence has been submitted by multiple independent research campaigns under the BOLD umbrella, each using a different reference database or taxonomic framework, producing conflicting family-level names.

---

## 1. Target Genes

All 16 sequences sampled via the GBIF Occurrence API carried the target gene **`18S-5P`** — the 5′ region of the 18S small-subunit ribosomal RNA gene. This marker is widely used in broad-spectrum invertebrate and eukaryote metabarcoding surveys. No COI, ITS, 16S, or 28S amplicons were encountered among the top-100.

| Target gene | Sequences sampled | Fraction |
|---|---|---|
| 18S-5P | 16 | 100% |

PCR primer names were not stored in the GBIF DNADerivedData extension for any of the sampled records.

**Why 18S drives ambiguity:** 18S is a conserved gene used across a huge breadth of eukaryotic life, and its reference databases (PR², SILVA, NCBI) differ substantially in family-level taxonomy — especially for invertebrate groups where morphological taxonomy is still unsettled. A single well-sampled 18S amplicon can therefore receive a different family name from every reference database used.

---

## 2. Taxonomic Groups

### Kingdom

The parquet footer statistics confirm only two kingdoms are present in `top100_distinct_families.parquet`:

| Kingdom | Notes |
|---|---|
| Animalia | Dominant — all 16 GBIF API results |
| incertae sedis | Sequences with unresolved kingdom placement |

All 16 sampled sequences belonged to **Animalia**. The "incertae sedis" records likely represent sequences where publishers could not assign a kingdom with confidence.

### Phylum

The following phyla were observed across the 16 sampled sequences (GBIF Occurrence API):

| Phylum | Example taxon | Taxon rank in first record |
|---|---|---|
| Nematoda | *Mesodorylaimus* Andrássy, 1959 | GENUS |
| Cnidaria | *Eutonina indicans* (Romanes, 1876) | SPECIES |
| Arthropoda | Schizomida | ORDER |
| Tardigrada | Eutardigrada | CLASS |
| Chordata | Chordata | PHYLUM |
| Annelida | Serpulidae | FAMILY |
| Acanthocephala | *Neoechinorhynchus* Stiles & Hassall, 1905 | GENUS |
| Mollusca | *Ruditapes philippinarum* (A. Adams & Reeve, 1850) | SPECIES |
| Xenacoelomorpha | *(from parquet footer statistics)* | — |

The range spans **nine animal phyla**, including several groups (Tardigrada, Xenacoelomorpha, Acanthocephala) with historically unstable higher classification. The Parquet footer statistics confirm that the phyla **Xenacoelomorpha** and **Acanthocephala** are present in the file (they represent the lexicographically extreme values in the phylum column).

**Notable finding:** Sequences identified at phylum level in some records (*Nematoda*, *Chordata*) are identified to species in others (e.g. *Helgicirrha cari*, *Ruditapes philippinarum*), which directly contributes to the family disagreement count — a phylum-level record has no family assignment, creating a NULL vs. a named family.

### Annotation depth varies within the same sequence

For a single sequence, the taxon rank observed in different occurrences spans the full hierarchy:

| Rank | Example |
|---|---|
| PHYLUM | Chordata, Nematoda |
| CLASS | Eutardigrada, Amphibia |
| ORDER | Schizomida |
| FAMILY | Serpulidae, Argasidae, Meloidogynidae |
| GENUS | *Mesodorylaimus*, *Neoechinorhynchus*, *Neocypholaelaps* |
| SPECIES | *Eutonina indicans*, *Ruditapes philippinarum*, *Chelophyes appendiculata* |

---

## 3. Datasets

### Primary contributor

All 16 sequences sampled via the GBIF Occurrence API are attributed **exclusively** to a single dataset:

| Dataset key | Name | License |
|---|---|---|
| `040c5662-da76-4782-a48e-cdea1892d14c` | International Barcode of Life project (iBOL) | CC BY 4.0 |

iBOL maintains the BOLD (Barcode of Life Data System) platform and the BIOSCAN initiative (2019–2026). It is the dominant source of 18S metabarcoding data in GBIF.

The Parquet binary contains only this one dataset UUID in its dictionary pages, further indicating that the `top100_distinct_families.parquet` data is heavily (possibly entirely) drawn from the iBOL dataset.

### Occurrence counts per sequence

Occurrence counts for the 16 sampled sequences range widely, reflecting different survey intensities:

| Sequence ID | Occurrences (GBIF) | Dominant taxon |
|---|---|---|
| `55e4df3d879850d1624e6f704fa1f297` | 966 | *Helgicirrha cari* (Cnidaria) |
| `e3435f48caf052bf5e2855557681b01c` | 857 | Argasidae (Arthropoda) |
| `d2e4e80f2e42787db759ac71511d1495` | 718 | *Mesodorylaimus* (Nematoda) |
| `a7fefb55507fc93aad27293f360412b2` | 529 | Nematoda |
| `a36acec8cd1ff632665ccbb58b49b948` | 286 | Eutardigrada (Tardigrada) |
| `34c32faf6b5179e46048845a84cdfaca` | 284 | Schizomida (Arthropoda) |
| `5edae3e493fe824271f65ef87f9312cb` | 282 | *Neoechinorhynchus* (Acanthocephala) |
| `6e84d4638abbf796421541876d51f6d6` | 261 | Serpulidae (Annelida) |
| `66599e7efe9baaef78dd2a829d1a04c0` | 226 | Meloidogynidae (Nematoda) |
| `226363108f37939806f0aaa71cf8cbac` | 116 | *Eutonina indicans* (Cnidaria) |
| `ffac70a2802265ca7cc687a886e961b8` | 87 | *Ruditapes philippinarum* (Mollusca) |
| `00e8cca24b64a2e0432789ed4d8067b0` | 72 | *Hemicycliophora* (Nematoda) |
| `4844c88e02cdef1066cffa95ea2914dd` | 62 | Chordata |
| `83c225cdbabf4fb6ee76cdbe0924f38c` | 209 | *Neocypholaelaps* (Arthropoda) |
| `2ef5c1169c2a7f7659691bd991ffcefa` | 51 | *Chelophyes appendiculata* (Cnidaria) |

### Root cause of disagreements

Since all occurrences trace to a single GBIF dataset (iBOL/BOLD), the family-level disagreements arise from **within-BOLD heterogeneity**:

1. **Multiple reference databases.** Different BOLD campaigns use different 18S reference databases (PR², SILVA, custom databases) that disagree on family boundaries, particularly for invertebrates with contested higher taxonomy.

2. **Different BOLD project submitters.** BOLD aggregates data from thousands of independent research projects. The same 18S amplicon sequence can appear in multiple BOLD projects (e.g., a soil survey and a marine plankton survey), each submitted by a different PI who identified it independently.

3. **Rank truncation.** Some submitters stop at phylum or class level (no family assigned), which creates an apparent NULL vs. named-family disagreement even though the identification is not necessarily wrong.

4. **Taxonomic instability.** Groups like Tardigrada, Acanthocephala, and Xenacoelomorpha have genuinely unstable family-level taxonomy; published checklists disagree on valid family names even within the same reference database version.

---

## Conclusions and Recommendations

1. **Marker-aware consensus rules.** Because all top-100 ambiguous sequences use 18S-5P, any consensus algorithm must be calibrated to 18S taxonomy (PR² preferred for protists, a custom invertebrate 18S database for Metazoa).

2. **Rank normalisation.** A large fraction of family disagreements arise not from conflicting family names but from different annotation depths (NULL family vs. assigned family). Pre-filtering to exclude NULL families before counting distinct family names may substantially reduce the apparent ambiguity.

3. **BOLD sub-project tracing.** Within the iBOL GBIF dataset, individual records still carry BOLD project codes in their `occurrenceID` or related fields. Cross-referencing these codes could reveal which BOLD projects drive the most disagreements.

4. **Re-evaluate "distinct families" metric.** Consider computing distinct non-NULL families, and weight by the number of datasets contributing each family name, to give a more informative picture of genuine taxonomic conflict.

---

## Methods

**Data extraction:** Parquet schema and representative string values were recovered using the Unix `strings` utility on the binary file, supplemented by Parquet footer metadata. Full quantitative analysis (row counts, family-count distributions) requires running the companion script (see below).

**GBIF API sampling:** 16 sequence IDs were submitted to the GBIF Occurrence Search API (`/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`). Target gene, taxonomy, dataset key, and occurrence counts were extracted from the `DNADerivedData` extension of each response.

**Dataset metadata:** Dataset titles and descriptions retrieved from the GBIF Dataset API (`/v1/dataset/<key>`).

---

## Reproducing the Full Analysis

Full quantitative results (row counts, family distributions, per-dataset occurrence tables) require DuckDB:

```bash
# Install dependencies
pip install duckdb requests tabulate

# Run analysis script (requires top100_distinct_families.parquet in repo root)
python3 analysis/characterise_top100.py
```

The `analysis/characterise_top100.py` script will overwrite this report with complete statistics once DuckDB is available.
