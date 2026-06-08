import express from 'express';
import { createRequire } from 'module';
import { createWriteStream, mkdirSync } from 'fs';
import { dirname } from 'path';
import { pickBestMatch } from './pickBestMatch.mjs';
import { assignTaxonomyToOccurrence } from './assignTaxonomyToOccurrence.mjs';

const _require = createRequire(import.meta.url);
const cache = _require('./caches/index.js');
const CACHE_DB = _require('./caches/config.js').CACHE.dataBaseName;

const selectorCache = new Map();
selectorCache.set('pickBestMatch', pickBestMatch);

async function loadSelector(name) {
  if (selectorCache.has(name)) return selectorCache.get(name);
  if (!/^\w+$/.test(name)) throw new Error(`Invalid selector name: ${name}`);
  const mod = await import(new URL(`./${name}.mjs`, import.meta.url));
  const fn = mod[name];
  if (typeof fn !== 'function') throw new Error(`Module ${name}.mjs does not export a function named '${name}'`);
  selectorCache.set(name, fn);
  return fn;
}

const VSEARCH_URL = process.env.VSEARCH_URL || 'http://0.0.0.0:8000/search/batch';
const PORT = process.env.PORT || 3000;

// Log the top N matches for every queried sequence (debugging/inspection aid):
//   LOG_TOP_MATCHES=<N>        how many matches to log per sequence
//   LOG_TOP_MATCHES_FILE=path  append parsed rows to this file as flat TSV instead
//                              of the console (better for large multi-request tests)
//   LOG_RAW_MATCHES_FILE=path  append the raw, unparsed vsearch blast6out lines
//                              (top N per query, in vsearch's own order) to this file
// N is shared by all three; if only a file path is given, N defaults to 5.
const LOG_TOP_MATCHES_FILE = process.env.LOG_TOP_MATCHES_FILE || null;
const LOG_RAW_MATCHES_FILE = process.env.LOG_RAW_MATCHES_FILE || null;
const LOG_TOP_MATCHES =
  (parseInt(process.env.LOG_TOP_MATCHES) || 0) ||
  ((LOG_TOP_MATCHES_FILE || LOG_RAW_MATCHES_FILE) ? 5 : 0);
const LOG_FIELDS = ['identity', 'qcovs', 'scientificName', 'taxonRank', 'dataset', 'targetGene'];
// blast6out column order, for the raw-log header row.
const BLAST6_COLUMNS = ['query', 'target', 'identity', 'alnlen', 'mismatch',
  'gapopen', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore'];

// Truncate-on-start: each server run produces a fresh log with a single header row.
// Creates the parent directory if needed; a stream error is logged, not fatal.
function openLogStream(path, headerCols) {
  mkdirSync(dirname(path), { recursive: true });
  const stream = createWriteStream(path, { flags: 'w' });
  stream.on('error', err => console.error(`Log file error (${path}):`, err.message));
  stream.write(headerCols.join('\t') + '\n');
  return stream;
}

const logStream = LOG_TOP_MATCHES_FILE
  ? openLogStream(LOG_TOP_MATCHES_FILE, ['queryId', 'rank', ...LOG_FIELDS])
  : null;
const rawLogStream = LOG_RAW_MATCHES_FILE
  ? openLogStream(LOG_RAW_MATCHES_FILE, BLAST6_COLUMNS)
  : null;

function logTopMatches(queryId, matches, n = LOG_TOP_MATCHES) {
  if (!n || !matches?.length) return;
  const top = [...matches]
    .sort((a, b) => (b.identity - a.identity) || (b.qcovs - a.qcovs))
    .slice(0, n);
  if (logStream) {
    // Flat TSV with a queryId column, one write per query block (writes are
    // serialised by the stream so blocks stay intact under concurrency).
    logStream.write(
      top.map((m, i) => [queryId, i + 1, ...LOG_FIELDS.map(f => m[f] ?? '')].join('\t')).join('\n') + '\n'
    );
  } else {
    const rows = [
      `top ${top.length} of ${matches.length} matches for ${queryId}:`,
      ['rank', ...LOG_FIELDS].join('\t'),
      ...top.map((m, i) => [i + 1, ...LOG_FIELDS.map(f => m[f] ?? '')].join('\t')),
    ];
    console.log(rows.join('\n'));  // single write keeps the block intact under concurrency
  }
}

// Append the top N raw blast6out lines per query, exactly as vsearch returned
// them (no parsing, no re-ordering). Called with the raw vsearch response text.
function logRawMatches(rawText, n = LOG_TOP_MATCHES) {
  if (!rawLogStream || !n || !rawText) return;
  const counts = {};
  const out = [];
  for (const line of rawText.split('\n')) {
    if (!line.trim()) continue;
    const tab = line.indexOf('\t');
    const queryId = tab === -1 ? line : line.slice(0, tab);
    counts[queryId] = (counts[queryId] || 0) + 1;
    if (counts[queryId] <= n) out.push(line);
  }
  if (out.length) rawLogStream.write(out.join('\n') + '\n');
}

// Field order matches the 23-field pipe-separated FASTA header
const HEADER_FIELDS = [
  'id', 'accessionNumber', 'scientificName',
  'decimalLatitude', 'decimalLongitude', 'typeStatus',
  'catalogueNumber', 'identifiedBy', 'taxonRank',
  'country', 'locality', 'basisOfRecord',
  'higherClassification', 'dataset', 'targetGene',
  'domain', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species',
];

function parseTargetHeader(header) {
  const parts = header.split('|');
  const obj = {};
  HEADER_FIELDS.forEach((field, i) => {
    obj[field] = (parts[i] || '').replace(/_/g, ' ');
  });
  return obj;
}

function parseFasta(text) {
  const seqs = {};
  let id = null;
  let bases = [];
  for (const line of text.split('\n')) {
    if (line.startsWith('>')) {
      if (id !== null) seqs[id] = bases.join('');
      id = line.slice(1).trim();
      bases = [];
    } else {
      bases.push(line.trim());
    }
  }
  if (id !== null) seqs[id] = bases.join('');
  return seqs;
}

// ── blast6out parser ─────────────────────────────────────────────────────────

function parseBlast6out(text, sequences) {
  const results = {};
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const cols = line.split('\t');
    if (cols.length < 12) continue;
    const queryId = cols[0];
    const match = parseTargetHeader(cols[1]);
    match.identity        = parseFloat(cols[2]);
    match.alignmentLength = parseInt(cols[3]);
    match.mismatches      = parseInt(cols[4]);
    match.gapOpenings     = parseInt(cols[5]);
    match.qstart          = parseInt(cols[6]);
    match.qend            = parseInt(cols[7]);
    match.sstart          = parseInt(cols[8]);
    match.send            = parseInt(cols[9]);
    match.evalue          = parseFloat(cols[10]);
    match.bitScore        = parseFloat(cols[11]);
    const qLen = sequences[queryId]?.length;
    match.qcovs = qLen
      ? Math.round((match.alignmentLength / qLen) * 1000) / 10
      : -1;
    if (!results[queryId]) results[queryId] = [];
    results[queryId].push(match);
  }
  return results;
}

// ── alnout parser ────────────────────────────────────────────────────────────

function parseAlnout(text, sequences) {
  const results = {};

  // Split into per-query blocks; prepend \n so the first "Query >" also matches
  const blocks = ('\n' + text).split('\nQuery >').slice(1);

  for (const block of blocks) {
    const lines = block.split('\n');
    const queryId = lines[0].trim();
    const qLen = sequences[queryId]?.length;

    // Summary table: "%Id   TLen  Target" header, then one row per match until blank line
    const hIdx = lines.findIndex(l => l.trim().startsWith('%Id'));
    if (hIdx === -1) continue;

    const summaryRows = [];
    for (let i = hIdx + 1; i < lines.length; i++) {
      const l = lines[i].trim();
      if (!l) break;
      const cols = l.split(/\s+/);
      summaryRows.push({
        identity:     parseFloat(cols[0]),   // already numeric, % sign stripped by parseInt if present
        targetLen:    parseInt(cols[1]),
        targetHeader: cols.slice(2).join(' '),
      });
    }

    // Alignment sub-blocks: each begins with " Query Xnt >" (leading space, then "Query Xnt >")
    // Split on that pattern to get one chunk per alignment
    const alnMap = {};  // targetHeader → { alignmentLength, alignment }
    const alnChunks = block.split(/\n Query \d+nt >/).slice(1);
    for (const chunk of alnChunks) {
      const chunkLines = chunk.split('\n');
      const targetLine = chunkLines.find(l => l.startsWith('Target '));
      if (!targetLine) continue;
      const targetHeader = targetLine.split('>')[1]?.trim();
      if (!targetHeader) continue;
      // Stats summary line: "X cols, X ids (X%), X gaps (X%)"
      const statsLine = [...chunkLines].reverse().find(l => /^\d+ cols,/.test(l.trim()));
      let alignmentLength = 0;
      if (statsLine) {
        const m = statsLine.trim().match(/^(\d+) cols/);
        if (m) alignmentLength = parseInt(m[1]);
      }
      alnMap[targetHeader] = { alignmentLength, alignment: ' Query ' + chunk };
    }

    const matches = [];
    for (const { identity, targetLen, targetHeader } of summaryRows) {
      const match = parseTargetHeader(targetHeader);
      const aln = alnMap[targetHeader];
      const alignmentLength = aln?.alignmentLength || 0;
      match.identity        = identity;
      match.targetLen       = targetLen;
      match.alignmentLength = alignmentLength;
      match.qcovs = qLen && alignmentLength
        ? Math.round((alignmentLength / qLen) * 1000) / 10
        : -1;
      if (aln?.alignment) match.alignment = aln.alignment;
      matches.push(match);
    }

    if (matches.length > 0) results[queryId] = matches;
  }

  return results;
}

// ── Express server ───────────────────────────────────────────────────────────

const app = express();
app.use(express.json({ limit: '10mb' }));                    // for /occurrence/classify
app.use(express.text({ type: 'text/*', limit: '50mb' }));   // for /search/batch

app.post('/search/batch', async (req, res) => {
  const outfmt = req.query.outfmt || 'blast6out';
  if (!['blast6out', 'alnout'].includes(outfmt)) {
    return res.status(400).json({ error: `Unknown outfmt: ${outfmt}` });
  }

  const selectorName = req.query.selector || 'pickBestMatch';
  let selector;
  try {
    selector = await loadSelector(selectorName);
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }

  const body = req.body;
  if (!body) return res.status(400).json({ error: 'No FASTA body provided' });

  const sequences = parseFasta(body);

  let vsearchRes;
  try {
    vsearchRes = await fetch(`${VSEARCH_URL}?outfmt=${outfmt}`, {
      method: 'POST',
      body,
      headers: { 'Content-Type': 'text/plain' },
    });
  } catch (err) {
    console.error('Upstream error:', err.message);
    return res.status(502).json({ error: 'Could not reach vsearch server', details: err.message });
  }

  if (!vsearchRes.ok) {
    const text = await vsearchRes.text();
    return res.status(502).json({ error: 'vsearch server error', status: vsearchRes.status, details: text });
  }

  const text = await vsearchRes.text();
  if (outfmt === 'blast6out') logRawMatches(text);
  const parsed = outfmt === 'blast6out'
    ? parseBlast6out(text, sequences)
    : parseAlnout(text, sequences);

  if (LOG_TOP_MATCHES) {
    for (const [queryId, matches] of Object.entries(parsed)) logTopMatches(queryId, matches);
  }

  const result = Object.fromEntries(
    Object.entries(parsed).map(([queryId, matches]) => [queryId, selector(queryId, matches)])
  );

  res.json(result);
});

// ── shared vsearch helper ─────────────────────────────────────────────────────

async function vsearchQuery(fasta) {
  const vsearchRes = await fetch(`${VSEARCH_URL}?outfmt=blast6out`, {
    method: 'POST',
    body: fasta,
    headers: { 'Content-Type': 'text/plain' },
  });
  if (!vsearchRes.ok) {
    const text = await vsearchRes.text();
    throw new Error(`vsearch error ${vsearchRes.status}: ${text}`);
  }
  const text = await vsearchRes.text();
  logRawMatches(text);
  return parseBlast6out(text, parseFasta(fasta));
}

async function cacheLookup(id) {
  try { return await cache.get(id, CACHE_DB); }
  catch { return null; }
}

async function cacheWrite(id, matches) {
  const top25 = [...matches]
    .sort((a, b) => (b.identity - a.identity) || (b.qcovs - a.qcovs))
    .slice(0, 25);
  try { await cache.set(id, CACHE_DB, top25); }
  catch { /* non-fatal */ }
}

async function vsearchQueryWithCache(fasta) {
  const seqs = parseFasta(fasta);
  const ids = Object.keys(seqs);

  const lookups = await Promise.all(ids.map(async id => [id, await cacheLookup(id)]));
  const matchesMap = {};
  const missIds = [];
  for (const [id, cached] of lookups) {
    if (cached !== null) matchesMap[id] = cached;
    else missIds.push(id);
  }

  if (missIds.length > 0) {
    const missFasta = missIds.map(id => `>${id}\n${seqs[id]}`).join('\n');
    const fresh = await vsearchQuery(missFasta);
    await Promise.all(
      Object.entries(fresh).map(async ([id, matches]) => {
        await cacheWrite(id, matches);
        matchesMap[id] = matches;
      })
    );
  }

  if (LOG_TOP_MATCHES) {
    for (const [id, matches] of Object.entries(matchesMap)) logTopMatches(id, matches);
  }

  return matchesMap;
}

// ── POST /occurrence/classify ─────────────────────────────────────────────────
//
// Accept a single GBIF occurrence object (JSON), extract its nucleotide
// sequences, run vsearch for each, and return a DnaClassification that the
// GBIF pipeline can feed to the taxon-matching service.
//
// Request body: a GBIF occurrence object (Content-Type: application/json).
//
// Response (200):
//   { scientificName, taxonRank, [kingdom, phylum, class, order, family, genus, species], remarks }
//
// Response (204): occurrence had no sequences or no matches were found.
//
// Response (400): malformed request body.
//
app.post('/occurrence/classify', async (req, res) => {
  const occurrence = req.body;

  if (!occurrence || typeof occurrence !== 'object') {
    return res.status(400).json({ error: 'Request body must be a JSON occurrence object' });
  }

  let classification;
  try {
    classification = await assignTaxonomyToOccurrence(occurrence, vsearchQueryWithCache);
  } catch (err) {
    console.error('Classification error:', err.message);
    return res.status(502).json({ error: 'Classification failed', details: err.message });
  }

  if (classification === null) {
    return res.status(204).end();
  }

  res.json(classification);
});

// ── POST /occurrence/classify/batch ──────────────────────────────────────────
//
// Accept an array of GBIF occurrence objects, classify all of them in a single
// vsearch round-trip by deduplicating sequences across occurrences before
// querying, then fanning results back to each occurrence.
//
// Request body: occurrence[] (Content-Type: application/json).
//
// Response (200): array of result objects, one per input occurrence, in order:
//   { gbifID, classification }
//   classification is null if the occurrence had no sequences or no matches.
//
// Response (400): malformed request body.
//
app.post('/occurrence/classify/batch', async (req, res) => {
  const occurrences = req.body;

  if (!Array.isArray(occurrences)) {
    return res.status(400).json({ error: 'Request body must be an array of occurrence objects' });
  }

  // Collect unique sequences across all occurrences.
  const seqMap = new Map(); // nucleotideSequenceID → sequence string
  for (const occ of occurrences) {
    const entries = occ.nucleotideSequence;
    if (!Array.isArray(entries)) continue;
    for (const { nucleotideSequenceID, sequence, invalid } of entries) {
      if (sequence && !invalid && !seqMap.has(nucleotideSequenceID)) {
        seqMap.set(nucleotideSequenceID, sequence);
      }
    }
  }

  // Single vsearch call covering all unique sequences.
  let matchesMap = {};
  if (seqMap.size > 0) {
    const fasta = [...seqMap.entries()].map(([id, seq]) => `>${id}\n${seq}`).join('\n');
    try {
      matchesMap = await vsearchQueryWithCache(fasta);
    } catch (err) {
      console.error('Batch vsearch error:', err.message);
      return res.status(502).json({ error: 'Could not reach vsearch server', details: err.message });
    }
  }

  // For each occurrence, inject a lookup-based searchSequences so
  // assignTaxonomyToOccurrence resolves from the cached matchesMap.
  const results = await Promise.all(
    occurrences.map(async (occurrence) => {
      async function searchSequences(fasta) {
        const ids = Object.keys(parseFasta(fasta));
        return Object.fromEntries(ids.map(id => [id, matchesMap[id] ?? []]));
      }
      try {
        const classification = await assignTaxonomyToOccurrence(occurrence, searchSequences);
        return { gbifID: occurrence.gbifID ?? null, classification };
      } catch (err) {
        return { gbifID: occurrence.gbifID ?? null, classification: null, error: err.message };
      }
    })
  );

  res.json(results);
});

app.listen(PORT, () => {
  console.log(`vsearch proxy listening on http://localhost:${PORT}`);
  console.log(`Forwarding to ${VSEARCH_URL}`);
  if (LOG_TOP_MATCHES) {
    const dest = logStream ? `file ${LOG_TOP_MATCHES_FILE}` : 'console';
    console.log(`Logging top ${LOG_TOP_MATCHES} matches per query to ${dest}`);
  }
  if (rawLogStream) {
    console.log(`Logging top ${LOG_TOP_MATCHES} raw vsearch matches per query to file ${LOG_RAW_MATCHES_FILE}`);
  }
});

// Flush the log files before exiting so the tail of a test run isn't lost.
const logStreams = [logStream, rawLogStream].filter(Boolean);
if (logStreams.length) {
  const closeLogs = () => {
    let pending = logStreams.length;
    for (const s of logStreams) s.end(() => { if (--pending === 0) process.exit(0); });
  };
  process.on('SIGINT', closeLogs);
  process.on('SIGTERM', closeLogs);
}
