# source-data

Reference databases used to build the combined 12S fish reference library.
This directory is excluded from git — each collaborator must download the files manually.

---

## MitoFish

**Source:** https://mitofish.aori.u-tokyo.ac.jp/download

Download the following two files and place them in `source-data/mitofish/`:

| File | Description |
| --- | --- |
| `mitofishdb.fa.gz` | Compressed FASTA of all fish mitochondrial sequences. Headers are bare GenBank accession IDs (e.g. `>PQ550629`). |
| `tables.tar` | Parquet files linking accessions to taxonomy and annotations: `seq_taxonid`, `taxonid_name`, `taxonid_speciesid`, `speciesid_lineageid`, `seq_description`, `seq_annotation`, `seq_heterospecific`. |

---

## NBDL — National Biodiversity DNA Library (Australia)

**Source:** https://www.gbif-test.org/dataset/3baf1ede-693d-4b22-b53e-255409d501f1/download

On the dataset page, select **Source Archive** to download the Darwin Core archive.
Place the file in `source-data/nbdl/`:

| File | Description |
| --- | --- |
| `nbdl.zip` | Darwin Core archive containing `dna.tsv` (sequences) and `occurrence.tsv` (occurrence metadata). |

To inspect contents:
```bash
unzip -l source-data/nbdl/nbdl.zip
```

---

## MIDORI2

**Source:** https://www.reference-midori.info/download.php

Navigate to **BLAST → UNIQ → srRNA** and download the latest GenBank release.
Place the directory in `source-data/midori2/`:

| File | Description |
| --- | --- |
| `MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta` | Unique nucleotide sequences for small subunit rRNA (12S for vertebrates), GenBank release 269. Headers encode full NCBI taxonomy: `>accession###rank_taxid;...`. |

The version number (`GB269`) will increment with new GenBank releases — download the latest available.

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
└── midori2/
    └── MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST/
        └── MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta
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
