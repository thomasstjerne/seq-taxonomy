-- Descriptive queries for top100_distinct_families.parquet
-- Run from the repo root:  duckdb -c ".read queries/top100_analysis.sql"

-- 1. Basic counts
SELECT
    COUNT(*)                             AS total_rows,
    COUNT(DISTINCT nucleotidesequenceid) AS unique_sequences,
    COUNT(DISTINCT datasetkey)           AS unique_datasets
FROM 'top100_distinct_families.parquet';

-- 2. Kingdom distribution
SELECT
    COALESCE(kingdom, '(NULL)')          AS kingdom,
    COUNT(*)                             AS occurrences,
    COUNT(DISTINCT nucleotidesequenceid) AS sequences
FROM 'top100_distinct_families.parquet'
GROUP BY 1
ORDER BY 2 DESC;

-- 3. Phylum distribution
SELECT
    COALESCE(kingdom, '(NULL)')          AS kingdom,
    COALESCE(phylum, '(NULL)')           AS phylum,
    COUNT(*)                             AS occurrences,
    COUNT(DISTINCT nucleotidesequenceid) AS sequences
FROM 'top100_distinct_families.parquet'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 20;

-- 4. Taxon rank distribution
SELECT
    COALESCE(taxonrank, '(NULL)') AS taxonrank,
    COUNT(*)                      AS occurrences
FROM 'top100_distinct_families.parquet'
GROUP BY 1
ORDER BY 2 DESC;

-- 5. Dataset contribution (occurrences and sequences per dataset)
SELECT
    datasetkey,
    COUNT(*)                             AS occurrences,
    COUNT(DISTINCT nucleotidesequenceid) AS sequences
FROM 'top100_distinct_families.parquet'
GROUP BY 1
ORDER BY 2 DESC;

-- 6. Per-sequence distinct family count (sorted by ambiguity)
SELECT
    nucleotidesequenceid,
    COUNT(DISTINCT family) FILTER (WHERE family IS NOT NULL) AS distinct_families_nonnull,
    COUNT(DISTINCT family)                                    AS distinct_families_incl_null,
    COUNT(*)                                                  AS occurrences,
    LIST(DISTINCT family ORDER BY family)                     AS family_list
FROM 'top100_distinct_families.parquet'
GROUP BY 1
ORDER BY 2 DESC, 3 DESC;

-- 7. Family names for the single most ambiguous sequence
SELECT
    family,
    COUNT(*) AS occurrences,
    datasetkey
FROM 'top100_distinct_families.parquet'
WHERE nucleotidesequenceid = (
    SELECT nucleotidesequenceid
    FROM 'top100_distinct_families.parquet'
    GROUP BY nucleotidesequenceid
    ORDER BY COUNT(DISTINCT family) DESC
    LIMIT 1
)
GROUP BY 1, 3
ORDER BY 2 DESC;
