from __future__ import annotations

from html import escape

from .start_flow import StartResult
from .review import OpportunityReview
from .blueprint import BlueprintPreview


def render_dashboard(result: StartResult | None = None) -> str:
    if result is None:
        result_panel = """
        <section id="result" class="result waiting">
          <p class="eyebrow">SİSTEM HAZIR</p>
          <h2>Kanıt tabanlı araştırmayı başlat</h2>
          <p>Etsy API onayı beklenirken mevcut gerçek kanıtlarla manual-first çalışır.</p>
        </section>"""
    else:
        state = "ready" if result.ready else "blocked"
        heading = "İnsan incelemesine hazır" if result.ready else "Bir adım tamamlanmalı"
        failures = len(result.snapshot_failures)
        opportunity = escape(result.opportunity_title or "Henüz fırsat yok")
        result_panel = f"""
        <section id="result" class="result {state}">
          <p class="eyebrow">{'KONTROLLER GEÇTİ' if result.ready else 'KONTROL GEREKİYOR'}</p>
          <h2>{heading}</h2>
          <div class="metrics">
            <article><strong>{result.claim_count}</strong><span>Gerçek claim</span></article>
            <article><strong>{result.unbound_count}</strong><span>Bağsız claim</span></article>
            <article><strong>{failures}</strong><span>Snapshot hatası</span></article>
            <article><strong>{result.llm_call_count}</strong><span>LLM çağrısı</span></article>
          </div>
          <div class="opportunity">
            <span>ÖNE ÇIKAN FIRSAT</span>
            <b>{opportunity}</b>
            <small>{escape(result.opportunity_status or 'HAZIRLANIYOR')}</small>
          </div>
          <p class="next">Sonraki adım: <b>{escape(result.next_action)}</b></p>
          {'<a class="review-link" href="/review">FIRSATI İNCELE →</a>' if result.ready else ''}
        </section>"""

    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Serhat AI Publisher</title>
<style>
:root{{--ink:#14231d;--muted:#66756e;--cream:#f6f1e7;--card:#fffdf8;--green:#186b4b;--lime:#d9f06d;--red:#a43d32}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 85% 0,#e6f1c5 0,transparent 35%),var(--cream);color:var(--ink);font-family:Segoe UI,Arial,sans-serif;min-height:100vh}}
main{{width:min(960px,92vw);margin:auto;padding:44px 0 70px}} header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:70px}} .brand{{font-weight:800;letter-spacing:-.03em;font-size:21px}} .mode{{font-size:12px;padding:9px 13px;border:1px solid #bdc9be;border-radius:99px;color:var(--green);background:#faffed}}
.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:55px;align-items:center}} h1{{font-size:clamp(46px,7vw,78px);line-height:.97;letter-spacing:-.065em;margin:0 0 24px}} .lead{{font-size:18px;line-height:1.65;color:var(--muted);max-width:570px}}
#start{{width:220px;height:220px;border:0;border-radius:50%;background:var(--ink);color:white;font-size:27px;font-weight:900;letter-spacing:.08em;cursor:pointer;box-shadow:0 22px 50px #14231d42;transition:.2s}} #start:hover{{transform:translateY(-4px);background:var(--green)}} #start:disabled{{opacity:.65;cursor:wait}}
.result{{margin-top:55px;padding:30px;border:1px solid #d6d5c9;border-radius:24px;background:#ffffffad;backdrop-filter:blur(7px)}} .result.ready{{border-color:#8ebd83}} .result.blocked{{border-color:#d9a49e}} .eyebrow{{font-size:11px;letter-spacing:.18em;font-weight:800;color:var(--green);margin:0 0 8px}} h2{{margin:0 0 10px;font-size:29px;letter-spacing:-.03em}} .result>p{{color:var(--muted)}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:25px 0}} .metrics article{{background:var(--card);padding:18px;border-radius:15px;border:1px solid #e6e2d8}} .metrics strong{{font-size:30px;display:block}} .metrics span{{font-size:12px;color:var(--muted)}} .opportunity{{display:flex;align-items:center;gap:15px;padding:18px;background:var(--ink);color:white;border-radius:15px}} .opportunity span{{font-size:10px;color:var(--lime)}} .opportunity b{{flex:1}} .opportunity small{{color:#dbe7df}} .next{{margin-bottom:0}}
.review-link{{display:inline-block;margin-top:16px;padding:13px 18px;border-radius:99px;background:var(--green);color:white;text-decoration:none;font-weight:800;font-size:12px;letter-spacing:.08em}}
footer{{margin-top:45px;color:var(--muted);font-size:12px}} @media(max-width:700px){{.hero{{grid-template-columns:1fr;text-align:center}} .lead{{margin:auto}} #start{{width:175px;height:175px}} .metrics{{grid-template-columns:repeat(2,1fr)}} header{{margin-bottom:45px}}}}
</style></head><body><main>
<header><div class="brand">SERHAT AI PUBLISHER</div><div class="mode">MANUAL-FIRST · API'SİZ</div></header>
<section class="hero"><div><p class="eyebrow">PUBLISHING RESEARCH OS</p><h1>Kanıtla.<br>Karar ver.<br>Üret.</h1><p class="lead">Gerçek pazar kanıtlarını doğrular, fırsatı insan onayına hazırlar. Bilinmeyen veriyi uydurmaz.</p></div><div style="text-align:center"><button id="start" type="button">BAŞLAT</button></div></section>
{result_panel}
<footer>Yerel çalışır · Veriler bu bilgisayarda kalır · WIP limiti: 1</footer>
</main><script>
const button=document.getElementById('start');
button.addEventListener('click',async()=>{{button.disabled=true;button.textContent='KONTROL…';try{{const response=await fetch('/start',{{method:'POST'}});document.open();document.write(await response.text());document.close();}}catch(e){{button.disabled=false;button.textContent='TEKRAR DENE';alert('Yerel uygulamaya ulaşılamadı.');}}}});
</script></body></html>"""


def render_review(review: OpportunityReview, message: str | None = None) -> str:
    types = "".join(
        f"<li><span>{escape(name)}</span><b>{count}</b></li>"
        for name, count in review.claim_types
    )
    confidence = " · ".join(f"{escape(name)}: {count}" for name, count in review.confidence_counts)
    price = "UNKNOWN"
    if review.price_min is not None:
        price = f"{review.price_min:.2f}–{review.price_max:.2f} {escape(review.currency or '')}"
    rating = "UNKNOWN"
    if review.rating_min is not None:
        rating = f"{review.rating_min:g}–{review.rating_max:g} yıldız"
    notice = f'<div class="notice">{escape(message)}</div>' if message else ""
    locked = review.status in {"APPROVED", "REJECTED", "PARKED"}
    controls = ""
    if not locked:
        controls = """
        <form method="post" action="/decision">
          <label>Karar gerekçesi<textarea name="rationale" required minlength="5" placeholder="Bu kararı neden veriyoruz?"></textarea></label>
          <label class="confirm"><input type="checkbox" name="confirm" value="YES" required> Bu kararın fırsat durumunu değiştireceğini anlıyorum.</label>
          <div class="actions">
            <button name="status" value="APPROVED" class="approve">ONAYLA</button>
            <button name="status" value="PARKED">BEKLET</button>
            <button name="status" value="REJECTED" class="reject">REDDET</button>
          </div>
        </form>"""
    else:
        controls = f'<div class="locked">Karar kaydedildi: <b>{escape(review.status)}</b></div>'
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fırsat İncelemesi</title>
<style>body{{margin:0;background:#f6f1e7;color:#14231d;font-family:Segoe UI,Arial,sans-serif}}main{{width:min(900px,92vw);margin:45px auto}}a{{color:#186b4b}}.eyebrow{{font-size:11px;letter-spacing:.17em;color:#186b4b;font-weight:800}}h1{{font-size:48px;letter-spacing:-.05em;margin:10px 0}}.sub{{color:#66756e}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}}.card,.panel{{background:#fffdf8;border:1px solid #ddd8cc;border-radius:18px;padding:20px}}.card b{{font-size:25px;display:block}}.card span{{font-size:12px;color:#66756e}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}ul{{list-style:none;padding:0;margin:0}}li{{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #eee9df;font-size:13px}}textarea{{display:block;width:100%;min-height:90px;margin-top:8px;padding:12px;border:1px solid #c9c6bb;border-radius:12px;font:inherit}}form{{margin-top:25px}}.confirm{{display:block;margin:13px 0;color:#66756e;font-size:13px}}.actions{{display:flex;gap:10px;margin-top:12px}}button{{padding:13px 20px;border-radius:99px;border:1px solid #b8b8ad;background:white;font-weight:800;cursor:pointer}}.approve{{background:#186b4b;color:white;border-color:#186b4b}}.reject{{color:#a43d32}}.notice,.locked{{margin:20px 0;padding:16px;border-radius:12px;background:#e4f0cf}}@media(max-width:650px){{.cards{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}h1{{font-size:36px}}}}</style></head>
<body><main><a href="/">← Ana ekran</a>{notice}<p class="eyebrow">İNSAN KARAR KAPISI</p><h1>{escape(review.title)}</h1><p class="sub">{escape(review.channel)} · {escape(review.product_type)} · {escape(review.niche)} · {escape(review.status)}</p>
<section class="cards"><div class="card"><b>{review.claim_count}</b><span>Aktif claim</span></div><div class="card"><b>{review.source_count}</b><span>Bağımsız snapshot</span></div><div class="card"><b>{price}</b><span>Gözlenen fiyat aralığı</span></div><div class="card"><b>{rating}</b><span>Gözlenen puan aralığı</span></div></section>
<section class="grid"><div class="panel"><h2>Kanıt dağılımı</h2><ul>{types}</ul></div><div class="panel"><h2>Karar notu</h2><p><b>Güven:</b> {confidence or 'UNKNOWN'}</p><p><b>En yüksek görülen yorum:</b> {review.review_count_max if review.review_count_max is not None else 'UNKNOWN'}</p><p>Bu ekran yalnız gözlenen veriyi gösterir. Talep, kârlılık veya başarı puanı uydurmaz.</p><p><a href="/blueprint">Ürün Blueprint önizlemesi →</a></p></div></section>{controls}</main></body></html>"""


def render_blueprint(preview: BlueprintPreview) -> str:
    unknowns = "".join(f"<li><span>{escape(field)}</span><b>UNKNOWN</b></li>" for field in preview.unknown_fields)
    state = "AÇIK — ürün planı hazırlanabilir" if preview.unlocked else "KİLİTLİ — önce insan onayı gerekiyor"
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ürün Blueprint</title>
<style>body{{margin:0;background:#14231d;color:#f7f2e8;font-family:Segoe UI,Arial,sans-serif}}main{{width:min(850px,92vw);margin:50px auto}}a{{color:#d9f06d}}.eyebrow{{color:#d9f06d;font-size:11px;letter-spacing:.18em;font-weight:800}}h1{{font-size:52px;letter-spacing:-.055em;margin:12px 0}}.state{{padding:15px 18px;border:1px solid #60746a;border-radius:14px;background:#20342b}}.known,.unknown{{margin-top:22px;background:#fffdf8;color:#14231d;padding:24px;border-radius:20px}}dl{{display:grid;grid-template-columns:160px 1fr;gap:12px}}dt{{color:#66756e}}dd{{margin:0;font-weight:700}}ul{{list-style:none;padding:0}}li{{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #e7e2d8}}li b{{color:#a43d32;font-size:12px}}</style></head><body><main><a href="/review">← Fırsat incelemesi</a><p class="eyebrow">PRODUCT BLUEPRINT</p><h1>{escape(preview.title)}</h1><div class="state">{state}</div><section class="known"><h2>Kanıtla bilinenler</h2><dl><dt>Kanal</dt><dd>{escape(preview.channel)}</dd><dt>Ürün tipi</dt><dd>{escape(preview.product_type)}</dd><dt>Niş</dt><dd>{escape(preview.niche)}</dd><dt>Gözlenen fiyat</dt><dd>{escape(preview.observed_price_range)}</dd></dl></section><section class="unknown"><h2>İnsan kararı gereken alanlar</h2><ul>{unknowns}</ul></section></main></body></html>"""
