const pptxgen = require("pptxgenjs");
const fs = require("fs");
const { applyTheme } = require("/home/amir/.claude/skills/synced/529f45dc-60fe-40f5-b0d7-e90bed89f697_014488a3-6d47-4f18-a988-2e0644732b5a/pptx/scripts/apply_theme.js");

const THEME = { name: "Load Safety Gate", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B1F23", lt1: "FFFFFF", dk2: "3A4248", lt2: "EEF0EC", accent1: "F2B705", accent2: "1F5F8B", accent3: "2A8A4A", accent4: "E03A3A", accent5: "8A96A0", accent6: "C9781A", hlink: "1F5F8B", folHlink: "3A4248" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Team Destroyerrrrs"; pres.title = "Load Safety Gate";
const C = pres.SchemeColor;
const FOOT = "Load Safety Gate  ·  Team Destroyerrrrs  ·  Computer Vision track";

pres.defineSlideMaster({ title: "DARK", background: { color: THEME.colors.dk1 }, objects: [
  { text: { text: FOOT, options: { x: 0.5, y: 7.05, w: 9, h: 0.3, fontSize: 10, color: THEME.colors.accent5, margin: 0 } } } ],
  slideNumber: { x: 12.3, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: THEME.colors.accent5 } });
pres.defineSlideMaster({ title: "LIGHT", background: { color: THEME.colors.lt1 }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 12.3, h: 0.8, fontSize: 32, bold: true, color: THEME.colors.dk1, margin: 0, valign: "middle" }, text: "" } },
  { text: { text: FOOT, options: { x: 0.5, y: 7.05, w: 9, h: 0.3, fontSize: 10, color: THEME.colors.accent5, margin: 0 } } } ],
  slideNumber: { x: 12.3, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: THEME.colors.accent5 } });

const TB = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1 }, o));
const pill = (s, text, x, y, w, color, fg) => { s.addShape(pres.ShapeType.roundRect, { x, y, w, h: 0.5, fill: { color }, rectRadius: 0.25, line: { color, width: 0 } }); TB(s, text, { x, y, w, h: 0.5, align: "center", valign: "middle", bold: true, color: fg || C.background1, fontSize: 14 }); };
const card = (s, x, y, w, h, title, body, accent) => {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2, width: 0 } });
  s.addShape(pres.ShapeType.ellipse, { x: x + 0.2, y: y + 0.2, w: 0.42, h: 0.42, fill: { color: accent || THEME.colors.accent1 }, line: { color: accent || THEME.colors.accent1, width: 0 } });
  TB(s, title, { x: x + 0.75, y: y + 0.15, w: w - 0.95, h: 0.5, bold: true, fontSize: 16, valign: "middle" });
  TB(s, body, { x: x + 0.2, y: y + 0.75, w: w - 0.4, h: h - 0.9, fontSize: 13, color: C.text2, valign: "top" });
};
const bullets = (items) => items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
const img = (p) => fs.existsSync(p) ? p : null;

// 1 Title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
TB(s, "Load Safety Gate", { x: 0.7, y: 1.4, w: 11.5, h: 1.2, fontSize: 54, bold: true, color: C.background1, fontFace: THEME.headFontFace });
TB(s, "One photo at the gate. GO or NO-GO before the truck leaves.", { x: 0.7, y: 2.6, w: 11.5, h: 0.7, fontSize: 24, color: THEME.colors.accent1 });
TB(s, "Mode: Startup   ·   Track: Computer Vision   ·   Team Destroyerrrrs", { x: 0.7, y: 3.5, w: 11.5, h: 0.5, fontSize: 16, color: THEME.colors.accent5 });
pill(s, "GO", 0.7, 4.6, 1.6, THEME.colors.accent3); pill(s, "WARN", 2.5, 4.6, 1.6, THEME.colors.accent6); pill(s, "NO-GO", 4.3, 4.6, 1.6, THEME.colors.accent4);
TB(s, "Body roll  ·  Overhang  ·  Height  ·  Plates and people blurred before anything is shown", { x: 0.7, y: 5.3, w: 11.5, h: 0.5, fontSize: 14, color: THEME.colors.accent5 });

// 2 Problem and user
pres.addSection({ title: "Problem" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Problem" });
s.addText("A badly loaded truck is checked by eye, or not at all", { placeholder: "title" });
card(s, 0.5, 1.3, 6.0, 1.25, "Who uses it", "The gate operator or dispatcher at a freight terminal, a fleet depot, or a dealer receiving yard. One photo, one answer, before the truck leaves.", THEME.colors.accent2);
card(s, 0.5, 2.67, 6.0, 1.25, "What goes wrong today", "Shifted or one-sided loads roll over. Overhanging cargo hits bridges, signs and other vehicles. Oversized loads draw fines and stop the truck at the first police post.", THEME.colors.accent4);
card(s, 0.5, 4.04, 6.0, 1.35, "Who pays", "The fleet owner or terminal, per gate. Partner angle: every Toyota and BYD arrives on a car carrier into a Royal Motors yard. Car carriers are the classic over-height and rear-overhang offenders.", THEME.colors.accent3);
card(s, 0.5, 5.51, 6.0, 1.25, "Regulation already exists", "Uzbekistan Decree 342, Annex 2: height 4.0 m, width 2.55 m, rear protrusion 2 m. Nobody measures it at the gate.", THEME.colors.accent1);
const ex1 = img("../eval/out/raw/car_carrier/car_carrier_1967_79_Saviem_SG2_fl_jpg.jpg");
if (ex1) s.addImage({ path: ex1, x: 6.9, y: 1.4, w: 5.9, h: 4.4, sizing: { type: "contain", w: 5.9, h: 4.4 } });
TB(s, "Live output of the deployed pipeline on a licensed test image (Wikimedia Commons, CC BY-SA 4.0).", { x: 6.9, y: 5.9, w: 5.9, h: 0.6, fontSize: 11, color: C.text2 });

// 3 Live demo
pres.addSection({ title: "Demo" });
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Demo" });
TB(s, "Live demo", { x: 0.7, y: 0.5, w: 12, h: 0.8, fontSize: 36, bold: true, color: C.background1, fontFace: THEME.headFontFace });
TB(s, "amir-kuldashev--load-safety-gate-web.modal.run", { x: 0.7, y: 1.4, w: 12, h: 0.7, fontSize: 26, color: THEME.colors.accent1, fontFace: "Courier New" });
TB(s, "Open it on your phone. Take a photo of any truck, or give us one. No login, no app.", { x: 0.7, y: 2.2, w: 12, h: 0.5, fontSize: 18, color: C.background1 });
TB(s, bullets(["Plates and people are pixelated first. The original is never stored.", "Green lines: body vertical edges and the ground line the roll is measured against.", "Red line: cargo beyond the body edge, in centimetres. Magenta: cargo top to ground, in metres.", "Verdict banner, per-check confidence, and the measured latency on CPU.", "When the photo does not allow a measurement the check says so. No guess, ever."]), { x: 0.7, y: 3.0, w: 7.3, h: 3.6, fontSize: 15, color: C.background1, isTextBox: true, margin: 0, valign: "top" });
const ex2 = img("../eval/out/dbg_9.jpg");
if (ex2) s.addImage({ path: ex2, x: 8.3, y: 3.0, w: 4.6, h: 3.6, sizing: { type: "contain", w: 4.6, h: 3.6 } });

// 4 Architecture
pres.addSection({ title: "Technology" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Technology" });
s.addText("A pipeline, not a prompt", { placeholder: "title" });
const steps = [["Photo", "phone or gate camera", THEME.colors.accent5], ["Detect", "YOLO-World boxes: truck, trailer, cargo, car, plate, person. YOLOv8-seg truck mask. Pretrained, no training.", THEME.colors.accent2],
  ["Blur", "plates and people pixelated before storage or display", THEME.colors.accent4], ["Measure", "wheel finder, ground line, body verticals vs scene verticals, scale from 2.55 m body or 1.05 m wheel", THEME.colors.accent1],
  ["Decide", "Decree 342 thresholds; GO, WARN, NO-GO, or CANNOT ASSESS", THEME.colors.accent3], ["Report", "annotated image, checklist, confidence, latency", THEME.colors.dk2]];
steps.forEach((st, i) => { const x = 0.5 + i * 2.1; s.addShape(pres.ShapeType.rect, { x, y: 1.6, w: 1.9, h: 3.3, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2, width: 0 } });
  s.addShape(pres.ShapeType.ellipse, { x: x + 0.65, y: 1.75, w: 0.6, h: 0.6, fill: { color: st[2] }, line: { color: st[2], width: 0 } });
  TB(s, String(i + 1), { x: x + 0.65, y: 1.75, w: 0.6, h: 0.6, align: "center", valign: "middle", bold: true, color: C.background1, fontSize: 14 });
  TB(s, st[0], { x: x + 0.1, y: 2.45, w: 1.7, h: 0.4, bold: true, fontSize: 15, align: "center" });
  TB(s, st[1], { x: x + 0.1, y: 2.9, w: 1.7, h: 1.9, fontSize: 11, color: C.text2, align: "center", valign: "top" });
  if (i < steps.length - 1) s.addShape(pres.ShapeType.rightArrow, { x: x + 1.88, y: 3.05, w: 0.26, h: 0.3, fill: { color: THEME.colors.accent5 }, line: { color: THEME.colors.accent5, width: 0 } }); });
card(s, 0.5, 5.2, 6.0, 1.6, "Ours", "Privacy stage, wheel finder, geometry, decision rules, the 301-image licensed set, the 120-image labelled evaluation, the app and the deployment.", THEME.colors.accent1);
card(s, 6.8, 5.2, 6.0, 1.6, "Borrowed, with attribution", "Two pretrained Ultralytics models (AGPL-3.0). Open-vocabulary prompts, no fine-tuning needed for the demo. Runs on CPU in 0.19 s per image.", THEME.colors.accent5);

// 5 Relative to what
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Technology" });
s.addText("Measured relative to the truck itself, so a phone photo is honest", { placeholder: "title" });
card(s, 0.5, 1.5, 4.0, 3.6, "Body roll", "Horizontal edges converge under perspective, so a level truck looks tilted if you compare top and bottom edges. We use the body's vertical edges instead: left and right halves converge in opposite directions and their mean cancels perspective. Reference: vertical lines in the scene (poles, walls), else the camera vertical at lower confidence.", THEME.colors.accent2);
card(s, 4.65, 1.5, 4.0, 3.6, "Overhang", "Cargo extent beyond the body edge at cargo height. Rear overhang in a side view, side overhang in a rear view. Converted to centimetres with a known object in the same image: body width 2.55 m or wheel diameter 1.05 m.", THEME.colors.accent4);
card(s, 8.8, 1.5, 4.0, 3.6, "Height", "Ground line through the tyre contact points to the top of cargo or body, same scale. Compared with the 4.0 m legal limit.", THEME.colors.accent1);
card(s, 0.5, 5.3, 12.3, 1.4, "Product version", "A fixed gate camera with known position and a reference marker removes the remaining ambiguity. The phone mode you see today is the degraded fallback, and it says CANNOT ASSESS when the view does not support a measurement.", THEME.colors.accent3);

// 6 Quality
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Technology" });
s.addText("Measured on a test set we built", { placeholder: "title" });
const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: THEME.colors.dk2 }, fontSize: 12 } });
const rows1 = [[hdr("Subset"), hdr("Images"), hdr("Truck found"), hdr("Wheels"), hdr("Scale"), hdr("Roll reported")],
  ["Car carriers", "70", "0.89", "0.60", "0.71", "0.21"], ["Flatbeds", "55", "0.87", "0.71", "0.76", "0.27"], ["Semi-trailers", "30", "0.97", "0.70", "0.83", "0.37"], ["Oversized loads", "44", "0.86", "0.50", "0.59", "0.11"], ["Night", "38", "0.97", "0.66", "0.74", "0.45"]];
s.addTable(rows1, { x: 0.5, y: 1.4, w: 6.2, colW: [1.6, 0.9, 1.1, 0.9, 0.8, 0.9], fontSize: 12, color: C.text1, border: { type: "solid", color: THEME.colors.lt2, pt: 1 }, rowH: 0.36 });
TB(s, "Detector hit rate on 301 licensed Commons photos (no labels needed). Night holds up: the truck mask is the most robust stage.", { x: 0.5, y: 3.7, w: 6.2, h: 0.7, fontSize: 11, color: C.text2 });
const rows2 = [[hdr("Check"), hdr("Precision"), hdr("Recall"), hdr("n")], ["Tilted body", "pending", "pending", ""], ["Rear overhang", "pending", "pending", ""], ["Side overhang", "pending", "pending", ""], ["Over height", "pending", "pending", ""], ["Night / rain subset", "pending", "pending", "25"]];
s.addTable(rows2, { x: 7.0, y: 1.4, w: 5.8, colW: [2.2, 1.2, 1.2, 1.2], fontSize: 12, color: C.text1, border: { type: "solid", color: THEME.colors.lt2, pt: 1 }, rowH: 0.36 });
TB(s, "Against 120 hand-labelled images (95 day, 25 night). Numbers come from eval/run_eval.py and are filled in once labelling is complete.", { x: 7.0, y: 3.7, w: 5.8, h: 0.7, fontSize: 11, color: C.text2 });
const stat = (x, big, small) => { TB(s, big, { x, y: 4.7, w: 3.9, h: 0.9, fontSize: 40, bold: true, color: THEME.colors.accent2, fontFace: THEME.headFontFace }); TB(s, small, { x, y: 5.6, w: 3.9, h: 0.8, fontSize: 12, color: C.text2 }); };
stat(0.5, "0.19 s", "per image on 2 CPU cores, measured on the deployed server"); stat(4.7, "< $0.001", "compute per inspection; one warm server about $90 per month"); stat(8.9, "0 faces", "stored. Plates and people pixelated before anything is kept");

// 7 Failure cases
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Technology" });
s.addText("Where it breaks, and what it does instead of guessing", { placeholder: "title" });
const fails = [["../eval/out/raw/overloaded/" + (fs.existsSync("../eval/out/raw/overloaded") ? fs.readdirSync("../eval/out/raw/overloaded")[0] : ""), "Not a truck, or a tiny truck in the frame. Result: CANNOT ASSESS. The overloaded-vehicles category on Commons is mostly carts and motorbikes."],
  ["../eval/out/raw/car_carrier/car_carrier_080625_A_3715G_225_2668149320_jpg.jpg", "Front or three-quarter views foreshorten the body. Roll confidence drops below the floor and the check is skipped."],
  ["../eval/out/raw/night/" + (fs.existsSync("../eval/out/raw/night") ? fs.readdirSync("../eval/out/raw/night")[1] : ""), "Night street with no truck in frame: CANNOT ASSESS. Dark trucks at night give a noisy mask edge and lower roll confidence; cargo the same colour as the body can merge into the mask."]];
fails.forEach((f, i) => { const x = 0.5 + i * 4.15; if (img(f[0])) s.addImage({ path: f[0], x, y: 1.4, w: 3.95, h: 2.9, sizing: { type: "contain", w: 3.95, h: 2.9 } }); TB(s, f[1], { x, y: 4.4, w: 3.95, h: 1.4, fontSize: 12, color: C.text2, valign: "top" }); });
card(s, 0.5, 5.9, 12.3, 0.95, "Design rule", "Every check reports a confidence and is skipped below a floor. A skipped check is shown as such, never as a pass.", THEME.colors.accent6);

// 8 Replication
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Technology" });
TB(s, "The replication test", { x: 0.7, y: 0.5, w: 12, h: 0.8, fontSize: 36, bold: true, color: C.background1, fontFace: THEME.headFontFace });
TB(s, "A weekend with the same tools gets you", { x: 0.7, y: 1.5, w: 5.8, h: 0.5, fontSize: 18, bold: true, color: THEME.colors.accent5 });
TB(s, bullets(["A detector that draws boxes around trucks and cargo", "A prompt to a vision model that says \"looks overloaded\"", "No measurement, no threshold, no number a gate operator can act on"]), { x: 0.7, y: 2.1, w: 5.8, h: 3.5, fontSize: 15, color: C.background1, isTextBox: true, margin: 0, valign: "top" });
TB(s, "What they do not get", { x: 6.9, y: 1.5, w: 5.8, h: 0.5, fontSize: 18, bold: true, color: THEME.colors.accent1 });
TB(s, bullets(["Perspective-safe roll from vertical edges, with a gravity reference in the same image", "Centimetres and metres from a known object in the frame, and a CANNOT ASSESS path", "A decision layer written from Decree 342, the regulation a police post actually applies", "A privacy stage that makes the product legal to pilot", "301 licensed images with hit rates, 120 labelled, and a deployed gate product"]), { x: 6.9, y: 2.1, w: 5.8, h: 4.0, fontSize: 15, color: C.background1, isTextBox: true, margin: 0, valign: "top" });

// 9 Budget and ROI
pres.addSection({ title: "Business" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Business" });
s.addText("Pilot budget and payback, every assumption on the slide", { placeholder: "title" });
const rows3 = [[hdr("Pilot cost, 3 months"), hdr("Amount"), hdr("Assumption")],
  ["Team: 2 engineers + 1 ops, part time", "[confirm]", "local salaries, 3 months"], ["Cameras and mounts, 3 gates", "$600", "$200 per gate, one-off"], ["Hosting", "$270", "one warm CPU server, $90 per month"],
  ["Labelling and data", "$500", "about 40 hours of labelling"], ["Legal and privacy review", "[confirm]", "blur at ingest, no personal data stored"]];
s.addTable(rows3, { x: 0.5, y: 1.4, w: 6.3, colW: [2.9, 1.2, 2.2], fontSize: 12, color: C.text1, border: { type: "solid", color: THEME.colors.lt2, pt: 1 }, rowH: 0.4 });
const rows4 = [[hdr("Avoided loss per year, one fleet"), hdr("Amount"), hdr("Assumption")],
  ["Rollovers prevented", "[confirm]", "cost of one rollover x events avoided"], ["Oversize fines avoided", "[confirm]", "fine x stops per month"], ["Cargo damage claims", "[confirm]", "claims per year x share caught at gate"], ["Operator time", "[confirm]", "minutes per manual walkaround x trucks per day"]];
s.addTable(rows4, { x: 7.0, y: 1.4, w: 5.8, colW: [2.6, 1.1, 2.1], fontSize: 12, color: C.text1, border: { type: "solid", color: THEME.colors.lt2, pt: 1 }, rowH: 0.4 });
card(s, 0.5, 4.6, 6.3, 2.2, "Unit economics", "Price per gate per month, software only. Compute per inspection is below $0.001, so margin is in the subscription, not the inference. One server serves dozens of gates.", THEME.colors.accent2);
card(s, 7.0, 4.6, 5.8, 2.2, "Payback", "Payback months = pilot cost / (avoided loss per month). Fill the [confirm] cells with the fleet's own figures and the formula gives the answer on the spot.", THEME.colors.accent3);

// 10 Next steps
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Business" });
TB(s, "Next steps", { x: 0.7, y: 0.5, w: 12, h: 0.8, fontSize: 36, bold: true, color: C.background1, fontFace: THEME.headFontFace });
const nx = [["Month 1", "Fixed, calibrated camera at one gate. Reference marker removes scale ambiguity. Ten-second video mode."], ["Month 2", "Fine-tune the detector on our labelled set. Add open door, loose strap and missing marking classes."], ["Month 3", "Weighbridge and dispatch integration. Pilot at a Royal Motors receiving yard on incoming car carriers."]];
nx.forEach((n, i) => { const x = 0.7 + i * 4.1; s.addShape(pres.ShapeType.rect, { x, y: 1.7, w: 3.8, h: 3.2, fill: { color: THEME.colors.dk2 }, line: { color: THEME.colors.dk2, width: 0 } }); TB(s, n[0], { x: x + 0.3, y: 1.9, w: 3.2, h: 0.5, fontSize: 20, bold: true, color: THEME.colors.accent1 }); TB(s, n[1], { x: x + 0.3, y: 2.5, w: 3.2, h: 2.2, fontSize: 14, color: C.background1, valign: "top" }); });
TB(s, "Repository: github.com/Winner-121/Destroyerrrrs_Final_Stage   ·   Demo: amir-kuldashev--load-safety-gate-web.modal.run", { x: 0.7, y: 5.4, w: 12, h: 0.5, fontSize: 13, color: THEME.colors.accent5 });

(async () => { await pres.writeFile({ fileName: "LoadSafetyGate_deck.pptx" }); await applyTheme("LoadSafetyGate_deck.pptx", THEME); console.log("written"); })();
