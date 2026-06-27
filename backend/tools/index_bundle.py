"""Dev tool: parse every PDF in data/bundle (warming the parse cache) and rank
witnesses by how strongly they bear on the Bates-v-Post-Office case-theory
issues. Output guides curation of the ~8-12 demo subset + finding gold anchors.

Run:  PYTHONPATH=. .venv/Scripts/python.exe tools/index_bundle.py
"""
from __future__ import annotations
import glob, json, os, sys, traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ingest import parse_doc  # noqa: E402

TOPICS = {
    "remote_access": ["remote", "remotely", "balancing transaction", "inject", " alter ",
                      " amend", "transaction correction", "appsup", "without the postmaster",
                      "without the sub", "branch account", "edit", "msu", "ssc"],
    "bugs":          ["bug", "defect", "error", "dalmellington", "callendar", "receipts and payment",
                      "discrepanc", "glitch", "fault", "known error", "kel", "anomal"],
    "training":      ["training", "trained", "induction", "how-to", "booklet", "course", "helpline"],
    "knowledge_mgmt":["knew", "aware", " board ", "senior management", "ismay", "conceal",
                      "cover up", "cover-up", "integrity of horizon", "second sight"],
    "prosecution":   ["prosecut", "convict", "shortfall", "made good", "own money", "suspended",
                      "dismiss", "audit", "criminal"],
    "fujitsu_role":  ["fujitsu", "icl", "helpdesk", "help desk", "support desk", "nbsc", "ssc",
                      "engineer", "software"],
}

def score(text_l):
    return {t: sum(text_l.count(k) for k in kws) for t, kws in TOPICS.items()}

rows = []
paths = sorted(glob.glob("data/bundle/*.pdf"))
print(f"parsing {len(paths)} PDFs...", flush=True)
for i, p in enumerate(paths, 1):
    name = os.path.basename(p)
    try:
        if os.path.getsize(p) == 0:
            print(f"[{i}/{len(paths)}] SKIP empty {name}", flush=True); continue
        d = parse_doc(p)
        text_l = " ".join(x.text for x in d.paras).lower()
        sc = score(text_l)
        rows.append({"id": d.id, "title": d.title, "date": d.date, "file": name,
                     "npars": len(d.paras), "chars": len(text_l), "topics": sc,
                     "total": sum(sc.values())})
        print(f"[{i}/{len(paths)}] {d.id} {d.title[:28]:28} ¶{len(d.paras):>3} "
              f"hits={sum(sc.values()):>3}", flush=True)
    except Exception as e:
        print(f"[{i}/{len(paths)}] ERROR {name}: {e!r}", flush=True)
        traceback.print_exc()

with open("data/bundle_index.json", "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)

print("\n==== TOP BY TOPIC ====", flush=True)
for t in TOPICS:
    top = sorted(rows, key=lambda r: r["topics"][t], reverse=True)[:8]
    print(f"\n# {t}")
    for r in top:
        print(f"  {r['topics'][t]:>3}  {r['id']}  {r['title'][:34]:34} ¶{r['npars']}")
print(f"\nindexed {len(rows)} docs -> data/bundle_index.json", flush=True)
