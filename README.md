# THOUGHTS v2 — a SKOS thesaurus browser

Point it at a SPARQL endpoint holding a SKOS thesaurus and you get:

- a **hierarchy** you can expand, with breadcrumbs for every route to a concept (polyhierarchy welcome)
- a **graph** of the current concept and its neighbours: blobs on sticks, wobbling, draggable
- **search** across concept names (instant) and synonyms
- a **details** view of everything said about a concept (right-click a node, or tap the centre node on a phone)
- a **brain**: drag concepts into it, combine them with AND / OR, and search the web for where they meet
- a **download** button for the data, as Turtle
- links you can share: `…/#uri=<concept URI>`

It runs as plain CGI. Drop the files on a web server that runs `.py` as CGI and it works. There's nothing to `pip install`, no framework, and no process to keep running.

## What it needs

**On the server:** Apache (or anything that runs CGI) and Python 3.8+. Only the standard library is used.

**In the data:** plain SKOS, nothing else.

What's in the hierarchy (the tree, the graph and search alike) is strictly:

- a `skos:Concept` with a `skos:prefLabel`, or
- a `skos:ConceptScheme` with a `skos:prefLabel` or `dct:title`,

with the label in your chosen language. Anything else stays out. That includes PoolParty's deprecated concepts, which keep a `dct:title` but lose their SKOS type. The details view still shows everything said about a concept.

| it uses | for |
|---|---|
| `skos:ConceptScheme` | the roots of the hierarchy |
| `skos:hasTopConcept` / `skos:topConceptOf` (either) | the scheme's top concepts |
| `skos:narrower` / `skos:broader` (either) | everything below |
| `skos:related` | sideways links in the graph |
| `skos:altLabel`, `skos:hiddenLabel` | synonyms, for search |
| `skos:inScheme` | placing concepts that have no parent |

A concept with several parents shows up under each of them, with a breadcrumb for each route. Concepts with no parent go at the top of their scheme. Concepts with no scheme become roots of their own.

## Install

1. Copy everything in this folder into a directory your web server can see:

   ```
   index.html   tree.py   concept.py   details.py   search.py   download.py
   sparql.py    config.py .htaccess
   ```

2. Make the scripts executable:

   ```sh
   chmod +x *.py
   ```

3. Edit `config.py`. At minimum, set `ENDPOINT_URL`.

4. Let Apache run them. The included `.htaccess` does it, if your server allows overrides (`AllowOverride Options FileInfo AuthConfig`, or `All`). Otherwise put the same lines in your vhost:

   ```apache
   <Directory /var/www/html/thesaurus>
       Options +ExecCGI
       AddHandler cgi-script .py
   </Directory>
   ```

   and make sure `mod_cgi` (or `mod_cgid`) is on: `a2enmod cgid`.

Open the folder in a browser.

> **Keep `config.py` private.** It holds your endpoint password. The `.htaccess` refuses requests for `config.py` and `sparql.py`. If you configure Apache some other way, do the same there.

## config.py

| setting | what it does |
|---|---|
| `ENDPOINT_URL` | your SPARQL endpoint (Blazegraph, GraphDB, Fuseki, Virtuoso, PoolParty…) |
| `USERNAME`, `PASSWORD`, `AUTH_METHOD` | credentials, if needed. `"basic"` or `"digest"` |
| `TITLE` | the browser tab title |
| `LANG` | label language. `"en"` also accepts `en-gb`, `en-us`… and prefers an exact match |
| `HOME_URI` | where to start. Empty means the first scheme |
| `PRIORITY_PREDICATES`, `EXCLUDED_PREDICATES` | ordering and hiding in the details view |
| `SEARCH_URL`, `SEARCH_LABEL` | where the brain sends its query (Google by default), and the button's wording. Set `SEARCH_URL = ""` to hide the brain |
| `SEARCH_OPERATOR` | how gathered concepts are joined to start with: `"AND"` or `"OR"` |
| `BLURB` | the text at the top of the brain's overlay |
| `DATA_DOWNLOAD` | `"endpoint"` (live, everything in the endpoint), a path to a `.ttl` file, or `""` for no button |
| `DATA_DOWNLOAD_NAME` | the downloaded file is saved as `<name>_<date>.ttl` |

The layout of the graph (spacing, how hard nodes avoid the brain and the edges, phone settings) lives in the `CONFIG` block at the top of the script in `index.html`. That's purely about display.

## How it works

The endpoint is the truth. Nothing is cached, so each page load reads it fresh:

| script | called | returns |
|---|---|---|
| `tree.py` | once per page load | the whole hierarchy (URIs, children, labels) plus display settings |
| `concept.py?uri=` | each time you move | the concept's neighbours, for the graph |
| `details.py?uri=` | right-click / tap | every property of the concept |
| `search.py?q=` | as you type | synonym matches (concept names are matched in the browser) |
| `download.py` | the download button | Turtle |

`sparql.py` is the shared helper behind all of them. It handles auth, PoolParty's quirks, label picking, and escaping anything that goes into a query. `index.html` uses [d3](https://d3js.org) for the graph, and the [Noto Sans Symbols 2](https://fonts.google.com/noto/specimen/Noto+Sans+Symbols+2) font for the tree's arrows.

Everything is keyed by URI. Two concepts with the same name stay two concepts, and search tells you which is which.

## Size

`tree.py` loads the whole hierarchy on each page load. A few thousand concepts is instant. Very large thesauri (hundreds of thousands of concepts across several schemes) work, but take a while. The page says so while it waits.
## Troubleshooting

- **The page loads but the hierarchy says it couldn't load.** The message shows what the endpoint said. Open `tree.py` directly in the browser to see the same thing as JSON.
- **You see Python source, or the browser offers to download a `.py`.** Apache isn't running them as CGI. Check `Options +ExecCGI`, `AddHandler cgi-script .py` and `mod_cgi`/`mod_cgid`.
- **500 errors.** Check the scripts are executable (`chmod +x`) and have Unix line endings, then look in Apache's error log.
- **No download button.** `DATA_DOWNLOAD` is empty, or the file isn't readable by the web server's user (it also needs to be able to pass through the folders above it).
