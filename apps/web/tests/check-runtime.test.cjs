"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { assertPatchedRuntime } = require("../scripts/check-runtime.cjs");

test("rejects the deployed vulnerable runtime and older Node 22 releases", () => {
  for (const version of ["22.23.2", "22.23.3", "22.22.4", "22.9.99"]) {
    assert.throws(() => assertPatchedRuntime(version), /CVE-2026-111497/);
  }
});

test("accepts the fixed release and later Node 22 patches", () => {
  for (const version of ["22.23.4", "22.23.5", "22.24.0"]) {
    assert.doesNotThrow(() => assertPatchedRuntime(version));
  }
});

test("requires explicit review when changing the supported Node major", () => {
  for (const version of ["20.20.0", "24.22.1", "26.12.1", "22.23.4-rc.1", "invalid"]) {
    assert.throws(() => assertPatchedRuntime(version));
  }
});
