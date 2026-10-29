#!/usr/bin/env python3
"""Pull README.md / context.md (and the pictures they use) from the project repos.

Reads repos.yml, shallow-clones every repository, and writes

    docs/projects/<repo>/index.md      <- README.md
    docs/projects/<repo>/context.md    <- context.md (optional)
    docs/projects/<repo>/<images...>   <- only the files the two documents refer to
    docs/projects/index.md             <- overview with one card per project

It also rewrites the menu in zensical.toml between the BEGIN/END GENERATED NAV markers.
A repository that cannot be cloned or has no README is skipped with a warning.

Usage:  python scripts/sync_projects.py            (run from the site repository)
"""
from __future__ import annotations

import datetime as dt
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "projects"
TOML = ROOT / "zensical.toml"

ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".mp4", ".webm"}
MAX_ASSET_BYTES = 10 * 1024 * 1024
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


# --------------------------------------------------------------------------- git
def clone(owner: str, repo: str, branch: str | None, dest: Path) -> None:
    cmd = ["git", "clone", "--depth", "1", "--quiet"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [f"https://github.com/{owner}/{repo}.git", str(dest)]
    subprocess.run(cmd, check=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


def current_branch(repo_dir: Path) -> str:
    out = subprocess.run(["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                         capture_output=True, text=True)
    return out.stdout.strip() or "HEAD"


# ------------------------------------------------------------------ link rewriting
class Rewriter:
    """Makes one document from a repository work on the site."""

    def __init__(self, owner, repo, branch, repo_dir, project_dir, is_index, copied):
        self.owner, self.repo, self.branch = owner, repo, branch
        self.repo_dir, self.project_dir = repo_dir, project_dir
        self.is_index = is_index   # README -> index.md (directory URL); context -> its own page
        self.copied = copied       # relative paths copied so far
        self.missing: set[str] = set()   # pictures the document refers to that do not exist

    def github(self, rel: str, is_dir: bool) -> str:
        kind = "tree" if is_dir else "blob"
        return f"https://github.com/{self.owner}/{self.repo}/{kind}/{self.branch}/{rel}"

    def copy_asset(self, rel: str) -> bool:
        src = (self.repo_dir / rel).resolve()
        try:
            src.relative_to(self.repo_dir.resolve())
        except ValueError:
            return False
        if not src.is_file() or src.stat().st_size > MAX_ASSET_BYTES:
            return False
        dst = self.project_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self.copied.add(rel)
        return True

    def target(self, url: str, in_html: bool) -> str:
        """URL to use on the site for a link or image found in the repo's document."""
        if not url or url.startswith("#") or url.startswith("//") or SCHEME.match(url):
            return url
        path, sep, frag = url.partition("#")
        path = path.split("?")[0]
        frag = sep + frag if frag else ""
        rel = unquote(path)
        while rel.startswith("./"):
            rel = rel[2:]
        rel = rel.lstrip("/")
        low = rel.lower()
        if low == "readme.md":
            return ("./" if self.is_index else "../") + frag
        if low == "context.md":
            return ("context.md" if self.is_index else "./") + frag
        target = self.repo_dir / rel
        if Path(rel).suffix.lower() in ASSET_EXT and self.copy_asset(rel):
            # Raw HTML is not rewritten by the site generator, so make that path page-relative.
            prefix = "../" if (in_html and not self.is_index) else ""
            return prefix + path
        if Path(rel).suffix.lower() in ASSET_EXT and not target.exists():
            self.missing.add(rel)
        if rel and target.exists():
            return self.github(rel, target.is_dir()) + frag
        return url  # unknown: leave as it is

    def apply(self, text: str) -> str:
        # leave fenced code blocks untouched
        parts = re.split(r"(^(?:```|~~~).*?^(?:```|~~~)[^\n]*$)", text, flags=re.S | re.M)
        return "".join(p if i % 2 else self._rewrite(p) for i, p in enumerate(parts))

    def _rewrite(self, text: str) -> str:
        # ![alt](url "title")  and  [text](url "title")
        def md(m):
            return f"{m.group(1)}({self.target(m.group(2), False)}{m.group(3) or ''})"
        text = re.sub(r"(!?\[[^\]]*\])\(\s*([^)\s]+)(\s+\"[^\"]*\")?\s*\)", md, text)

        # <img src="..."> / <a href="..."> / <source src="...">
        def attr(m):
            return f'{m.group(1)}="{self.target(m.group(2), True)}"'
        return re.sub(r"\b(src|href)=\"([^\"]+)\"", attr, text)


# ------------------------------------------------------------------------- pages
def yaml_str(s: str) -> str:
    return yaml.safe_dump(" ".join(s.split()), default_flow_style=True, width=100000).splitlines()[0]


def front_matter(title: str, description: str = "") -> str:
    lines = ["---", f"title: {yaml_str(title)}"]
    if description:
        lines.append(f"description: {yaml_str(description)}")
    lines.append("---\n")
    return "\n".join(lines)


def build_project(owner: str, p: dict, workdir: Path) -> dict | None:
    repo = p["repo"]
    repo_dir = workdir / repo
    try:
        clone(owner, repo, p.get("branch"), repo_dir)
    except subprocess.CalledProcessError:
        print(f"  ! {repo}: clone failed, skipped", file=sys.stderr)
        return None
    readme = next((f for f in repo_dir.iterdir() if f.name.lower() == "readme.md"), None)
    if readme is None:
        print(f"  ! {repo}: no README.md, skipped", file=sys.stderr)
        return None

    branch = p.get("branch") or current_branch(repo_dir)
    project_dir = OUT / repo
    project_dir.mkdir(parents=True, exist_ok=True)
    copied: set[str] = set()
    title = p.get("title", repo)
    repo_url = f"https://github.com/{owner}/{repo}"
    context = next((f for f in repo_dir.iterdir() if f.name.lower() == "context.md"), None)

    # README -> index.md
    rw = Rewriter(owner, repo, branch, repo_dir, project_dir, True, copied)
    body = rw.apply(readme.read_text(encoding="utf-8"))
    missing = set(rw.missing)
    footer = f"\n\n---\n\nSource: [{owner}/{repo}]({repo_url}), synced {dt.date.today().isoformat()}."
    if context:
        footer += " Background and design decisions: [developer notes](context.md)."
    (project_dir / "index.md").write_text(
        front_matter(title, p.get("summary", "")) + body + footer + "\n", encoding="utf-8")

    # context.md -> context.md
    if context:
        rw_ctx = Rewriter(owner, repo, branch, repo_dir, project_dir, False, copied)
        notes = rw_ctx.apply(context.read_text(encoding="utf-8"))
        missing |= rw_ctx.missing
        intro = ('!!! note "Developer notes"\n'
                 "    Written for people (and AI-assisted sessions) who continue work on this "
                 "project. For what it is and how to build it, see the [project page](./).\n\n")
        (project_dir / "context.md").write_text(
            front_matter(f"{title}: developer notes") + intro + notes + "\n", encoding="utf-8")

    # card image
    image = p.get("image")
    if image and not rw.copy_asset(image):
        print(f"  ! {repo}: image '{image}' not found", file=sys.stderr)
        image = None

    print(f"  ok {repo}: {len(copied)} file(s) copied" + (", with developer notes" if context else ""))
    for rel in sorted(missing):
        print(f"  ! {repo}: referenced but not in the repository: {rel}", file=sys.stderr)
    return {**p, "title": title, "image": image, "has_context": context is not None}


def card(p: dict) -> str:
    img = (f'<img src="{p["repo"]}/{p["image"]}" alt="" loading="lazy">' if p.get("image")
           else '<span class="project-card__noimg"></span>')
    status = f'<small>{html.escape(p["status"])}</small>' if p.get("status") else ""
    summary = html.escape(" ".join(p.get("summary", "").split()))
    return (f'<a class="project-card" href="{p["repo"]}/">{img}'
            f'<span class="project-card__body"><strong>{html.escape(p["title"])}</strong>'
            f'<span>{summary}</span>{status}</span></a>')


def write_overview(projects: list[dict]) -> None:
    cards = "\n".join(card(p) for p in projects)
    (OUT / "index.md").write_text(
        "---\ntitle: Projects\nhide:\n  - toc\n---\n\n# Projects\n\n"
        "Each project page is the README of its GitHub repository; the developer notes explain "
        "the decisions behind it.\n\n"
        f'<div class="project-grid">\n{cards}\n</div>\n', encoding="utf-8")


def nav_block(projects: list[dict]) -> str:
    items = ['  { "Projects" = [', '    "projects/index.md",']
    for p in projects:
        pages = [f'"projects/{p["repo"]}/index.md"']
        if p["has_context"]:
            pages.append(f'{{ "Developer notes" = "projects/{p["repo"]}/context.md" }}')
        title = p["title"].replace('"', '\\"')
        items.append(f'    {{ "{title}" = [{", ".join(pages)}] }},')
    items.append("  ] },")
    return "\n".join(items)


def write_nav(projects: list[dict]) -> None:
    text = TOML.read_text(encoding="utf-8")
    pattern = re.compile(r"(  # BEGIN GENERATED NAV\n).*?(  # END GENERATED NAV)", re.S)
    if not pattern.search(text):
        sys.exit("zensical.toml: BEGIN/END GENERATED NAV markers not found")
    TOML.write_text(pattern.sub(lambda m: m.group(1) + nav_block(projects) + "\n" + m.group(2), text),
                    encoding="utf-8")


def main() -> None:
    cfg = yaml.safe_load((ROOT / "repos.yml").read_text(encoding="utf-8"))
    owner = cfg["owner"]
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    done = []
    print(f"Syncing {len(cfg['projects'])} project(s) from github.com/{owner}")
    with tempfile.TemporaryDirectory() as tmp:
        for p in cfg["projects"]:
            result = build_project(owner, p, Path(tmp))
            if result:
                done.append(result)
    if not done:
        sys.exit("No projects could be synced.")
    write_overview(done)
    write_nav(done)
    print(f"Done: {len(done)} project(s).")


if __name__ == "__main__":
    main()
