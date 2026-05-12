# Intra-dataset Taxonomic Ambiguity — Dataset Inventory

**Source file:** `trino_joined.parquet`
**Query:** `queries/intra_dataset_ambiguity.sql`
**Output:** `output/intra_dataset_ambiguity.xlsx`
**Analysis date:** 2026-05-12

---

## What this analysis asks

Within a single GBIF dataset, does the same `nucleotidesequenceid` ever carry more than one distinct `scientificname`? This reveals internal inconsistency within a single publisher's data — a different (and arguably more serious) problem than cross-dataset disagreement.

The Excel file lists the top 10 most ambiguous sequences per dataset, with the number of distinct scientific names, number of occurrences, a name summary, and a GBIF link.

---

## Key numbers

| Metric | Count |
|---|---|
| Datasets with at least one intra-dataset conflict | 56 |
| Unique sequences involved | 116,529 |
| Total occurrences involved | 2,048,518 |

93% of ambiguous sequences and 85% of involved occurrences belong to a single dataset (iBOL/BOLD).

---

## Datasets in the Excel file

### `040c5662-da76-4782-a48e-cdea1892d14c` — International Barcode of Life project (iBOL)
**Sequences (top 10 shown):** 108,435 total · Max names on one sequence: 514

By far the dominant source of intra-dataset ambiguity. BOLD is a repository that aggregates submissions from hundreds of independent research projects, each with its own taxonomy pipeline. The same sequence (BIN) can be submitted by multiple projects with different species identifications. The top sequence (`599536af`) carries 514 distinct names spanning nematodes, sea cucumbers, polychaetes, beetles, and spiders — a consequence of an extremely conserved barcode region being placed differently by every project that encountered it. This is a structural property of how BOLD aggregates data, not a simple data error.

---

### `9f0e1ca6-fb08-4c72-9a4a-1e3b7a528c10` — Global soil organisms
**Sequences (top 10 shown):** 5,359 total · Max names on one sequence: 3 · Occurrences: 64,391

A large global soil metabarcoding dataset. With 5,359 ambiguous sequences and a maximum of only 3 names per sequence, the conflicts are likely driven by multi-run or multi-sample submissions annotated against slightly different reference database versions, or by OTU clustering artefacts where the same representative sequence is assigned to different taxa across samples.

---

### `8241c49f-36bc-4cf2-a707-75bae56e9986` — UNESCO eDNA expedition in Ningaloo Coast (Australia): May 2023
**Sequences (top 10 shown):** 1,236 total · Max names on one sequence: 3 · Occurrences: 8,853

Marine eDNA metabarcoding from the Ningaloo Coast. 1,236 sequences with conflicting names, all with at most 3 names. Likely reflects the same sequence appearing across multiple samples or replicates annotated with slightly different results, or a mixed-marker dataset where the same sequence receives different names depending on the reference used.

---

### `cb8a261a-66cb-4068-809e-9e773359bb30` — Insektmobilen — National citizen science and DNA metabarcoding survey of flying insects in June 2018 and 2019
**Sequences (top 10 shown):** 440 total · Max names on one sequence: 6 · Occurrences: 37,180

Danish citizen science insect survey using DNA metabarcoding (COI). With 37,180 occurrences involved and up to 6 names per sequence, this is a substantial dataset where the same ASV is annotated differently across years (2018 vs. 2019) or across different analytical runs, possibly reflecting updates to the reference database between the two survey years.

---

### `6b9f8685-e080-4330-a211-e61ad6bdbe64` — Improving knowledge of Asian pteridophytes through DNA sampling of specimens in regional collections
**Sequences (top 10 shown):** 211 total · Max names on one sequence: 6

Fern (pteridophyte) barcoding dataset from herbarium specimens. 211 ambiguous sequences suggests either that specimens were re-identified between submissions, or that the same sequence was submitted with different taxonomic treatments (e.g. lumping vs. splitting of fern species).

---

### `50c9509d-22c7-4a22-a47d-8c48425ef4a7` — iNaturalist Research-grade Observations
**Sequences (top 10 shown):** 195 total · Max names on one sequence: 258

iNaturalist is a citizen science platform where observations can be re-identified over time by the community. The extreme maximum of 258 names on a single sequence reflects this: a sequence associated with many independent iNaturalist observations, each of which may have received a different community identification. The `nucleotidesequenceid` is NULL for the most extreme cases, meaning they represent records without a proper sequence hash.

---

### `9baace02-10fe-4972-b3ec-2cb647c55194` — Fungal Internal Transcribed Spacer RNA (ITS) RefSeq Targeted Loci Project
**Sequences (top 10 shown):** 119 total · Max names on one sequence: 6 · Occurrences: 290

NCBI RefSeq curated ITS sequences for fungi. Conflicts here likely reflect cases where the same ITS sequence has been submitted to GenBank under different species names by different research groups — a common situation in fungal taxonomy where species concepts are contested or have been revised.

---

### `63283fef-d82f-40ba-9346-c4810e9690dc` — Saproxylic fungi of fine woody debris studied by metabarcoding-based MycoPins method in Oulanka, Finland, 2022–2023
**Sequences (top 10 shown):** 105 total · Max names on one sequence: 4 · Occurrences: 9,633

Finnish forest fungal metabarcoding dataset. 105 sequences with up to 4 names and nearly 10,000 occurrences involved. Likely reflects the same OTU/ASV being annotated differently across samples or substrate types within the dataset.

---

### `3bfbda20-1a91-4cf9-992f-bc1e9e5b7dad` — Fungal 18S Ribosomal RNA (SSU) RefSeq Targeted Loci Project
**Sequences (top 10 shown):** 97 total · Max names on one sequence: 24 · Occurrences: 274

NCBI RefSeq curated fungal 18S sequences. The top sequence carries 24 distinct *Alternaria* species names — a textbook example of a conserved marker (18S SSU) being unable to resolve species within a hyper-diverse cryptic genus. Each name comes from a separate GenBank submission by a different research group. Classic marker-resolution failure.

---

### `84d26682-f762-11e1-a439-00145eb45e9a` — Danish Mycological Society, fungal records database
**Sequences (top 10 shown):** 77 total · Max names on one sequence: 4 · Occurrences: 279

Danish fungal occurrence database. Conflicts likely reflect the same fungal sequence being associated with different species names across records submitted at different times or by different observers, consistent with ongoing taxonomic revisions in fungal systematics.

---

### `8681d2b2-7bb3-4e76-87ee-fd16b1f425e2` — Environmental DNA illuminates the darkness of mesophotic assemblages of fishes from West Indian Ocean
**Sequences (top 10 shown):** 68 total · Max names on one sequence: 2 · Occurrences: 412

Deep-water fish eDNA dataset. All conflicts involve exactly 2 names — conservative, likely reflecting cases where a sequence matches two closely related fish species equally well, and different samples in the dataset received different placements.

---

### `0b0dc293-3b26-49db-b9f1-817b31ebf603` — Bacterial 16S Ribosomal RNA RefSeq Targeted Loci Project
**Sequences (top 10 shown):** 68 total · Max names on one sequence: 7 · Occurrences: 152

NCBI RefSeq curated bacterial 16S sequences. The same 16S sequence submitted under different bacterial names by different groups, reflecting the well-known difficulties of species delimitation in bacteria using 16S alone (the marker has insufficient resolution below genus level for many groups).

---

### `bf3f09bd-3af6-45be-a2c4-bd5c285cab8a` — Fungal 28S Ribosomal RNA (LSU) RefSeq Targeted Loci Project
**Sequences (top 10 shown):** 60 total · Max names on one sequence: 9 · Occurrences: 148

NCBI RefSeq curated fungal LSU (28S) sequences. Same pattern as the ITS and 18S RefSeq projects — GenBank submissions from multiple groups assigning different names to the same sequence, driven by fungal taxonomic revision and cryptic diversity.

---

### `82818753-a3d1-4c29-a837-e6fde0a58672` — Bacterial 5S Ribosomal RNA RefSeq Targeted Loci Project
**Sequences (top 10 shown):** 50 total · Max names on one sequence: 5 · Occurrences: 121

NCBI RefSeq curated bacterial 5S sequences. 5S rRNA is extremely short and highly conserved, offering very limited taxonomic resolution. Multiple bacterial names mapping to the same 5S sequence is expected and reflects the marker's fundamental limitations.

---

### `af6f962a-3dad-43df-a9e3-36ad528a4977` — Environmental DNA reveals tropical shark diversity in contrasting levels of anthropogenic impact
**Sequences (top 10 shown):** 16 total · Max names on one sequence: 10 · Occurrences: 325

Tropical shark eDNA study. The top sequence (`5d5c2f4e`) carries 10 names spanning sharks, bony fish, seabirds, and terrestrial birds — a highly conserved vertebrate 12S fragment that multiple reference databases place in entirely different vertebrate classes. A well-known problem with short 12S amplicons in mixed vertebrate environments.

---

### Remaining datasets (15 datasets, 1–9 sequences each)

| Dataset | Key | Sequences | Max names | Summary |
|---|---|---|---|---|
| iNaturalist Research-grade Observations | `50c9509d` | 9 | 258 | See above; remainder are non-NULL sequences |
| Biological Collection of the National Taiwan Museum | `24f1ac6a` | 9 | 4 | Museum collection barcodes, likely re-identified specimens |
| ITS2 fungal OTUs from decaying Norway spruce, Finland | `42c9c70f` | 9 | 2 | Fungal metabarcoding; all 2-name conflicts |
| Fungal Culture Collection of Yugra State University | `e752fa90` | 6 | 5 | Culture collection; same isolate submitted under different names |
| Freshwater invertebrates, Kenai Peninsula, Alaska | `9d7baaac` | 6 | 2 | Metabarcoding; 2-name conflicts only |
| Archaeal 16S RefSeq Targeted Loci Project | `39446ba3` | 5 | 2 | Same 16S sequence under different archaeal names |
| ITEM fungal repository (ISPA-ITEM-01) | `18abd151` | 5 | 2 | Culture collection; nomenclature synonymy likely |
| Yeast ITS & LSU DNA sequences | `3229500b` | 4 | 2 | Yeast barcodes; 2-name conflicts |
| Chironomid DNA Barcode Database | `02cc981e` | 3 | 2 | Chironomid (midge) COI barcodes; 2-name conflicts |
| Kenai NWR Pollinator Surveys metabarcoding, 2022 | `86875091` | 3 | 2 | Pollinator metabarcoding |
| BulkDNA macrobenthos, Belgian North Sea | `537ba214` | 2 | 2 | Benthic metabarcoding |
| Spider barcodes, Ecuador forest ecosystems | `39c2d84a` | 2 | 2 | Spider COI barcodes |
| Archaeal 5S RefSeq Targeted Loci Project | `c2d141d6` | 2 | 2 | Same limitations as bacterial 5S |
| ARMS-MBON hard-bottom communities: ITS 2020–2021 | `b8950b46` | 1 | 2 | Marine hard-bottom metabarcoding |
| Auchenorrhyncha barcode collection | `f692203b` | 1 | 2 | Planthopper/leafhopper COI barcodes |
| Bacterial 23S RefSeq Targeted Loci Project | `f8fe66a3` | 1 | 2 | Same as 16S pattern |
| Fungarium of Yugra State University | `d922b606` | 1 | 2 | Herbarium-style fungal collection |
| Peatland fungi, Northwestern Siberia (eDNA) | `aa9fabb1` | 1 | 2 | Fungal metabarcoding |
| Macrofungi bogs monitoring, Northwestern Siberia | `f9eab20b` | 1 | 2 | Fungal metabarcoding |
| Fungi from forest plots, Northwestern Siberia | `fa49d9f1` | 1 | 2 | Fungal metabarcoding |
| ARMS-MBON hard-bottom communities: 18S 2018–2020 | `6f2f07f3` | 1 | 2 | Marine hard-bottom metabarcoding |
| CNR-IPSP Tree Fungal Pathogens Dataset | `36075f43` | 1 | 2 | Fungal plant pathogen collection |

---

## Datasets with only NULL sequence IDs (not in Excel file)

Several DFO (Fisheries and Oceans Canada) datasets appear in the raw query but have no valid `nucleotidesequenceid` — all their conflicts involve NULL-keyed rows where the sequence identity is unknown. These are excluded from the Excel output but worth noting:

| Dataset | Max names on NULL | Occurrences |
|---|---|---|
| DFO Maritimes Lobster & Finfish eDNA (COI), Bay of Fundy 2018–2019 | 340 | 35,697 |
| DFO Maritimes Lobster & Finfish eDNA (18S), Bay of Fundy 2018–2019 | 209 | 85,917 |
| DFO Monthly GRDI eDNA (COI), Halifax 2021–2022 | 179 | 41,541 |
| DFO Monthly GRDI eDNA (COI), Bay of Fundy 2019–2021 | 297 | 36,413 |
| DFO Monthly GRDI eDNA (18S), Bay of Fundy 2019–2021 | 258 | 29,267 |
| DFO Maritimes Zooplankton (COI) AEIP 2019 | 107 | 34,017 |
| DFO Maritimes Zooplankton (18S) AEIP 2019 | 121 | 11,592 |
| DFO Monthly GRDI eDNA (16S), Bay of Fundy 2019–2021 | 72 | 8,814 |
| DFO Monthly GRDI eDNA (12S), Bay of Fundy 2019–2021 | 57 | 6,334 |
| DFO Monthly GRDI eDNA (18S), Iqaluit 2019 | 118 | 2,360 |
| DFO Monthly GRDI eDNA (16S), Iqaluit 2019 | 64 | 1,280 |
| DFO Monthly GRDI eDNA (12S), Iqaluit 2019 | 3 | 4 |

These datasets submitted occurrences without sequence IDs. The "conflicts" registered are artefacts of grouping all NULL rows together — they do not represent genuine intra-sequence disagreement. The DFO datasets are a candidate for follow-up to determine whether sequence IDs can be recovered or assigned retrospectively.
