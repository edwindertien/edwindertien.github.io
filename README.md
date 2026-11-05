# edwindertien.github.io

Personal site with documentation of projects, built with [Zensical](https://zensical.org)
and published to GitHub Pages by GitHub Actions.

The project pages are not written here. Each project's `README.md` (and `context.md`, shown as
"Developer notes") is pulled from its own GitHub repository every time the site is built.

## What to edit where

| I want to...                                   | Edit this                                   |
|------------------------------------------------|---------------------------------------------|
| Add, remove or reorder a project               | `repos.yml`                                 |
| Change a project's card text or hero picture   | `repos.yml` (`title`, `summary`, `image`)   |
| Change the text of a project page              | The README / `context.md` in *that* repo    |
| Change the landing page (intro, featured cards)| `docs/index.md`                             |
| Change colours, card layout, spacing           | `docs/stylesheets/extra.css`                |
| Change site name, theme features, colour palette | `zensical.toml` (outside the generated menu) |
| Change when or how the site is built           | `.github/workflows/docs.yml`                |
| Change how repos are pulled in                 | `scripts/sync_projects.py`                  |
| Add standalone tools (plain HTML, no Zensical) | A folder at the repo root, see below        |

Do not edit these, they are generated and overwritten on every build:

- `docs/projects/` (the synced project pages; it is in `.gitignore`)
- the part of the `nav` in `zensical.toml` between `# BEGIN GENERATED NAV` and `# END GENERATED NAV`

### Adding a project

Add an entry to `repos.yml` and push:

```yaml
  - repo: picoObergransad          # GitHub repository name, also the URL on the site
    title: Obergransad LED Matrix  # name in the menu and on the card
    summary: A 16x16 LED matrix on a Pico W with audio and WiFi animation upload.
    image: docs/photo.jpg          # picture inside that repo, shown on the card (optional)
    status: prototype              # small label on the card (optional)
```

Only `repo` is required. The order in the file is the order in the menu and on the cards.
A repository without a README, or one that cannot be cloned, is skipped with a warning.
Names of other repositories that could be added are listed as a comment at the bottom of `repos.yml`.

To feature a project on the home page, add a card to `docs/index.md` (copy an existing
`<a class="project-card">` block). The image path there is
`projects/<repo>/<path of the image in the repo>`.

### Standalone tools (rubrics and other plain HTML)

Folders that must be served exactly as they are (for example `education/`) are not processed by
Zensical. The workflow copies them into the built site, and the list is in `docs.yml`:

```yaml
for dir in education; do   # add more folders here if needed
```

A file `education/sensors/index.html` ends up at `https://edwindertien.github.io/education/sensors/`.
A new top-level folder is only published once its name is added to that line.

## How the site is built

On every run (push to `main`/`master`, the nightly schedule at about 03:17 UTC, or the
"Run workflow" button in the Actions tab):

1. `scripts/sync_projects.py` reads `repos.yml`, clones each repository (shallow), and writes the
   project pages, the copied pictures, the projects overview and the menu into `docs/projects/`
   and `zensical.toml`.
2. `zensical build --clean` turns `docs/` into the site in `site/`.
3. The standalone folders are copied into `site/`.
4. The result is deployed to GitHub Pages.

A change in a project repository therefore shows up after the next nightly build, or immediately
after running the workflow by hand. A push to *this* repo is only needed for changes made here.

GitHub Pages must be set to Settings, Pages, Source: **GitHub Actions**.

## Testing locally

Requires Python 3.10 or newer and git.

```sh
# once
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# every time
python scripts/sync_projects.py    # pulls the READMEs; reports skipped repos and missing pictures
zensical serve                     # preview at http://localhost:8000, reloads on changes
```

Other useful commands:

```sh
zensical build --clean             # build the site into site/, like the workflow does
```

Notes:

- The sync step needs internet access and clones the public repositories over HTTPS.
- Running the sync script rewrites the generated part of the menu in `zensical.toml`. The workflow
  does the same, so you can either commit that change or discard it with `git checkout zensical.toml`.
- Edits to `docs/index.md` and `extra.css` are picked up by `zensical serve` immediately; after a
  change in `repos.yml` run the sync script again.
- Standalone folders such as `education/` are not part of the preview. To check them, build the site
  and copy them in by hand: `cp -r education site/`, then open the files from `site/`.

## Troubleshooting

| Symptom                                           | Likely cause and fix                                                       |
|---------------------------------------------------|----------------------------------------------------------------------------|
| Workflow succeeds but the old site (or nothing) is shown | Pages source is not set to "GitHub Actions"                          |
| A project is missing from the menu                | See the sync output: no README, wrong repo name, or clone failed           |
| `! referenced but not in the repository: ...`     | The README points to a picture that is not committed in that repo; fix it there |
| Broken image on a project page                    | Same as above, or the picture is larger than 10 MB (not copied)            |
| A link inside a README goes to GitHub instead of the page | Intended: links to source files and folders point to the GitHub source |
| A tool in `education/` gives a 404                | Its folder name is not in the `for dir in ...` line of `docs.yml`          |
| Private repository fails to clone                 | The script only handles public repos; a private one needs an access token in the workflow |

Zensical is still a 0.x release. If a build suddenly fails after a Zensical update, pin the
previous version in `requirements.txt` (for example `zensical==0.0.73`) and report it.