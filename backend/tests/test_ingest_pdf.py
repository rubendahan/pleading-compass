"""Witness-statement parser tests (the real CMS bundle path).

`parse_statement` is a *pure* function over the raw text pdfplumber extracts,
so we can test the real-bundle paragraph/metadata logic deterministically
without depending on the gitignored 1.8 GB of PDFs. The raw string below mirrors
the real Inquiry layout: repeated (OCR-mangled) statement-number watermarks,
"Page X of Y" footers, a metadata header, ALL-CAPS section headings, numbered
paragraphs that wrap across lines AND across page breaks, and a closing
"Statement of Truth".
"""
from __future__ import annotations

from src.ingest import parse_statement, _clean_id

# Two watermark spellings (O-for-0, spaced) exactly like the real extracts.
RAW = """WITNO6660100
WITNO6660100
Witness Name: Amandeep Singh
Statement No.: WITNO6660100
Exhibits: None
Dated: 13 January 2023
POST OFFICE HORIZON IT INQUIRY
FIRST WITNESS STATEMENT OF AMANDEEP SINGH
I, Amandeep Singh, will say as follows...
INTRODUCTION
1. I worked on the Horizon helpdesk support desk, formerly ICL
Epson support Desk. I initially worked for ICL, then Fujitsu.
2. Prior to starting the role we received a few days' training, which
was insufficient to fully support Postmasters.
Page 1 of 2
WITN06660100
W I TN06660100
3. Support staff could put through balancing transactions remotely to
correct a branch discrepancy without the Postmaster being present.
Statement of Truth
I believe the content of this statement to be true.
Signed: GRO
Dated: 13/01/2023
Page 2 of 2
"""


def test_clean_id_from_various_filenames():
    assert _clean_id("WITN06660100 - Amandeep Singh - Witness Statement") == "WITN06660100"
    assert _clean_id("witn07520100") == "WITN07520100"
    assert _clean_id("witn09480100_0") == "WITN09480100"     # drop the _0 dedup suffix
    assert _clean_id("WITN01020200 (1)") == "WITN01020200"


def test_metadata_extracted():
    doc = parse_statement(RAW, fallback_id="witn06660100")
    assert doc.id == "WITN06660100"                 # normalised from the OCR-mangled header
    assert doc.doc_type == "witness"
    assert "Amandeep Singh" in doc.title
    assert doc.date == "13 January 2023"


def test_real_paragraph_numbers_are_anchors():
    doc = parse_statement(RAW, fallback_id="witn06660100")
    nums = [p.n for p in doc.paras]
    assert nums == [1, 2, 3]                         # the document's OWN numbering, not 1..N reflow


def test_multiline_and_cross_page_join():
    doc = parse_statement(RAW, fallback_id="x")
    p1 = doc.para(1)
    # the two physical lines of para 1 are joined into one paragraph
    assert "formerly ICL Epson support Desk" in p1.text
    # para 3 wraps across a page break (watermark + "Page 1 of 2" interleaved) and must still join
    p3 = doc.para(3)
    assert "balancing transactions remotely" in p3.text
    assert "without the Postmaster being present" in p3.text


def test_noise_and_headings_stripped():
    doc = parse_statement(RAW, fallback_id="x")
    blob = " ".join(p.text for p in doc.paras)
    assert "WITN" not in blob                        # watermark lines dropped
    assert "Page 1 of 2" not in blob and "Page 2 of 2" not in blob
    assert "INTRODUCTION" not in blob                # ALL-CAPS section heading dropped
    assert "Statement of Truth" not in blob          # body stops there
    assert "Signed" not in blob


def test_body_stops_at_statement_of_truth():
    doc = parse_statement(RAW, fallback_id="x")
    assert [p.n for p in doc.paras] == [1, 2, 3]     # nothing after "Statement of Truth"
