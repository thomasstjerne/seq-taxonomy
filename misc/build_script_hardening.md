# Hardening `analysis/download_and_convert.sh` for unattended/scheduled runs

Observations collected while running the first full fresh build
(2026-09-15, `--source-dir`/`--output-dir` on Samsung_T5).

Line references are against `analysis/download_and_convert.sh` at commit `1e75958`.

---

## Status

| Finding | Status |
|---|---|
| 1. curl has no `--fail` | **fixed** — `--fail --show-error --retry 3 --connect-timeout 30` |
| 2. partial downloads cached as complete | **fixed** — `.part` + verify + `mv` |
| — download content/archive verification | **added** — `verify_download()`, Tier 0 |
| — UDB self-hit smoke test | **added** — Tier 3, fails the build below 95% |
| — header delimiter corruption (28 nbdl records) | **fixed** — `strip_delimiters()` in all 11 converters |
| 8/9. BOLDistilled version pinning | **fixed** — release resolved at convert time |
| 3, 4, 5, 6, 7, 10–16, 18–22 | open |

## Critical — can silently produce a corrupt index

### 1. `curl` has no `--fail`: HTTP errors are written to disk as data
`curl -L --progress-bar $curl_flags -o "$dest" "$url"` (line 165). On a 404 or 503 curl
writes the **error page body** to `$dest` and exits 0. The script then unzips/converts an
HTML document. Nothing in the run reports a problem.

This is not a hypothetical: **18 of the 25 datasets with endpoints pin a version in the URL**
(`GB269`, `GenBank269_2025-12-09`, `v5.1.0.0`, `19.02.2025`, `2026/04`). Upstream rotation
is the expected steady state, not an exception.

*Fix:* add `--fail --show-error` (and consider `--retry 3 --retry-delay 5 --connect-timeout 30`).

### 2. Partial downloads are cached as complete, forever
The skip test is presence-only: `if [[ -f "$dest" ]]` (line 160). Because `set -e` aborts the
run on a failed curl, a truncated file is *guaranteed* to be left behind by any network
interruption — and every subsequent run then prints `Already present: …` and proceeds.

*Fix:* download to `$dest.part` and `mv` into place only on curl success. Optionally record
and compare `Content-Length`.

### 3. A filtered run destroys the production combined FASTA and UDB
`bash analysis/download_and_convert.sh gtdb` skips the other datasets via `continue`
(line 136), so `DATASET_FASTAS` ends up holding a single entry — and the script then
unconditionally rebuilds `$COMBINED` from it (line 227) and rebuilds the UDB from that
(line 242). The full reference index is replaced by a one-dataset index.

*Fix:* when `$REQUESTED` is non-empty, skip the concatenate/UDB stages unless an explicit
`--rebuild-combined` flag is passed.

### 4. Outputs are published non-atomically, with no space preflight
`cat "${parts[@]}" > "$COMBINED"` and `vsearch --makeudb_usearch … --output "$UDB"` both
write directly over the live artefacts. A crash, a kill, or a full disk mid-write leaves a
truncated FASTA or UDB where a working one used to be. `grep -c "^>"` on a truncated
combined FASTA still succeeds and reports a plausible count.

*Fix:* write `$COMBINED.tmp` / `$UDB.tmp` and `mv` on success. Check free space against a
size estimate before concatenating (~4 GB combined FASTA, ~16 GB UDB at current sources).

---

## High — run reliability

### 5. One failing dataset aborts all 26, salvaging nothing
`set -euo pipefail` (line 27) with no per-dataset error handling. A single flaky endpoint
after 12 GB of successful downloads kills the run before the combined FASTA is built.

*Fix:* wrap each dataset in a function, trap failure, record it, continue; print a summary
table at the end and exit non-zero if anything failed.

### 6. No lock file
Two overlapping scheduled runs share `$SOURCE_DIR` and `$OUTPUT_DIR` and will interleave
writes. *Fix:* `mkdir`-based lock (portable) or `flock` on Linux.

### 7. `--insecure` on 14 MIDORI endpoints
TLS verification is disabled for every MIDORI download. In an unattended context this
removes the only check that the payload came from the expected host, and it masks the
certificate problem that presumably motivated it. *Fix:* pin a CA bundle, or re-test —
the upstream certificate may since have been fixed.

---

## Medium — version staleness

### 8. Two opposite version-pinning failure modes coexist
- **Versioned URL** (18 datasets): breaks loudly-ish when upstream rotates — except that
  finding 1 turns it into a silent corruption instead.
- **Version-neutral URL, versioned contents** (BOLDistilled): the URL keeps working and the
  *filenames inside* change. Fixed 2026-09-15 by resolving the release in
  `boldistilled_to_fasta.py`; the resolved release is recorded as
  `output/fasta/boldistilled_coi.fasta.version`.

### 9. `prepare_sentinel` skips extraction when the version moves
22 entries use a sentinel; 14 embed `GB269` and 3 embed a date
(`unite` 19.02.2025, `its2_global` 2023-01-17, `bell_brosi_rbcl` Nov2019/Jul2021).
A sentinel naming one release means a newly downloaded archive of a *different* release is
never extracted — the run reports "Preparation already done" and converts the old files.
This was the BOLDistilled bug; the pattern is still present elsewhere.

### 10. `version:` in `datasets.yaml` is an unverified assertion
It is never checked against what was downloaded. `boldistilled` is now `rolling` with the
real release recorded at build time; every other entry can still drift silently.

*Suggested:* a build manifest written next to the UDB recording, per dataset, the URL, the
resolved version, file sizes, and sequence counts. Config states intent; manifest records fact.

### 11. `fasta_stem` derivation is fragile
`echo "$convert_cmd" | sed 's/ --[a-z].*//' | awk '{print $NF}'` (line 194) assumes the output
stem is the last positional and that every flag is lowercase. An uppercase flag or a
path-valued final positional silently yields the wrong path.

*Fix:* an explicit `output_fasta:` key per dataset in `datasets.yaml`.

---

## Logging

### 12. `curl --progress-bar` spams a non-tty log
At 17/26 datasets the log was 65 KB across 304 lines, almost entirely carriage-return
progress bars. *Fix:* `--no-progress-meter` when `! [ -t 1 ]`, plus a one-line
`-w '%{http_code} %{size_download} %{time_total}s'` summary per download.

### 13. No timestamps anywhere
Impossible to tell how long a dataset took, or when a stall began. *Fix:* prefix each
structural line with an ISO timestamp.

### 14. No per-dataset outcome line
Converters print their own counts in varying formats; there is no uniform
`dataset / status / sequences / duration` record to grep.

### 15. The vsearch build log is overwritten every run
`LOG="$OUTPUT_DIR/${OUTPUT_NAME}.log"` (line 242) — no history across builds.

### 16. The run ends with a bare `Done.`
No summary of how many datasets were processed, skipped or failed, and the exit code is 0
as long as the last command succeeded.

---

## What the first full run actually revealed (2026-09-15, 58 min)

The run completed cleanly: 26/26 datasets, 5,075,399 sequences in the combined FASTA
(4.7 GB), 18 GB UDB. No download turned out to be an HTML error page, and the combined
count matches the sum of its parts exactly — so none of the corruption modes above fired
*this time*. Notes that only the real run could produce:

### 17. The version fix was load-bearing, not theoretical
BOLDistilled had indeed rotated: **Apr2026 → Jul2026, 1,503,527 → 1,980,804 sequences (+32%)**.
Under the old config this run would have died at dataset 19 of 26, ~45 minutes in:
`prepare_sentinel` named the Apr2026 file, which does not exist in a fresh source dir, so
extraction would have run and produced *Jul2026* filenames — after which `convert_cmd`,
still naming Apr2026, would `FileNotFoundError` and `set -e` would abort everything
(finding 5). Two of the failure modes above compounding in the ordinary case.

### 18. Only 2 of 26 sources had changed — the other 24 re-downloaded identically
Every version-pinned URL returned the same data as the May build (the dedup counts match
`CLAUDE.md`'s table exactly: its2_global 307,976→258,218, mitofish 43,870→37,145,
pr2 223,357→196,218). So ~11 GB of transfer and most of the 58 minutes bought two changed
datasets — BOLDistilled, plus `ncbi_matk` which had never been built.

*Suggested:* conditional requests (`curl -z` / `If-Modified-Since`, or compare
`Content-Length` via `--head`) so a scheduled run skips unchanged sources. This matters more
as the schedule tightens.

### 19. Atomic publish (finding 4) conflicts with current disk headroom
Samsung_T5 is down to **29 GB free**. In-place overwrite is roughly space-neutral because
`cat >` and vsearch truncate first. Writing to `.tmp` and `mv`-ing — the fix recommended
above — needs the old and new artefacts to coexist, i.e. **~23 GB extra peak**, which does
not currently fit. Either fix must come with a free-space preflight, or the promote step has
to delete the previous artefact first (giving up the rollback that made it worth doing).

### 20. There is no post-build verification step
The checks worth automating were all run by hand afterwards:
- combined sequence count == sum of the per-dataset parts (catches truncated `cat`)
- no source file is `text/html` (catches finding 1)
- no per-dataset FASTA is empty or implausibly small
- the UDB actually loads and answers a known query

Without these, a bad build is indistinguishable from a good one until the annotation service
starts returning nonsense.

### 21. There is no promote/publish step
The new artefacts sit in `$OUTPUT_DIR` on Samsung_T5. `CLAUDE.md` and the documented vsearch
server command both point at `output/fasta/gbif_dna_taxonomy_annotation.udb` in the repo,
which is still the **May build**. Nothing in the pipeline switches a consumer over, and
nothing records which build is live.

### 22. Timing and sizing for the scheduler
- Total 58 min (10:33 → 11:32); the vsearch UDB build was the last ~10 min.
- Peak source-data footprint ~11 GB; outputs 4.7 GB + 18 GB.
- Set any scheduler timeout well above 1 h — `ncbi_matk` is a live Entrez fetch whose
  duration depends on NCBI, and it produces no progress output while running.

### 23. The UDB nearly doubled — 9.6 GB → 18 GB
Consequence outside this script: the annotation sizing work assumed a 9 GB index. Cold-start
page-in was already ~211 s across 4 pods at that size. Pod memory and warm-up cost need
re-checking against 18 GB before the throughput numbers are reused.


---

## Implemented 2026-09-16

### Tier 0 — download verification
`verify_download()` runs on every freshly downloaded file *and* on every cached file
before it is trusted. It rejects empty files, anything `file(1)` identifies as HTML or
XML (the error-page case), and archives that fail an integrity test
(`unzip -qt` / `tar -tzf` / `gzip -t`). Downloads now go to `$dest.part` and are renamed
only after verifying, so an interrupted transfer can never be cached as complete. A cached
file that fails verification is deleted and re-fetched rather than silently reused.

`curl` gained `--fail --show-error --retry 3 --retry-delay 5 --connect-timeout 30` and a
one-line `http/size/time` summary per download. The progress bar is now used only on a tty
(`--no-progress-meter` otherwise), which removes the carriage-return spam from scheduled logs.

Verified against real data — rejects a fake 404 HTML body, a truncated zip, a truncated
gzip and an empty file; passes `source.zip`, `mitofishdb.fa.gz` and the UNITE tarball.

### Tier 3 — UDB self-hit smoke test
After the UDB is built, ~200 sequences are sampled and queried against the new index. Each
must find itself at >=99% identity; below 95% the build fails and the sample plus hits are
left in place for inspection. This is the only check that can fail on a structurally
plausible but corrupt index — every count-based check passes on one.

Sampling takes 4 records from the head and 4 from the tail of **each per-dataset FASTA**,
via `sample_records()`. The first attempt stepped evenly through the combined FASTA instead,
which had two problems: it required a second full read of a 4.7 GB file (~2 min), and with a
step of `COUNT/200` it could not reach any dataset smaller than ~25,000 sequences — `nbdl`
(2,909) and `refSeq_arc_16s` (1,160) were both missed entirely. Sampling the parts is
effectively free (awk exits after n records; `tail` seeks) and covers 26/26 datasets. Because
the parts are concatenated in order, the samples still span the whole index positionally, so
a truncated UDB is still caught.

Parts smaller than the 256 KB tail window contribute their records twice, so the pass rate is
computed over *distinct* query IDs — otherwise those duplicates would deflate it.

### Header delimiter corruption
`sanitize()` collapsed whitespace but never stripped `|`, the field delimiter itself. No
converter handled it. NBDL's `identifiedBy` lists multiple collectors as
`Pogonoski | Russell`, which produced headers of 24-27 fields and shifted `dataset`,
`targetGene` and the whole taxonomy block for 28 records — wrong, silently, since May.

Fixed in two places: `sanitize()` now maps `|` to `/` and drops `>`, and every converter
applies `strip_delimiters()` at the `"|".join(fields)` call so the 23-field contract holds
regardless of which helper produced a value. Re-converting nbdl gives 2,909/2,909 headers at
exactly 23 fields.

**Note:** the shipped index still contains the 28 bad records. They are corrected only by a
rebuild.
