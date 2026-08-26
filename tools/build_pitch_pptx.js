// Builds SQRlane_Pitch.pptx — the deck as a PowerPoint file, for handing to a
// room that expects one. Same content and sources as static/deck.html.
//
//   npm install pptxgenjs && node tools/build_pitch_pptx.js
//
// It reports its own fit warnings and exits clean only when every text box fits
// its shape and no content overlaps a wrapped title. Those two checks exist
// because both faults shipped in the first render and neither is visible to the
// OOXML validator: the generator has to catch them, or a person has to.

// SQRlane pitch deck — What / Why / How / Team.
//
// Monochrome by instruction: black, white, grey, off-white, nothing else. The
// visual interest has to come from scale contrast, the dark/light rhythm of the
// section dividers, and generous white space — not from colour.
//
// Fonts are rendered by the reader's PowerPoint, not by us, so both faces are
// ones that ship everywhere: Arial for everything, Courier New for eyebrows,
// citations and placeholder slots. That mono/sans contrast does most of the work.

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";          // 10" x 5.625" — must be set before any slide
pres.author = "SQRlane";
pres.title = "SQRlane — Pitch Deck";

const INK = "171717", INK2 = "4D4D4D", INK3 = "8F8F8F";
const PAPER = "FAFAFA", WHITE = "FFFFFF", RULE = "E2E2E2", G100 = "F2F2F2";
const ON_DARK = "C9C9C9", ON_DARK_2 = "9A9A9A";
const SANS = "Arial", MONO = "Courier New";

const W = 10, H = 5.625, M = 0.55, CW = W - 2 * M;

// ---- text metrics -------------------------------------------------------
// PowerPoint does the real layout; this only has to be close enough to catch
// text that cannot possibly fit its box. Every miss it reports was a genuine
// overflow in the render, and the three defects it found first — a two-line
// title sitting under the cards, a wrapped card heading pushing its body out
// of the card, and four bodies spilling past their edge — are exactly the
// class of fault no schema validator sees.
const CH = { reg: 0.50, bold: 0.54 };            // average glyph width, in em
const lineH = (pt, mult = 1.2) => pt * 1.2 * mult / 72;
const estLines = (text, wIn, pt, bold) => {
  const per = Math.max(1, Math.floor(wIn / (pt * (bold ? CH.bold : CH.reg) / 72)));
  return String(text).split("\n").reduce((n, para) =>
    n + Math.max(1, Math.ceil(para.length / per)), 0);
};
const estH = (text, wIn, pt, bold, mult) => estLines(text, wIn, pt, bold) * lineH(pt, mult);

let SLIDE = 0, WARNINGS = [], TOP = 0;
const clearsTitle = (what, y) => {
  if (TOP && y < TOP - 0.02)
    WARNINGS.push(`slide ${SLIDE}  ${what} sits at ${y.toFixed(2)}" but the title runs to ${TOP.toFixed(2)}"`);
};
const fits = (what, needed, available) => {
  if (needed > available + 0.02)
    WARNINGS.push(`slide ${SLIDE}  ${what}: needs ${needed.toFixed(2)}" but has ${available.toFixed(2)}"`);
};


// Fresh objects every time: pptxgenjs converts option values to EMU in place,
// so a shared literal is silently corrupted after its first use.
const card = (x, y, w, h, dark, stroke) => ({
  shape: pres.ShapeType.roundRect, x, y, w, h, rectRadius: 0.06,
  fill: { color: dark ? INK : WHITE },
  line: { color: stroke || (dark ? INK : RULE), width: 0.75 },
});

function newSlide() { SLIDE++; TOP = 0; return pres.addSlide(); }

function bg(s, dark) {
  s.background = { color: dark ? INK : PAPER };
}

function eyebrow(s, section, sub) {
  s.addText(
    [{ text: section, options: { bold: true, color: INK } },
     { text: "   " + sub, options: { color: INK3 } }],
    { x: M, y: 0.30, w: CW, h: 0.22, fontFace: MONO, fontSize: 8.5,
      charSpacing: 1.2, isTextBox: true, margin: 0, valign: "middle" });
}

function title(s, text, opts = {}) {
  const size = opts.size || 25, w = opts.w || CW, y = opts.y === undefined ? 0.58 : opts.y;
  // Sized from the text, not guessed: a hand-set height is what put slide 14's
  // second title line underneath the cards.
  const h = estLines(text, w, size, true) * lineH(size, 1.02);
  s.addText(text, { x: M, y, w, h, fontFace: SANS, fontSize: size, bold: true,
    color: opts.color || INK, lineSpacingMultiple: 1.02, isTextBox: true,
    margin: 0, valign: "top" });
  TOP = y + h + (opts.gap === undefined ? 0.26 : opts.gap);
  return TOP;   // where content may start
}

function note(s, runs, y) {
  s.addText(runs, {
    x: M, y: y || 4.94, w: CW, h: 0.5, fontFace: MONO, fontSize: 7,
    color: INK3, lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top",
  });
}

// A figure and what it is. `n` is the number, `unit` the small trailing unit.
function stat(s, o) {
  clearsTitle(`stat "${o.n}"`, o.y);
  fits("stat below slide edge", o.y + o.h, H - 0.25);
  s.addShape(card(o.x, o.y, o.w, o.h, o.dark).shape, card(o.x, o.y, o.w, o.h, o.dark));
  const pad = 0.18;
  s.addText(
    [{ text: o.n, options: { fontSize: o.nSize || 24, bold: true, color: o.dark ? WHITE : INK } },
     // A word unit takes a space; a symbol unit does not — "~10 apps", but "60%".
     ...(o.unit ? [{ text: (/^[a-z]/i.test(o.unit) ? " " : "") + o.unit,
                     options: { fontSize: 11, color: o.dark ? ON_DARK_2 : INK3 } }] : [])],
    { x: o.x + pad, y: o.y + pad - 0.02, w: o.w - pad * 2, h: 0.42,
      fontFace: SANS, isTextBox: true, margin: 0, valign: "middle" });
  const labelAvail = o.h - pad * 2 - 0.46 - (o.src ? 0.30 : 0);
  fits(`stat "${o.n}" label`, estH(o.label, o.w - pad * 2, 9, false, 1.18), labelAvail);
  s.addText(o.label, {
    x: o.x + pad, y: o.y + pad + 0.44, w: o.w - pad * 2, h: labelAvail,
    fontFace: SANS, fontSize: 9, color: o.dark ? ON_DARK : INK2,
    lineSpacingMultiple: 1.18, isTextBox: true, margin: 0, valign: "top" });
  if (o.src) s.addText(o.src, {
    x: o.x + pad, y: o.y + o.h - pad - 0.26, w: o.w - pad * 2, h: 0.26,
    fontFace: MONO, fontSize: 6.5, color: o.dark ? ON_DARK_2 : INK3,
    lineSpacingMultiple: 1.15, isTextBox: true, margin: 0, valign: "bottom" });
}

// A titled block of prose or bullets.
function block(s, o) {
  clearsTitle(`block "${o.head}"`, o.y);
  fits("block below slide edge", o.y + o.h, H - 0.25);
  s.addShape(card(o.x, o.y, o.w, o.h, o.dark).shape, card(o.x, o.y, o.w, o.h, o.dark));
  const pad = 0.18;
  let cy = o.y + pad;
  if (o.tag) {
    s.addText(o.tag, { x: o.x + pad, y: cy, w: o.w - pad * 2, h: 0.18,
      fontFace: MONO, fontSize: 6.5, charSpacing: 1, color: o.dark ? ON_DARK_2 : INK3,
      isTextBox: true, margin: 0, valign: "middle" });
    cy += 0.24;
  }
  const bw = o.w - pad * 2;
  const headH = estLines(o.head, bw, 11, true) * lineH(11, 1.05);
  s.addText(o.head, { x: o.x + pad, y: cy, w: bw, h: headH,
    fontFace: SANS, fontSize: 11, bold: true, color: o.dark ? WHITE : INK,
    isTextBox: true, margin: 0, valign: "top" });
  cy += headH + 0.07;
  const avail = o.y + o.h - cy - pad;
  if (o.body) fits(`block "${o.head}" body`, estH(o.body, bw, 8.8, false, 1.2), avail);
  const BULLET_INDENT = 0.35;
  if (o.bullets) fits(`block "${o.head}" bullets`,
    o.bullets.reduce((n, b) => n + estH(b, bw - BULLET_INDENT, 8.8, false, 1.18), 0)
      + o.bullets.length * 0.06, avail);
  if (o.body) s.addText(o.body, { x: o.x + pad, y: cy, w: o.w - pad * 2, h: o.y + o.h - cy - pad,
    fontFace: SANS, fontSize: 8.8, color: o.dark ? ON_DARK : INK2,
    lineSpacingMultiple: 1.2, isTextBox: true, margin: 0, valign: "top" });
  if (o.bullets) s.addText(
    o.bullets.map((b, i) => ({ text: b, options: { bullet: { code: "2013" }, breakLine: i < o.bullets.length - 1 } })),
    { x: o.x + pad, y: cy, w: o.w - pad * 2, h: o.y + o.h - cy - pad,
      fontFace: SANS, fontSize: 8.8, color: o.dark ? ON_DARK : INK2,
      lineSpacingMultiple: 1.18, paraSpaceAfter: 4, isTextBox: true, margin: 0, valign: "top" });
}

// label / figure / description, separated by hairlines.
function rows(s, items, y0, rowH) {
  clearsTitle("rows", y0);
  fits("rows below slide edge", y0 + items.length * rowH, H - 0.25);
  items.forEach((it, i) => {
    const y = y0 + i * rowH;
    s.addShape(pres.ShapeType.line, { x: M, y, w: CW, h: 0,
      line: { color: RULE, width: 0.75 } });
    s.addText(it.k, { x: M, y: y + 0.10, w: 1.35, h: 0.24, fontFace: MONO, fontSize: 6.5,
      charSpacing: 1, color: INK3, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(it.v, { x: M + 1.45, y: y + 0.07, w: 1.85, h: 0.30, fontFace: SANS,
      fontSize: 13, bold: true, color: INK, isTextBox: true, margin: 0, valign: "middle" });
    // The citation is a claim about provenance, not part of the sentence, so it
    // gets its own line in mono rather than running on from the description.
    fits(`row "${it.k}" description`,
      estH(it.d, CW - 3.45, 8.5, false, 1.18) + (it.src ? 0.15 : 0), rowH - 0.16);
    s.addText([{ text: it.d, options: { breakLine: !!it.src } },
               ...(it.src ? [{ text: it.src, options: { fontFace: MONO, fontSize: 6.5, color: INK3 } }] : [])],
      { x: M + 3.45, y: y + 0.08, w: CW - 3.45, h: rowH - 0.16,
        fontFace: SANS, fontSize: 8.5, color: INK2, lineSpacingMultiple: 1.18,
        isTextBox: true, margin: 0, valign: "top" });
  });
  s.addShape(pres.ShapeType.line, { x: M, y: y0 + items.length * rowH, w: CW, h: 0,
    line: { color: RULE, width: 0.75 } });
}

function divider(n, name, line) {
  const s = newSlide(); bg(s, true);
  s.addText("SECTION " + n, { x: M, y: 1.85, w: CW, h: 0.24, fontFace: MONO,
    fontSize: 9, charSpacing: 1.6, color: ON_DARK_2, isTextBox: true, margin: 0 });
  s.addText(name, { x: M, y: 2.18, w: CW, h: 0.85, fontFace: SANS, fontSize: 40,
    bold: true, color: WHITE, isTextBox: true, margin: 0, valign: "top" });
  s.addText(line, { x: M, y: 3.12, w: 6.2, h: 0.4, fontFace: SANS, fontSize: 11,
    color: ON_DARK, isTextBox: true, margin: 0, valign: "top" });
  s.addText("SQRLANE", { x: M, y: H - 0.62, w: 3, h: 0.24, fontFace: MONO, fontSize: 7,
    charSpacing: 1.4, color: ON_DARK_2, isTextBox: true, margin: 0, valign: "middle" });
  return s;
}

/* ============================ 01 · COVER ============================ */
{
  const s = newSlide(); bg(s, true);
  s.addText([{ text: "SQRLANE", options: { bold: true, color: WHITE } },
             { text: '   "SQUARE LANE"', options: { color: ON_DARK_2 } }],
    { x: M, y: 0.45, w: CW, h: 0.24, fontFace: MONO, fontSize: 9, charSpacing: 1.5,
      isTextBox: true, margin: 0, valign: "middle" });
  s.addText("Trade-lane risk,\ndecided.", { x: M, y: 1.45, w: 6.4, h: 1.5,
    fontFace: SANS, fontSize: 40, bold: true, color: WHITE,
    lineSpacingMultiple: 0.98, isTextBox: true, margin: 0, valign: "top" });
  s.addText("Agents that sit on top of the forwarder's TMS — watch everything that moves a lane, decide what to do about each booking, draft the mail, and queue the change back onto the record. A person approves. Nothing sends itself.",
    { x: M, y: 3.12, w: 6.0, h: 0.95, fontFace: SANS, fontSize: 10.5, color: ON_DARK,
      lineSpacingMultiple: 1.28, isTextBox: true, margin: 0, valign: "top" });
  s.addText("01  WHAT      02  WHY      03  HOW      04  TEAM",
    { x: M, y: H - 0.72, w: 6, h: 0.26, fontFace: MONO, fontSize: 7.5, charSpacing: 1.1,
      color: ON_DARK_2, isTextBox: true, margin: 0, valign: "middle" });
  s.addText("ABIR KHAN  ·  CONFIDENTIAL", { x: W - M - 3, y: H - 0.72, w: 3, h: 0.26,
    fontFace: MONO, fontSize: 7.5, charSpacing: 1.1, color: ON_DARK_2, align: "right",
    isTextBox: true, margin: 0, valign: "middle" });
}

/* ============================== 01 · WHAT ============================== */
divider("01", "The What", "The problem, and what it costs.");

{ // the claim
  const s = newSlide(); bg(s);
  eyebrow(s, "01 WHAT", "THE STATUS QUO IS MANUAL, AND IT IS EXPENSIVE");
  const top = title(s, "European freight forwarding still runs on people doing the data work by hand.", { size: 23, w: 8.4 });
  const w = 2.83, g = 0.21;
  stat(s, { x: M, y: top, w, h: 1.95, n: "€3.4bn", unit: "a year", dark: true, nSize: 24,
    label: "the annual labour value of the work being done by hand across the European market.",
    src: "SQRLANE ANALYSIS" });
  block(s, { x: M + w + g, y: top, w, h: 1.95, head: "No product problem",
    body: "The software to run a forwarding desk exists. Buying more of it does not remove the hours, because the hours are not going into the software. They are going into moving information towards it." });
  block(s, { x: M + (w + g) * 2, y: top, w, h: 1.95, head: "A labour problem nobody priced",
    body: "We are not displacing a competing tool. We are displacing spreadsheets and hours — a harder sale to start, and a far larger one to finish." });
  s.addText([{ text: "Every hour on the next four slides is someone ", options: { color: INK2 } },
             { text: "carrying information towards a record", options: { bold: true, color: INK } },
             { text: ", by hand, because nothing else will.", options: { color: INK2 } }],
    { x: M, y: top + 2.14, w: 8.4, h: 0.4, fontFace: SANS, fontSize: 10.5,
      lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top" });
}

{ // what the work actually is
  const s = newSlide(); bg(s);
  eyebrow(s, "01 WHAT", "WHAT THE WORK ACTUALLY IS");
  const top = title(s, "Three jobs, done by hand, on every single shipment.");
  const w = 2.83, g = 0.21;
  block(s, { x: M, y: top, w, h: 1.55, tag: "01", head: "Quoting",
    body: "Rates rebuilt by hand for every enquiry, across carriers that publish nothing in a common format." });
  block(s, { x: M + w + g, y: top, w, h: 1.55, tag: "02", head: "Track and trace",
    body: "Status chased by email and phone, then retyped into the system so the customer can be told." });
  block(s, { x: M + (w + g) * 2, y: top, w, h: 1.55, tag: "03", head: "Documents and exceptions",
    body: "Every mismatch escalates to a person, because the system that spots it cannot resolve it." });
  stat(s, { x: M, y: top + 1.75, w: 4.32, h: 1.45, n: "~30 parties", unit: "· 200+ interactions", nSize: 19,
    label: "for one refrigerated shipment from East Africa to Europe.",
    src: "MAERSK SHIPMENT TRACE, 2014" });
  block(s, { x: M + 4.58, y: top + 1.75, w: 4.32, h: 1.45, head: "And that was 2014",
    body: "Before team chat and messaging apps became operational infrastructure in freight. The interactions have not reduced. The channels carrying them have multiplied." });
}

{ // where the hours go
  const s = newSlide(); bg(s);
  eyebrow(s, "01 WHAT", "WHERE THE HOURS ACTUALLY GO");
  const top = title(s, "Sixty percent of the day is spent carrying information, not deciding anything.", { size: 23, w: 8.4 });
  stat(s, { x: M, y: top, w: 4.32, h: 2.05, n: "60", unit: "%", dark: true, nSize: 26,
    label: "of the working day goes to coordination — chasing status, searching for information, switching between apps. Only 40% goes to the skilled work.",
    src: "ASANA, ANATOMY OF WORK INDEX 2022" });
  block(s, { x: M + 4.58, y: top, w: 4.32, h: 2.05, head: "The five things that eat it",
    bullets: ["Finding it. Which app, whose thread, which version.",
              "Retyping it. Into the system, by hand.",
              "Deciding what is true. Three places, three versions.",
              "Switching. Around 25 times a day, across ten apps.",
              "One person holding it. They take leave and the shipment stalls."] });
  s.addText([{ text: "Coordination that needs ", options: { color: INK2 } },
             { text: "judgement", options: { bold: true, color: INK } },
             { text: " — negotiating a rate, deciding a reroute — is what the forwarder sells. Coordination that only ", options: { color: INK2 } },
             { text: "carries information", options: { bold: true, color: INK } },
             { text: " from one place to another is not. We take the second.", options: { color: INK2 } }],
    { x: M, y: top + 2.24, w: 8.4, h: 0.62, fontFace: SANS, fontSize: 10.5,
      lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top" });
  note(s, "The third one is the only one that costs money rather than time. A surcharge agreed in a chat that never reaches the invoice is paid by the forwarder.", 4.94);
}

{ // why the record is never right
  const s = newSlide(); bg(s);
  eyebrow(s, "01 WHAT", "WHY THE RECORD IS NEVER RIGHT");
  const top = title(s, "A booking's true state is assembled in someone's head. The system holds an old, partial copy.", { size: 23, w: 8.4 });
  const w = 2.83, g = 0.21;
  stat(s, { x: M, y: top, w, h: 1.95, n: "under 40", unit: "%", nSize: 22,
    label: "of freight forwarders use a forwarding management system at all. Only 23% have digitised three quarters of their processes.",
    src: "MAGAYA 2025 — 71 FORWARDERS, NOV 2024" });
  stat(s, { x: M + w + g, y: top, w, h: 1.95, n: "1,300", unit: "+ a day", nSize: 24,
    label: "emails filed by hand by one chartering desk, before they changed how it worked.",
    src: "VITERRA, VIA SEDNA" });
  stat(s, { x: M + (w + g) * 2, y: top, w, h: 1.95, n: "~10", unit: "apps", nSize: 24,
    label: "and about 25 switches between them, per person per day — costing four hours a week just re-orienting.",
    src: "ASANA, ANATOMY OF WORK INDEX 2022" });
  s.addText([{ text: "The booking is agreed over email. The rate is amended in a chat. The carrier sends an exception notice somewhere else again. ", options: { color: INK2 } },
             { text: "None of it reaches the record on its own.", options: { bold: true, color: INK } },
             { text: " A person carries it across, one message at a time.", options: { color: INK2 } }],
    { x: M, y: top + 2.14, w: 8.4, h: 0.62, fontFace: SANS, fontSize: 10.5,
      lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top" });
}

{ // why it persists
  const s = newSlide(); bg(s);
  eyebrow(s, "01 WHAT", "WHO HAS IT, AND WHY IT PERSISTS");
  const top = title(s, "Nobody has fixed it because hiring works.");
  const w = 2.83, g = 0.21;
  block(s, { x: M, y: top, w, h: 1.85, tag: "01", head: "The substitute is headcount",
    body: "They add people when volume grows, because there is nothing on the market that does the work." });
  block(s, { x: M + w + g, y: top, w, h: 1.85, tag: "02", head: "Nothing to integrate with",
    body: "Most forwarders have no system of record to connect to. And the channels the work lives in are conversations, not systems — so nobody connected them." });
  block(s, { x: M + (w + g) * 2, y: top, w, h: 1.85, dark: true, tag: "03", head: "So cost scales with volume",
    body: "Winning a bigger customer means hiring against it. The margin problem gets worse exactly when the business gets better." });
  s.addText([{ text: "That last line is the whole problem. It is not an efficiency story — ", options: { color: INK2 } },
             { text: "it is a ceiling on the business", options: { bold: true, color: INK } },
             { text: ", and it is the version a finance director acts on.", options: { color: INK2 } }],
    { x: M, y: top + 2.04, w: 8.4, h: 0.62, fontFace: SANS, fontSize: 10.5,
      lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top" });
}

/* =============================== 02 · WHY =============================== */
divider("02", "The Why", "The market, and the gap in it.");

{ // the gap
  const s = newSlide(); bg(s);
  eyebrow(s, "02 WHY", "THE GAP — TWO MATURE CATEGORIES, AND A PERSON BETWEEN THEM");
  title(s, "One side alerts. The other side executes. Nobody closes the distance.", { size: 25, w: 8.4 });
  const w = 2.83, g = 0.21, y = 1.74, h = 2.68;
  block(s, { x: M, y, w, h, tag: "CATEGORY ONE — RISK", head: "Risk platforms",
    bullets: ["Everstream, Interos, Resilinc, Prewave.",
              "They stop at the alert. They do not decide, and they never touch a booking.",
              "They mostly read the same wires as each other.",
              "Enterprise-priced — out of reach for the mid-market."] });
  block(s, { x: M + w + g, y, w, h, dark: true, tag: "THE GAP", head: "The desk",
    body: "A person reads the alert, works out which bookings it touches, decides reroute or hold, writes two mails, and re-keys the consequence into the TMS — one booking at a time.\n\nThis is the manual bridge. It is where the hours go, and it is what SQRlane is." });
  block(s, { x: M + (w + g) * 2, y, w, h, tag: "CATEGORY TWO — EXECUTION", head: "TMS & visibility",
    bullets: ["CargoWise, Riege Scope, Descartes, Transporeon, project44.",
              "They hold the booking and move it — after someone has decided it should move.",
              "They do not watch the world.",
              "Deeply embedded, and staying. Not a rip-and-replace target."] });
  note(s, "Named for positioning only. None of these systems is connected to SQRlane today — no vendor, no credential, no endpoint, and nothing is ever written. The TMS layer in the current build is a demo connector.", 4.58);
}

{ // market
  const s = newSlide(); bg(s);
  eyebrow(s, "02 WHY", "MARKET");
  title(s, "We are not displacing a competing tool. We are displacing spreadsheets and hours.", { size: 23, w: 8.4 });
  rows(s, [
    { k: "THE BUDGET", v: "€3.4bn / yr", d: "Annual labour value of the manual data work across European freight forwarding — the budget an agent that does that work is paid out of, not the industry's €208.1bn turnover.", src: "SQRLANE ANALYSIS   ·   TURNOVER: TRANSPORT INTELLIGENCE, 2025" },
    { k: "SAM", v: "19,000+ firms", d: "European forwarding, logistics and customs companies, employing 1,000,000+ staff — the desks this software would sit on.", src: "CLECAT" },
    { k: "BEACHHEAD", v: "213 companies", d: "Named, in DACH and Benelux; 1,479 in the full ICP. A finite list, not a segment estimate — big enough to feel the re-keying, too small to employ a risk analyst.", src: "SQRLANE ANALYSIS" },
    { k: "SOM", v: "[ €n ] ARR", d: "[ n ] accounts × [ €n ] ACV by [ year ]. Priced per seat on the desk, not per shipment." },
  ], 1.66, 0.74);
  note(s, "The €3.4bn and the target-company counts are our own analysis, not third-party research — say so if asked, and be ready to show the working. Fill the SOM row with a bottom-up ACV you can defend, then delete this line.", 4.80);
}

{ // why now / what holds
  const s = newSlide(); bg(s);
  eyebrow(s, "02 WHY", "WHY NOW, AND WHAT HOLDS");
  title(s, "Three things became true at once.");
  const w = 2.83, g = 0.21, y = 1.30, h = 1.85;
  block(s, { x: M, y, w, h, tag: "01", head: "Disruption is now constant",
    body: "Red Sea diversions, Rhine low water, port strikes, tariff filings. A desk that absorbed one bad quarter a year now absorbs one a month." });
  block(s, { x: M + w + g, y, w, h, tag: "02", head: "Reasoning got cheap per booking",
    body: "Per-token inference means a judgement call on every shipment costs cents, not a data-science team. Three years ago this product was not affordable." });
  block(s, { x: M + (w + g) * 2, y, w, h, tag: "03", head: "The TMS finally has a door",
    body: "Modern forwarding systems expose the booking over an API. The decision can be written back onto the record instead of typed onto it." });
  s.addText("What holds, once we are in", { x: M, y: 3.34, w: CW, h: 0.26, fontFace: SANS,
    fontSize: 11, bold: true, color: INK, isTextBox: true, margin: 0, valign: "middle" });
  [["The write-back is the moat", "Alerting is commoditised. Being trusted to change a booking is not — it is earned per account, over months of approved decisions, and does not transfer."],
   ["The reasoning trail compounds", "Every decision records why it was made and whether a human approved it. That history is the customer's, and it makes the next decision better."],
   ["Breadth is hard to copy cheaply", "42 free sources across six families, read together every run. Any one is easy. All of them, concurrently, without one slow source stalling the cycle, is the engineering."]]
    .forEach(([head, body], i) => {
      const x = M + i * (w + g);
      s.addText(head, { x, y: 3.66, w, h: 0.22, fontFace: SANS, fontSize: 9.5, bold: true,
        color: INK, isTextBox: true, margin: 0, valign: "middle" });
      s.addText(body, { x, y: 3.90, w, h: 0.82, fontFace: SANS, fontSize: 8.5, color: INK2,
        lineSpacingMultiple: 1.2, isTextBox: true, margin: 0, valign: "top" });
    });
  note(s, "We do not claim to be first to alerting — that category is a decade old and crowded. The claim is narrower and more defensible: first to carry the decision all the way back onto the booking.", 4.82);
}

/* =============================== 03 · HOW =============================== */
divider("03", "The How", "The loop, and what we sell.");

{ // the loop
  const s = newSlide(); bg(s);
  eyebrow(s, "03 HOW", "THE LOOP");
  title(s, "It opens and closes in the same place: the booking.");
  // Both ends say TMS on purpose: the loop closes where it opened, and calling
  // the last node something else made it read as a second system.
  const boxes = [["TMS", "read the book", true], ["Watch", "42 sources, six families", false],
                 ["Decide", "reroute · hold · on plan", false], ["Draft", "carrier · customer", false],
                 ["TMS", "queued, not written", true]];
  const bw = 1.62, bg2 = 0.21, by = 1.70, bh = 1.00;
  boxes.forEach(([head, sub, dark], i) => {
    const x = M + i * (bw + bg2);
    s.addShape(card(x, by, bw, bh, dark).shape, card(x, by, bw, bh, dark));
    s.addText(head, { x, y: by + 0.22, w: bw, h: 0.24, fontFace: SANS, fontSize: 11,
      bold: true, color: dark ? WHITE : INK, align: "center", isTextBox: true, margin: 0, valign: "middle" });
    s.addText(sub, { x, y: by + 0.50, w: bw, h: 0.22, fontFace: MONO, fontSize: 6.5,
      color: dark ? ON_DARK_2 : INK3, align: "center", isTextBox: true, margin: 0, valign: "middle" });
    if (i < boxes.length - 1) s.addShape(pres.ShapeType.line, {
      x: x + bw + 0.03, y: by + bh / 2, w: bg2 - 0.06, h: 0,
      line: { color: INK3, width: 1, endArrowType: "triangle" } });
  });
  // The return leg: down from the last box, back along, and up into the TMS.
  const lastCx = M + 4 * (bw + bg2) + bw / 2, firstCx = M + bw / 2, ry = by + bh + 0.45;
  // Drawn in ink at full weight: the return leg is the claim, not a connector.
  // The horizontal run is split so its label sits in a gap rather than on an
  // opaque box that would have to match the slide colour.
  const GAP_L = 3.85, GAP_R = 6.20;
  s.addShape(pres.ShapeType.line, { x: lastCx, y: by + bh, w: 0, h: 0.45, line: { color: INK, width: 1.25 } });
  s.addShape(pres.ShapeType.line, { x: GAP_R, y: ry, w: lastCx - GAP_R, h: 0, line: { color: INK, width: 1.25 } });
  s.addShape(pres.ShapeType.line, { x: firstCx, y: ry, w: GAP_L - firstCx, h: 0, line: { color: INK, width: 1.25 } });
  s.addShape(pres.ShapeType.line, { x: firstCx, y: by + bh, w: 0, h: 0.45,
    line: { color: INK, width: 1.25, beginArrowType: "triangle" } });
  s.addText("every action, back onto the same booking",
    { x: GAP_L, y: ry - 0.10, w: GAP_R - GAP_L, h: 0.20, fontFace: SANS, fontSize: 8,
      bold: true, color: INK, align: "center", isTextBox: true, margin: 0, valign: "middle" });
  s.addText("exception flag  ·  discharge port  ·  routing code  ·  revised ETA  ·  communication log",
    { x: M, y: ry + 0.24, w: CW, h: 0.22, fontFace: MONO, fontSize: 7.5, color: INK3,
      align: "center", isTextBox: true, margin: 0, valign: "middle" });
  s.addText("QUEUED — not written.  Waiting on a person.",
    { x: M, y: ry + 0.46, w: CW, h: 0.22, fontFace: MONO, fontSize: 7.5, bold: true, color: INK,
      align: "center", isTextBox: true, margin: 0, valign: "middle" });
  s.addText([{ text: "Connect, don't migrate.", options: { bold: true, color: INK } },
             { text: "  The bookings are read out of the system of record, the agents decide against those records, and every action is written back onto them. The forwarder keeps their TMS, their data and their process — nothing to rip out.", options: { color: INK2 } }],
    { x: M, y: 4.14, w: 8.4, h: 0.72, fontFace: SANS, fontSize: 10,
      lineSpacingMultiple: 1.25, isTextBox: true, margin: 0, valign: "top" });
}

{ // what it watches
  const s = newSlide(); bg(s);
  eyebrow(s, "03 HOW", "WHAT IT WATCHES");
  title(s, "Not a news monitor. 42 free, keyless sources in six families, read together on every run.", { size: 23, w: 8.4 });
  const fam = [["31", "News — regional broadcasters on the corridors' doorsteps, the international wires and the trade press."],
               ["3", "River gauges — water levels on the waterways a barge leg depends on."],
               ["3", "Weather & sea state — gusts over the crane, wave height on the corridor."],
               ["2", "Seismic & natural hazards — each reading mapped to the nearest chokepoint, or dropped."],
               ["2", "Government filings — tariff, sanctions, customs and port-security registers."],
               ["1", "Reference rates — the rate a reroute is actually billed at."]];
  const fw = 2.83, fg = 0.21, fh = 0.76;
  fam.forEach(([n, label], i) => {
    const x = M + (i % 3) * (fw + fg), y = 1.66 + Math.floor(i / 3) * (fh + 0.18);
    s.addShape(card(x, y, fw, fh, false).shape, card(x, y, fw, fh, false));
    s.addText(n, { x: x + 0.14, y: y + 0.08, w: 0.62, h: fh - 0.16, fontFace: SANS,
      fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(label, { x: x + 0.78, y: y + 0.09, w: fw - 0.92, h: fh - 0.18, fontFace: SANS,
      fontSize: 7.6, color: INK2, lineSpacingMultiple: 1.15, isTextBox: true, margin: 0, valign: "middle" });
  });
  block(s, { x: M, y: 3.56, w: 4.32, h: 1.20, head: "Prose goes to the model. Numbers never do.",
    body: "A gust, a wave height, a magnitude and a water level are classified by a threshold. Cheaper, repeatable, and it cannot hallucinate a severity." });
  block(s, { x: M + 4.58, y: 3.56, w: 4.32, h: 1.20, head: "Nothing is load-bearing",
    body: "Every source is its own function inside a shared budget, and the families are read concurrently. One that is down or slow is reported failed and skipped." });
  note(s, "Reading close to the event is why a disruption often lands here before the international wires carry it. Reading widely is why it lands here at all when it never becomes a headline.", 4.90);
}

{ // scope
  const s = newSlide(); bg(s);
  eyebrow(s, "03 HOW", "SCOPE — WHAT THE AGENTS ACTUALLY DO");
  title(s, "One desk, covered.");
  s.addText("Every output is a change to a booking.", { x: M, y: 1.06, w: CW, h: 0.26,
    fontFace: SANS, fontSize: 11, color: INK2, isTextBox: true, margin: 0, valign: "middle" });
  const w = 2.83, g = 0.21, h = 1.80;
  const items = [
    { tag: "RUNNING TODAY", head: "Risk · Routing · Comms", body: "Watches six families and classifies what matters to a lane. Weighs slack against added transit and expected delay — reroute, hold or on plan, with the reasoning recorded." },
    { tag: "COMMERCIAL", head: "RFQ · Quoting · Rate", body: "Inbound rate request read into structured fields, priced against the lane including the surcharge a live disruption adds, and answered with a drafted quote on the booking." },
    { tag: "INBOUND", head: "Inbox · Documents", body: "Carrier and customer mail triaged: intent classified, linked to the booking, a reply drafted where one is warranted — and none where it is not. Documents read, checked and filed." },
    { tag: "EXECUTION", head: "Booking · Milestones", body: "The amendment a decision forces: a reroute is a change of discharge port, a hold is a hold at the load port. Milestones tracked and pushed onto the record." },
    { tag: "FINANCE & COMPLIANCE", head: "Invoice · Customs", body: "Carrier invoice reconciled against the rate agreed — the surcharge never quoted is the finding. A reroute moves the country of entry, so it escalates rather than files." },
    { tag: "THE GATE", head: "Nothing sends, nothing writes", dark: true, body: "Every mail is DRAFT — not sent. Every record change is QUEUED — not written. One approval queue, grouped by the booking it came from." },
  ];
  items.forEach((it, i) => block(s, Object.assign({},
    it, { x: M + (i % 3) * (w + g), y: 1.48 + Math.floor(i / 3) * (h + 0.20), w, h })));
}

{ // where the build is
  const s = newSlide(); bg(s);
  eyebrow(s, "03 HOW", "WHERE THE BUILD ACTUALLY IS");
  title(s, "What is real today, said plainly.");
  rows(s, [
    { k: "REAL", v: "Risk detection", d: "All 42 sources are read live, on every run, against the real internet. The source count on screen is counted from the run, not asserted." },
    { k: "REAL", v: "The reasoning", d: "Routing and comms decisions are made by the model on the run, with a recorded trail and a deterministic fallback that is badged when it is used." },
    { k: "DEMO", v: "The TMS connector", d: "Both directions are modelled and the read is the only door to the book — but no TMS is contacted. No vendor, no credential, no endpoint. A write-back is a described change, and it stays one." },
    { k: "SYNTHETIC", v: "The bookings", d: "Seven authored shipments, so a disruption can be shown on demand instead of waited for — injected in the same format a live event arrives in, through the same pipeline." },
    { k: "NEXT", v: "First live TMS", d: "[ design partner ] — the integration and trust wall is the real work, and the single highest-value thing on the other side of it." },
  ], 1.30, 0.68);
  note(s, "We show this slide in the room. A demo that overclaims gets found out in the first question, and a forwarder who has been sold vapour before will ask it.", 4.88);
}

/* ============================== 04 · TEAM ============================== */
divider("04", "The Team", "Who is building it.");

{ // team
  const s = newSlide(); bg(s);
  eyebrow(s, "04 TEAM", "FOUNDERS");
  title(s, "Founders");
  const w = 4.32, g = 0.26;
  [["Abir Khan", "Co-founder & [ role ]"], ["[ Full name ]", "Co-founder & [ role ]"]].forEach(([name, role], i) => {
    const x = M + i * (w + g), y = 1.30, h = 1.95;
    s.addShape(card(x, y, w, h, false).shape, card(x, y, w, h, false));
    s.addText(role, { x: x + 0.18, y: y + 0.16, w: w - 0.36, h: 0.2, fontFace: MONO,
      fontSize: 6.5, charSpacing: 1, color: INK3, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(name, { x: x + 0.18, y: y + 0.40, w: w - 0.36, h: 0.32, fontFace: SANS,
      fontSize: 16, bold: true, color: name.startsWith("[") ? INK3 : INK,
      isTextBox: true, margin: 0, valign: "middle" });
    s.addText(["[ One line on what they own here — product, commercial or engineering ]",
               "[ Most relevant role, company, years ]",
               "[ The thing that makes them credible on this specific problem ]"]
      .map((b, j) => ({ text: b, options: { bullet: { code: "2013" }, breakLine: j < 2 } })),
      { x: x + 0.18, y: y + 0.78, w: w - 0.36, h: 0.92, fontFace: MONO, fontSize: 7.5,
        color: INK3, lineSpacingMultiple: 1.2, paraSpaceAfter: 4, isTextBox: true, margin: 0, valign: "top" });
  });
  block(s, { x: M, y: 3.46, w, h: 1.20, head: "Why this team, for this problem",
    body: "[ The one sentence an investor repeats to their partner. Ideally: we have run this desk / we have shipped this integration / we have sold to this buyer before. ]" });
  block(s, { x: M + w + g, y: 3.46, w, h: 1.20, head: "Advisors & design partners",
    body: "[ Name — Head of Ops at a forwarder, or the operator who validated the problem ]\n[ Name — domain or go-to-market advisor ]" });
  note(s, "Keep it to three bullets each. On a team slide the reader is asking one question — why you — and a fourth bullet has never answered it.", 4.82);
}

/* =============================== CLOSE =============================== */
{
  const s = newSlide(); bg(s, true);
  s.addText([{ text: "SQRLANE", options: { bold: true, color: WHITE } },
             { text: '   "SQUARE LANE"', options: { color: ON_DARK_2 } }],
    { x: M, y: 0.42, w: CW, h: 0.24, fontFace: MONO, fontSize: 9, charSpacing: 1.5,
      isTextBox: true, margin: 0, valign: "middle" });
  s.addText("Risk, decision, communication and the record — closed, on the booking.",
    { x: M, y: 1.05, w: 7.2, h: 1.0, fontFace: SANS, fontSize: 27, bold: true, color: WHITE,
      lineSpacingMultiple: 1.04, isTextBox: true, margin: 0, valign: "top" });
  const w = 2.83, g = 0.21, y = 2.25, h = 1.60;
  const OUTLINE = "3D3D3D";
  [["THE ASK", "[ €n ]", "[ pre-seed / seed ], for [ n ] months of runway."],
   ["BUYS", "", "[ First live TMS integration with a design partner ]\n[ Two more engineers ]\n[ n paying accounts by month n ]"],
   ["TALK TO US", "", "[ contact@sqrlane.com ]\n[ sqrlane.com ]\n\nThe working demo runs in under two minutes, on command. Ask for it."]]
    .forEach(([tag, big, body], i) => {
      const x = M + i * (w + g), invert = i === 2;   // the contact card is the one to land on
      s.addShape(card(x, y, w, h, !invert, invert ? WHITE : OUTLINE).shape,
                 card(x, y, w, h, !invert, invert ? WHITE : OUTLINE));
      s.addText(tag, { x: x + 0.18, y: y + 0.15, w: w - 0.36, h: 0.2, fontFace: MONO,
        fontSize: 6.5, charSpacing: 1, color: invert ? INK3 : ON_DARK_2,
        isTextBox: true, margin: 0, valign: "middle" });
      if (big) s.addText(big, { x: x + 0.18, y: y + 0.40, w: w - 0.36, h: 0.36, fontFace: SANS,
        fontSize: 20, bold: true, color: ON_DARK_2, isTextBox: true, margin: 0, valign: "middle" });
      s.addText(body, { x: x + 0.18, y: y + (big ? 0.82 : 0.42), w: w - 0.36, h: h - (big ? 1.0 : 0.6),
        fontFace: big ? SANS : MONO, fontSize: big ? 8.5 : 7.5,
        color: invert ? INK2 : ON_DARK, lineSpacingMultiple: 1.3,
        isTextBox: true, margin: 0, valign: "top" });
    });
  s.addText("SOURCES  ·  Maersk shipment trace, 2014  ·  CLECAT  ·  Asana, Anatomy of Work Index 2022  ·  Magaya, State of Digitization in Freight Forwarding 2025  ·  Viterra via Sedna  ·  Transport Intelligence, 2025  ·  SQRlane analysis.  No performance, accuracy or traction figure about SQRlane appears in this deck, because none has been measured.",
    { x: M, y: H - 1.05, w: CW, h: 0.62, fontFace: MONO, fontSize: 6.2, color: ON_DARK_2,
      lineSpacingMultiple: 1.3, isTextBox: true, margin: 0, valign: "bottom" });
}

pres.writeFile({ fileName: "SQRlane_Pitch.pptx" }).then(f => {
  console.log("wrote", f, "—", SLIDE, "slides");
  if (WARNINGS.length) {
    console.log("\n" + WARNINGS.length + " FIT WARNINGS:");
    WARNINGS.forEach(w => console.log("  " + w));
  } else console.log("no fit warnings");
});
