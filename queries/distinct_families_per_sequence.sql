SELECT
    nucleotidesequenceid,
    COUNT(DISTINCT family) AS n_distinct_families,
    LIST(DISTINCT family ORDER BY family) AS families
FROM 'trino_joined.parquet'
GROUP BY nucleotidesequenceid
ORDER BY n_distinct_families DESC
LIMIT 50;
