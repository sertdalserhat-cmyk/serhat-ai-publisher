# S-2 v1.2 Implementation Note

Gerekçe: Frozen v1.1 şemasında `ttl_days` kaynak satırında tek değerken D.4 kuralı TTL'yi
`source_family + claim_type` çiftine bağlıyordu. Aynı kaynak farklı TTL'li claim'ler taşıyabilir.

Karar: `source.ttl_days` geriye dönük şema uyumluluğu için kalır ve ingest sırasında `0`
yazılır. Staleness hesabının otoriter değeri `vocab.py` içindeki her `claim_type.ttl_days`
değeridir. Yeni tablo eklenmez; claim sözlüğü dışında TTL türetilmez.
