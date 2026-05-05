# Characterisation of the Top-100 Most Taxonomically Ambiguous Sequences

**Source file:** `top100_distinct_families.parquet`
**Analysis date:** 2026-05-05
**Total rows:** 12,637
**Unique sequences:** 100
**Unique datasets:** 1

---

## Summary

All 100 sequences originate from a single GBIF dataset — the **International Barcode of Life project (iBOL/BOLD)**. They are almost exclusively **invertebrate animal** sequences spanning 18 phyla. Taxonomic disagreements arise entirely from within-BOLD heterogeneity: the same sequence has been submitted by multiple independent research campaigns under the BOLD umbrella, each using a different reference database or taxonomic framework, producing conflicting family-level names.

---

## 1. Target Genes

All 100 unique sequences were submitted to the GBIF Occurrence Search API (`/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`).

| Target gene | Sequences sampled | Fraction |
| --- | --- | --- |
| — | 100 | 100% |

**Note:** The `targetGene` field in the DNADerivedData extension was not populated for any record — the gene cannot be determined from the API response alone. Based on prior inspection of the parquet data, these sequences are consistent with **18S-5P** (5′ region of the 18S small-subunit rRNA gene).

---

## 2. Taxonomic Groups

### Kingdom

| kingdom | occurrences | sequences |
| --- | --- | --- |
| Animalia | 12635 | 100 |
| incertae sedis | 2 | 2 |

### Top phyla (by occurrence count)

| kingdom | phylum | occurrences | sequences |
| --- | --- | --- | --- |
| Animalia | Arthropoda | 6336 | 98 |
| Animalia | Nematoda | 2025 | 78 |
| Animalia | Annelida | 976 | 70 |
| Animalia | Cnidaria | 959 | 84 |
| Animalia | Mollusca | 718 | 63 |
| Animalia | Porifera | 571 | 35 |
| Animalia | Platyhelminthes | 479 | 60 |
| Animalia | Chordata | 122 | 19 |
| Animalia | Bryozoa | 96 | 9 |
| Animalia | Acanthocephala | 89 | 31 |
| Animalia | Tardigrada | 82 | 16 |
| Animalia | Echinodermata | 66 | 4 |
| Animalia | Nemertea | 58 | 8 |
| Animalia | Chaetognatha | 26 | 5 |
| Animalia | Priapulida | 14 | 1 |
| Animalia | Ctenophora | 7 | 3 |
| Animalia | Onychophora | 5 | 1 |
| Animalia | Brachiopoda | 4 | 4 |
| incertae sedis | (NULL) | 2 | 2 |
| Animalia | Sipuncula | 1 | 1 |

### Taxon rank distribution

Note: rows with null family are excluded, so UNRANKED and higher-rank-only records do not appear.

| taxonrank | occurrences |
| --- | --- |
| SPECIES | 5204 |
| GENUS | 4691 |
| FAMILY | 2688 |
| SUBSPECIES | 54 |

---

## 3. Datasets

All occurrences come from a single dataset:

| Dataset key | Title | Occurrences | Sequences |
| --- | --- | --- | --- |
| `040c5662-da76-4782-a48e-cdea1892d14c` | International Barcode of Life project (iBOL) | 12,637 | 100 |

### Family-count summary (top 20 sequences)

| nucleotidesequenceid | distinct_families | occurrences |
| --- | --- | --- |
| 599536af886f27024759e6412a317d19 | 167 | 800 |
| e3435f48caf052bf5e2855557681b01c | 119 | 785 |
| e3b8a47e2e59db0f6b0cdb6883151f39 | 115 | 433 |
| d2e4e80f2e42787db759ac71511d1495 | 100 | 526 |
| a7fefb55507fc93aad27293f360412b2 | 91 | 272 |
| 55e4df3d879850d1624e6f704fa1f297 | 90 | 822 |
| 5c412d102bb35c6980d363fa06d9b603 | 71 | 238 |
| fa315f5a0ac38f67948c297ec9811335 | 69 | 255 |
| 203a482f2e11aca81a75858267db29b4 | 67 | 366 |
| 18489132d2d08d1f6b3416c6524069de | 64 | 179 |
| 97412dc8de50c9b7085d539d29765513 | 58 | 178 |
| 90972af980bfdf78c0e43bfb992113f2 | 52 | 156 |
| 6e84d4638abbf796421541876d51f6d6 | 51 | 207 |
| fc09b6a6b4b6f5281b39d23c16bce207 | 51 | 110 |
| 254b2165f18f89d956bd374d6de5f22d | 49 | 157 |
| d190469a54c5f66484be416fa99c387d | 48 | 178 |
| a36acec8cd1ff632665ccbb58b49b948 | 45 | 219 |
| 83c225cdbabf4fb6ee76cdbe0924f38c | 43 | 190 |
| 2eee54fdb0d5b404cec41efa5aa0075b | 43 | 156 |
| 9d4216d6f2f6c9c4283ef831414e765a | 42 | 145 |

---

## Root Cause of Disagreements

1. **Multiple reference databases.** Different BOLD campaigns use different reference databases (PR², SILVA, custom databases) that disagree on family boundaries, particularly for invertebrates with contested higher taxonomy.
2. **Different BOLD project submitters.** The same amplicon sequence can appear in multiple BOLD projects submitted by different PIs who identified it independently.
3. **Taxonomic instability.** Groups like Tardigrada, Acanthocephala, and Xenacoelomorpha have genuinely unstable family-level taxonomy across published reference databases.

---

## Recommendations

1. **Marker-aware consensus.** Calibrate any consensus algorithm to the specific marker in use (PR² for protists, a curated invertebrate database for Metazoa).
2. **BOLD sub-project tracing.** Within the iBOL GBIF dataset, individual records carry BOLD project codes that could identify which projects drive the most disagreements.
3. **Re-evaluate the ambiguity metric.** Consider weighting by the number of datasets contributing each family name to give a more informative picture of genuine conflict vs. within-dataset noise.
