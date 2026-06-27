from src.ingest import load_bundle
from src.pleadings import seed_propositions
from src.pipeline import analyze
from src.judges.stub import judge
from src import report

BUNDLE = "data/selftest/bundle"


def test_emoji():
    assert report.emoji("SUPPORTED") == "🟢"
    assert report.emoji("CONTRADICTED") == "🔴"
    assert report.emoji("NOT_ADDRESSED") == "⚪"


def test_cli_render_has_sections():
    b = load_bundle(BUNDLE)
    res = analyze(b, seed_propositions(), judge, side="claimant")
    text = report.render_cli(res)
    assert "🟢" in text                       # P1 supported
    assert "Cross-examination points" in text
    assert "Gaps to fill" in text


def test_markdown_memo():
    b = load_bundle(BUNDLE)
    res = analyze(b, seed_propositions(), judge, side="claimant")
    md = report.render_markdown(res)
    assert md.startswith("# Case theory stress test")
    assert "| Proposition |" in md
