#!/usr/bin/env bash
# Download all reference database sources and convert them to normalised FASTA.
#
# Reads datasets.yaml (repo root) for source URLs, extraction steps, and
# conversion commands. Each dataset is processed independently; pass one or
# more short_names as arguments to run only those datasets.
#
# Usage:
#   bash analysis/download_and_convert.sh                          # download + convert all
#   bash analysis/download_and_convert.sh gtdb pr2                 # selected datasets
#   bash analysis/download_and_convert.sh --download-only          # download + prepare only
#   bash analysis/download_and_convert.sh --convert-only           # convert only (skip download)
#   bash analysis/download_and_convert.sh --convert-only gtdb pr2  # flags and filters can combine
#   bash analysis/download_and_convert.sh --list                   # print available datasets
#
# Requirements: yq v4  (brew install yq)
#               vsearch  (brew install vsearch)
#               curl, unzip, tar, python3

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$REPO_ROOT/datasets.yaml"
cd "$REPO_ROOT"

# ── dependency check ──────────────────────────────────────────────────────────
if ! command -v yq &>/dev/null; then
    echo "Error: yq is required. Install with: brew install yq" >&2
    exit 1
fi

# ── argument parsing ──────────────────────────────────────────────────────────
DO_DOWNLOAD=true
DO_CONVERT=true
REQUESTED=""   # colon-delimited list of requested short_names, empty = all

for arg in "$@"; do
    case "$arg" in
        --download-only) DO_CONVERT=false ;;
        --convert-only)  DO_DOWNLOAD=false ;;
        --list|--help)   : ;;  # handled below
        -*) echo "Unknown flag: $arg" >&2; exit 1 ;;
        *)  REQUESTED="$REQUESTED:$arg:" ;;
    esac
done

# ── helpers ───────────────────────────────────────────────────────────────────
count=$(yq '.datasets | length' "$CONFIG")

list_datasets() {
    for i in $(seq 0 $((count - 1))); do
        sn=$(yq ".datasets[$i].short_name" "$CONFIG")
        tg=$(yq ".datasets[$i].target_gene" "$CONFIG")
        ver=$(yq ".datasets[$i].version // \"?\"" "$CONFIG")
        sc=$(yq ".datasets[$i].taxonomic_scope" "$CONFIG")
        printf "  %-16s %-6s %-10s %s\n" "$sn" "$tg" "$ver" "$sc"
    done
}

if [[ "${1-}" == "--list" || "${1-}" == "--help" ]]; then
    echo "Available datasets:"
    list_datasets
    exit 0
fi

# ── main loop ─────────────────────────────────────────────────────────────────
for i in $(seq 0 $((count - 1))); do
    short_name=$(yq ".datasets[$i].short_name" "$CONFIG")
    target_gene=$(yq ".datasets[$i].target_gene" "$CONFIG")

    # Skip if a filter was given and this dataset isn't in it
    if [[ -n "$REQUESTED" && "$REQUESTED" != *":$short_name:"* ]]; then
        continue
    fi

    echo ""
    echo "════════════════════════════════════════"
    echo "  $short_name  ($target_gene)"
    echo "════════════════════════════════════════"

    dir="source-data/$short_name"
    mkdir -p "$dir"

    # ── download endpoints ──────────────────────────────────────────────────
    if [[ "$DO_DOWNLOAD" == true ]]; then
        endpoint_count=$(yq ".datasets[$i].endpoints | length" "$CONFIG")
        curl_flags=$(yq ".datasets[$i].curl_flags // \"\"" "$CONFIG")

        if [[ "$endpoint_count" -eq 0 ]]; then
            echo "  No endpoints configured — skipping download."
        else
            for j in $(seq 0 $((endpoint_count - 1))); do
                url=$(yq ".datasets[$i].endpoints[$j]" "$CONFIG")
                filename=$(basename "$url")
                dest="$dir/$filename"

                if [[ -f "$dest" ]]; then
                    echo "  Already present: $filename"
                else
                    echo "  Downloading $filename …"
                    # shellcheck disable=SC2086
                    curl -L --progress-bar $curl_flags -o "$dest" "$url"
                fi
            done
        fi

        # ── prepare (extraction etc.) ─────────────────────────────────────
        prepare_cmd=$(yq ".datasets[$i].prepare_cmd // \"\"" "$CONFIG")
        prepare_sentinel=$(yq ".datasets[$i].prepare_sentinel // \"\"" "$CONFIG")

        if [[ -n "$prepare_cmd" ]]; then
            if [[ -n "$prepare_sentinel" && -e "$prepare_sentinel" ]]; then
                echo "  Preparation already done (sentinel exists: $prepare_sentinel)"
            else
                echo "  Preparing …"
                eval "$prepare_cmd"
            fi
        fi
    fi

    # ── convert ─────────────────────────────────────────────────────────────
    if [[ "$DO_CONVERT" == true ]]; then
        convert_cmd=$(yq ".datasets[$i].convert_cmd" "$CONFIG")
        echo "  Converting …"
        eval "$convert_cmd"
    fi

done

# ── concatenate all dataset FASTAs into one combined file ─────────────────────
if [[ "$DO_CONVERT" == true ]]; then
    COMBINED="output/fasta/gbif_dna_taxonomy_annotation.fasta"
    echo ""
    echo "════════════════════════════════════════"
    echo "  Concatenating all FASTAs"
    echo "════════════════════════════════════════"

    # Collect all per-dataset FASTAs, excluding the combined output itself
    parts=()
    for f in output/fasta/*.fasta; do
        [[ "$f" == "$COMBINED" ]] && continue
        parts+=("$f")
    done

    cat "${parts[@]}" > "$COMBINED"
    COUNT=$(grep -c "^>" "$COMBINED")
    echo "  Done — $COUNT sequences written to $COMBINED"

    # ── build vsearch UDB index ───────────────────────────────────────────────
    echo ""
    echo "════════════════════════════════════════"
    echo "  Building vsearch UDB"
    echo "════════════════════════════════════════"
    UDB="output/fasta/gbif_dna_taxonomy_annotation.udb"
    LOG="output/fasta/gbif_dna_taxonomy_annotation.log"
    vsearch --makeudb_usearch "$COMBINED" --output "$UDB" --log "$LOG"
    echo "  Done — $UDB"
fi

echo ""
echo "Done."
