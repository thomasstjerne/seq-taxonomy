# Taxonomic annotation analysis of GBIF DNA sequences

## What the analysis does

The script `analysis/plot_species_sequence_distributions.py` queries the full GBIF DNA occurrence dataset (`trino_joined.parquet`, 171M rows) to characterise how consistently sequences are annotated with species names across datasets. It produces three plots and one table:

1. **Annotation disagreement** (`species_disagreement.png`) — rank plot of sequences carrying two or more distinct species names, ordered from most to fewest conflicting names. Shows the scale and severity of annotation conflict.
2. **Sequence coverage per species name** (`species_coverage.png`) — rank abundance plot of how many sequences each species name covers. Shows the breadth of use of different names.
3. **Taxonomic ambiguity** (`species_ambiguity.png`) — bar chart comparing sequences with consistent vs. conflicting species annotations, restricted to sequences appearing in more than one GBIF record.
4. **Family/genus breakdown** (`ambiguous_sequences_by_family_genus.xlsx`) — table of the 14,597 family/genus groups containing sequences with conflicting annotations, ranked by number of ambiguous sequences.

The key analytical unit throughout is the `nucleotidesequenceid` — an MD5 hash uniquely identifying an exact sequence variant (ASV or OTU). The same sequence can appear in multiple GBIF datasets, potentially with different taxonomic annotations.

---

## Key numbers (full GBIF dataset, May 2026)

| Metric | Count |
|---|---|
| Total unique sequences in GBIF | 22,036,768 |
| Sequences appearing in more than one GBIF record | 6,176,964 |
| Of those, with at least one species-level annotation | 380,810 (6%) |
| Of those, annotated only at coarser rank or unranked | 5,796,154 (94%) |
| With exactly one distinct species name (consistent) | 356,131 |
| With two or more distinct species names (conflicting) | 24,679 |
| Distinct species names in use | 275,289 |
| Family/genus groups containing conflicting sequences | 14,597 |

---

## Key takeaways

### 1. Annotation conflict is real but not universal
Of the 380,810 sequences appearing in multiple records with a species-level annotation, **24,679 (6.5%) carry conflicting species names**. The majority (93.5%) are consistent across datasets. This means reannotation is most urgently needed for a defined, tractable subset — not the entire corpus.

### 2. The conflict is taxonomically widespread
The 24,679 conflicting sequences span 14,597 family/genus combinations, suggesting the problem is not confined to a few taxonomic groups. The family/genus breakdown table is the starting point for identifying which groups are most affected and should be prioritised.

### 3. Severity varies enormously
The disagreement rank plot shows a very long tail: most conflicting sequences have 2–3 competing names, but a small number carry dozens or even hundreds of distinct annotations. These extreme cases likely reflect well-known taxonomically difficult groups (cryptic species complexes, poorly delimited taxa) or data quality issues (misidentified reference sequences propagated across datasets).

### 4. Species-level annotation is rare even among multi-record sequences
Of the 6,176,964 sequences appearing in more than one GBIF record, only 380,810 (6%) carry any species-level annotation at all. The remaining 94% are annotated only at genus, family, order or coarser ranks — meaning annotation depth, not just consistency, is a fundamental limitation of the current GBIF dataset.

### 5. Most sequences are seen only once
The majority of the 22M unique sequences appear in only one GBIF record, meaning annotation consistency cannot even be assessed for them. Reannotation against a curated reference database is the only way to assign or improve annotations for this large fraction.

### 6. Species name coverage is highly unequal
The coverage rank plot follows a steep power-law curve: a handful of species names are associated with thousands of sequences, while most names cover only one or a few. This has implications for reference database completeness — gaps in the reference for rare or poorly-studied taxa will be the limiting factor in annotation quality.

---

## Implications for the reannotation workflow

- **The reference database approach is well-motivated.** With 6.5% of multi-record, species-annotated sequences in conflict, and the remainder potentially misannotated with no way to detect it from GBIF data alone, alignment against a curated reference is the most reliable path to consistent annotations.
- **Prioritise the 24,679 conflicting sequences first.** These are the cases where the status quo is demonstrably wrong for at least one publisher. A consensus rule applied to these sequences has the clearest impact.
- **Use the family/genus breakdown to guide reference database curation.** Groups with many conflicting sequences are where reference database coverage and quality matter most.
- **Annotation depth is a separate problem.** The taxon rank distribution (30% genus-level, only 18% species-level) means a large share of GBIF DNA records cannot currently be resolved to species at all — reannotation against the reference database is also the mechanism for improving annotation depth, not just resolving conflicts.
