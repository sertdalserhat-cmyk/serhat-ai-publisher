# S-2 v1.4 Binary Secret Scan Note

Literal secret taraması yalnız `text/*` snapshot'lara uygulanır. PNG gibi ikili dosyalarda
sıkıştırılmış rastgele baytlar literal desenlerle tesadüfen eşleşebilir. S-2'de OCR yasak
olduğundan görsel içindeki metin zaten taranamaz; görseller hash ve immutable snapshot
kontrollerinden geçmeye devam eder.
