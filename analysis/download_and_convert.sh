#!/usr/bin/env bash
# Download all reference database sources and convert them to normalised FASTA.
#
# Reads datasets.yaml (repo root) for source URLs, extraction steps, and
# conversion commands. Each dataset is processed independently; pass one or
# more short_names as arguments to run only those datasets.
#
# Usage:
#   bash analysis/download_and_convert.sh                                        # download + convert all
#   bash analysis/download_and_convert.sh gtdb pr2                               # selected datasets
#   bash analysis/download_and_convert.sh --download-only                        # download + prepare only
#   bash analysis/download_and_convert.sh --convert-only                         # convert only (skip download)
#   bash analysis/download_and_convert.sh --skip-udb                             # skip the final UDB build
#   bash analysis/download_and_convert.sh --convert-only gtdb pr2                # flags and filters can combine
#   bash analysis/download_and_convert.sh --list                                 # print available datasets
#   bash analysis/download_and_convert.sh --config small12s.yaml                 # use a custom config file
#   bash analysis/download_and_convert.sh --output-name small_12s                # set output FASTA/UDB base name
#   bash analysis/download_and_convert.sh --source-dir /path/to/storage           # store source data on external storage
#   bash analysis/download_and_convert.sh --output-dir /path/to/storage           # write FASTAs and UDB to external storage
#
# Requirements (cross-platform):
#   yq       mikefarah v4 — NOT the Python jq-wrapper 'yq' (https://github.com/mikefarah/yq)
#   vsearch  only for the final UDB build (https://github.com/torognes/vsearch)
#   python3  >= 3.9, plus per-converter deps (duckdb, pandas, openpyxl)
#   curl, unzip, tar

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$REPO_ROOT/datasets.yaml"
cd "$REPO_ROOT"

# ── dependency check ──────────────────────────────────────────────────────────
require_cmd() {  # require_cmd <command> <install hint>
    if ! command -v "$1" &>/dev/null; then
        echo "Error: '$1' is required but was not found on PATH." >&2
        echo "  Install: $2" >&2
        exit 1
    fi
}

require_cmd yq      "mikefarah yq v4 — https://github.com/mikefarah/yq  (macOS: brew install yq; Linux: snap install yq, or download the binary)"
require_cmd curl    "your OS package manager  (Debian/Ubuntu: apt install curl; Fedora/RHEL: dnf install curl; macOS: brew install curl)"
require_cmd python3 "https://www.python.org  (Debian/Ubuntu: apt install python3; macOS: brew install python)"

# yq must be the mikefarah Go implementation v4. The Python 'yq' (a jq wrapper)
# and mikefarah v3 use incompatible syntax and would fail cryptically downstream.
yq_version="$(yq --version 2>&1 || true)"
if ! printf '%s\n' "$yq_version" | grep -Eq 'mikefarah|version v?4'; then
    echo "Error: the installed 'yq' is not the required mikefarah v4 implementation." >&2
    echo "  Found:    $yq_version" >&2
    echo "  Required: mikefarah yq v4 — https://github.com/mikefarah/yq" >&2
    echo "  (The Python 'yq' jq-wrapper and mikefarah v3 are NOT compatible.)" >&2
    exit 1
fi

# ── argument parsing ──────────────────────────────────────────────────────────
DO_DOWNLOAD=true
DO_CONVERT=true
DO_UDB=true
REQUESTED=""   # colon-delimited list of requested short_names, empty = all
OUTPUT_NAME="gbif_dna_taxonomy_annotation"
SOURCE_DIR="$REPO_ROOT/source-data"
OUTPUT_DIR="$REPO_ROOT/output/fasta"
DATASET_FASTAS=()  # FASTAs produced by this run, in order
DO_LIST=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --download-only) DO_CONVERT=false ;;
        --convert-only)  DO_DOWNLOAD=false ;;
        --skip-udb)      DO_UDB=false ;;
        --list|--help)   DO_LIST=true ;;  # handled after parsing (args are consumed by this loop)
        --config)
            shift
            [[ $# -eq 0 ]] && { echo "Error: --config requires a path argument" >&2; exit 1; }
            CONFIG="$1"
            # Resolve relative paths against repo root
            [[ "$CONFIG" != /* ]] && CONFIG="$REPO_ROOT/$CONFIG"
            [[ -f "$CONFIG" ]] || { echo "Error: config file not found: $CONFIG" >&2; exit 1; }
            ;;
        --output-name)
            shift
            [[ $# -eq 0 ]] && { echo "Error: --output-name requires a name argument" >&2; exit 1; }
            OUTPUT_NAME="$1"
            ;;
        --source-dir)
            shift
            [[ $# -eq 0 ]] && { echo "Error: --source-dir requires a path argument" >&2; exit 1; }
            SOURCE_DIR="$1"
            [[ "$SOURCE_DIR" != /* ]] && SOURCE_DIR="$REPO_ROOT/$SOURCE_DIR"
            ;;
        --output-dir)
            shift
            [[ $# -eq 0 ]] && { echo "Error: --output-dir requires a path argument" >&2; exit 1; }
            OUTPUT_DIR="$1"
            [[ "$OUTPUT_DIR" != /* ]] && OUTPUT_DIR="$REPO_ROOT/$OUTPUT_DIR"
            ;;
        -*) echo "Unknown flag: $1" >&2; exit 1 ;;
        *)  REQUESTED="$REQUESTED:$1:" ;;
    esac
    shift
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

if [[ "$DO_LIST" == true ]]; then
    echo "Available datasets:"
    list_datasets
    exit 0
fi

# vsearch is only needed for the final UDB build — check it before doing any work.
if [[ "$DO_UDB" == true && "$DO_CONVERT" == true ]]; then
    require_cmd vsearch "https://github.com/torognes/vsearch  (conda: conda install -c bioconda vsearch; Debian/Ubuntu: apt install vsearch; macOS: brew install vsearch)"
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

    dir="$SOURCE_DIR/$short_name"
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
        prepare_cmd="${prepare_cmd//source-data\//$SOURCE_DIR/}"
        prepare_sentinel=$(yq ".datasets[$i].prepare_sentinel // \"\"" "$CONFIG")
        prepare_sentinel="${prepare_sentinel//source-data\//$SOURCE_DIR/}"

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
        convert_cmd="${convert_cmd//source-data\//$SOURCE_DIR/}"
        convert_cmd="$convert_cmd --output-dir \"$OUTPUT_DIR\""
        echo "  Converting …"
        eval "$convert_cmd"
        # Derive the output FASTA path: last positional argument before any -- flags
        fasta_stem=$(echo "$convert_cmd" | sed 's/ --[a-z].*//' | awk '{print $NF}')
        DATASET_FASTAS+=("$OUTPUT_DIR/${fasta_stem}.fasta")

        # ── post-process (e.g. within-species dedup) ──────────────────────
        postprocess_cmd=$(yq ".datasets[$i].postprocess_cmd // \"\"" "$CONFIG")
        postprocess_fasta=$(yq ".datasets[$i].postprocess_fasta // \"\"" "$CONFIG")
        if [[ -n "$postprocess_cmd" ]]; then
            postprocess_cmd="${postprocess_cmd//source-data\//$SOURCE_DIR/}"
            postprocess_cmd="${postprocess_cmd//output\/fasta\//$OUTPUT_DIR/}"
            echo "  Post-processing …"
            eval "$postprocess_cmd"
            if [[ -n "$postprocess_fasta" ]]; then
                # Use the post-processed FASTA in the combined output instead of the raw one.
                # (Index explicitly rather than [-1]; negative subscripts need bash 4.3+, not macOS 3.2.)
                DATASET_FASTAS[$((${#DATASET_FASTAS[@]} - 1))]="$OUTPUT_DIR/${postprocess_fasta}.fasta"
            fi
        fi
    fi

done

# ── concatenate all dataset FASTAs into one combined file ─────────────────────
if [[ "$DO_CONVERT" == true ]]; then
    mkdir -p "$OUTPUT_DIR"
    COMBINED="$OUTPUT_DIR/${OUTPUT_NAME}.fasta"
    echo ""
    echo "════════════════════════════════════════"
    echo "  Concatenating all FASTAs"
    echo "════════════════════════════════════════"

    parts=("${DATASET_FASTAS[@]+"${DATASET_FASTAS[@]}"}")

    if [[ ${#parts[@]} -eq 0 ]]; then
        echo "  No FASTAs were produced — nothing to concatenate." >&2
        exit 1
    fi

    cat "${parts[@]}" > "$COMBINED"
    COUNT=$(grep -c "^>" "$COMBINED")
    echo "  Done — $COUNT sequences written to $COMBINED"

    # ── build vsearch UDB index ───────────────────────────────────────────────
    if [[ "$DO_UDB" == true ]]; then
        echo ""
        echo "════════════════════════════════════════"
        echo "  Building vsearch UDB"
        echo "════════════════════════════════════════"
        UDB="$OUTPUT_DIR/${OUTPUT_NAME}.udb"
        LOG="$OUTPUT_DIR/${OUTPUT_NAME}.log"
        vsearch --makeudb_usearch "$COMBINED" --output "$UDB" --log "$LOG"
        echo "  Done — $UDB"
    fi
fi

echo ""
echo "Done."
