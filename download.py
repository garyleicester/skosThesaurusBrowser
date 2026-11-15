#!/usr/bin/env python3
# download.py  —  the data, as Turtle
#
#   download.py          → the Turtle itself (as an attachment)
#   download.py?info=1   → JSON {available, filename, bytes?, modified}
#
# config.DATA_DOWNLOAD decides the source:
#   "endpoint"        → CONSTRUCT everything from the endpoint, live
#   "/path/file.ttl"  → that file, as-is
#   ""                → off (404)
# Nothing in the request can change what's read.

import sys, os, datetime, email.utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, sparql


def main():
    info = "info" in sparql.params()
    source = getattr(config, "DATA_DOWNLOAD", "") or ""
    name = getattr(config, "DATA_DOWNLOAD_NAME", "") or "thesaurus"

    if source == "endpoint":
        today = datetime.date.today()
        filename = f"{name}_{today:%Y-%m-%d}.ttl"
        if info:
            return sparql.respond_json({"available": True, "filename": filename,
                                        "modified": f"{today:%Y-%m-%d}", "live": True})
        data = sparql.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", accept="text/turtle")
        return sparql.respond(data, "text/turtle; charset=utf-8", headers=[
            ("Content-Disposition", f'attachment; filename="{filename}"'),
            ("Content-Length", str(len(data))),
        ])

    if source and os.path.isfile(source) and os.access(source, os.R_OK):
        stat = os.stat(source)
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)
        ext = os.path.splitext(source)[1] or ".ttl"
        filename = f"{name}_{modified:%Y-%m-%d}{ext}"
        if info:
            return sparql.respond_json({"available": True, "filename": filename, "bytes": stat.st_size,
                                        "modified": f"{modified:%Y-%m-%d}", "live": False})
        with open(source, "rb") as f:
            data = f.read()
        return sparql.respond(data, "text/turtle; charset=utf-8", headers=[
            ("Content-Disposition", f'attachment; filename="{filename}"'),
            ("Content-Length", str(len(data))),
            ("Last-Modified", email.utils.formatdate(stat.st_mtime, usegmt=True)),
        ])

    if info:
        return sparql.respond_json({"available": False})
    sparql.respond("No data download available.\n", "text/plain", "404 Not Found")


sparql.run(main)
