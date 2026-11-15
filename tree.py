#!/usr/bin/env python3
# tree.py  —  the whole hierarchy, read live from the endpoint
#
# Returns JSON:
#   roots    : [uri]            ConceptSchemes (plus any concepts with no home)
#   children : {uri: [uri]}     from skos:hasTopConcept / topConceptOf / narrower / broader
#   labels   : {uri: label}     best label in config.LANG
#   settings : what the page needs from config.py
#
# Only "members" make it into the hierarchy (see sparql.member_pattern):
#   skos:Concept with a skos:prefLabel, or
#   skos:ConceptScheme with a skos:prefLabel or dct:title.
#
# Paths (breadcrumbs, where to expand the tree) are worked out in the browser
# by walking `children` — so nothing special is needed in the data: plain SKOS,
# polyhierarchy included.

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, sparql


def main():
    # Everything allowed in the hierarchy, with its labels and kind
    member_rows = sparql.select(f"""
    SELECT ?s ?lp ?label ?scheme WHERE {{
      {sparql.member_pattern("s")}
      BIND(EXISTS {{ ?s a skos:ConceptScheme }} AS ?scheme)
    }}""")

    # Schemes and their top concepts — stated either way round
    tops = sparql.select("""
    SELECT DISTINCT ?scheme ?top WHERE {
      { ?scheme skos:hasTopConcept ?top } UNION { ?top skos:topConceptOf ?scheme }
    }""")

    # Parent → child links — stated either way round
    edges = sparql.select("""
    SELECT DISTINCT ?parent ?child WHERE {
      { ?parent skos:narrower ?child } UNION { ?child skos:broader ?parent }
    }""")

    # Which scheme(s) each concept is in — to place concepts that have no parent
    in_scheme = sparql.select("""
    SELECT DISTINCT ?c ?scheme WHERE { ?c skos:inScheme ?scheme }""")

    labels = sparql.best_labels(member_rows, pred="lp")
    members = set(labels)
    schemes = {r["s"] for r in member_rows if r.get("scheme") in ("true", "1")}

    children = {}
    def link(parent, child):
        # both ends must be members: no deprecated or untyped stragglers
        if parent in members and child in members and parent != child and child not in schemes:
            lst = children.setdefault(parent, [])
            if child not in lst:
                lst.append(child)

    for r in tops:
        if r["scheme"] in schemes:
            link(r["scheme"], r.get("top"))
    for r in edges:
        link(r["parent"], r["child"])

    # Concepts with no parent at all: top of their scheme, or a root of their own
    has_parent = {c for kids in children.values() for c in kids}
    concept_schemes = {}
    for r in in_scheme:
        concept_schemes.setdefault(r["c"], set()).add(r["scheme"])
    loose = set()
    for c in members - schemes - has_parent:
        homes = concept_schemes.get(c, set()) & schemes
        if homes:
            for s in homes:
                link(s, c)
        else:
            loose.add(c)

    by_label = lambda u: labels.get(u, u).lower()
    roots = sorted(schemes, key=by_label) + sorted(loose, key=by_label)
    for kids in children.values():
        kids.sort(key=by_label)

    home = config.HOME_URI if config.HOME_URI in members else (roots[0] if roots else "")

    download = getattr(config, "DATA_DOWNLOAD", "") or ""
    if download and download != "endpoint" and not os.access(download, os.R_OK):
        download = ""

    sparql.respond_json({
        "roots": roots,
        "children": children,
        "labels": labels,
        "settings": sparql.page_settings(home=home, download=bool(download)),
    })


sparql.run(main)
