-- Datasets where the same nucleotidesequenceid is associated with more than one
-- distinct scientificName, with the top 10 most ambiguous sequences per dataset.
WITH seq_counts AS (
    SELECT
        datasetkey,
        nucleotidesequenceid,
        COUNT(DISTINCT scientificname) AS n_names
    FROM 'trino_joined.parquet'
    GROUP BY datasetkey, nucleotidesequenceid
    HAVING COUNT(DISTINCT scientificname) > 1
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY datasetkey ORDER BY n_names DESC) AS rn
    FROM seq_counts
)
SELECT datasetkey, nucleotidesequenceid, n_names
FROM ranked
WHERE rn <= 10
ORDER BY datasetkey, n_names DESC;
