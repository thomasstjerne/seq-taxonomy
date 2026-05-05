-- Descriptive analysis of top100_distinct_families.parquet
-- Run after generate_top100_distinct_families.sql has produced the parquet.
--
-- Usage:
--   duckdb -c ".read queries/top100_analysis.sql"

-- 1. Per-sequence ambiguity summary
SELECT
    nucleotidesequenceid,
    COUNT(DISTINCT family)              AS n_distinct_families,
    COUNT(DISTINCT datasetkey)          AS n_datasets,
    COUNT(*)                            AS n_occurrences,
    LIST(DISTINCT family ORDER BY family) AS distinct_families
FROM 'top100_distinct_families.parquet'
WHERE family IS NOT NULL
GROUP BY nucleotidesequenceid
ORDER BY n_distinct_families DESC;

-- 2. Kingdom / phylum distribution
SELECT
    kingdom,
    phylum,
    COUNT(DISTINCT nucleotidesequenceid) AS n_sequences,
    COUNT(*)                             AS n_occurrences
FROM 'top100_distinct_families.parquet'
GROUP BY kingdom, phylum
ORDER BY n_sequences DESC;

-- 3. Dataset contribution
SELECT
    datasetkey,
    COUNT(DISTINCT nucleotidesequenceid) AS n_sequences,
    COUNT(*)                             AS n_occurrences,
    COUNT(DISTINCT family)               AS n_distinct_families_contributed
FROM 'top100_distinct_families.parquet'
GROUP BY datasetkey
ORDER BY n_occurrences DESC;

-- 4. Family disagreement: pairs of families assigned to the same sequence
SELECT
    a.nucleotidesequenceid,
    a.family AS family_a,
    b.family AS family_b,
    COUNT(*) AS co_occurrence_count
FROM 'top100_distinct_families.parquet' a
JOIN 'top100_distinct_families.parquet' b
    ON  a.nucleotidesequenceid = b.nucleotidesequenceid
    AND a.family < b.family
GROUP BY 1, 2, 3
ORDER BY co_occurrence_count DESC
LIMIT 30;
