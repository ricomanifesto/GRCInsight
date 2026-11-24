// The artifact commit tree: the accepted payload under site/, the release
// descriptor, the hosting adapter and the provider configuration. Only the
// payload, the descriptor, and the receipt and listing the adapter writes are
// ever served.
const fs = require('node:fs');
const path = require('node:path');

const { assertRelativePath, canonicalJson, inventoryDigest, inventoryOfDir, sha256 } = require('./canonical');
const { LAYOUT } = require('./release');

const ADAPTER_SOURCE = path.join(__dirname, '..', 'adapter', 'build.js');
const PROVIDER_CONFIG = Object.freeze({ buildCommand: `node ${LAYOUT.adapter}`, framework: null });

function buildArtifactTree({ payloadDir, descriptorBytes }) {
  const files = new Map();
  for (const entry of inventoryOfDir(payloadDir)) {
    files.set(`${LAYOUT.payloadPrefix}${entry.path}`, fs.readFileSync(path.join(payloadDir, ...entry.path.split('/'))));
  }
  files.set(LAYOUT.descriptor, Buffer.from(descriptorBytes));
  files.set(LAYOUT.adapter, fs.readFileSync(ADAPTER_SOURCE));
  files.set(LAYOUT.providerConfig, Buffer.from(canonicalJson(PROVIDER_CONFIG)));
  return { files, treeDigest: treeDigestOf(files) };
}

function treeDigestOf(files) {
  return inventoryDigest([...files].map(([relativePath, bytes]) => ({ path: relativePath, sha256: sha256(bytes) })));
}

// Validate Git-tree paths before either proof or rollback reads their blobs.
function listPayloadEntries(git, commit) {
  const entries = git.listTree(commit).filter((entry) => entry.path.startsWith(LAYOUT.payloadPrefix));
  const seen = new Set();
  for (const entry of entries) {
    const relativePath = entry.path.slice(LAYOUT.payloadPrefix.length);
    assertRelativePath(relativePath);
    if (entry.type !== 'blob' || !['100644', '100755'].includes(entry.mode)) throw new Error(`${entry.path} is not a regular file in ${commit}`);
    if (seen.has(relativePath)) throw new Error(`${entry.path} is listed twice in ${commit}`);
    seen.add(relativePath);
  }
  return entries;
}

function lstatIfPresent(target) {
  try { return fs.lstatSync(target); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

// Republish exact prior bytes without rebuilding, refusing pre-existing links
// and files in the caller's private rollback directory.
function extractPayload(git, commit, targetDir) {
  const entries = listPayloadEntries(git, commit);
  const root = path.resolve(targetDir);
  const rootStats = lstatIfPresent(root);
  if (rootStats && (rootStats.isSymbolicLink() || !rootStats.isDirectory())) throw new Error('payload target must be a regular directory, not a symlink');
  const targets = entries.map((entry) => {
    const relativePath = entry.path.slice(LAYOUT.payloadPrefix.length);
    const segments = relativePath.split('/');
    let target = root;
    for (let index = 0; index < segments.length; index += 1) {
      target = path.join(target, segments[index]);
      const stats = lstatIfPresent(target);
      if (!stats) continue;
      if (stats.isSymbolicLink()) throw new Error(`${entry.path} crosses a symlink in the payload target`);
      if (index === segments.length - 1) throw new Error(`${entry.path} already exists in the payload target`);
      if (!stats.isDirectory()) throw new Error(`${entry.path} crosses a non-directory in the payload target`);
    }
    return target;
  });
  const blobs = git.readBlobs(entries.map((entry) => entry.oid));
  entries.forEach((entry, index) => {
    const target = targets[index];
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, blobs[index], { flag: 'wx' });
  });
  return targetDir;
}

module.exports = { PROVIDER_CONFIG, buildArtifactTree, extractPayload, listPayloadEntries, treeDigestOf };
