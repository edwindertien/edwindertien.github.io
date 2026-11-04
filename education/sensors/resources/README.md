# Handoff: Sensors A6 (Hall-effect rotation sensor) grading system

State as of 2026-11-03: all 30 unique reports (54 students) graded AND rechecked with the figures under the strict reading (section 3c); see a6-overview.csv.

## 1. What exists (folder `assignment6/`)

| File | What it is |
| --- | --- |
| `rubric-sensors-hall.yaml` | The rubric (26 criteria, 30 pt, grade = 1 + 9 x points/30). Source of truth. |
| `rubric-sensors-a6.html` | The grading tool (copy of the A3 tool; localStorage key `rubric_session_sensors_a6`; fetches the YAML next to it). |
| `rubric-session-sensors-a6.json` | The session (empty at the start). Load it with the load-session button; it carries the rubric YAML. |
| `review-sensors-assignment-6.md` | Review of assignment, template and reference example, rubric changes, set-up steps. |
| `handoff/add_assessment.py` | Appends one graded pair to the session JSON from a grade file (validates ids, indices, forbidden characters; writes a .bak). |
| `handoff/criteria-cheatsheet.md` | Every criterion id, points and the numbered checklist items (the indices used in grade files). |
| `handoff/grading-matrix.md` | Score per criterion per graded pair (the calibration record); starts with the reference example. |
| `handoff/grades/reference_example.json` | Grade file of Edwin's reference solution (strict reading, 23/30). Example of the grade-file format and note style. |
| `handoff/test_tool.js` | Headless check of the tool: `npm install jsdom js-yaml` in this folder, then `node test_tool.js ../rubric-sensors-a6.html ../rubric-session-sensors-a6.json`. |
| `handoff/gen_rubric_a6.py` | Generator of the YAML from a compact definition (edit there, then regenerate and re-embed in the HTML). |

## 2. How the tool and session work
- Each criterion = one slider (integer points) + one checklist of observations (never changes the score) with two notes boxes (to improve / well done).
- Session JSON: `{yaml, assessments:[{id, name, meta:{student, project, assessor}, values:{...}}], aid, currentId}`. Values: `<criterion>` = points; `<criterion>_obs__neg__<i>` / `__pos__<i>` = ticked item; `<criterion>_obs__neg_note` / `__pos_note` = notes; `overall_note`.
- Strings that go into the YAML or notes must not contain double quotes, backticks, backslashes or the sequence dollar-brace.
- Pairs get identical scores as two assessments (one per student).

## 3. Grading conventions (carried over from A3, adapted)
Anchor: the reference example scored strictly is 23/30 (7.9). The A3 worked example was the benchmark for a 7 (20/30); if you prefer the same here, tighten an_reference, me_reference and me_procedure to 0 for the reference (decision pending, see the review). General: award a 1-point item when its core demand is met; judge each criterion on content wherever it sits, except that a remark only in Results does not earn a Conclusion criterion (improvements, accuracy); no penalty for lateness; AI / Grammarly statements are not graded.

| Criterion | Rule (strict reading) |
| --- | --- |
| intro type / principle / goal | Types named (linear Hall sensors with magnet wheel, potentiometer); principle at name level counts if both parts are covered; goal short and not buried in process. |
| measurand | Explicit statement of the quantity (rotation angle of the wheel) and unit (degrees). Mixing electrical and mechanical angle, or only counts or volts = 0. |
| principle / reference | Own explanation (alternating polarity, 90 degree phase from the spacing; potentiometer as wiper divider); reference needs its principle and a datasheet value (effective electrical angle, taper). |
| equations (2) | Chain field -> voltage -> counts -> degrees with numbers; atan2, unwrapping and scaling 270/1440 (multiply), reference formula. Text that contradicts the code, or no expected swing = 1. |
| conditioning (2) | Schematic with both Hall sensors and the potentiometer, plus the expected use of the ADC range; centre / amplitude per sensor mentioned. Schematic only = 1. |
| setup | Component location + physical arrangement (wheel, magnets, air gap) + conditions (room / table / temperature). No conditions = 0. Photo not required. |
| code (2) | Sketch that outputs the Hall angle and the reference angle per line, with unwrapping, compact. Raw-only logging or very long uncleaned code = 1. |
| reference method | How the potentiometer angle is obtained (datasheet angle) and aligned with the wheel angle (offset / scale). Datasheet-only is allowed. |
| samples / procedure | Number of swings, direction, sample rate; ordered steps, starting position, static points or sorting for precision. |
| time series / calibration / error | Raw A4, A5 and potentiometer in time; x-y of calculated versus reference angle (ideal line); error plot with sign (against the reference angle is better; against time still earns the point). |
| non-ideal details | Lissajous of the two Hall signals, close-up of the error within a transition, or of the resolution steps. Bumps only mentioned = 0. |
| graphing | 0 if axis titles are missing or quantities are mislabelled (counts and degrees mixed). |
| accuracy | Mean error alone = 0. Needs worst case or RMS in degrees, with the range or the reference accuracy. |
| resolution | Must include the used ADC range (about 245 of 1023 counts) and the reference (0.25 degrees per count). Single value for the Hall angle without the used range = 0. |
| precision | Standard deviation of repeated readings at fixed angles = 1; standard deviation of the error over the whole range only with a caveat = 1, bare number = 0. |
| range | Angular range with magnets and transitions (270 degrees), swing in V or counts, reference range compared; wheel and potentiometer ranges not mixed. |
| non-linearities | Periodic error per transition quantified, cause named (offset, amplitude, phase), edge effect checked against the reference range. Words only = 0. |
| improvements | Named bottleneck + concrete option in the Conclusion = 1; improvements only in Results, or none = 0. |
| template (2) / references | Template followed, figures numbered and referenced; references: datasheets (Hall sensor, magnet, potentiometer), field calculator and wiki figures credited. |

## 3b. Rulings by Edwin (2026-11-02), applied in the rubric text and in the grading
- **Potentiometer range:** the datasheet gives 280 +/- 5 degrees mechanical; the electrical range is much smaller (nominal about 28 to 252 degrees, from the taper curve). Acknowledging the difference is good; forgetting it is not a big deal; using 280 degrees (mechanical and electrical) or 280 degrees mechanical with 270 electrical is fine.
- **Sensor types:** A1301 (2.5 mV/G) and A1302 (1.3 mV/G) are both in use (one report has an A1324, 5 mV/G). Students have to check which one they have; assuming one is fine. Good: comparing the measured swing with the expected one and using the right value for the right sensor.
- **Implementation:** eventually in code, not only in Excel; a conversion done in a spreadsheet is accepted when the formula and constants are stated explicitly in the report.
- **Centring and Lissajous:** centring each signal (min / max) and discussing the x-y (Lissajous) plot is a good addition (in an_conditioning, re_nonlinear, co_nonlin, co_improve).
- **Template and header:** deviations are only a small remark (fo_template stays 2 if the rest is fine).
- **Pairs and duplicates:** students mostly work in pairs but may hand in individually (individual work, or collaboration stated elsewhere). Duplicate files of one report are graded once and added as two assessments (one per student). 55 files in the zip = 32 unique reports; `clusters` of identical files are in the conversation notes (first run: albayrak/mihai, alireanu/peeters, aparicio/janke, aragno, ariens/jenkins, borgonjen/jan, brant/vries, brockmann/dijk, bruggert/kloks, crosswaite, colak, dauria/enea, emmelot, faber/khan, goedejohan/kuipers (two files, one of 49 pages), goytizolo/landeweerd, hartog, hawryluk/samoila, huizing/otten, karasoy/truran, koning/reimer, langeslag/meinders, lukacie/mataic, schintz/stroo, schroten/spieker, stoica/yarder, throup/townsley, tromp (two files), walrave, wang).

## 3c. Strict reading applied in the recheck (Edwin, 2026-11-03)
- an_reference = 1 only when the electrical range of the potentiometer is recognised as smaller than the mechanical travel and used (mechanical 280 degrees only = 0; observing the flat ends without naming them = 0). co_range needs the electrical range stated (anywhere in the report, with its consequence).
- me_setup = 1 needs the room temperature (a desk or the SmartXP alone = 0). me_code = 2 needs floats, text and code in agreement and constants traceable to data; an int angle (truncation) or a mismatch caps it at 1. An int-truncation or print-rounding step is not a resolution (co_resolution = 0). co_resolution needs both the sensor and the reference.
- co_precision needs holds or turning to a position and returning to it; sweep spread or the standard deviation of the error = 0. co_accuracy needs RMS or worst case in degrees plus a percentage of the range or a quantified remark on the reference in the accuracy discussion, with numbers consistent with the figures. an_conditioning = 2 needs per-sensor centre and amplitude from the data plus the used ADC range compared with the expected swing. re_time needs the raw Hall signals plotted. re_nonlinear needs a Lissajous plot or a close-up.
- Crosswaite (benchmark) is 28/30 under this reading; student numbers missing are not reflected in points.

## 4. Verified facts and reference values
- **A1302** (Allegro A1301/A1302 datasheet): sensitivity typical 1.3 mV/G (1.0 to 1.6 at 25 degrees C, 0.85 to 1.75 over temperature); quiescent output Vcc/2 (2.5 V at 5 V); ratiometric (quiescent and sensitivity scale with Vcc); linear output at 5 V. The A1301 is 2.5 mV/G typical. Students with an A1324/5/6 have different sensitivities: check their datasheet.
- **Swing:** 481 G (calculator, N45 diameter 4 x 1.5 mm magnet) x 1.3 mV/G = 625 mV; with the sensitivity tolerance 0.48 to 0.77 V. On the 10-bit ADC (4.888 mV per count): 1.2 V peak-to-peak = 245 counts = 24 % of the range; amplitude about 123 counts.
- **Field calculator distance:** the plot origin of the K&J calculator is the centre of the magnet (Crosswaite's screenshot: Field origin at (0 in, 4.25 mm), 429 G); the reference example's 481 G at 4 mm is therefore 4 mm from the centre = 3.25 mm from the face. Students must state which distance they use.
- **Field vs distance:** on-axis formula for a diameter 4 x 1.5 mm N45 disc (Br about 1.35 T): 481 G at 3.2 mm from the surface = 4 mm from the magnet centre; about 300 G at 4 mm from the surface. The reference text says 5 mm centre-to-sensor, which does not match the 481 G (see the review).
- **Geometry:** the polarity alternates, so one transition (360 electrical degrees) is two magnet pitches. For 9 magnets over 270 degrees: pitch 33.75 degrees, transition 67.5 mechanical degrees, 4 transitions = 1440 electrical degrees, scale 270/1440 = 0.1875. D_sensor = D_magnet + 90 electrical degrees.
- **Resolution:** potentiometer 252/1023 = 0.246 degrees per count; single-signal estimate 270/960 = 0.28 degrees; with atan2 about 1/A rad = 0.47 electrical = 0.09 mechanical degrees (a bound: noise and offset errors come on top).
- **Potentiometer (datasheet 2160633.pdf = Alps RK09K1130AH1, 10 kOhm +/-20 %, taper B = linear):** overall rotational angle 280 +/- 5 degrees; the taper curve is flat near 0 % until about 28 degrees and near 100 % above about 252 degrees (nominal electrical range about 224 degrees); at 140 degrees the output only has to be within 40-60 %; the datasheet asks for an output-side impedance of at least 100x the total resistance. Student data agree with the nominal curve once the wheel pitch is right: Peeters / Reanu derive 225 to 233 degrees, and Crosswaite's apparent 82.9 degrees per wave on the 280 degree scale is 67.5 x 280/228, i.e. a span of 228 degrees.
- **Wheel:** 9 magnets spread over 270 degrees: pitch 33.75 degrees, one wave (N + S) = 67.5 degrees, scale 270/1440. Several students assume a 40 degree pitch (360/9) and 80 degrees per wave; that is wrong, it shows up as an apparent 80-83 degree wave on the 280 degree potentiometer scale (error period about 40 degrees on that scale = 33.75 degrees of rotation).
- **Sensors:** A1301 2.5 mV/G, A1302 1.3 mV/G, A1324 5.0 mV/G (A1324 found by several groups, also Peeters / Reanu, Mihai / Albayrak, Aparicio / Janke). Expected swing = field x sensitivity; clipping near the rails when the field is large (3.5 mm from the magnet centre gives about 650 G; 4 mm about 480 G).

## 5. Errors in the reference example (used as benchmark)
Text versus code (arctan(y/x) versus atan2 with swapped arguments and an extra -1; division versus multiplication by 270/1440); edge errors of -20 degrees probably from the potentiometer range (flat output near both ends, nominal electrical range about 28 to 252 degrees) against the 270 degree wheel range; precision called the standard deviation of the error; fixed centre of 512 for both sensors; distance 5 mm versus 4 mm for the 481 G; footnote numbering. Full list in `review-sensors-assignment-6.md`.

## 6. Workflow for each new report
1. Render the pages (`pdftoppm -r 110`; for a docx convert to PDF first) and look at the figures.
2. Recompute the key numbers before judging (swing in counts, resolution, per-transition angle, angle formula in text versus code, error statistics).
3. Write a grade file (format: see `grades/reference_example.json` and `add_assessment.py`), with notes in the style of the reference example; flag 2-4 borderline calls.
4. `python3 add_assessment.py <session.json> <grades.json>` (same scores for both students of a pair).
5. Confirm with `node test_tool.js <tool.html> <session.json>` (points and grade per assessment).
6. Reply with: points and grade, a short table by section, strengths, technical findings, borderline calls, and the updated session JSON.
7. Overlap check between reports (figures, numbers, code) was done for A3 with page rendering, curve correlation and shared-number search; repeat after all reports are in.

## 7. Pending
- Decision on the anchor of the reference example (20/30 or 23/30).
- All reports graded. Recheck pending: decide the tightening rules, view the figures of the reports graded from text and captions, re-run; check the Crosswaite anchor; overlap check (Peeters / Karasoy / Wang sketches; Aragno / Colak constants).
- Template and assignment fixes proposed in the review.
- Sensors A3 and A6 systems are independent (different keys and files).
