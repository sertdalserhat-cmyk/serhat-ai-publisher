# Serhat AI Publisher — S-2 Evidence Store

API gerektirmeyen, manual-first kanıt defteri. Python 3.11+, SQLite ve yerel dosyalarla çalışır.

```powershell
python -m pip install pytest
python -m src.cli init
python -m pytest -v
```

Bu bilgisayarda `python` komutu PATH'te değilse paketli Python yolu kullanılabilir:

```powershell
& 'C:\Users\hs\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m src.cli init
```

Komutlar: `init`, `ingest`, `claim add`, `claim withdraw`, `opp new`, `opp status`, `opp activate`, `link`, `verify`, `stale`, `report`, `backup`, `doctor`.

Ham kanıtlar `evidence/` altında salt okunur saklanır ve Git'e girmez. Veritabanına elle SQL ile veri girilmez. Üçüncü taraf içerik yerel kalır ve yeniden yayımlanmaz. Haftalık harici yedek alınmalıdır.

Secret taraması yalnızca 11 sabit literal kullanır. **Bu bir savunma katmanıdır, temizlik kanıtı değildir.** API anahtarlarını veya tokenları kanıt dosyalarına yapıştırmayın.

`USPTO_NO_MATCH_IN_SEARCH_SCOPE` yalnız seçilen arama kapsamında eşleşme görülmediğini söyler; hukuki temizlik değildir. Eyalet kayıtları, common-law markalar, farklı yazımlar, görsel markalar ve ABD dışı siciller kapsam dışında kalabilir.

S-2 deterministiktir ve LLM çağrısı yapmaz. S-3 ancak tüm testler, bağsız iddia sayısı sıfır ve kullanıcı tarafından gerçek sayfalardan girilmiş 30 gerçek claim tamamlandıktan sonra başlar.

## Kullanıcı paneli

Windows'ta `BASLAT.cmd` dosyasına çift tıklayın. Yerel Serhat AI Publisher paneli tarayıcıda açılır.
Büyük **BAŞLAT** düğmesi mevcut snapshot hash'lerini, claim sayısını, citation binding durumunu,
LLM çağrı sayısını ve öne çıkan fırsatın inceleme durumunu doğrular.

Panel yalnızca `127.0.0.1` üzerinde çalışır; internete açılmaz. Etsy API onayı gelene kadar manual-first
Evidence Store verilerini kullanır ve bilinmeyen pazar verilerini üretmez.

## G-1 ve gerçek veri

Etsy API key onayı S-2'yi engellemez. Onay gelene kadar tüm kaynaklar manual-first girilir.
Demo verileri yalnız yazılım doğrulaması içindir; 30 gerçek claim yerine geçmez. Gerçek claim'lerde
sayfayı insanın görmesi, kısa birebir alıntı/locator kullanması ve erişim koşullarına uyması gerekir.
