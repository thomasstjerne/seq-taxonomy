-- Generate top100_distinct_families.parquet:
-- All occurrences of the ~100 sequences with the most distinct family-level annotations.
-- Run against trino_joined.parquet for the full analysis; small_dataset.parquet for a demo.
--
-- Usage:
--   duckdb -c ".read queries/generate_top100_distinct_families.sql"

CREATE OR REPLACE VIEW source AS
    SELECT * FROM 'trino_joined.parquet';
    -- For demo use small_dataset.parquet:
    -- SELECT * FROM 'small_dataset.parquet';

-- Step 1: rank sequences by number of distinct family annotations
CREATE OR REPLACE TEMP TABLE top100_seqs AS
SELECT
    nucleotidesequenceid,
    COUNT(DISTINCT family)                          AS n_distinct_families,
    COUNT(DISTINCT datasetkey)                      AS n_datasets,
    COUNT(*)                                        AS n_occurrences,
    LIST(DISTINCT family ORDER BY family)           AS distinct_families
FROM source
WHERE family IS NOT NULL
GROUP BY nucleotidesequenceid
ORDER BY n_distinct_families DESC, n_datasets DESC
LIMIT 100;

-- Step 2: pull all occurrence rows for those sequences
COPY (
    SELECT s.*
    FROM source s
    INNER JOIN top100_seqs t USING (nucleotidesequenceid)
) TO 'top100_distinct_families.parquet' (FORMAT PARQUET);

-- Summary preview
SELECT
    nucleotidesequenceid,
    n_distinct_families,
    n_datasets,
    n_occurrences,
    distinct_families
FROM top100_seqs
ORDER BY n_distinct_families DESC;
