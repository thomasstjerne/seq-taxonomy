#!/usr/bin/env bash
# Build a combined 12S reference FASTA from NBDL, MIDORI2, and MitoFish.
# Output: output/testdata_12s.fasta
#
# Usage: bash analysis/build_12s_fasta.sh
# Run from the repo root.

set -euo pipefail

NBDL_DIR="source-data/nbdl/extracted"
MIDORI2_FASTA="source-data/midori2/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST/MIDORI2_UNIQ_NUC_GB269_srRNA_BLAST.fasta"
MITOFISH_FASTA="source-data/mitofish/mitofishdb.fa.gz"
MITOFISH_TABLES="source-data/mitofish/tables"
OUTPUT="output/fasta/testdata_12s.fasta"

# Extract MitoFish tables if not already done
if [ ! -d "$MITOFISH_TABLES" ]; then
    echo "Extracting MitoFish tables …"
    mkdir -p "$MITOFISH_TABLES"
    tar -xf source-data/mitofish/tables.tar -C "$MITOFISH_TABLES"
fi

echo "=== NBDL ==="
python3 analysis/dwc_to_fasta.py "$NBDL_DIR" nbdl_12s --target-gene 12s

echo ""
echo "=== MIDORI2 ==="
python3 analysis/midori2_to_fasta.py "$MIDORI2_FASTA" midori2_12s --target-gene 12s

echo ""
echo "=== MitoFish ==="
python3 analysis/mitofish_to_fasta.py "$MITOFISH_FASTA" "$MITOFISH_TABLES" mitofish_12s --target-gene 12s

echo ""
echo "=== Combining ==="
cat output/fasta/nbdl_12s.fasta output/fasta/midori2_12s.fasta output/fasta/mitofish_12s.fasta > "$OUTPUT"

COUNT=$(grep -c "^>" "$OUTPUT")
echo "Done — $COUNT sequences written to $OUTPUT"
