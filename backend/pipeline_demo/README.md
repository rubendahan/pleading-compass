# Full pipeline demo: Benjamin's A1 backend -> our mapper -> our AppData

This is the complete pipeline running with a strong LLM.

1. `benjamin_a1_gpt54/` is the real output of **Benjamin's `hackthelaw` backend**
   (https://github.com/BenjaminisCoding/Hackthelaw), run on his machine with an
   Azure `gpt-5.4` deployment over the official CMS Meridian bundle. `claim_reports.md`
   is his per-claim robustness review; `run_metadata.json` records the model.
2. `../a1_bridge.py` is **our mapper**. It reads that output, splits every document into
   numbered paragraphs, re-grounds each finding to a verbatim quote, maps his
   robustness scores to our verdict vocabulary (SUPPORTED / CONTRADICTED /
   NOT_ADDRESSED / UNVERIFIED) plus legal overlays, and emits the AppData contract.
3. `app_a1_gpt54.json` is the result, ready for the Pleading Compass front to render.

Reproduce:
```
python a1_bridge.py --run pipeline_demo/benjamin_a1_gpt54 \
       --case <path-to>/cases/cms_synthetic --out pipeline_demo/app_a1_gpt54.json
```
