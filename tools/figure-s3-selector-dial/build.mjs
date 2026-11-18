// Index-0 Selector Dial — CortexFlow blog figure (standalone light SVG).
// Concept (verified GitHub n8n-io/n8n issue #44299, filed 17 Nov 2026): the
// S3-compatible node's File > Upload reads the binary field name with
// `this.getNodeParameter('binaryPropertyName', 0)` — item 0's name for every
// item — while the lookup below it already uses the current index i. Item 1
// carries its file under `data`, item 2 under `attachment`; the press stamps
// item 1's label (`data`) onto both, and item 2's own `attachment` tag sits
// unread beside it. The lit-orange lever is the fix: rename every item's
// binary key to one fixed name (`attachment`) in a Code node before the S3
// node. Download in the same file and the separate AWS S3 node already use
// the current index, so only this upload read is stuck on 0.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../../custom-skills/local-anatomy/kit/iso-kit.mjs";
import * as G from "../../../custom-skills/local-anatomy/kit/lathe.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = "/home/hatch/workspace/blog/public/figures/fix-n8n-s3-upload-wrong-binary-field-selector-dial.svg";

const WIDTH = 680;
const HEIGHT = 420;

const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
// Horizontal turned part along an axis: two-point profile gives a capped cylinder.
const along = (origin, axis, s0, s1, r, tone, style = {}) => {
  const F = G.frameAlong(origin, axis);
  return S(G.solidOf([[s0, r], [s1, r]], F, P), { tone, ...style });
};
// 3D segment projected to a screen-space d string (for face-plane details).
const seg3 = (a, b) => {
  const [x0, y0] = k.iso(a, P);
  const [x1, y1] = k.iso(b, P);
  return `M${x0.toFixed(1)} ${y0.toFixed(1)}L${x1.toFixed(1)} ${y1.toFixed(1)}`;
};

const PLATE = { x: -160, y: -80, w: 320, d: 160, r: 8 };
const BELT = { x: -70, y: 8, w: 210, d: 24 };
const BELT_TOP = 12.4;
const PARCEL_H = 12;
const P1 = { x: -51, y: 12, w: 22, d: 16, r: 1 };
const P2 = { x: 64, y: 12, w: 22, d: 16, r: 1 };
const DIAL = [28, 20];
const DIAL_R = 15;
const DIAL_TOP = 53;

const P = k.fitProjection(
  [
    ...k.boxCorners(PLATE, -17, 0),
    [DIAL[0], DIAL[1], DIAL_TOP], // dial top
    [DIAL[0], DIAL[1], 40], // press beam
    [-40, 20, BELT_TOP + PARCEL_H], // parcel 1 top
    [75, 20, BELT_TOP + PARCEL_H], // parcel 2 top
    [-120, 58, 37], // fix lever knob
    [75, 47, 1.2], // unread tag
    [-140, -72, 1], // ruler strip
  ],
  WIDTH,
  HEIGHT,
  { pad: 30, azimuth: 45 },
);
const at = (point) => k.iso(point, P);

function plate() {
  const out = [`<path class="iso-halo" d="${k.haloOf(PLATE, -17, 12, P)}"/>`];
  for (const [x, y] of byDepth(k.corners(PLATE, 22))) {
    out.push(S(k.cylinder(x, y, 7, -17, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.4, -15.4, 3.4, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(PLATE, -12, 12, P, 8, 1.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "lo" }));
  const screws = k.corners(PLATE, 10);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  // Ruler strip along the back edge.
  const strip = { x: -140, y: -76, w: 280, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.8, 0.6, [2, 3.6], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  out.push(D([at([strip.x + 2, strip.y + 3.5, 0.6]), at([strip.x + strip.w - 2, strip.y + 3.5, 0.6])], { size: 0.45 }));
  return out.join("");
}

function conveyor() {
  const out = [];
  out.push(S(k.slabOf(BELT, 0, 4, P, 5, 0.6), { tone: "mid" }));
  out.push(along([-66, 8, 7], [0, 1, 0], 0, 24, 4, "mid"));
  out.push(along([136, 8, 7], [0, 1, 0], 0, 24, 4, "mid"));
  out.push(S(k.slabOf(BELT, 11, 1.4, P, 5), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: BELT.x, y: BELT.y, w: BELT.w, d: 1.6, r: 0.7 }, 12.4, 1.6, P, 2), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: BELT.x, y: BELT.y + BELT.d - 1.6, w: BELT.w, d: 1.6, r: 0.7 }, 12.4, 1.6, P, 2), { tone: "mid", crease: "none" }));
  return out.join("");
}

function parcel(plan, label) {
  const top = BELT_TOP + PARCEL_H;
  const cx = plan.x + plan.w / 2;
  const cy = plan.y + plan.d / 2;
  return [
    S(k.slabOf(plan, BELT_TOP, PARCEL_H, P, 3, 0.5), { tone: "hi", crease: "lo" }),
    L(k.planOutline(k.insetPlan(plan, 2), top, P, 3), { tone: "faint" }),
    k.faceTextSvg(k.topMatrix([cx, cy], top, P, "x"), label, { size: 3.4, tone: "lo", anchor: "middle" }),
  ].join("");
}

function parcels() {
  const out = [];
  out.push(parcel(P1, "data"));
  out.push(parcel(P2, "data"));
  // Item 2's own label, unread, lying on the plate beside its parcel.
  const tag = { x: 62, y: 42, w: 26, d: 10, r: 1 };
  out.push(S(k.slabOf(tag, 0, 1.2, P, 3, 0.4), { tone: "mid", crease: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(tag, 1.5), 1.2, P, 3), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([75, 47], 1.2, P, "x"), "attachment", { size: 2.4, tone: "lo", anchor: "middle" }));
  return out.join("");
}

function press() {
  // C-frame stamping press between the parcels, driven by the selector dial
  // on top: back columns only, beam cantilevered forward, stamp head raised
  // mid-cycle so neither parcel is hidden under it.
  const out = [];
  out.push(S(k.slabOf({ x: 10, y: 8, w: 4, d: 6, r: 1 }, 0, 34, P, 4, 0.6), { tone: "mid" }));
  out.push(S(k.slabOf({ x: 42, y: 8, w: 4, d: 6, r: 1 }, 0, 34, P, 4, 0.6), { tone: "mid" }));
  out.push(S(k.slabOf({ x: 10, y: 8, w: 36, d: 26, r: 1 }, 34, 6, P, 4, 0.5), { tone: "mid" }));
  out.push(D([at([12, 10, 40]), at([44, 10, 40]), at([12, 32, 40]), at([44, 32, 40])], { size: 0.45 }));
  // Stamp head raised above the belt, face just below it.
  out.push(S(k.slabOf({ x: 20, y: 12, w: 16, d: 16, r: 1 }, 28, 6, P, 3, 0.5), { tone: "mid" }));
  out.push(S(k.slabOf({ x: 21, y: 13, w: 14, d: 14, r: 0.8 }, 27, 1, P, 3), { tone: "lo", crease: "none" }));
  out.push(L(k.planOutline(k.insetPlan({ x: 21, y: 13, w: 14, d: 14, r: 0.8 }, 1), 27, P, 3), { tone: "faint" }));
  return out.join("");
}

function dial() {
  // Rotary field-name selector, locked at 0, mounted on the press beam.
  const out = [];
  const [x, y] = DIAL;
  out.push(S(k.cylinder(x, y, 2.5, 40, 6, P, 20), { tone: "mid" }));
  out.push(S(k.cylinder(x, y, DIAL_R, 46, 7, P, 64, 0.8), { tone: "hi", crease: "lo" }));
  out.push(L(k.knurl(x, y, DIAL_R, DIAL_TOP - 3.4, DIAL_TOP, 84, P, 0.3), { tone: "lo" }));
  out.push(L(k.sideArc(x, y, DIAL_R, DIAL_TOP - 3.4, P, 40), { tone: "faint" }));
  out.push(L(k.ring(x, y, DIAL_R - 2.2, DIAL_TOP, P, 64), { tone: "lo" }));
  const ticks = k.radialTicks(x, y, DIAL_R - 3, 24, 6, DIAL_TOP, [1.2, 2.6], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  // The 0 marker at the rim, where the needle points.
  out.push(S(k.slabOf({ x: x + DIAL_R - 3.4, y: y - 1.6, w: 3.4, d: 3.2, r: 0.8 }, DIAL_TOP, 2, P, 2), { tone: "mid" }));
  out.push(L(k.ring(x, y, 1.6, DIAL_TOP, P, 16), { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([x + 8.5, y + 5.5], DIAL_TOP, P, "x"), "0", { size: 3, tone: "lo", anchor: "middle" }));
  // Needle locked at 0 (pointing +x). Tip is a free end by design.
  out.push(L(k.lineOnTop([x, y], [x + DIAL_R - 4, y], DIAL_TOP + 0.2, P), { tone: "lo", free: "end" }));
  out.push(D([at([x, y, DIAL_TOP + 0.2])], { size: 0.5, tone: "hi" }));
  return out.join("");
}

function fixLever() {
  // Front-left cabinet: the fix lever (lit orange) re-labels both parcels
  // `attachment` before they reach the press.
  const out = [];
  out.push(S(k.slabOf({ x: -140, y: 44, w: 40, d: 28, r: 2 }, 0, 18, P, 5, 0.8), { tone: "mid" }));
  out.push(S(k.slabOf({ x: -139, y: 45, w: 38, d: 26, r: 2 }, 18, 2, P, 5, 0.5), { tone: "mid" }));
  out.push(S(k.cylinder(-120, 58, 3, 20, 4, P, 24), { tone: "mid" }));
  out.push(L(k.knurl(-120, 58, 3, 20, 24, 24, P), { tone: "lo" }));
  out.push(S(k.cylinder(-120, 58, 1.6, 24, 10, P, 16), { tone: "hi", lit: true }));
  out.push(S(G.sphereOf([-120, 58, 35], 2.2, P), { tone: "mid", lit: true }));
  out.push(S(k.slabOf({ x: -134, y: 69.4, w: 22, d: 1.2, r: 0.4 }, 8, 4, P, 3), { tone: "lo", crease: "none" }));
  const rules = [
    seg3([-132, 70.6, 10.6], [-116, 70.6, 10.6]),
    seg3([-132, 70.6, 9.6], [-120, 70.6, 9.6]),
    seg3([-132, 70.6, 8.6], [-118, 70.6, 8.6]),
  ].join("");
  out.push(L(rules, { tone: "lo", free: true }));
  return out.join("");
}

const cornerText = (x, y, anchor, text) =>
  `<text x="${x}" y="${y}" text-anchor="${anchor}" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="9" fill="var(--anatomy-muted)">${text}</text>`;

function corners() {
  return [
    cornerText(16, 24, "start", "Fig 1"),
    cornerText(WIDTH - 16, 24, "end", "index-0 selector dial"),
    cornerText(16, HEIGHT - 14, "start", "static figure"),
    cornerText(WIDTH - 16, HEIGHT - 14, "end", "item 1 data \u00B7 item 2 stamped data \u00B7 attachment unread"),
  ].join("");
}

// CortexFlow light tokens: cream paper, signal-orange lit accent (wins over the
// kit's light-theme tokens via the attribute selector).
const ORANGE = `<style>.iso[data-theme="light"]{--anatomy-paper:#FFFDF5;--anatomy-lit:#FF4D00;--anatomy-lit-top:#ff8a50;--anatomy-lit-shade:#e04a00;}</style>`;

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label:
    "Index-0 selector dial: a stamping press whose rotary field-name selector is locked at 0. Two parcels ride a conveyor — item 1 labelled data, item 2 labelled attachment — but the press stamps item 1's label, data, onto both; item 2's own attachment tag lies unread beside it. The lit orange lever is the fix: rename every item's binary key to one fixed name before the press.",
  standalone: "light",
  body: [
    ORANGE,
    plate(),
    conveyor(),
    parcels(),
    press(),
    dial(),
    fixLever(),
    corners(),
  ],
});

writeFileSync(OUT, svg);
console.log("wrote", OUT, `(${(svg.length / 1024).toFixed(1)} KB)`);
