# Sensors A6 (Hall-effect rotation sensor): review notes

Basis: the assignment text with the figure (D_magnet, D_sensor), the template, and your completed reference. Datasheet checks: A1301/A1302 (Allegro) and the Alps RK09K family, from public copies, because the wiki blocks automated access. Where I could not verify something, it is marked as a question and not as an error.

## 0. What I made (same architecture as A3)

| File | What it is |
| --- | --- |
| `rubric-sensors-hall.yaml` | The rubric: 26 criteria, 30 pt (3 + 7 + 6 + 5 + 6 + 3), grade = 1 + 9 x points/30. Source of truth. |
| `rubric-sensors-a6.html` | The grading tool (copy of the A3 tool; localStorage key `rubric_session_sensors_a6`; fetches the YAML next to it). |
| `rubric-session-sensors-a6.json` | Empty session carrying the rubric (load it with the load-session button). |
| `handoff/` | README with grading conventions, criteria cheatsheet (indices), grading matrix, `add_assessment.py`, `test_tool.js`, `gen_rubric_a6.py`, grade file of the reference example, seed prompt. |

Tested: the YAML parses (26 sliders, 30 pt); the tool loads it headlessly, shows 26 sliders, adds up the reference example to 23/30 and generates the feedback text; `add_assessment.py` validates all ids and indices.

## 1. Reference example: things to fix

### Technical (these would mislead students who copy the example)

1. **Text and code disagree on the angle formula.** The Analysis uses `x = analogRead(A4)/512 - 1`, `y = analogRead(A5)/512 - 1`, `alpha = arctan(y/x)`. The code uses `atan2((phaseA-512)-1, (phaseB-512)-1)`: atan2 instead of arctan (arctan(y/x) loses the quadrant, atan2 is needed), the signals in the other order (A first), an extra `-1` (the centre becomes 513) and no normalisation.
2. **The scaling is inverted in the text.** `alphatotal = (alpha + angleoffset) / (270/1440)` divides; the code multiplies by `270.0/1440.0`, which is correct (67.5 mechanical degrees per 360 electrical degrees).
3. **The edge errors are probably the reference, not the sensor.** The error is up to -20 degrees at the edges of the range. The wheel spans 270 degrees but the potentiometer is only 252 degrees electrical (about 280 degrees mechanical stop), so the reference saturates before the wheel does. The Conclusion mentions the 252/280 contradiction but does not connect it to the edge error. Better: fit `angle_ref = a x pot + b` and evaluate only the common range.
4. **Precision is not measured.** The Method says the data is sorted to get precision at a number of points; the Conclusion then gives the standard deviation of the error over the whole range (8.03 degrees). That contains the systematic error of every transition, so it is accuracy spread, not precision. Static holds, or the sorted data per angle bin, would give a real precision.
5. **Resolution: the estimate counts one traversal and the reference limits the demonstration.** 245 counts per transition is the peak-to-peak swing (1.2 V / 4.88 mV). With two signals and atan2 the angle resolution is about 1/A radians, with A = 0.6 V / 4.88 mV = 123 counts: 0.47 electrical degrees = 0.09 mechanical degrees. The potentiometer resolves 252/1023 = 0.25 degrees per count, so the reference cannot demonstrate anything finer than about 0.25 degrees. The text says 0.28 degrees for the sensor and that it is higher in the data ("at least 5 steps per degree"), which is consistent, but the limit of the reference should be said.
6. **Fixed centre of 512.** The quiescent output is Vcc/2 only within the datasheet tolerance, and the sensitivity of an A1302 is 1.0 to 1.6 mV/G at 25 degrees C (typical 1.3). So each sensor has its own offset and amplitude; a fixed 512 and equal amplitudes give an ellipse and an off-centre circle and therefore the bumps between the transitions. The reference suggests a look-up table; a min/max calibration of the two signals, or a Lissajous check, would be the first step.
7. **Distance and field.** The text says the distance between magnet centres and sensors is about 5 mm and takes 481 G at 4 mm from the field calculator. For a diameter 4 x 1.5 mm N45 disc (Br about 1.35 T) the on-axis formula gives about 480 G at 3.2 mm from the surface, i.e. 4 mm from the magnet centre; at 4 mm from the surface it is about 300 G. The measured swing (2.5 V +/- 0.6 V) matches 481 G, so the 5 mm in the text is probably wrong or refers to something else. Worth one sentence on what the calculator distance means (surface or centre).
8. **Footnotes.** The reference has four footnotes (Hall datasheet first); the template cites `[^0]` but lists `[^1]` to `[^3]`, so the Hall-sensor datasheet is missing from the template footnote list and the numbering is off by one.

### Structure and format

- Figure 5 (raw values) has no x-axis title; the error plot has no figure number and no caption, and is against sample number (not against the reference angle).
- The equations are images, so they are not searchable and cannot be checked against the code in the text.
- No conditions (room, temperature), no sample rate, no rotation direction or starting position.

## 2. Template

- Analysis: add a one-line prompt for the measurand ("The measurand is ... expressed in ..."). In A3 nearly every pair scored 0 on this; the same will happen here, and electrical versus mechanical angle makes it a real point.
- Analysis: prompts for the centre voltage and amplitude of each sensor, for the fraction of the ADC range that is used (the assignment says to pay attention to the used voltage range), and for the alignment of the potentiometer zero with the wheel.
- Method: the template has no prompt for conditions (room, temperature, how the wheel is turned) or sample rate, so the setup point will again be lost by most.
- Results: the template asks for a time series, the calculated angle versus the reference, and an error plot, but not for an x-y plot of calculated versus reference angle, or for a Lissajous plot of A4 against A5, which shows the bumps best.
- Conclusion: add "Non-linearities / systematic errors" next to accuracy, precision, resolution and range (the rubric has a criterion for it), and "from repeated readings at the same angle" at precision.
- Footnotes: see item 8 above.

## 3. Assignment text

- Typos: "which has be done on purpose", missing space in "(!)see".
- "find a formula ... (hint, you can use the arctan function ...)": say atan2.
- "check the markings on the sensor": the template and the reference assume an A1302 (1.3 mV/G typical, verified). The A1301 is 2.5 mV/G; for the A1324/5/6 check the linked datasheet. Ask students to state which part they have, otherwise the expected swing is wrong for them.
- The potentiometer: the assignment links `2160633.pdf`, the template footnote links the Alps RK09K datasheet. The RK09K family has 280 degrees total rotation (RK09D 300 degrees) and both linear and logarithmic tapers, so ask students to state the part number and the taper; the reference assumes linear and 252 degrees.
- The figure: say that D_magnet is 360 electrical degrees (two magnet pitches, because the polarity alternates) and that D_sensor = D_magnet + 90 electrical degrees.
- "measure angular range ... precision and accuracy": no definitions. The rubric rewards precision from repeated readings at the same angle and accuracy as worst case or RMS in percent of the range; say so in the assignment, or the results will again be a standard deviation of the error.
- Hysteresis is not asked here. I dropped it from the rubric (see 4).

## 4. Rubric: what changed with respect to A3

Points and structure are unchanged: 3 + 7 + 6 + 5 + 6 + 3 = 30, one slider plus one observation checklist per criterion (checklists never change the score). Criteria were retuned, not added or removed:

| Criterion | A6 retuning |
| --- | --- |
| intro type / principle / goal | Linear (ratiometric) Hall sensors with magnet wheel and potentiometer; Hall effect, sine / cosine pair, wiper divider; goal with range, resolution, precision, accuracy. |
| measurand | Rotation angle in degrees; electrical versus mechanical angle must not be mixed (360 electrical degrees = 2 magnet pitches = 67.5 degrees for 9 magnets). |
| principle | Alternating polarity, ratiometric output, why the sensor spacing gives a 90 degree phase. |
| reference | Potentiometer: wiper divider, 252 degrees electrical (280 mechanical), linear taper, 0.25 degrees per count, alignment of the angle scales. |
| equations (2) | Field x sensitivity = swing in mV and in counts (480 G x 1.3 mV/G = 0.62 V = 245 counts); atan2; unwrapping; scaling 270/1440; reference formula. |
| conditioning (2) | Schematic with both Hall sensors and the potentiometer, expected use of the ADC range (a quarter), centre and amplitude, ratiometric ADC. |
| setup / code / reference / samples / procedure | Wheel, magnets, air gap, conditions; angle and reference per line with unwrapping; alignment of the potentiometer; number of swings and static points; starting position. |
| time series / calibration / error | Raw A4, A5 and potentiometer; x-y of calculated versus reference angle with ideal line; error against reference angle. |
| non-linear details (was hysteresis) | Lissajous plot of the two Hall signals, error within a transition, or close-up of the resolution steps. |
| accuracy / resolution / precision / range | Worst case or RMS in degrees and percent of range; resolution including the used ADC range and the limit of the reference; precision from repeated angles; angular range, range per transition, swing in V, reference versus wheel range. |
| non-linearities (was hysteresis, etc.) | Periodic error per transition quantified, cause (offset, amplitude, phase), edge effect from the reference range. |
| improvements | Bottleneck from the data and a concrete option (min / max calibration, ellipse correction, look-up table, gain, smaller air gap, better reference). |
| template / references | Unchanged, with Hall datasheet, magnet datasheet, potentiometer datasheet and the field calculator. |

### The reference example scored with this rubric

Strict reading, same rules as A3: **23/30 = grade 7.9**. Introduction 3, Analysis 5, Method 5, Results 4, Conclusion 3, Format 3 (per-criterion scores and notes in `handoff/grading-matrix.md` and `handoff/grades/reference_example.json`).

Your A3 worked example was the benchmark for a 7 (20/30). Five calls in the reference are borderline (each about 0.3 grade point): an_reference, me_reference, me_procedure, me_setup (no conditions) and re_nonlinear. If you want the reference to sit at a 7 as in A3, tighten an_reference, me_reference and me_procedure to 0, which gives 20/30. Say which you prefer and I will fix it in the README before grading starts.

### What to expect from A3 experience

- The measurand will score 0 for most unless the template prompts for it.
- Setup conditions (room, temperature) and the sample rate will be missed by most.
- Precision will mostly be the standard deviation of the error over the whole range; the rubric gives that 1 point only with a caveat.
- Improvements are often only in the Results, not in the Conclusion; those do not count.

## 5. Setting it up next to the other rubrics

Same procedure as for A3. Files: `rubric-sensors-hall.yaml` and `rubric-sensors-a6.html`. What differs from the A3 tool (four settings): page title, `DEFAULT_YAML`, the `localStorage` key (`rubric_session_sensors_a6`) and `SERVER_RUBRIC_URL` (`rubric-sensors-hall.yaml`), plus the project placeholder.

1. Put both files in the repo next to the others (for example `sensorsAssessment/`), commit and push; open `rubric-sensors-a6.html`. First visit loads the embedded default.
2. To change the rubric later: edit the YAML (or regenerate it with `handoff/gen_rubric_a6.py`), push, press **Load server rubric**. Assessments are kept; do not rename field ids. Strings in the YAML must not contain double quotes, backticks, backslashes or the sequence dollar-brace (the YAML is embedded in a JS template literal).
3. Marking: **+ New** per student, set the sliders, tick the observations, use the notes boxes as the Canvas comment, then **Copy** or **Download .md**. Use **Save** (JSON) to back up; sessions live only in that browser. `handoff/add_assessment.py` adds graded pairs to the session JSON from a small grade file.

## 6. Questions for you

1. Anchor the reference at 7 (20/30) as in A3, or leave it at 23/30 (7.9)?
2. Is dropping hysteresis acceptable? I replaced it by non-ideal details (Lissajous, error per transition) in Results and by systematic errors in the Conclusion.
3. Do you want the prompts above added to the template (measurand, conditions, x-y and Lissajous plots)? That would remove the cheap zeros seen in A3.
4. Which potentiometer and which Hall sensor types do the students have (all A1302?)? It decides the reference values in the rubric descriptions.
