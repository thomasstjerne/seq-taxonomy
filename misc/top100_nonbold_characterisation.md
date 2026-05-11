# Characterisation of the Top-100 Most Taxonomically Ambiguous Sequences (Non-BOLD)

**Source file:** `trino_joined.parquet`
**Filter:** Excludes GBIF dataset `040c5662-da76-4782-a48e-cdea1892d14c` (International Barcode of Life / iBOL)
**Analysis date:** 2026-05-11
**Total rows:** 25,946
**Unique sequences:** 100
**Unique datasets:** 24

---

## Summary

Without the iBOL/BOLD dataset, the level of family-level disagreement drops dramatically — the most conflicted sequence spans only **7 distinct families** (vs. 167 in the BOLD-inclusive top-100). The 100 sequences here cover a broad taxonomic range: Bacteria, Chromista (protists, dinoflagellates), Fungi, Animalia, and Plantae, reflecting a mixture of environmental metabarcoding datasets using diverse markers (16S, 18S, ITS, COI). Disagreements arise primarily from sequences that match highly conserved marker regions across distantly related taxa, and from different reference databases used by independent metabarcoding surveys.

---

## 1. Taxonomic Groups

### Kingdom / Phylum

| Kingdom | Phylum | Occurrences | Sequences |
| --- | --- | --- | --- |
| Bacteria | Proteobacteria | 7,871 | 11 |
| Bacteria | Bacteroidota | 3,497 | 3 |
| Bacteria | Verrucomicrobiota | 2,927 | 3 |
| Bacteria | Myxococcota_A | 2,647 | 6 |
| Chromista | Ciliophora | 1,894 | 8 |
| Animalia | Arthropoda | 1,473 | 12 |
| Bacteria | Planctomycetota | 1,151 | 6 |
| Fungi | Ascomycota | 1,136 | 6 |
| Bacteria | Actinobacteriota | 1,044 | 2 |
| Chromista | Myzozoa | 516 | 14 |
| Plantae | Tracheophyta | 462 | 11 |
| Chromista | Cryptophyta | 273 | 2 |
| Protozoa | Sarcomastigophora | 227 | 1 |
| Chromista | Haptophyta | 151 | 3 |
| Chromista | Cercozoa | 112 | 2 |
| incertae sedis | NULL | 71 | 6 |
| Fungi | Basidiomycota | 65 | 15 |
| Protozoa | Choanozoa | 59 | 1 |
| Animalia | Nematoda | 49 | 1 |
| Chromista | Ochrophyta | 43 | 3 |
| Animalia | Chordata | 38 | 2 |
| Animalia | Cnidaria | 32 | 6 |
| Bacteria | Cyanobacteria | 32 | 1 |
| Bacteria | Bdellovibrionota | 10 | 6 |
| Chromista | Bigyra | 12 | 1 |
| Plantae | Bryophyta | 2 | 1 |
| Animalia | Echinodermata | 1 | 1 |
| Fungi | Chytridiomycota | 1 | 1 |

### Taxon rank distribution

Note: rows with null family are excluded, so UNRANKED and higher-rank-only records do not appear here.

| Taxon rank | Occurrences |
| --- | --- |
| FAMILY | 15,678 |
| SPECIES | 8,855 |
| GENUS | 7,513 |
| UNRANKED | 1,311 |

---

## 2. Datasets

24 datasets contribute to the top-100 sequences. One dataset is heavily dominant:

| Dataset key | Occurrences | Sequences |
| --- | --- | --- |
| `227eb73f-9b53-4a66-b2ef-e12c960d76ba` | 23,017 | 35 |
| `9fc74265-28a7-4d62-97ea-33eb5588562e` | 9,953 | 6 |
| `efe230b2-0a42-41ec-b50a-f3c19ca4a99b` | 1,514 | 4 |
| `cb8a261a-66cb-4068-809e-9e773359bb30` | 1,455 | 11 |
| `9012def0-bd87-48a0-ac9e-e0e78dd37689` | 313 | 12 |
| `fbf49d0a-df4c-4b89-ba71-143bf6430a91` | 248 | 3 |
| `e0b59ee7-19ae-4eb0-9217-33317fb50d47` | 221 | 12 |
| `4e15ad17-be62-4101-8cc2-9f315e27f1dc` | 191 | 3 |
| `d8f7cf5d-df32-4b34-bd60-ea85272155e1` | 140 | 7 |
| `9a228813-6288-4aba-a8f8-480e425b5f62` | 109 | 4 |
| `ed868722-2b6f-45b6-8c0f-d8b376858b35` | 73 | 7 |
| `e27dc4f2-2538-41a0-ab58-593762feddd1` | 65 | 19 |
| `7d116cef-af47-4eb0-95a4-aaf69d54d325` | 49 | 2 |
| `2c32f022-e417-41ee-ae4d-aba2b35e5601` | 47 | 23 |
| `110155d2-f474-4012-9209-eebf20fd9be1` | 42 | 13 |
| `af6f962a-3dad-43df-a9e3-36ad528a4977` | 39 | 2 |
| `3b8c5ed8-b6c2-4264-ac52-a9d772d69e9f` | 31 | 7 |
| `6bce37d6-a682-4cca-89c4-7464cefa65e9` | 26 | 4 |
| `75d65a6f-0749-4af9-84b9-aa1d8f660e5c` | 19 | 9 |
| `9f0e1ca6-fb08-4c72-9a4a-1e3b7a528c10` | 13 | 13 |
| `e752fa90-3931-4fae-8472-396f207ccddd` | 10 | 1 |
| `50c9509d-22c7-4a22-a47d-8c48425ef4a7` | 6 | 2 |
| `84d26682-f762-11e1-a439-00145eb45e9a` | 4 | 3 |
| `9e29a2fe-d780-48a8-a93f-9ce041f9202f` | 4 | 2 |

### Family-count summary (top 20 sequences)

| nucleotidesequenceid | distinct_families | occurrences |
| --- | --- | --- |
| 5d5c2f4e38096e258e79899915694fbe | 7 | 27 |
| ffb39969749938b574c5163afe8f6eb8 | 5 | 12 |
| b57259c96913f95d705b4e963013570c | 4 | 64 |
| dfdf1fa6aa6ee2b65c73017116fccfee | 4 | 53 |
| a39618d8650554d98925e1790aa644ba | 4 | 10 |
| 0dfc213cc1af2da8b8924f731cbe6894 | 3 | 1,109 |
| 544f4e7590344457fefb04a72462b1c6 | 3 | 515 |
| 3e36a018ff2393198f89bd41aa2dbe3b | 3 | 388 |
| 3167e3f7e7797a1c913ae20351471667 | 3 | 259 |
| d3ee18440e44d971555aaab87986e303 | 3 | 183 |
| 0b0d2eb1357dc0acb3a634b44e318865 | 3 | 49 |
| 18ae6361b3b337203ebdca142016b233 | 3 | 3 |
| f4aad8f52b13fa4d537d176b486798d7 | 2 | 3,547 |
| 02af91e538ccf09eb820f758f530dc02 | 2 | 3,222 |
| 29c01877b71274b3c1f911ea3821c89d | 2 | 2,915 |
| 53e462150be1cb5919bf239504ec4b9e | 2 | 2,367 |
| eb839967c222031fed189918d3080ae1 | 2 | 2,249 |
| 47c746a35e2ee5394d15b8a9e5ec097f | 2 | 1,830 |
| dd44ec4757db425e09bb00bee8aafb2b | 2 | 1,736 |
| 97728fc2743a8d2c388119a1eb700096 | 2 | 1,664 |

---

## 3. Notable Sequences

### Most conflicted: `5d5c2f4e38096e258e79899915694fbe` (7 families)

Assigned families: Carcharhinidae, Diodontidae, Labridae, Monacanthidae, Phalacrocoracidae, Phasianidae, Scombridae (+ NULL).

A striking cross-class conflict — sharks (Carcharhinidae), pufferfish (Diodontidae), wrasses (Labridae), filefish (Monacanthidae), tunas (Scombridae), cormorants (Phalacrocoracidae), and pheasants (Phasianidae). Assignments span fish, seabirds, and terrestrial birds. This is consistent with a highly conserved marker region (likely a short 12S or 16S fragment) where the reference database provides insufficient resolution to discriminate among vertebrates, and different databases make divergent placements.

### Second: `ffb39969749938b574c5163afe8f6eb8` (5 families)

Assigned families: Carangidae, Gobiidae, Labridae, Synodontidae, Tripterygiidae. All marine teleost fish — a more coherent conflict driven by reference-database disagreement on which fish family a sequence belongs to rather than cross-kingdom noise.

### Diptera cluster: `b57259c96913f95d705b4e963013570c` (4 families)

Assigned families: Mycetophilidae, Phoridae, Simuliidae, Sphaeroceridae — all Diptera (flies). Likely a COI or ITS2 sequence where the barcode region does not cleanly resolve to one fly family.

---

## Root Causes of Disagreements

1. **Conserved marker regions with poor resolution.** The top sequence spans sharks, fish, and birds — indicating a short or highly conserved fragment (likely vertebrate 12S/16S) that cannot discriminate at family level. Different reference databases place it differently based on their closest-match entries.
2. **Mixed-marker datasets.** The top-100 spans Bacteria (16S), protists and algae (18S), fungi (ITS), and metazoans (COI/12S). Each marker has its own reference database ecology; sequences from one dataset may be compared against a database calibrated for a different marker, producing spurious cross-kingdom placements.
3. **Dominant dataset effect.** A single dataset (`227eb73f`) contributes 89% of total occurrences (23,017 of 25,946) across 35 of the 100 sequences, suggesting it is the primary driver of within-top-100 conflict — but disagreement still requires at least one other dataset per sequence.
4. **Environmental/metagenomic noise.** Several bacterial family conflicts (e.g., `BACL11`, `UBA2385`, `UBA7430`, `CAJQPC01`, `MB11C04`) involve provisional GTDB-style labels that are absent or mapped differently in NCBI/SILVA-based databases used by other datasets.

---

## Contrast with BOLD-inclusive Top-100

| Metric | BOLD-inclusive | Non-BOLD |
| --- | --- | --- |
| Max distinct families | 167 | 7 |
| Unique datasets | 1 | 24 |
| Total rows | 12,637 | 25,946 |
| Dominant taxonomic group | Invertebrate Animalia (18S-5P) | Bacteria + Chromista (mixed markers) |
| Primary disagreement source | Within-BOLD multi-project submissions | Cross-dataset reference database divergence |

The BOLD dataset is by far the dominant driver of high family-level ambiguity in the full GBIF sequence corpus. Outside of BOLD, genuine cross-dataset family disagreement is modest (≤7 families per sequence) and often explainable by marker-resolution limits or reference-database labelling conventions.

---

## Recommendations

1. **Treat BOLD as a separate stratum.** Consensus algorithms should handle BOLD occurrences separately from other datasets, given the qualitatively different disagreement pattern (within-project vs. cross-dataset).
2. **Marker-aware filtering.** Sequences where the top conflict spans multiple kingdoms (as in `5d5c2f4e`) should be flagged as low-confidence regardless of marker, and excluded from family-level consensus assignments.
3. **GTDB label harmonisation.** Provisional bacterial family labels (UBA\*, CAJQPC01, MB11C04) should be mapped to their NCBI/SILVA equivalents before any consensus step; they are a primary source of spurious two-family disagreements in bacterial sequences.
4. **Dataset weighting.** Consider down-weighting the dominant dataset (`227eb73f`) when it alone drives the second family assignment for a sequence — a single large survey should not override consistent assignments from multiple independent sources.
