#!/usr/bin/env python3
# search.py?q=…  —  synonyms (skos:altLabel / hiddenLabel) matching q
#
# Concept names (prefLabels) are matched instantly in the browser from the
# tree; this adds the synonyms, which only the endpoint knows. Only hierarchy
# members are returned (see sparql.member_pattern).
# Returns JSON: [{uri, label, synonym}]

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sparql

MAX_RESULTS = 50


def main():
    q = sparql.params().get("q", "").strip().lower()
    if len(q) < 3:
        return sparql.respond_json([])

    rows = sparql.select(f"""
    SELECT DISTINCT ?s ?syn ?lp ?label WHERE {{
      VALUES ?sp {{ skos:altLabel skos:hiddenLabel }}
      ?s ?sp ?syn .
      {sparql.lang_filter("syn")}
      FILTER(CONTAINS(LCASE(STR(?syn)), {sparql.literal(q)}))
      {sparql.member_pattern("s")}
    }} LIMIT {MAX_RESULTS * 4}""")

    labels = sparql.best_labels(rows, pred="lp")
    seen, out = set(), []
    for r in rows:
        key = (r["s"], r["syn"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"uri": r["s"], "label": labels[r["s"]], "synonym": r["syn"]})
    sparql.respond_json(out[:MAX_RESULTS])


sparql.run(main)
