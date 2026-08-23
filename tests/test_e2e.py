from src.claims import add_claim
from src.ingest import ingest
from src.opportunity import create_opportunity, link_claims
from src.report import generate_report


def test_t18_report_binds_claim_to_source(connection, tmp_path):
    evidence = tmp_path / "evidence"
    source = ingest(connection, data=b"1,234 results for nursery wall art", source_family="AMAZON_KDP",
                    kind="MANUAL_PASTE", url="https://example.test/search", retrieved_at="2026-08-23T14:10:00+00:00", evidence_dir=evidence)
    claim = add_claim(connection, source_id=source.source_id, claim_type="AMZ_SEARCH_RESULT_COUNT", subject="nursery",
                      value_num=1234, unit="count", observed_at="2026-08-23", quote="1,234 results for nursery wall art", evidence_dir=evidence)
    opp = create_opportunity(connection, title="Space Nursery", channel="KDP", product_type="low_content", niche="space nursery wall art")
    link_claims(connection, opp, [claim.claim_id])
    out = generate_report(connection, opportunity_id=opp, out_path=tmp_path / "report.html")
    text = out.read_text(encoding="utf-8")
    assert "Bağsız iddia sayısı: 0" in text
    assert source.source_id in text and "https://example.test/search" in text
    assert "1,234 results for nursery wall art" in text
    assert "platformun bildirdiği yaklaşık sayı" in text
    assert "1234.0 count" in text
