#!/usr/bin/env python3
# details.py?uri=…  —  everything said about a resource, for the details overlay
#
# Returns JSON: { uri, label, properties: [
#     { predicate, name, values: [{value, label, lang, isIri}] } ] }
# in config.PRIORITY_PREDICATES order, then A–Z; config.EXCLUDED_PREDICATES dropped.
# Rendering (and escaping) happens in the browser.

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, sparql


def main():
    uri = sparql.params().get("uri", "")
    node = sparql.iri(uri)
    if not node:
        return sparql.respond_json({"error": "missing or invalid uri"}, "400 Bad Request")

    rows = sparql.select(f"""
    SELECT ?p ?o ?lp ?label WHERE {{
      {node} ?p ?o .
      OPTIONAL {{
        FILTER(isIRI(?o))
        VALUES ?lp {{ skos:prefLabel dct:title rdfs:label }}
        ?o ?lp ?label .
        {sparql.lang_filter("label")}
      }}
    }}""")

    labels = sparql.best_labels(rows, subj="o", pred="lp")
    excluded = set(config.EXCLUDED_PREDICATES)

    props = {}
    for r in rows:
        p = r["p"]
        if p in excluded:
            continue
        o = r["o"]
        is_iri = r.get("o_type") == "uri"
        vals = props.setdefault(p, {})
        if o not in vals:
            vals[o] = {
                "value": o,
                "label": labels.get(o, "") if is_iri else "",
                "lang": r.get("o_lang", ""),
                "isIri": is_iri,
            }

    priority = list(config.PRIORITY_PREDICATES)
    def short(p):
        return re.split(r"[/#]", p.rstrip("/#"))[-1] or p
    def key(p):
        return (priority.index(p), "") if p in priority else (len(priority), short(p).lower())

    own = sparql.best_labels([{"s": uri, "p": r["p"], "label": r["o"], "label_lang": r.get("o_lang", "")}
                              for r in rows if r["p"] in sparql.LABEL_PREDICATES
                              and r.get("o_type") != "uri"
                              and (not r.get("o_lang") or r["o_lang"].split("-")[0].lower()
                                   == config.LANG.split("-")[0].lower())])

    sparql.respond_json({
        "uri": uri,
        "label": own.get(uri) or sparql.fallback_label(uri),
        "properties": [
            {"predicate": p, "name": short(p),
             "values": sorted(props[p].values(), key=lambda v: (v["label"] or v["value"]).lower())}
            for p in sorted(props, key=key)
        ],
    })


sparql.run(main)
