#!/usr/bin/env python3
"""
MC-form reader (Universiteit Twente 4-option forms, 25 questions + 7-digit student number)

    pip install -r requirements.txt
    python app.py            # then open http://127.0.0.1:5000

Upload a scanned PDF (one form per page), optionally an answer key and a roster
(Canvas export as csv/xlsx/ods). Every page is aligned on the four black corner
squares, the bubbles are measured, and uncertain items are flagged for review.
Corrections are made in the browser and saved per job in ./data/<job>/.
"""
import csv
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
import webbrowser

import cv2
import numpy as np
from flask import (Flask, abort, jsonify, redirect, render_template_string,
                   request, send_file, url_for)

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:  # pragma: no cover
    try:
        import fitz  # older PyMuPDF
    except ImportError:
        fitz = None

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# --------------------------------------------------------------------------
# Geometry (calibrated on 150 dpi A4 pages after alignment on the corner marks)
# --------------------------------------------------------------------------
W, H = 1240, 1755
CORNERS_DST = np.float32([[94, 98], [1150, 100], [92, 1646], [1148, 1648]])  # TL TR BL BR
ROWS_Y = [575.1 + (1249.7 - 575.1) / 24 * i for i in range(25)]
COLS_X = [224.7, 268.5, 313.8, 357.3]  # A B C D (first block: questions 1-25)
ID_X = [595.6, 620.8, 645.4, 670.5, 694.9, 720.3, 745.0]
ID_Y = [241.5, 263.6, 285.5, 307.6, 329.2, 350.6, 372.9, 394.4, 416.2, 437.6]
ID_DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
LETTERS = "abcd"

DEFAULTS = dict(fill_threshold=75, faint_threshold=90, cross_min=0.04,
                cross_diff=0.04, cross_single=0.10, scribble=0.35)


# --------------------------------------------------------------------------
# Image processing
# --------------------------------------------------------------------------
def find_corners(img):
    _, b = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY_INV)
    n, _, st, cen = cv2.connectedComponentsWithStats(b)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 25 < w < 70 and 25 < h < 70 and a > 0.8 * w * h:
            out.append(cen[i])
    return out


def order_corners(c):
    p = np.array(c, np.float32)
    s = p.sum(1)
    d = p[:, 0] - p[:, 1]
    return np.float32([p[s.argmin()], p[d.argmax()], p[d.argmin()], p[s.argmax()]])


def align(img):
    """Return (aligned image, ok). Falls back to a plain resize if the 4 marks are not found."""
    c = find_corners(img)
    if len(c) == 4:
        M = cv2.getPerspectiveTransform(order_corners(c), CORNERS_DST)
        return cv2.warpPerspective(img, M, (W, H), borderValue=255), True
    return cv2.resize(img, (W, H)), False


_DISK = {}


def _disk(r):
    if r not in _DISK:
        m = np.zeros((2 * r + 1, 2 * r + 1), bool)
        cv2.circle(m.view(np.uint8), (r, r), r, 1, -1)
        _DISK[r] = m
    return _DISK[r]


def bubble_score(im, x, y, r=5):
    """Darkness (0-255) inside a small disk; best of a 3x3 shift to tolerate misalignment."""
    d = _disk(r)
    best = 0.0
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            cx, cy = int(round(x + dx)), int(round(y + dy))
            patch = im[cy - r:cy + r + 1, cx - r:cx + r + 1]
            if patch.shape != d.shape:
                continue
            best = max(best, 255 - float(patch[d].mean()))
    return best


_RING = {}


def ring_ink(im, x, y, r0=10, r1=15):
    """Fraction of dark pixels in the ring just outside the bubble (strokes of a crossing-out X)."""
    if (r0, r1) not in _RING:
        m = np.zeros((2 * r1 + 1, 2 * r1 + 1), np.uint8)
        cv2.circle(m, (r1, r1), r1, 1, -1)
        cv2.circle(m, (r1, r1), r0, 0, -1)
        _RING[(r0, r1)] = m.astype(bool)
    m = _RING[(r0, r1)]
    cx, cy = int(round(x)), int(round(y))
    patch = im[cy - r1:cy + r1 + 1, cx - r1:cx + r1 + 1]
    if patch.shape != m.shape:
        return 0.0
    return float((patch[m] < 140).mean())


def measure(im):
    A = np.zeros((25, 4))
    O = np.zeros((25, 4))
    for q in range(25):
        for k, x in enumerate(COLS_X):
            A[q, k] = bubble_score(im, x, ROWS_Y[q])
            O[q, k] = ring_ink(im, x, ROWS_Y[q])
        O[q] -= O[q].min()  # remove printed-background baseline of this row
    I = np.zeros((10, 7))
    for j, x in enumerate(ID_X):
        for i, y in enumerate(ID_Y):
            I[i, j] = bubble_score(im, x, y, 4)
    return A, O, I


def decode_id(I, th):
    s = ""
    for j in range(7):
        on = [ID_DIGITS[i] for i in range(10) if I[i, j] > th]
        s += str(on[0]) if len(on) == 1 else ("?" if not on else "[" + "".join(map(str, on)) + "]")
    return s


def interpret(A, O, par):
    """Turn measurements into answers + flags. Flag levels: check (needs a human), auto (resolved, FYI)."""
    th = par["fill_threshold"]
    ans, flags = [], []
    for q in range(25):
        on = [k for k in range(4) if A[q, k] > th]
        if len(on) == 1:
            k = on[0]
            ans.append(LETTERS[k])
            if O[q, k] > par["cross_single"]:
                flags.append(dict(q=q + 1, level="check", msg="single mark with ink outside the bubble (crossed out?)"))
            elif A[q, k] < par["faint_threshold"]:
                flags.append(dict(q=q + 1, level="check", msg="faint mark"))
        elif not on:
            ans.append("")
            flags.append(dict(q=q + 1, level="check", msg="blank"))
        else:
            order = sorted(on, key=lambda k: -O[q, k])
            top, second = O[q, order[0]], O[q, order[1]]
            names = "/".join(LETTERS[k].upper() for k in on)
            if top > par["scribble"]:
                ans.append("")
                flags.append(dict(q=q + 1, level="check", msg=f"multiple marks {names}; heavy scribble on {LETTERS[order[0]].upper()}"))
            elif top >= par["cross_min"] and top - second >= par["cross_diff"]:
                rest = [k for k in on if k != order[0]]
                if len(rest) == 1:
                    ans.append(LETTERS[rest[0]])
                    flags.append(dict(q=q + 1, level="auto",
                                      msg=f"{LETTERS[order[0]].upper()} crossed out, kept {LETTERS[rest[0]].upper()}"))
                else:
                    ans.append("")
                    flags.append(dict(q=q + 1, level="check", msg=f"multiple marks {names}, still more than one left"))
            else:
                ans.append("")
                flags.append(dict(q=q + 1, level="check", msg=f"multiple marks {names}; cannot tell which is crossed out"))
    return ans, flags


# --------------------------------------------------------------------------
# Roster / ID resolution
# --------------------------------------------------------------------------
def load_roster(path, filename):
    import pandas as pd
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "csv":
        sheets = {"csv": pd.read_csv(path, header=None, dtype=str, sep=None, engine="python")}
    else:
        eng = "odf" if ext == "ods" else None
        sheets = pd.read_excel(path, header=None, dtype=str, sheet_name=None, engine=eng)
    best = {}
    for df in sheets.values():
        for c in df.columns:
            ids = df[c].astype(str).str.strip().str.lower().str.replace(r"^s", "", regex=True)
            ok = ids.str.fullmatch(r"\d{7}")
            if ok.sum() < 3:
                continue
            for name_col in df.columns:
                if name_col == c:
                    continue
                names = df[name_col].astype(str)
                if names[ok].str.contains(r"[A-Za-z]{2}").mean() > 0.9 and names[ok].str.fullmatch(r"\d+").sum() == 0:
                    cand = {i: n.strip() for i, n in zip(ids[ok], names[ok])}
                    if len(cand) > len(best):
                        best = cand
                    break
    return best


def resolve_id(raw, roster):
    """raw like '3[23]253961' or '3??2324' -> (id or '', note)."""
    if re.fullmatch(r"\d{7}", raw):
        if roster and raw not in roster:
            return raw, "not in roster"
        return raw, ""
    if not roster:
        return "", "ID incomplete (no roster to resolve it)"
    pat = "".join(("[0-9]" if ch == "?" else ch) for ch in re.sub(r"\[(\d+)\]", r"[\1]", raw))
    hits = [i for i in roster if re.fullmatch(pat, i)]
    if len(hits) == 1:
        return hits[0], "resolved via roster"
    return "", f"ID incomplete; {len(hits)} roster matches"


# --------------------------------------------------------------------------
# Job handling
# --------------------------------------------------------------------------
def jdir(job):
    if not re.fullmatch(r"[0-9a-f]{8}", job):
        abort(404)
    p = os.path.join(DATA, job)
    if not os.path.isdir(p):
        abort(404)
    return p


def load_json(path, default=None):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def render_pdf(path):
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed (pip install pymupdf)")
    doc = fitz.open(path)
    z = 150 / 72
    for pg in doc:
        pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), colorspace=fitz.csGRAY, alpha=False)
        yield np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)


def process_job(job, par, key, roster):
    d = jdir(job)
    os.makedirs(os.path.join(d, "pages"), exist_ok=True)
    pages = []
    for n, raw in enumerate(render_pdf(os.path.join(d, "source.pdf")), start=1):
        im, ok = align(raw)
        cv2.imwrite(os.path.join(d, "pages", f"{n:03d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
        A, O, I = measure(im)
        ans, flags = interpret(A, O, par)
        raw_id = decode_id(I, par["fill_threshold"])
        sid, note = resolve_id(raw_id, roster)
        if not ok:
            flags.insert(0, dict(q=0, level="check", msg="corner marks not found: page not aligned, readings unreliable"))
        pages.append(dict(page=n, id_raw=raw_id, id=sid, id_note=note, name=roster.get(sid, ""),
                          answers=ans, flags=flags, reviewed=False, aligned=ok,
                          A=np.round(A, 0).tolist(), O=np.round(O, 3).tolist()))
    seen = {}
    for p in pages:
        if p["id"]:
            seen.setdefault(p["id"], []).append(p["page"])
    for p in pages:
        if p["id"] and len(seen[p["id"]]) > 1:
            p["id_note"] = (p["id_note"] + "; " if p["id_note"] else "") + "duplicate on pages " + ",".join(map(str, seen[p["id"]]))
    save_json(os.path.join(d, "results.json"), pages)


def score(answers, key):
    if not key:
        return None
    return sum(1 for a, k in zip(answers, key) if a and a == k)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024


@app.route("/")
def index():
    jobs = []
    for j in sorted(os.listdir(DATA), key=lambda x: -os.path.getmtime(os.path.join(DATA, x))):
        meta = load_json(os.path.join(DATA, j, "meta.json"))
        if meta:
            res = load_json(os.path.join(DATA, j, "results.json"), [])
            meta.update(id=j, n=len(res), reviewed=sum(1 for p in res if p["reviewed"]))
            jobs.append(meta)
    return render_template_string(INDEX, jobs=jobs, fitz_ok=fitz is not None, par=DEFAULTS)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("pdf")
    if not f or not f.filename.lower().endswith(".pdf"):
        return "Please choose a PDF", 400
    job = uuid.uuid4().hex[:8]
    d = os.path.join(DATA, job)
    os.makedirs(d)
    f.save(os.path.join(d, "source.pdf"))
    key = re.sub(r"[^a-d]", "", request.form.get("key", "").lower())
    if key and len(key) != 25:
        shutil.rmtree(d)
        return "The answer key must contain exactly 25 letters a-d", 400
    roster = {}
    rf = request.files.get("roster")
    if rf and rf.filename:
        rp = os.path.join(d, "roster_upload" + os.path.splitext(rf.filename)[1])
        rf.save(rp)
        try:
            roster = load_roster(rp, rf.filename)
        except Exception as e:  # noqa
            shutil.rmtree(d)
            return f"Could not read the roster: {e}", 400
        if not roster:
            shutil.rmtree(d)
            return "No student numbers (7 digits) + names found in the roster file", 400
    par = dict(DEFAULTS)
    for k in par:
        try:
            par[k] = float(request.form.get(k, par[k]))
        except ValueError:
            pass
    save_json(os.path.join(d, "meta.json"), dict(title=request.form.get("title") or os.path.splitext(f.filename)[0],
                                                 filename=f.filename, key=key, roster=roster, par=par,
                                                 created=time.strftime("%Y-%m-%d %H:%M")))
    try:
        process_job(job, par, key, roster)
    except Exception as e:  # noqa
        shutil.rmtree(d)
        return f"Processing failed: {e}", 500
    return redirect(url_for("job_page", job=job))


@app.route("/job/<job>")
def job_page(job):
    jdir(job)
    return render_template_string(JOB, job=job)


@app.route("/api/job/<job>")
def api_job(job):
    d = jdir(job)
    meta = load_json(os.path.join(d, "meta.json"))
    res = load_json(os.path.join(d, "results.json"))
    for p in res:
        p.pop("A", None)
        p.pop("O", None)
    geo = dict(W=W, H=H, rows_y=ROWS_Y, cols_x=COLS_X, id_x=ID_X, id_y=ID_Y, id_digits=ID_DIGITS)
    return jsonify(meta=dict(title=meta["title"], key=meta["key"], n_roster=len(meta["roster"])), pages=res, geo=geo)


@app.route("/api/job/<job>/page/<int:n>", methods=["GET"])
def api_page(job, n):
    res = load_json(os.path.join(jdir(job), "results.json"))
    if not 1 <= n <= len(res):
        abort(404)
    return jsonify(res[n - 1])


@app.route("/api/job/<job>/page/<int:n>", methods=["POST"])
def api_page_save(job, n):
    d = jdir(job)
    path = os.path.join(d, "results.json")
    res = load_json(path)
    meta = load_json(os.path.join(d, "meta.json"))
    if not 1 <= n <= len(res):
        abort(404)
    body = request.get_json(force=True)
    p = res[n - 1]
    ans = body.get("answers", p["answers"])
    p["answers"] = [a if a in list(LETTERS) else "" for a in ans][:25]
    sid = re.sub(r"\D", "", str(body.get("id", p["id"])))
    p["id"] = sid
    p["name"] = str(body.get("name", p["name"]))[:120]
    if sid and sid in meta["roster"] and not p["name"]:
        p["name"] = meta["roster"][sid]
    p["reviewed"] = bool(body.get("reviewed", p["reviewed"]))
    save_json(path, res)
    return jsonify(ok=True, name=p["name"])


@app.route("/api/job/<job>/key", methods=["POST"])
def api_key(job):
    d = jdir(job)
    meta = load_json(os.path.join(d, "meta.json"))
    key = re.sub(r"[^a-d]", "", str(request.get_json(force=True).get("key", "")).lower())
    if key and len(key) != 25:
        return jsonify(ok=False, error="need exactly 25 letters a-d"), 400
    meta["key"] = key
    save_json(os.path.join(d, "meta.json"), meta)
    return jsonify(ok=True, key=key)


@app.route("/img/<job>/<int:n>.jpg")
def img_page(job, n):
    return send_file(os.path.join(jdir(job), "pages", f"{n:03d}.jpg"), mimetype="image/jpeg", max_age=3600)


@app.route("/crop/<job>/<int:n>/<int:q>.png")
def img_crop(job, n, q):
    if not 1 <= q <= 25:
        abort(404)
    im = cv2.imread(os.path.join(jdir(job), "pages", f"{n:03d}.jpg"), 0)
    if im is None:
        abort(404)
    y = int(ROWS_Y[q - 1])
    c = cv2.resize(im[y - 18:y + 18, 170:385], None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".png", c)
    return send_file(io.BytesIO(buf.tobytes()), mimetype="image/png", max_age=3600)


def table_rows(job):
    d = jdir(job)
    meta = load_json(os.path.join(d, "meta.json"))
    res = load_json(os.path.join(d, "results.json"))
    rows = []
    for p in res:
        full = p["name"] or meta["roster"].get(p["id"], "")
        sur = full.split(",")[0].strip().lower() if full else ""
        sc = score(p["answers"], meta["key"])
        issues = "; ".join(f"Q{f['q']}: {f['msg']}" for f in p["flags"] if f["level"] == "check")
        rows.append(dict(name=sur, id=p["id"], answers=p["answers"], page=p["page"], full=full, score=sc,
                         reviewed="yes" if p["reviewed"] else "no", issues=issues))
    return meta, rows


@app.route("/export/<job>.csv")
def export_csv(job):
    meta, rows = table_rows(job)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["name", "student number"] + list(range(1, 26)) + ["page", "full name", "score", "reviewed", "open issues"])
    if meta["key"]:
        w.writerow(["key", ""] + list(meta["key"]))
    for r in rows:
        w.writerow([r["name"], r["id"]] + r["answers"] + [r["page"], r["full"], "" if r["score"] is None else r["score"], r["reviewed"], r["issues"]])
    return send_file(io.BytesIO(out.getvalue().encode("utf-8-sig")), mimetype="text/csv", as_attachment=True,
                     download_name=f"{meta['title']}.csv")


@app.route("/export/<job>.xlsx")
def export_xlsx(job):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    meta, rows = table_rows(job)
    wb = Workbook()
    ws = wb.active
    ws.title = "answers"
    ws.append(["name", "student number"] + list(range(1, 26)) + ["page", "full name", "score", "reviewed", "open issues"])
    if meta["key"]:
        ws.append(["key", None] + list(meta["key"]))
    for r in rows:
        ws.append([r["name"], int(r["id"]) if r["id"] else None] + r["answers"] +
                  [r["page"], r["full"], r["score"], r["reviewed"], r["issues"]])
    for c in ws[1]:
        c.font = Font(bold=True)
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name=f"{meta['title']}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/job/<job>/delete", methods=["POST"])
def delete(job):
    shutil.rmtree(jdir(job))
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------
BASE_CSS = """
:root{--bg:#f6f7f9;--fg:#1d2330;--mut:#667;--card:#fff;--line:#d9dde4;--ok:#1a8a3c;--warn:#d98200;--bad:#c62828;--acc:#2456c8}
*{box-sizing:border-box}body{margin:0;font:14px/1.4 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
a{color:var(--acc)}button,.btn{font:inherit;padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:pointer;text-decoration:none;color:var(--fg)}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}input,select{font:inherit;padding:5px 7px;border:1px solid var(--line);border-radius:6px}
"""

INDEX = """<!doctype html><meta charset=utf-8><title>MC form reader</title><style>""" + BASE_CSS + """
main{max-width:900px;margin:30px auto;padding:0 16px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:20px}
label{display:block;margin:10px 0 3px;font-weight:600}small{color:var(--mut)}table{width:100%;border-collapse:collapse}td,th{padding:6px;border-bottom:1px solid var(--line);text-align:left}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
</style><main><h1>MC form reader</h1>
{% if not fitz_ok %}<div class=card style="border-color:var(--bad)">PyMuPDF is missing: <code>pip install pymupdf</code></div>{% endif %}
<div class=card><h3>New job</h3>
<form method=post action="/upload" enctype=multipart/form-data>
<label>Scanned PDF (one form per page)</label><input type=file name=pdf accept=".pdf" required>
<label>Title <small>(used for the export file names)</small></label><input name=title placeholder="e.g. sensors test 2" style="width:100%">
<label>Answer key <small>(optional; 25 letters a-d, e.g. cdcdbaaadabbdcacbbbcbddc c)</small></label><input name=key style="width:100%" placeholder="25 letters, spaces allowed">
<label>Roster <small>(optional; Canvas export as csv / xlsx / ods; used to resolve unreadable student numbers and to fill names)</small></label><input type=file name=roster accept=".csv,.xlsx,.xls,.ods">
<details style="margin-top:12px"><summary>Detection thresholds</summary><div class=grid>
{% for k,v in par.items() %}<div><label>{{k}}</label><input name="{{k}}" value="{{v}}"></div>{% endfor %}</div></details>
<p><button class=primary>Upload and process</button></p></form></div>
<div class=card><h3>Earlier jobs</h3>{% if jobs %}<table><tr><th>title<th>created<th>pages<th>reviewed<th><th></tr>
{% for j in jobs %}<tr><td><a href="/job/{{j.id}}">{{j.title}}</a><td>{{j.created}}<td>{{j.n}}<td>{{j.reviewed}} / {{j.n}}
<td><a href="/export/{{j.id}}.csv">csv</a> &middot; <a href="/export/{{j.id}}.xlsx">xlsx</a>
<td><form method=post action="/job/{{j.id}}/delete" onsubmit="return confirm('Delete this job and its images?')"><button>delete</button></form></tr>{% endfor %}</table>
{% else %}<small>nothing yet</small>{% endif %}</div></main>"""

JOB = """<!doctype html><meta charset=utf-8><title>review</title><style>""" + BASE_CSS + """
body{height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{display:flex;gap:12px;align-items:center;padding:8px 14px;background:#fff;border-bottom:1px solid var(--line)}header h2{margin:0;font-size:16px;flex:1}
#wrap{flex:1;display:grid;grid-template-columns:270px minmax(300px,1fr) 400px;min-height:0}
#list{overflow:auto;background:#fff;border-right:1px solid var(--line)}#list div{padding:6px 10px;border-bottom:1px solid var(--line);cursor:pointer;display:flex;gap:6px;align-items:center}
#list div.sel{background:#e5edff}#list .t{flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.chip{font-size:11px;padding:1px 6px;border-radius:9px;color:#fff}.c-ok{background:var(--ok)}.c-warn{background:var(--warn)}.c-bad{background:var(--bad)}.c-grey{background:#99a}
#view{overflow:auto;padding:8px;position:relative}#stage{position:relative;width:100%;max-width:900px;margin:auto}#stage img{width:100%;display:block;border:1px solid var(--line)}#stage svg{position:absolute;inset:0;width:100%;height:100%}
#side{overflow:auto;background:#fff;border-left:1px solid var(--line);padding:10px}
.row{display:grid;grid-template-columns:34px 1fr auto;gap:6px;align-items:center;padding:3px 4px;border-radius:5px}.row.chk{background:#fff1d6}.row.aut{background:#e8f6ec}.row.done{opacity:.6}
.opts button{width:30px;padding:3px 0;margin-right:2px}.opts button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.msg{font-size:12px;color:var(--mut);grid-column:2/4}.crop{height:42px;border:1px solid var(--line);grid-column:1/4}
input.id{width:110px;font-family:monospace;font-size:15px}.note{font-size:12px;color:var(--warn)}
.kbd{font-size:11px;color:var(--mut)}
</style>
<header><a href="/">&larr; jobs</a><h2 id=title></h2><span>key: <input id=key size=30 placeholder="25 letters"> </span><button onclick="saveKey()">set</button>
<a class=btn id=ecsv>csv</a><a class=btn id=exlsx>xlsx</a></header>
<div id=wrap><div id=list></div><div id=view><div id=stage><img id=pimg><svg id=ov viewBox="0 0 1240 1755"></svg></div></div>
<div id=side></div></div>
<script>
const JOB="{{job}}";let D=null,cur=0,P=null,dirty=false,onlyFlag=false;
const $=s=>document.querySelector(s);
async function init(){D=await (await fetch('/api/job/'+JOB)).json();$('#title').textContent=D.meta.title+'  ('+D.pages.length+' pages)';
 $('#key').value=D.meta.key;$('#ecsv').href='/export/'+JOB+'.csv';$('#exlsx').href='/export/'+JOB+'.xlsx';buildList();
 const first=D.pages.findIndex(p=>!p.reviewed);open(first<0?0:first);}
function score(a){const k=D.meta.key;if(!k)return null;let s=0;a.forEach((v,i)=>{if(v&&v===k[i])s++});return s}
function chip(p){const n=p.flags.filter(f=>f.level==='check').length;
 if(p.reviewed)return '<span class="chip c-ok">done</span>';if(n)return '<span class="chip c-warn">'+n+' check</span>';return '<span class="chip c-grey">ok</span>'}
function buildList(){const L=$('#list');L.innerHTML='';D.pages.forEach((p,i)=>{const d=document.createElement('div');d.id='li'+i;
 const s=score(p.answers);d.innerHTML='<b>'+p.page+'</b><span class=t>'+(p.name||p.id||'(no id)')+'</span>'+(s===null?'':'<small>'+s+'</small>')+chip(p)+(p.id_note?'<span class="chip c-bad" title="'+p.id_note+'">id</span>':'');
 d.onclick=()=>open(i);L.appendChild(d)});}
async function open(i){if(dirty)await save(false);cur=i;P=JSON.parse(JSON.stringify(D.pages[i]));dirty=false;
 document.querySelectorAll('#list div').forEach(e=>e.classList.remove('sel'));const li=$('#li'+i);li.classList.add('sel');li.scrollIntoView({block:'nearest'});
 $('#pimg').src='/img/'+JOB+'/'+P.page+'.jpg';render();}
function render(){drawOverlay();const S=$('#side');let h='';
 h+='<div><b>Page '+P.page+'</b> '+(P.aligned?'':'<span class="chip c-bad">not aligned</span>')+'</div>';
 h+='<div style="margin:8px 0">student number <input class=id id=sid value="'+P.id+'" oninput="P.id=this.value;dirty=true"> <small>read: <code>'+P.id_raw+'</code></small></div>';
 if(P.id_note)h+='<div class=note>'+P.id_note+'</div>';
 h+='<div style="margin:8px 0">name <input id=nm style="width:290px" value="'+(P.name||'').replace(/"/g,'&quot;')+'" oninput="P.name=this.value;dirty=true"></div>';
 const sc=score(P.answers);h+='<div style="margin:6px 0">score: <b>'+(sc===null?'(no key)':sc+' / 25')+'</b> &nbsp; <label><input type=checkbox '+(P.reviewed?'checked':'')+' onchange="P.reviewed=this.checked;dirty=true;buildList();selList()"> reviewed</label></div>';
 h+='<div style="margin:6px 0"><button class=primary onclick="saveNext()">save &amp; next page</button> <button onclick="save(true)">save</button> <label><input type=checkbox '+(onlyFlag?'checked':'')+' onchange="onlyFlag=this.checked;render()"> only flagged</label></div>';
 h+='<div class=kbd>click a letter to set the answer; click it again to clear</div><div style="margin-top:6px">';
 const fl={};P.flags.forEach(f=>{(fl[f.q]=fl[f.q]||[]).push(f)});
 if(fl[0])h+='<div class=note>'+fl[0].map(f=>f.msg).join('; ')+'</div>';
 for(let q=1;q<=25;q++){const f=fl[q]||[];const lvl=f.some(x=>x.level==='check')?'chk':(f.length?'aut':'');if(onlyFlag&&!lvl)continue;
  h+='<div class="row '+lvl+'"><b>'+q+'</b><span class=opts>'+'abcd'.split('').map(c=>'<button class="'+(P.answers[q-1]===c?'on':'')+'" onclick="setA('+q+',\\''+c+'\\')">'+c.toUpperCase()+'</button>').join('')+'</span>'
   +'<span>'+(D.meta.key?(P.answers[q-1]===D.meta.key[q-1]?'<span style="color:var(--ok)">&#10003;</span>':'<span style="color:var(--bad)">&#10007;</span>'):'')+'</span>';
  if(f.length)h+='<div class=msg>'+f.map(x=>x.msg).join('; ')+'</div><img class=crop src="/crop/'+JOB+'/'+P.page+'/'+q+'.png">';
  h+='</div>';}
 S.innerHTML=h+'</div>';}
function selList(){const li=$('#li'+cur);if(li)li.classList.add('sel')}
function setA(q,c){P.answers[q-1]=(P.answers[q-1]===c?'':c);dirty=true;render();drawOverlay()}
function drawOverlay(){const g=D.geo;let s='';const key=D.meta.key;
 for(let q=0;q<25;q++){const f=P.flags.filter(x=>x.q===q+1);const bad=f.some(x=>x.level==='check');
  for(let k=0;k<4;k++){const c='abcd'[k];if(P.answers[q]===c)s+='<circle cx="'+g.cols_x[k]+'" cy="'+g.rows_y[q]+'" r="13" fill="none" stroke="'+(bad?'#d98200':'#1a8a3c')+'" stroke-width="3"/>';}
  if(!P.answers[q])s+='<rect x="170" y="'+(g.rows_y[q]-14)+'" width="215" height="28" fill="none" stroke="#c62828" stroke-width="3"/>';
  else if(bad)s+='<rect x="170" y="'+(g.rows_y[q]-14)+'" width="215" height="28" fill="none" stroke="#d98200" stroke-width="2" stroke-dasharray="5 3"/>';
  if(key&&P.answers[q]&&P.answers[q]!==key[q]){const k=P.answers[q].charCodeAt(0)-97;}}
 const id=(P.id||'').padEnd(7,' ');for(let j=0;j<7;j++){const d=id[j];if(d===' ')continue;const i=g.id_digits.indexOf(+d);if(i<0)continue;
  s+='<circle cx="'+g.id_x[j]+'" cy="'+g.id_y[i]+'" r="11" fill="none" stroke="#2456c8" stroke-width="3"/>';}
 $('#ov').innerHTML=s;}
async function save(show){const body={answers:P.answers,id:P.id,name:P.name,reviewed:P.reviewed};
 const r=await fetch('/api/job/'+JOB+'/page/'+P.page,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const j=await r.json();if(j.name&&!P.name){P.name=j.name}
 D.pages[cur]=Object.assign(D.pages[cur],{answers:P.answers.slice(),id:P.id,name:P.name,reviewed:P.reviewed});dirty=false;buildList();selList();if(show)render();}
async function saveNext(){P.reviewed=true;await save(false);if(cur<D.pages.length-1)open(cur+1);else render();}
async function saveKey(){const r=await fetch('/api/job/'+JOB+'/key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:$('#key').value})});
 const j=await r.json();if(!j.ok){alert(j.error);return}D.meta.key=j.key;$('#key').value=j.key;buildList();selList();render()}
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});
init();
</script>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)
