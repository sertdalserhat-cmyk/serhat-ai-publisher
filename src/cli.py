from __future__ import annotations
import argparse, hashlib, shutil
from datetime import datetime
from pathlib import Path
from . import __version__
from .claims import add_claim
from .config import BACKUP_DIR, DB_PATH, EVIDENCE_DIR
from .cost import LLMDisabledError, record_llm_call
from .db import connect, initialize
from .ingest import ingest
from .decisions import log_decision
from .opportunity import activate, create_opportunity, link_claims, set_status
from .report import generate_report
from .snapshot import verify_snapshots
from .staleness import stale_claim_ids

def build_parser():
    p=argparse.ArgumentParser(prog="publisher"); p.add_argument("--version",action="version",version=__version__); p.add_argument("--db",default=str(DB_PATH)); p.add_argument("--evidence",default=str(EVIDENCE_DIR)); sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("init")
    q=sub.add_parser("ingest"); q.add_argument("--family",required=True); q.add_argument("--kind",required=True); q.add_argument("--url"); q.add_argument("--locale",default="US"); q.add_argument("--retrieved-at",required=True); q.add_argument("--file",required=True)
    q=sub.add_parser("claim"); ss=q.add_subparsers(dest="claim_command",required=True); a=ss.add_parser("add"); a.add_argument("--source",required=True); a.add_argument("--type",required=True); a.add_argument("--subject",required=True); a.add_argument("--value-num",type=float); a.add_argument("--value-text"); a.add_argument("--unit"); a.add_argument("--market"); a.add_argument("--observed-at",required=True); a.add_argument("--quote"); a.add_argument("--locator"); a.add_argument("--confidence"); w=ss.add_parser("withdraw"); w.add_argument("claim_id"); w.add_argument("--reason",required=True)
    q=sub.add_parser("opp"); ss=q.add_subparsers(dest="opp_command",required=True); n=ss.add_parser("new"); n.add_argument("--title",required=True); n.add_argument("--channel",required=True); n.add_argument("--product-type",required=True); n.add_argument("--niche",required=True); n.add_argument("--confirm",action="store_true"); n.add_argument("--reason"); s=ss.add_parser("status"); s.add_argument("opportunity_id"); s.add_argument("status"); s.add_argument("--reason",required=True); a=ss.add_parser("activate"); a.add_argument("opportunity_id")
    q=sub.add_parser("link"); q.add_argument("--opp",required=True); q.add_argument("--claims",required=True)
    sub.add_parser("verify"); sub.add_parser("stale"); q=sub.add_parser("report"); q.add_argument("--opp",required=True); q.add_argument("--out",required=True); q.add_argument("--fresh",action="store_true"); sub.add_parser("backup"); q=sub.add_parser("doctor"); q.add_argument("--test-llm-guard",action="store_true"); return p

def backup(db_path):
    BACKUP_DIR.mkdir(parents=True,exist_ok=True); target=BACKUP_DIR/f"publisher_{datetime.now():%Y%m%d_%H%M%S}.db"; shutil.copy2(db_path,target); target.with_suffix(".db.sha256").write_text(hashlib.sha256(target.read_bytes()).hexdigest()+"\n",encoding="ascii")
    for old in sorted(BACKUP_DIR.glob("publisher_*.db"),reverse=True)[14:]: old.unlink(missing_ok=True); old.with_suffix(".db.sha256").unlink(missing_ok=True)
    return target

def main(argv=None):
    a=build_parser().parse_args(argv); db_path=Path(a.db); evidence=Path(a.evidence)
    if a.command=="init":
        initialized = initialize(db_path)
        version = initialized.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        initialized.close()
        print(f"Veritabanı hazır (schema_version={version}).")
        return 0
    conn=connect(db_path)
    try:
        if a.command=="ingest": r=ingest(conn,data=Path(a.file).read_bytes(),source_family=a.family,kind=a.kind,url=a.url,locale=a.locale,retrieved_at=a.retrieved_at,file_name=a.file,evidence_dir=evidence); print(r.message); return 0
        if a.command=="claim" and a.claim_command=="add": r=add_claim(conn,source_id=a.source,claim_type=a.type,subject=a.subject,value_num=a.value_num,value_text=a.value_text,unit=a.unit,market=a.market,observed_at=a.observed_at,quote=a.quote,locator=a.locator,confidence=a.confidence,evidence_dir=evidence); print("UYARI: "+r.warning if r.warning else r.claim_id); print(r.claim_id) if r.warning else None; return 0
        if a.command=="claim":
            with conn:
                cursor=conn.execute("UPDATE claim SET status='WITHDRAWN' WHERE id=? AND status='ACTIVE'",(a.claim_id,))
                if cursor.rowcount != 1: raise ValueError("Aktif claim bulunamadı")
            log_decision(conn,entity_type="CLAIM",entity_id=a.claim_id,actor="human:serhat",action="WITHDRAW",rationale=a.reason); print(a.claim_id,"geri çekildi:",a.reason); return 0
        if a.command=="opp" and a.opp_command=="new": print(create_opportunity(conn,title=a.title,channel=a.channel,product_type=a.product_type,niche=a.niche,confirm=a.confirm,rationale=a.reason)); return 0
        if a.command=="opp" and a.opp_command=="activate": activate(conn,a.opportunity_id); print(a.opportunity_id,"aktif"); return 0
        if a.command=="opp":
            set_status(conn,a.opportunity_id,a.status,a.reason); print("Durum güncellendi"); return 0
        if a.command=="link": link_claims(conn,a.opp,a.claims.split(",")); print("İddialar bağlandı"); return 0
        if a.command=="verify": bad=verify_snapshots(conn,evidence); print("FAIL: "+", ".join(bad) if bad else "Tüm snapshot hash'leri OK"); return bool(bad)
        if a.command=="stale": print("\n".join(stale_claim_ids(conn)) or "Eskimiş iddia yok"); return 0
        if a.command=="report": print(generate_report(conn,opportunity_id=a.opp,out_path=a.out,fresh=a.fresh)); return 0
        if a.command=="backup": print(backup(db_path)); return 0
        if a.command=="doctor":
            print("DB:",db_path,"Evidence bytes:",sum(x.stat().st_size for x in evidence.rglob('*') if x.is_file()) if evidence.exists() else 0)
            if a.test_llm_guard:
                try: record_llm_call(conn,llm_enabled=False)
                except LLMDisabledError as exc: print("LLMDisabledError:",exc)
            return 0
    except (ValueError,LLMDisabledError) as exc: print("RED:",exc); return 1
    finally: conn.close()
    return 1
if __name__=="__main__": raise SystemExit(main())
