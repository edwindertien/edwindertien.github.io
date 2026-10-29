# Sensors A3 (Resistive Sensing): review notes

Scope: assignment text, student template, worked example, pasted Canvas rubric.
Sources used for checking: your three documents, the Phidgets page for the load cell (prodid=223, read today), and Tekscan A101 specs as quoted by Mouser. I could **not** open your wiki or the Tekscan PDF (both block automated access), so schematic designators (R1, R4, A2, A3) are taken from your worked example, not verified against the wiki.

Arithmetic in the example was re-computed; numbers below are mine, not copied.

---

## 1. Worked example: things to fix

### Technical (these would mislead students who copy the example)

| # | Where | Issue | Suggested fix |
|---|---|---|---|
| 1 | Analysis, last paragraph; Conclusion, hysteresis paragraph | Load-cell spec numbers do not match the Phidgets page: rated-output error is **±800 nV/V** (0.1 %), not ±100 µV/V (12.5 %); repeatability, non-linearity and hysteresis are each **390 mg**, not 39 g. Off by 100x. So "10.0 ± 1.25 mV/g" and "100 g seems larger than the specified 39 g" both break. | Recompute the expected error. In the hysteresis discussion compare with the **A101** spec instead (hysteresis < 4.5 % FS, linearity < ±3 % FS, repeatability < ±2.5 %), since the foil sensor is clearly the dominant effect. If you used an older datasheet PDF, check it, the web page may differ. |
| 2 | Conclusion, accuracy | Accuracy is given as the **mean error (1.68 g)**. A least-squares calibration makes the mean error about zero by construction, so this says nothing. The error plot shows excursions of about -100 / +70 g (up to ~20 % of a 500 g range). This is exactly what the rubric warns about ("mean and stddev tell only part of the story"). | Give worst-case or RMS error in g **and** % of full scale, over the valid range only (50-450 g), and discuss the accuracy of the reference. |
| 3 | Precision (43.8 g) | The text itself says clipped samples are included, but the number is not recomputed. | Recompute for 50-450 g. |
| 4 | Conclusion, resolution | "Not uniformly distributed" is stated but not calculated, although the rubric asks for it. With F = 850000/N - 819, resolution per count is 850000/N^2: **0.82 g/count at N = 1018, 2.57 g/count at N = 575** (3x worse). | Add both numbers. |
| 5 | Conclusion, resolution | "443 counts for the 500 g range" mixes things up: by the example's own formula N = 575 corresponds to about 659 g, and 500 g corresponds to N = 644 (374 counts, ~1.34 g/count average). | Re-derive, or drop the average and give the two end values from #4. |
| 6 | Analysis vs Fig. 4 | Analysis predicts about 10 kΩ at 500 g, i.e. 0.45 V, raw count about 93. Fig. 4 shows raw values only down to about 575 (about 2.8 V, about 128 kΩ). Never reconciled. Also: the A101 resistance range 3.6-30.85 kΩ is specified for 0.25-4 lb (about 113 g - 1.8 kg), so this assignment sits at the very low end of the specified range. | One sentence on this (fingertip versus the 3.8 mm sensing area, low end of the specified range). It is also good material for "systematic errors". |
| 7 | Table 1 | 826 counts gives **403.3 g**, table says 401. 19 counts gives 9.28 (table: 9.2, truncated). Text says "five sample points" but the table has six rows. | Fix the numbers and the count. |
| 8 | Units | Everything is in g (mass) for a force measurement; 780 g is 7.65 N, not 7.8 N; 5 N is 510 g, not 500 g; the intro says "pressure". The rubric's **measurand** criterion (quantity + units) is not met by the example. | Add one sentence: measurand = force on the sensing area, expressed as equivalent mass in g (1 g is about 9.81 mN). Use "force" consistently. |
| 9 | Analysis | Formula uses R2, the schematic labels the 100 kΩ pull-up R1. "200.000" (decimal separator) reads as 200.0 in English. "(5.0 * 0.0008) / 780)" has unbalanced brackets. Per-gram output is 10.3 mV/g (2005 x 5.13 µV/g), the text rounds to 10.0. | Cosmetic, but students copy notation. |
| 10 | Nice to add | The offset of 20 counts (about 10 g) matches the Phidgets zero balance of ±11.7 g. Creep 1.6 g/hr and 39 mg/°C temperature effect are also on that page. | Good for the reference-accuracy discussion. |

### Structure and format

- **Duplicate "Figure 6"** (calibration x-y and error plot). Error plot should be 7, hysteresis 8; the text currently calls the hysteresis plot "Figure 7".
- Graphs: default spreadsheet titles in Dutch ("en", "loadcel"); no axis titles on the error and hysteresis plots; Fig. 4 puts raw counts (about 1000) and grams on one unlabelled axis; Fig. 6 has no ideal line; Fig. 7 shows the full 0-500 g although the text says 50-450 g; up and down branches are not marked.
- No close-up of the non-uniform resolution (named in the rubric).
- Method: no experimental conditions (room, temperature, desk), no photo of the two-sensor finger press (Fig. 3 is the kitchen-scale calibration only).
- Code: the listing has no `setup()` / `Serial.begin`, and the combined sketch that prints **both** calibrated values (an assignment bullet) is not shown.
- Conclusion has no **range** statement and no **improvements / systematic errors** paragraph (the only suggestion is the gain resistor, in Results).
- Wiki figures (schematic, shield drawing) are not credited; only the two datasheets have footnotes.

**Rough score of the example against the rubric as I read it: about 20/30 (grade about 7).** If it is meant as a "full marks" reference, the fixes above matter.

---

## 2. Template

- **Pink text is left over from an older procedure**: "calibration steps at 100, 200, 300, 400 and 500 g" at the start of the time series, "cycles pushed by fingertip" at the end. The current assignment and the example calibrate the load cell separately (table with kitchen scale) and then record push-release cycles. Either rewrite these as `[describe ...]` placeholders or remove them.
- Typos visible to students: "machtes", "condendsed", "entirye", "reciproke" (reciprocal).
- Notation: formula placeholder says `R2`, schematic pull-up is `R1`.
- **No prompt for several rubric items**:
  - Intro: no hint what is expected (sensor type, principle, goal).
  - Measurand and units.
  - Setup: experimental conditions and a photo (add a setup photo figure; the example already has one, which shifts numbering by one).
  - Conclusion: only resolution, accuracy, precision and hysteresis are prompted. Add **range**, **non-linearities** and **bottlenecks / improvements (systematic errors)**.
  - Non-uniform resolution close-up (only hysteresis is prompted).
  - References / source credit for wiki figures.
- **Near-free points**: "physical principle" and "the reference" are already written in the template, so every student gets them. Consider replacing part of the text with `[explain in your own words how force becomes a resistance change]`.

## 3. Assignment text

- **"CLZ616c"** appears twice; the example says "CZL616C". The Phidgets page itself is titled "Single Point Load Cell - 780g (3132_0)". Pick one spelling and match the wiki part list.
- "5N (500g)": 5 N is about 510 g. Fine as a safety margin, but say "about 500 g".
- "Known reference weights" for the load cell, but the example uses a kitchen scale and a finger. Say which you expect.
- The foil sensor is called a "pressure sensor"; Tekscan calls the A101 a **force** sensor. Matters for the measurand criterion.
- **Precision**: the rubric prefers a standard deviation from repeated measurements of the same thing. The assignment only asks for one continuous push-release series, so students can only give the std of the error (which is what the example does). Either add "hold a few fixed forces and log 10+ samples each", or accept the std of the error as the expected answer.
- Name the graphs explicitly: time series, x-y calibration, error plot, hysteresis loop (plus resolution close-up). Currently "relevant graphs".
- Optional: the A101 specs apply to a *conditioned* sensor (a few loading cycles first). A sentence on conditioning gives students a real improvement to discuss.

## 4. Rubric: points and coverage

Total **30 points** (3 + 7 + 6 + 5 + 6 + 3), 26 criteria. Grade = 1 + 9 x earned/30, same formula as the other rubrics.

I did not change any point values. I fixed typos (quantitity, consisely, tels, Si) and renamed "Results - graphing/procedure" to "graphing quality" (it is about scaling and units, not procedure).

Two things you may want to add (not in the YAML, they would change the total):

1. **Calibration function / linearisation** is an explicit assignment bullet but has no criterion of its own (it only partly falls under "relevant equations"). It is in the observation checklist for now.
2. **Language / academic style** is a criterion in your other rubrics but not here.

Half points: the tool truncates slider values to integers (`parseInt`). If you use 0.5 in Canvas, change `parseInt` to `parseFloat` in `buildField` and set `step: 0.5`.

---

## 5. Setting it up next to the other rubrics

Files: `rubric-sensors-resistive.yaml` (the rubric, source of truth) and `rubric-sensors.html` (the tool, a copy of `rubric-srd.html`).

What differs from the SRD tool (only four settings): page title, `DEFAULT_YAML` (now the Sensors rubric), the `localStorage` key (`rubric_session_sensors_a3`) and `SERVER_RUBRIC_URL` (`rubric-sensors-resistive.yaml`). The student-name label and project placeholder were also adjusted.

1. In the repo, create a folder beside the others, e.g. `sensorsAssessment/`, and put both files in it.
2. Commit and push (GitHub Pages). Open `.../sensorsAssessment/rubric-sensors.html`. First visit loads the embedded default.
3. To change the rubric later: edit the YAML, push, then press **Load server rubric** in the tool. Your assessments are kept. Do not rename field `id`s, scores are stored by id. **Load server rubric** only works over http(s), not from `file://` (test locally with `python3 -m http.server`).
4. Each tool needs its **own localStorage key** because all of them live on the same origin. If you clone this setup for a fourth rubric, change title, key, `SERVER_RUBRIC_URL` and `DEFAULT_YAML`.
5. Marking: **+ New** per student or group, fill in the name, set the sliders, tick observations (they never change the score), use the notes boxes as the Canvas "Comment", then **Copy** or **Download .md**. Use **Save** (JSON) to back up, since sessions live only in that browser.
