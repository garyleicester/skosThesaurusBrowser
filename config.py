# =============================================================================
# config.py  —  the only file you should need to edit
# =============================================================================
# Not a CGI script: the .htaccess that ships alongside stops it being served.

# ── SPARQL endpoint ──────────────────────────────────────────────────────────
ENDPOINT_URL = "https://example.org/blazegraph/namespace/kb/sparql"
USERNAME     = ""          # leave both empty for an open endpoint
PASSWORD     = ""
AUTH_METHOD  = "basic"     # "basic" or "digest"

# ── Display ──────────────────────────────────────────────────────────────────
TITLE = "THOUGHTS"         # browser tab title

# What goes in the hierarchy (tree, graph and search):
#   skos:Concept       with a skos:prefLabel
#   skos:ConceptScheme with a skos:prefLabel or dct:title
# in LANG. Anything else (e.g. PoolParty's deprecated concepts, which keep a
# dct:title but lose their SKOS type) is left out. Details still show all.

# Label language. Matches the language and its regional variants, so "en"
# also matches "en-gb" / "en-us"; untagged labels are always accepted.
LANG = "en"

# Concept (or scheme) URI shown on load. Leave "" to start at the first
# ConceptScheme (alphabetically by label).
HOME_URI = ""

# ── Details overlay ──────────────────────────────────────────────────────────
# Predicates shown first, in this order. Everything else follows A–Z.
PRIORITY_PREDICATES = [
    "http://www.w3.org/2004/02/skos/core#prefLabel",
    "http://www.w3.org/2004/02/skos/core#altLabel",
    "http://www.w3.org/2004/02/skos/core#definition",
    "http://www.w3.org/2004/02/skos/core#scopeNote",
    "http://www.w3.org/2004/02/skos/core#example",
    "http://www.w3.org/2004/02/skos/core#topConceptOf",
    "http://www.w3.org/2004/02/skos/core#hasTopConcept",
    "http://www.w3.org/2004/02/skos/core#broader",
    "http://www.w3.org/2004/02/skos/core#narrower",
    "http://www.w3.org/2004/02/skos/core#related",
    "http://www.w3.org/2004/02/skos/core#inScheme",
]

# Predicates never shown.
EXCLUDED_PREDICATES = [
]

# ── Brain / basket search ────────────────────────────────────────────────────
# Drag concepts onto the brain; they're joined into a query and searched here.
# The query is appended, URL-encoded. Set SEARCH_URL = "" to hide the brain.
#   e.g. "https://www.google.com/search?q="
#        "https://duckduckgo.com/?q="
#        or your own library / discovery search
SEARCH_URL = "https://www.google.com/search?q="
SEARCH_LABEL = "Search with Google"
SEARCH_OPERATOR = "AND"    # how concepts are joined to start with: "AND" or "OR"

# The text at the top of the brain's overlay. Plain text.
BLURB = ("gather your (my?) thoughts! drag concepts from the graph to build a search. "
         "toggle the default operator (AND / OR), refine and edit your search, and see "
         "where the thoughts that occupy my (and now your?) mind overlap & intersect …")

# ── Data download ────────────────────────────────────────────────────────────
#   ""          → no download button
#   "endpoint"  → whatever the endpoint holds, fetched live as Turtle
#                 (a SPARQL CONSTRUCT; fine for small/medium graphs)
#   "/path/to/file.ttl" → serve that file as-is
DATA_DOWNLOAD = "endpoint"
DATA_DOWNLOAD_NAME = "thesaurus"   # download is saved as <name>_<date>.ttl
