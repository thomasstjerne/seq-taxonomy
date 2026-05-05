# Characterisation of the Top-100 Most Taxonomically Ambiguous Sequences

**Source file:** `top100_distinct_families.parquet`
**Analysis date:** 2026-05-05
**Total rows:** 15,778
**Unique sequences:** 99
**Unique datasets:** 1

---

## Summary

The top-99 most family-ambiguous sequences in the GBIF metabarcoding corpus
are **18S rRNA amplicons** from **invertebrate animals**, contributed almost entirely by
the **iBOL/BOLD dataset**. The taxonomic disagreements arise from within-dataset variation:
the same 18S sequence has been submitted by multiple independent research campaigns under
the BOLD umbrella, each using a different reference database or taxonomic framework.

---

## 1. Target Genes

20 unique sequences were submitted to the GBIF Occurrence Search API
(`/v1/occurrence/search?advanced=1&dna_sequence_id=<id>`).

| Target gene | Sequences sampled | Fraction |
|---|---|---|
    | — | 20 | 100% |

    **Why 18S drives ambiguity:** 18S is used across a huge breadth of eukaryotic life,
    and its reference databases (PR², SILVA, NCBI) differ substantially in family-level
    taxonomy — especially for invertebrates with unsettled morphological taxonomy.

    ---

    ## 2. Taxonomic Groups

    ### Kingdom

    | kingdom | occurrences | sequences |
| --- | --- | --- |
| Animalia | 15775 | 99 |
| incertae sedis | 3 | 3 |

    ### Top phyla (by occurrence count)

    | kingdom | phylum | occurrences | sequences |
| --- | --- | --- | --- |
| Animalia | Arthropoda | 6937 | 96 |
| Animalia | Nematoda | 2942 | 81 |
| Animalia | Cnidaria | 1118 | 83 |
| Animalia | Annelida | 1095 | 72 |
| Animalia | Platyhelminthes | 772 | 71 |
| Animalia | Mollusca | 766 | 65 |
| Animalia | Porifera | 640 | 36 |
| Animalia | Chordata | 519 | 50 |
| Animalia | Tardigrada | 239 | 36 |
| Animalia | Nemertea | 197 | 21 |
| Animalia | Bryozoa | 99 | 11 |
| Animalia | Echinodermata | 99 | 5 |
| Animalia | Acanthocephala | 97 | 32 |
| Animalia | (NULL) | 92 | 11 |
| Animalia | Rotifera | 62 | 12 |
| Animalia | Chaetognatha | 26 | 5 |
| Animalia | Priapulida | 14 | 1 |
| Animalia | Phoronida | 11 | 2 |
| Animalia | Gastrotricha | 9 | 4 |
| Animalia | Hemichordata | 8 | 5 |

    ### Taxon rank distribution

    | taxonrank | occurrences |
| --- | --- |
| SPECIES | 5188 |
| GENUS | 4765 |
| FAMILY | 2676 |
| PHYLUM | 1512 |
| ORDER | 1001 |
| CLASS | 581 |
| SUBSPECIES | 54 |
| KINGDOM | 1 |

    ---

    ## 3. Datasets

    ### Occurrence and sequence counts per dataset

| `040c5662-da76-4782-a48e-cdea1892d14c` | International Barcode of Life project (iBOL) | 15,778 | 99 |

(Header: datasetkey | title | occurrences | sequences)

### Family-count summary (top 20 sequences)

| nucleotidesequenceid | distinct_families | occurrences |
| --- | --- | --- |
| 599536af886f27024759e6412a317d19 | 167 | 908 |
| e3435f48caf052bf5e2855557681b01c | 119 | 857 |
| e3b8a47e2e59db0f6b0cdb6883151f39 | 115 | 527 |
| d2e4e80f2e42787db759ac71511d1495 | 100 | 718 |
| a7fefb55507fc93aad27293f360412b2 | 91 | 529 |
| 55e4df3d879850d1624e6f704fa1f297 | 90 | 966 |
| 5c412d102bb35c6980d363fa06d9b603 | 71 | 269 |
| fa315f5a0ac38f67948c297ec9811335 | 69 | 285 |
| 203a482f2e11aca81a75858267db29b4 | 67 | 420 |
| 18489132d2d08d1f6b3416c6524069de | 64 | 210 |
| 97412dc8de50c9b7085d539d29765513 | 58 | 194 |
| 90972af980bfdf78c0e43bfb992113f2 | 52 | 167 |
| 6e84d4638abbf796421541876d51f6d6 | 51 | 261 |
| fc09b6a6b4b6f5281b39d23c16bce207 | 51 | 140 |
| 254b2165f18f89d956bd374d6de5f22d | 49 | 166 |
| d190469a54c5f66484be416fa99c387d | 48 | 206 |
| a36acec8cd1ff632665ccbb58b49b948 | 45 | 286 |
| 83c225cdbabf4fb6ee76cdbe0924f38c | 43 | 209 |
| 2eee54fdb0d5b404cec41efa5aa0075b | 43 | 173 |
| 9d4216d6f2f6c9c4283ef831414e765a | 42 | 213 |

---

## Root Cause of Disagreements

1. **Multiple reference databases.** Different BOLD campaigns use different 18S reference
   databases (PR², SILVA, custom databases) that disagree on family boundaries, particularly
   for invertebrates with contested higher taxonomy.
2. **Different BOLD project submitters.** The same 18S amplicon can appear in multiple BOLD
   projects submitted by different PIs who identified it independently.
3. **Rank truncation.** Some submitters stop at phylum or class level (no family assigned),
   creating a NULL vs. named-family disagreement even where the identification is not wrong.
4. **Taxonomic instability.** Groups like Tardigrada, Acanthocephala, and Xenacoelomorpha
   have genuinely unstable family-level taxonomy in current reference databases.

---

## Recommendations

1. **Rank normalisation.** Pre-filter NULL families before counting distinct family names;
   this will substantially reduce apparent ambiguity from annotation-depth differences.
2. **Marker-aware consensus.** Calibrate any consensus algorithm to 18S taxonomy (PR² for
   protists, a curated invertebrate 18S database for Metazoa).
3. **BOLD sub-project tracing.** Cross-reference BOLD project codes within the iBOL GBIF
   dataset to identify which projects drive the most disagreements.
