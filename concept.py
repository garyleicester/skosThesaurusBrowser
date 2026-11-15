#!/usr/bin/env python3
# concept.py?uri=…  —  a concept's neighbours, live, for the graph view
#
# Returns JSON: { uri, label, related: [{uri, label, relation}] }
# relation is one of: broader, narrower, related, topConceptOf, hasTopConcept
# (each stated either way round in the data). Only hierarchy members are
# included as neighbours (see sparql.member_pattern).

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sparql


def main():
    uri = sparql.params().get("uri", "")
    node = sparql.iri(uri)
    if not node:
        return sparql.respond_json({"error": "missing or invalid uri"}, "400 Bad Request")

    rows = sparql.select(f"""
    SELECT DISTINCT ?other ?relation ?lp ?label WHERE {{
      {{ {node} skos:broader ?other .        BIND("broader" AS ?relation) }}
      UNION {{ ?other skos:narrower {node} . BIND("broader" AS ?relation) }}
      UNION {{ {node} skos:narrower ?other . BIND("narrower" AS ?relation) }}
      UNION {{ ?other skos:broader {node} .  BIND("narrower" AS ?relation) }}
      UNION {{ {node} skos:related ?other .  BIND("related" AS ?relation) }}
      UNION {{ ?other skos:related {node} .  BIND("related" AS ?relation) }}
      UNION {{ {node} skos:topConceptOf ?other .  BIND("topConceptOf" AS ?relation) }}
      UNION {{ ?other skos:hasTopConcept {node} . BIND("topConceptOf" AS ?relation) }}
      UNION {{ {node} skos:hasTopConcept ?other . BIND("hasTopConcept" AS ?relation) }}
      UNION {{ ?other skos:topConceptOf {node} .  BIND("hasTopConcept" AS ?relation) }}
      FILTER(isIRI(?other) && ?other != {node})
      {sparql.member_pattern("other")}
    }}""")
    labels = sparql.best_labels(rows, subj="other", pred="lp")

    own = sparql.best_labels(sparql.select(f"""
    SELECT ?s ?lp ?label WHERE {{
      VALUES ?s {{ {node} }}
      {sparql.member_pattern("s")}
    }}"""), pred="lp")

    # one entry per neighbour (a concept both related and narrower keeps the
    # hierarchical relation — it's the more informative of the two)
    order = ["broader", "topConceptOf", "narrower", "hasTopConcept", "related"]
    seen = {}
    for r in rows:
        o, rel = r["other"], r["relation"]
        if o not in seen or order.index(rel) < order.index(seen[o]):
            seen[o] = rel

    sparql.respond_json({
        "uri": uri,
        "label": own.get(uri) or sparql.fallback_label(uri),
        "related": sorted(({"uri": o, "label": labels[o], "relation": rel} for o, rel in seen.items()),
                          key=lambda d: (order.index(d["relation"]), d["label"].lower())),
    })


sparql.run(main)
