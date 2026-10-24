import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { BlockMath } from "../components/block-math";

test("renders process formulas as display math with accessible MathML", () => {
  const html = renderToStaticMarkup(<BlockMath math={String.raw`F = \frac{E}{\pi r^2}`} />);
  assert.match(html, /katex-display/);
  assert.match(html, /<math/);
  assert.match(html, /<mfrac>/);
});

test("keeps the error renderer and escapes invalid formula text", () => {
  const formula = String.raw`\notACommand{<script>alert(1)</script>}`;
  const html = renderToStaticMarkup(<BlockMath math={formula} renderError={() => <code>{formula}</code>} />);
  assert.match(html, /<code>/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("does not enable trusted HTML or executable links", () => {
  for (const math of [String.raw`\href{javascript:alert(1)}{click}`, String.raw`\htmlClass{injected}{x}`]) {
    const html = renderToStaticMarkup(<BlockMath math={math} />);
    assert.doesNotMatch(html, /href="javascript:|class="injected"/);
  }
});
