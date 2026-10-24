"use strict";

// Node 22.23.4 backports the CVE-2026-111497 fix; its Brotli version
// string alone does not identify whether the security patch is present.
// https://nodejs.org/en/blog/release/v22.23.4
function assertPatchedRuntime(version = process.versions.node) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
  if (!match) throw new Error(`Unrecognized Node.js version: ${version}`);
  const [, major, minor, patch] = match.map(Number);
  if (major !== 22 || minor < 23 || (minor === 23 && patch < 4)) {
    throw new Error(
      `Node.js ${version} is not approved: use Node 22 >=22.23.4 for CVE-2026-111497.`,
    );
  }
}

if (require.main === module) {
  assertPatchedRuntime();
  console.log(`Patched Node.js runtime verified: ${process.versions.node}`);
}

module.exports = { assertPatchedRuntime };
