# MC form reader

A small local web tool that reads scanned multiple-choice answer forms (Universiteit Twente, 4 options A–D, 25 questions, 7-digit student number), flags what it is unsure about, and lets you check and correct the result in the browser before exporting.

Built for the *Sensors for Creative Technology* test 2 (October 2026), where 57 forms were scanned into one PDF and the results had to go into a grading spreadsheet.

## Quick start

Requirements: Python 3.9+.

```
pip install -r requirements.txt
python app.py
```

A browser tab opens at http://127.0.0.1:5000. Use `python app.py --no-browser` to suppress that, or set `PORT=8000` to change the port. The server only listens on localhost.

## Using it

1. **Upload** a PDF with one form per page. Optional extras:
   - **Title:** used for the export file names.
   - **Answer key:** 25 letters a–d. It can also be set or changed later on the review page.
   - **Roster:** a Canvas export as csv, xlsx or ods. The tool looks for a column of 7-digit student numbers (an optional leading `s` is ignored) and a column of names. With a roster it fills in names and can complete a student number that was read incompletely.
   - **Detection thresholds:** the defaults worked on all 57 forms of the test run. See *Tuning* below.
2. **Review.** The page list is on the left, the aligned scan with overlay in the middle, and the readings on the right.
   - Green rings mark accepted answers, orange rings or dashed boxes mark flagged ones, and a red box marks a blank question.
   - Blue rings mark the student number as currently entered.
   - Flagged questions show the reason and a zoomed crop of that row. Click a letter to set the answer, and click it again to clear it.
   - Edit the student number or name if needed. Typing a number that is in the roster fills the name on save.
   - **Save & next page** marks the page as reviewed and moves on. Edits are written to disk on every save.
   - "Only flagged" hides the questions that need no attention.
3. **Export** as csv or xlsx from the review page header (or from the job list).

Jobs are listed on the start page, so you can come back to a half-reviewed job later. Deleting a job removes its images and results.

### Export format

One row per page: `name` (lowercase surname, taken from the roster or typed name), `student number`, answers `1`–`25` (lowercase letters, empty cell = no answer), then `page`, `full name`, `score` (against the key, if given), `reviewed` and `open issues`. If a key is set, it appears as the first data row. The first 27 columns follow the column layout used in `sensors2026.ods` (tab `test2`), so rows can be pasted directly.

## How to read the flags

| Flag | Meaning | What the tool did |
|---|---|---|
| orange row, "blank" | no bubble filled | left empty |
| "multiple marks … cannot tell which is crossed out" | two or more bubbles filled and no clear crossing-out | left empty, you decide |
| "heavy scribble" | one bubble is covered in scribbles, which fooled the cross detection | left empty |
| "single mark with ink outside the bubble" | one filled bubble with extra strokes, possibly cancelled with no replacement | kept the mark |
| "faint mark" | a filled bubble that is lighter than usual | kept the mark |
| green row, "X crossed out, kept Y" | two bubbles filled, one clearly crossed out | picked the other one (informational, no action needed) |
| ID note "resolved via roster" | some ID digits were unreadable or doubly marked, and exactly one roster entry fits | filled in the match |
| ID note "ID incomplete" / "not in roster" / "duplicate" | the number needs attention | left as read, or empty |
| "not aligned" | the four corner marks were not found, so readings are unreliable | processed anyway |

On a form, a cancelled answer is a filled bubble with an X drawn over it, as the form's instructions describe. Because such a bubble still looks filled, the tool has to detect the X itself.

## Technical description

Everything is in `app.py` (Flask, OpenCV, NumPy, PyMuPDF; pandas and openpyxl for roster reading and xlsx export).

**Pipeline per page**

1. **Render.** Each PDF page is rendered to grayscale at 150 dpi.
2. **Align.** The four black corner squares (square connected components of 25–70 px, nearly solid) are located, ordered TL/TR/BL/BR, and a perspective transform maps them onto fixed target positions in a 1240×1755 frame. This removes skew, rotation and scale differences between scans. If the squares are not found, the page is just resized and flagged.
3. **Measure.** The bubble grid is fixed in the aligned frame (coordinates calibrated on the first clean form). For each of the 100 answer bubbles and the 70 student-number bubbles the tool measures:
   - *Fill*: mean darkness (255 − gray) inside a small disk. Because the small disk covers the interior of the bubble but not the printed ring, a 3×3 pixel shift search tolerates slight misalignment. Empty bubbles score around 40–60 and filled ones above ~80, regardless of pen colour (the dark and the light scans both separate cleanly; the default threshold is 75).
   - *Ring ink* (answers only): fraction of dark pixels in an annulus just outside the bubble, minus the minimum of the same row. Strokes of an X extend beyond the bubble, a plain mark does not.
4. **Interpret.**
   - Exactly one filled bubble is the answer.
   - None is a blank.
   - Several: if the one with the most outside ink clearly stands out (at least 0.04 and 0.04 above the next), it counts as crossed out and the single remaining mark is the answer. A heavy scribble (ring ink above 0.35) or an unclear case is left empty and flagged.
   - Student number: one filled bubble per column gives the digit; none gives `?`; several give `[23]`. Patterns are matched against the roster as regular expressions.
5. **Persist.** The aligned page is stored as JPEG, the raw measurements and flags go to `results.json`, and later edits (answers, ID, name, reviewed) overwrite the corresponding fields.

**Files**

```
app.py                  the whole application
requirements.txt
data/<job-id>/
    source.pdf          the uploaded scan
    roster_upload.*     the roster file, if given
    meta.json           title, key, roster (id -> name), thresholds
    results.json        one record per page: readings, flags, your corrections
    pages/001.jpg ...   aligned page images used by the review screen
```

**HTTP routes** (all local): `/` job list, `/upload`, `/job/<id>` review page, `/api/job/<id>` and `/api/job/<id>/page/<n>` (JSON, GET/POST), `/api/job/<id>/key`, `/img/<id>/<n>.jpg`, `/crop/<id>/<n>/<q>.png`, `/export/<id>.csv|xlsx`.

## Tuning

The thresholds are on the upload form and stored per job (`meta.json`):

| Name | Default | Effect |
|---|---|---|
| `fill_threshold` | 75 | darkness above which a bubble counts as filled; raise it if pencil smudges are read as marks, lower it for very light ink |
| `faint_threshold` | 90 | filled bubbles below this are flagged as faint |
| `cross_min` | 0.04 | minimum outside ink for a bubble to count as crossed out |
| `cross_diff` | 0.04 | how much more outside ink the crossed bubble needs than the other |
| `cross_single` | 0.10 | outside ink on a lone mark that triggers a flag |
| `scribble` | 0.35 | outside ink above which a bubble is treated as a scribble |

Changing thresholds requires a new upload, because processing happens once per job.

## Validation

On the test 2 scan (57 forms):

- A benchmark of 9 forms entered by hand beforehand: all 225 answers agreed.
- The other 48 forms were compared with answers I verified by eye, including the ambiguous cases and the automatic crossing-out resolutions I inspected: no automatic resolution was wrong. 8 questions are intentionally left blank for human review (cancelled marks that are too subtle for the ring measurement).
- Student numbers: 55 of 57 were decoded straight from the bubbles and found in the Canvas list. One form with a double-marked digit was resolved with the roster, and one form with an empty ID block has to be matched by name and typed in by hand.
- Typical run time: about 10 s for 57 pages.

## Limitations and notes

- **Form layout is hard-coded.** Only the form version used here is supported (25 questions in the first block, 7-digit number, corner marks). A different layout needs new coordinates at the top of `app.py`; the 50/75/100-question blocks and the teacher grid are not read.
- **Scans must be reasonably straight.** Perspective correction handles moderate skew, but pages scanned upside down are not detected.
- **Handwritten names are not read.** Names come from the roster through the student number. Check the name on the form yourself if the ID had to be corrected.
- **Pencil and very light pen** may need a lower `fill_threshold`; heavy highlighting or fill outside the circle can fool the ring measurement.
- **Faint X marks** (a cancelled answer with a very light stroke) are not detected reliably; those cases end up flagged rather than guessed.
- **Privacy.** Everything stays on your machine in `./data`, and the app serves localhost only. Uploaded PDFs contain student names and numbers, so keep or delete the folder accordingly.
- This is a review aid, not a grader of record: the person checking the flagged items is the final authority on every answer.
