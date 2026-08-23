from __future__ import annotations

from html import escape

from .start_flow import StartResult


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
