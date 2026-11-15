# sparql.py  —  shared helpers for the CGI scripts (not a CGI script itself)
#
# Standard library only: nothing to pip install.

import sys, os, json, re
import urllib.request, urllib.parse, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

SKOS = "http://www.w3.org/2004/02/skos/core#"
DCT  = "http://purl.org/dc/terms/"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"

PREFIXES = f"""PREFIX skos: <{SKOS}>
PREFIX dct:  <{DCT}>
PREFIX rdfs: <{RDFS}>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""

# Label predicates, best first. A resource's display label is the best one
# available in the configured language.
LABEL_PREDICATES = [SKOS + "prefLabel", DCT + "title", RDFS + "label"]


# ── Talking to the endpoint ──────────────────────────────────────────────────

def _opener():
    handlers = []
    if config.USERNAME or config.PASSWORD:
        pw = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pw.add_password(None, config.ENDPOINT_URL, config.USERNAME, config.PASSWORD)
        if getattr(config, "AUTH_METHOD", "basic").lower() == "digest":
            handlers.append(urllib.request.HTTPDigestAuthHandler(pw))
        else:
            handlers.append(_PreemptiveBasicAuth(pw))
    return urllib.request.build_opener(*handlers)


class _PreemptiveBasicAuth(urllib.request.HTTPBasicAuthHandler):
    """Send credentials up front, rather than waiting for a 401 challenge
    (some endpoints answer an unauthenticated query with 403, not 401)."""
    def http_request(self, req):
        user, pw = self.passwd.find_user_password(None, req.full_url)
        if user is not None:
            import base64
            token = base64.b64encode(f"{user}:{pw}".encode()).decode()
            req.add_unredirected_header("Authorization", f"Basic {token}")
        return req
    https_request = http_request


def query(sparql, accept="application/sparql-results+json"):
    """POST a query (form-encoded, the most widely supported way) and return
    the raw response bytes."""
    form = {"query": PREFIXES + sparql}
    if "poolparty" in config.ENDPOINT_URL.lower():
        # PoolParty wants the result format as a form field too
        form["content-type"] = "application/json" if "json" in accept else accept
        if "json" in accept:
            accept = "application/json"
    req = urllib.request.Request(
        config.ENDPOINT_URL,
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": accept,
            "User-Agent": "thesaurus-browser",
        },
    )
    with _opener().open(req, timeout=60) as resp:
        return resp.read()


def select(sparql):
    """Run a SELECT; return a list of {var: value} dicts (values as strings,
    plus var+'_lang' for language-tagged literals)."""
    data = json.loads(query(sparql))
    rows = []
    for b in data.get("results", {}).get("bindings", []):
        row = {}
        for k, v in b.items():
            row[k] = v.get("value", "")
            if v.get("xml:lang"):
                row[k + "_lang"] = v["xml:lang"]
            row[k + "_type"] = v.get("type", "")
        rows.append(row)
    return rows


# ── Making user input safe to put in a query ─────────────────────────────────

_BAD_IRI = re.compile(r'[\s<>"{}|\\^`]')

def iri(value):
    """Return <value> if it's a plausible absolute IRI, else None."""
    if not value or _BAD_IRI.search(value) or not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
        return None
    return f"<{value}>"


def literal(value):
    """Escape a string as a SPARQL string literal."""
    esc = (value.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\r", "\\r"))
    return f'"{esc}"'


def lang_filter(var):
    """FILTER keeping ?var if untagged or in the configured language family:
    LANG "en" or "en-gb" both accept en, en-gb, en-us… (label_rank then
    prefers the exact match)."""
    primary = config.LANG.split("-")[0]
    return f'FILTER(LANG(?{var}) = "" || LANGMATCHES(LANG(?{var}), {literal(primary)}))'


def member_pattern(var, label_var="label", pred_var="lp"):
    """What counts as being in the hierarchy (tree, graph and search alike):
         a skos:Concept with a skos:prefLabel, or
         a skos:ConceptScheme with a skos:prefLabel or dct:title,
       in the configured language. Binds ?label_var / ?pred_var.
       Anything else — e.g. PoolParty's deprecated concepts, which keep a
       dct:title but lose their SKOS type — stays out."""
    return f"""{{
        {{ ?{var} a skos:Concept .       VALUES ?{pred_var} {{ skos:prefLabel }}           ?{var} ?{pred_var} ?{label_var} . }}
        UNION
        {{ ?{var} a skos:ConceptScheme . VALUES ?{pred_var} {{ skos:prefLabel dct:title }} ?{var} ?{pred_var} ?{label_var} . }}
        {lang_filter(label_var)}
      }}"""


def label_rank(pred, lang):
    """Lower is better: label predicate order first, then exact language,
    same language family, untagged."""
    p = LABEL_PREDICATES.index(pred) if pred in LABEL_PREDICATES else len(LABEL_PREDICATES)
    want = config.LANG.lower()
    lang = (lang or "").lower()
    if lang == want:
        l = 0
    elif lang and lang.split("-")[0] == want.split("-")[0]:
        l = 1
    else:
        l = 2
    return (p, l)


def best_labels(rows, subj="s", pred="p", label="label"):
    """From rows of (subject, label predicate, label), pick each subject's best label."""
    best = {}
    for r in rows:
        s = r.get(subj)
        if not s or not r.get(label):
            continue
        rank = label_rank(r.get(pred, ""), r.get(label + "_lang", ""))
        if s not in best or rank < best[s][0]:
            best[s] = (rank, r[label])
    return {s: v[1] for s, v in best.items()}


def fallback_label(uri):
    """Last resort: the end of the URI."""
    tail = re.split(r"[/#]", uri.rstrip("/#"))[-1]
    return urllib.parse.unquote(tail) or uri


# ── What the page needs to know from config.py ───────────────────────────────

DEFAULT_BLURB = ("gather your thoughts! drag concepts from the graph to build a search. "
                 "toggle the default operator (AND / OR), refine and edit your search, "
                 "and see where they overlap & intersect …")

def page_settings(**extra):
    """Display settings for index.html. Every setting has a default, so an
    older config.py keeps working."""
    get = lambda name, default: getattr(config, name, default)
    operator = str(get("SEARCH_OPERATOR", "AND")).upper()
    return {
        "title":          get("TITLE", "Thesaurus"),
        "blurb":          get("BLURB", DEFAULT_BLURB),
        "searchUrl":      get("SEARCH_URL", "https://www.google.com/search?q="),
        "searchLabel":    get("SEARCH_LABEL", "Search"),
        "searchOperator": operator if operator in ("AND", "OR") else "AND",
        **extra,
    }


# ── CGI plumbing ─────────────────────────────────────────────────────────────

def params():
    qs = os.environ.get("QUERY_STRING", "")
    return {k: v[0] for k, v in urllib.parse.parse_qs(qs, keep_blank_values=True).items()}


def respond(body, content_type="application/json", status=None, headers=()):
    out = sys.stdout.buffer
    if status:
        out.write(f"Status: {status}\r\n".encode())
    out.write(f"Content-Type: {content_type}\r\n".encode())
    for k, v in headers:
        out.write(f"{k}: {v}\r\n".encode())
    out.write(b"\r\n")
    out.write(body if isinstance(body, bytes) else body.encode("utf-8"))
    out.flush()


def respond_json(obj, status=None):
    respond(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", status,
            headers=[("Cache-Control", "no-cache")])


def run(main):
    """Run a CGI entry point, turning any failure into a JSON error."""
    try:
        main()
    except urllib.error.HTTPError as e:
        respond_json({"error": f"endpoint said {e.code} {e.reason}"}, "502 Bad Gateway")
    except urllib.error.URLError as e:
        respond_json({"error": f"couldn't reach endpoint: {e.reason}"}, "502 Bad Gateway")
    except Exception as e:  # keep the page alive; say what went wrong
        respond_json({"error": f"{type(e).__name__}: {e}"}, "500 Internal Server Error")
