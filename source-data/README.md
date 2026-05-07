# source-data

Reference databases used to build the combined 12S fish reference library.
This directory is excluded from git — each collaborator must download the files manually.

---

## MitoFish

**Source:** https://mitofish.aori.u-tokyo.ac.jp/download

```bash
curl -O https://mitofish.aori.u-tokyo.ac.jp/download/fullseq/2026/04/mitofishdb.fa.gz
curl -O https://mitofish.aori.u-tokyo.ac.jp/download/tables/2026/04/tables.tar
```

Place both files in `source-data/mitofish/`.

| File | Description |
| --- | --- |
| `mitofishdb.fa.gz` | Compressed FASTA of all fish mitochondrial sequences. Headers are bare GenBank accession IDs (e.g. `>PQ550629`). |
| `tables.tar` | Parquet files linking accessions to taxonomy and annotations: `seq_taxonid`, `taxonid_name`, `taxonid_speciesid`, `speciesid_lineageid`, `seq_description`, `seq_annotation`, `seq_heterospecific`. |

---

## NBDL — National Biodiversity DNA Library (Australia)

```bash
curl -o source-data/nbdl/nbdl.zip https://labs.gbif.org/~tsjeppesen/nbdl.zip
```

| File | Description |
| --- | --- |
| `nbdl.zip` | Darwin Core archive containing `dna.tsv` (sequences) and `occurrence.tsv` (occurrence metadata). |

---

## MIDORI2

```bash
curl -O https://www.reference-midori.info/download/Databases/GenBank269_2025-12-09/BLAST/uniq/fasta/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta.zip
```

Place the file in `source-data/midori2/` and unzip it:

```bash
unzip MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta.zip -d source-data/midori2/
```

| File | Description |
| --- | --- |
| `MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta` | Unique nucleotide sequences for small subunit rRNA (12S for vertebrates), GenBank release 269. Headers encode full NCBI taxonomy: `>accession###rank_taxid;...`. |

The version number (`GB269`) will increment with new GenBank releases — check https://www.reference-midori.info/download.php for the latest.

---

## PR2

```bash
curl -L -o source-data/PR2/pr2_version_5.1.0_merged.xlsx https://github.com/pr2database/pr2database/releases/download/v5.1.0.0/pr2_version_5.1.0_merged.xlsx
```

| File | Description |
| --- | --- |
| `pr2_version_5.1.0_merged.xlsx` | Merged PR2 reference database (v5.1.0), 240k sequences, primarily 18S rRNA. Columns include full taxonomy, GenBank metadata, and sample provenance. |

---

## GTDB — Genome Taxonomy Database

**Source:** https://gtdb.ecogenomic.org

```bash
curl -o source-data/gtdb/bac120_ssu_reps.fna.gz https://data.gtdb.ecogenomic.org/releases/latest/genomic_files_reps/bac120_ssu_reps.fna.gz
curl -o source-data/gtdb/ar53_ssu_reps.fna.gz https://data.gtdb.ecogenomic.org/releases/latest/genomic_files_reps/ar53_ssu_reps.fna.gz
curl -o source-data/gtdb/bac120_taxonomy.tsv https://data.gtdb.ecogenomic.org/releases/latest/bac120_taxonomy.tsv
curl -o source-data/gtdb/ar53_taxonomy.tsv https://data.gtdb.ecogenomic.org/releases/latest/ar53_taxonomy.tsv
```

Place all four files in `source-data/gtdb/`.

| File | Description |
| --- | --- |
| `bac120_ssu_reps.fna.gz` | 16S SSU rRNA sequences for bacterial species-cluster representatives (~30 MB). One sequence per GTDB species cluster. |
| `ar53_ssu_reps.fna.gz` | 16S SSU rRNA sequences for archaeal species-cluster representatives (~2 MB). |
| `bac120_taxonomy.tsv` | Two-column TSV (no header): `genome_accession<TAB>d__Domain;p__Phylum;...;s__Species`. |
| `ar53_taxonomy.tsv` | Same format as above for archaea. |

---

## RefSeq 16S (Archaea)

**Source:** NCBI BioProject PRJNA33317, hosted via GBIF

```bash
curl -o source-data/refSeq_arc_16s/PRJNA33317.zip https://hosted-datasets.gbif.org/ncbi/PRJNA33317.zip
unzip source-data/refSeq_arc_16s/PRJNA33317.zip -d source-data/refSeq_arc_16s/extracted
```

| File | Description |
| --- | --- |
| `PRJNA33317.zip` | Darwin Core archive of NCBI RefSeq 16S rRNA sequences for Archaea (~392 KB). |

---

## RefSeq 16S (Bacteria)

**Source:** NCBI BioProject PRJNA33175, hosted via GBIF

```bash
curl -o source-data/refSeq_bac_16s/PRJNA33175.zip https://hosted-datasets.gbif.org/ncbi/PRJNA33175.zip
unzip source-data/refSeq_bac_16s/PRJNA33175.zip -d source-data/refSeq_bac_16s/extracted
```

| File | Description |
| --- | --- |
| `PRJNA33175.zip` | Darwin Core archive of NCBI RefSeq 16S rRNA sequences for Bacteria (~9.9 MB). |

---

## RefSeq ITS

**Source:** NCBI BioProject PRJNA177353, hosted via GBIF

```bash
curl -o source-data/refseq_its/PRJNA177353.zip https://hosted-datasets.gbif.org/ncbi/PRJNA177353.zip
unzip source-data/refseq_its/PRJNA177353.zip -d source-data/refseq_its/extracted
```

| File | Description |
| --- | --- |
| `PRJNA177353.zip` | Darwin Core archive containing `dna.txt` (sequences) and `occurrence.txt` (occurrence metadata). Positional/headerless format following standard DwC field indices. |

---

## BOLDistilled

```bash
curl -o source-data/BOLDistilled/source.zip https://us-sea-1.linodeobjects.com/boldistilled/source.zip
unzip source-data/BOLDistilled/source.zip -d source-data/BOLDistilled/
```

| File | Description |
| --- | --- |
| `BOLDistilled_COI_Apr2026_SEQUENCES.fasta` | COI sequences keyed by `sampleID\|BIN`. |
| `BOLDistilled_COI_Apr2026_TAXONOMY.tsv` | BIN-level taxonomy with concordant/discordant rank annotations. |

---

## Directory structure

After downloading, the directory should look like:

```
source-data/
├── mitofish/
│   ├── mitofishdb.fa.gz
│   └── tables.tar
├── nbdl/
│   └── nbdl.zip
├── midori2/
│   └── MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST/
│       └── MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta
├── PR2/
│   └── pr2_version_5.1.0_merged.xlsx
├── boldistilled/
│   └── source/
│       ├── BOLDistilled_COI_Apr2026_SEQUENCES.fasta
│       └── BOLDistilled_COI_Apr2026_TAXONOMY.tsv
├── refSeq_arc_16s/
│   └── extracted/
│       ├── dna.txt
│       └── occurrence.txt
├── refSeq_bac_16s/
│   └── extracted/
│       ├── dna.txt
│       └── occurrence.txt
├── refseq_its/
│   └── extracted/
│       ├── dna.txt
│       └── occurrence.txt
└── gtdb/
    ├── bac120_ssu_reps.fna.gz
    ├── ar53_ssu_reps.fna.gz
    ├── bac120_taxonomy.tsv
    └── ar53_taxonomy.tsv
```

---

## Converting to normalised FASTA

Once all source files are in place, a single script builds each individual FASTA
and concatenates them into `output/testdata_12s.fasta`:

```bash
bash analysis/build_12s_fasta.sh
```

Run from the repo root. The script will:

1. Extract the MitoFish parquet tables from `tables.tar` (once, into `source-data/mitofish/tables/`)
2. Extract the 12S region from each NBDL record → `output/nbdl_12s.fasta`
3. Convert the MIDORI2 srRNA FASTA → `output/midori2_12s.fasta`
4. Extract annotated 12S subsequences from MitoFish mitogenomes → `output/mitofish_12s.fasta`
5. Concatenate all three into `output/testdata_12s.fasta`

All output FASTAs share the same pipe-separated header format:

```
>ID|accessionNumber|scientificName|decimalLatitude|decimalLongitude|typeStatus|catalogueNumber|identifiedBy|taxonRank|country|locality|basisOfRecord|higherClassification|dataset|targetGene
```

Fields unavailable in a given source are left empty; the pipe delimiters are always present so columns stay aligned across sources.

Other converters (run individually from the repo root):

```bash
# PR2 18S
python3 analysis/pr2_to_fasta.py source-data/PR2/pr2_version_5.1.0_merged.xlsx pr2_18s --target-gene 18s

# BOLDistilled COI
python3 analysis/boldistilled_to_fasta.py source-data/BOLDistilled/BOLDistilled_COI_Apr2026_SEQUENCES.fasta source-data/BOLDistilled/BOLDistilled_COI_Apr2026_TAXONOMY.tsv boldistilled_coi --target-gene coi

# UNITE ITS
python3 analysis/unite_to_fasta.py source-data/UNITE/sh_general_release_dynamic_s_all_19.02.2025.fasta unite_its --target-gene its

# refSeq ITS (DwC archive)
python3 analysis/dwc_to_fasta.py source-data/refseq_its/extracted refseq_its --target-gene its

# GTDB 16S (bacteria + archaea combined)
python3 analysis/gtdb_to_fasta.py source-data/gtdb gtdb_16s --target-gene 16s
```
