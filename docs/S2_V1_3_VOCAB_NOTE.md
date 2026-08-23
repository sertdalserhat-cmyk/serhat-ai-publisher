# S-2 v1.3 Vocabulary Note

Gerçek Etsy Türkiye gözlemi iki sözlük boşluğunu ortaya çıkardı.

- `ETSY_PRICE`, değeri dönüştürmeden gözlemlenen ISO para birimini (`USD`, `TRY`, `EUR`,
  `GBP`, `CAD`, `AUD`) kabul eder. Kur çevrimi veya normalizasyon yapılmaz.
- `ETSY_REVIEW_COUNT` (`count`, TTL 30, platform-reported) ve
  `ETSY_REVIEW_RATING` (`stars`, TTL 30) eklendi.

Bu değişiklikler yeni motor eklemez; yalnız kullanıcının gerçekten gördüğü Etsy verisinin
yanlış USD etiketiyle saklanmasını veya tamamen kaybedilmesini önler.
