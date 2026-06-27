"""DOCX bundle parser tests (the real CMS synthetic bundle path).

The bundle is *Meridian Retail v TechFlow* — 21 DOCX (pleadings, contracts,
correspondence, records, witness statements, expert reports). We test the pure
helpers (filename classification + numbered-paragraph extraction) deterministically,
without depending on the gitignored .docx files.
"""
from __future__ import annotations

from src.ingest import _classify_doc, _numbered_paragraphs, _seq_paragraphs


def test_classify_doc_types_and_party():
    assert _classify_doc("02_Particulars_of_Claim") == ("pleading", "claimant")
    assert _classify_doc("01_Claim_Form") == ("pleading", "claimant")
    assert _classify_doc("16_Witness_Statement_Helena_Vance") == ("witness", "claimant")
    assert _classify_doc("19_Expert_Report_Whitfield_IT") == ("expert", "claimant")
    assert _classify_doc("03_Master_Services_Agreement") == ("contract", "neutral")
    assert _classify_doc("07_Change_Order_No_3") == ("contract", "neutral")
    assert _classify_doc("08_UAT_Acceptance_Certificate") == ("record", "neutral")
    assert _classify_doc("13_Defect_Log") == ("record", "neutral")
    assert _classify_doc("09_Email_Go-Live_Readiness") == ("correspondence", "neutral")
    # side-specific correspondence must beat the generic "letter"/"email" rule
    assert _classify_doc("15_Letter_TechFlow_Response") == ("correspondence", "defendant")
    assert _classify_doc("14_Letter_Notice_of_Termination") == ("correspondence", "claimant")


# Mimics a pleading: court-header preamble, numbered paras (real numbers),
# a multi-line paragraph, sub-particulars "(a)"/"(b)", stop at the truth statement.
PLEADING_LINES = [
    "Claim No. HT-2025-000231",
    "IN THE HIGH COURT OF JUSTICE",
    "MERIDIAN RETAIL GROUP PLC", "Claimant", "- and -", "TECHFLOW SOLUTIONS LIMITED", "Defendant",
    "PARTICULARS OF CLAIM",
    "1.\tThe Claimant operates a chain of retail stores",
    "in the United Kingdom.",
    "8.\tIn breach of the MSA, TechFlow delivered the Platform late.",
    "9.\tMeridian did not at any time request any change to the agreed scope.",
    "15.\tThe Claimant has suffered loss. PARTICULARS:",
    "(a)\tWasted expenditure: 1,800,000.",
    "(b)\tLoss of profit: 4,200,000.",
    "Statement of Truth",
    "The Claimant believes the facts are true.",
]


def test_numbered_paragraphs_use_real_numbers():
    paras = _numbered_paragraphs(PLEADING_LINES)
    nums = [p.n for p in paras]
    assert nums == [1, 8, 9, 15]                       # the pleading's OWN paragraph numbers
    # court-header preamble is dropped (not numbered)
    assert all("HIGH COURT" not in p.text for p in paras)


def test_numbered_paragraphs_join_and_fold():
    paras = {p.n: p.text for p in _numbered_paragraphs(PLEADING_LINES)}
    assert paras[1] == "The Claimant operates a chain of retail stores in the United Kingdom."
    # sub-particulars (a)/(b) fold into their parent paragraph 15
    assert "Wasted expenditure" in paras[15] and "Loss of profit" in paras[15]
    # body stops at the statement of truth
    assert 15 == max(paras) and "believes the facts" not in " ".join(paras.values())


def test_numbered_paragraphs_handle_expert_section_collision():
    # Expert reports interleave section headings ("2. Availability") with numbered
    # paragraphs; the monotonic rule keeps the substantive paragraphs addressable.
    lines = [
        "1. Introduction and instructions",
        "1.\tI am Dr Whitfield, an IT expert.",
        "2. Availability of the Platform",
        "2.\tUnavailability attributable to the Platform was approximately 6.2%.",
        "3.\tThat is materially lower than the 40% figure pleaded.",
    ]
    paras = {p.n: p.text for p in _numbered_paragraphs(lines)}
    assert "6.2%" in paras[2]
    assert "materially lower" in paras[3]


def test_seq_paragraphs_number_sequentially():
    paras = _seq_paragraphs(["First line.", "", "Second line.", "Third."])
    assert [(p.n, p.text) for p in paras] == [(1, "First line."), (2, "Second line."), (3, "Third.")]
