# S-4 Product Blueprint — Sözleşme Taslağı v0.1

Durum: **UYGULANDI — S4-T01…T15 PASS**

## Amaç

`APPROVED` durumundaki bir fırsatın bağlı ve doğrulanmış claim'lerinden, kitap/ürün
üretiminde kullanılabilecek kanıta dayalı bir Product Blueprint adayı hazırlamak.

## Değişmez güvenlik sınırları

- Frozen S-2 ve tamamlanmış S-3 tabloları/kuralları değiştirilmez.
- Yalnız `APPROVED` fırsatlar için Blueprint adayı üretilebilir.
- Kullanılan her pazar bulgusu mevcut bir `claim.id` ile bağlanır.
- Kaynaksız başarı, talep, satış, dönüşüm, kâr veya hukuki sonuç üretilemez.
- Kanıtlanmayan alanlar `UNKNOWN` kalır; model tahminle dolduramaz.
- Model yalnız Blueprint adayı üretir; insan onayı olmadan kalıcılaştırılamaz.
- İnsan onayı olmadan kitap dosyası, metadata, fiyat, KDP/Etsy kaydı veya yayın
  durumu değiştirilemez.
- KDP'deki mevcut “Coding with AI” gönderimi bu aşamanın girdisi değildir ve
  değiştirilmez; durumu yalnız kullanıcı bildirimiyle güncellenir.
- LLM bütçesi varsayılan olarak kapalıdır. Dry-run ağsız ve sıfır maliyetlidir.

## Blueprint adayı alanları

- `opportunity_id`
- `working_title`
- `target_reader`
- `reader_problem`
- `product_promise`
- `format`
- `language`
- `market`
- `differentiators[]`
- `content_outline[]`
- `risks[]`
- `unknowns[]`
- `evidence_claim_ids[]`
- `status = DRAFT_REVIEW`

## İlk acceptance kapıları

- S4-T01: `APPROVED` olmayan fırsat reddedilir.
- S4-T02: En az bir bağlı ve aktif claim olmadan aday üretilemez.
- S4-T03: Bilinmeyen veya başka fırsata ait claim referansı reddedilir.
- S4-T04: Her kanıtlı bulgu geçerli `claim.id` taşır.
- S4-T05: Zorunlu alanlar eksikse atomik sıfır yazım.
- S4-T06: `UNKNOWN` alanları korunur; otomatik doldurulmaz.
- S4-T07: Dry-run ağ/model çağrısı ve maliyet oluşturmaz.
- S4-T08: Model çıktısı doğrudan kalıcı Blueprint yazamaz.
- S4-T09: İnsan reddi sıfır kalıcı yazımla sonuçlanır.
- S4-T10: İnsan onayı tam Blueprint ve karar günlüğü oluşturur.
- S4-T11: Aynı adayın tekrar onayı yinelenen Blueprint oluşturmaz.
- S4-T12: Blueprint işlemi claim, source ve snapshot kayıtlarını değiştiremez.
- S4-T13: KDP/yayın alanlarına hiçbir yan etki oluşmaz.
- S4-T14: Rapor tüm `evidence_claim_ids` bağlantılarını gösterir.
- S4-T15: Tam regresyon sonunda S-2/S-3 testleri ve `unbound claims = 0` korunur.

## Uygulama sırası

1. Blueprint aday şeması ve saf doğrulayıcı.
2. Kanıt paketi oluşturucu.
3. Ağsız deterministik dry-run.
4. İnsan inceleme/karar kapısı.
5. Kalıcı şema ve karar günlüğü (yalnız onaydan sonra).
6. Acceptance testleri ve gerçek `opp_0001` üzerinde yazımsız demo.

Gerçek `opp_0001` üzerinde yazımsız dry-run tamamlanmıştır. Kalıcı gerçek Blueprint
yalnız ayrıca verilen açık insan onayından sonra oluşturulur.
