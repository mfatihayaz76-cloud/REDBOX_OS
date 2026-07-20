# CRC-4 — Commercial Starting Catalog Acceptance

## Kabul Durumu

**TAMAMLANDI — 20.07.2026**

## Yetkili Veri Otoritesi

- Veri sahibi: Fatih Ayaz
- Ürün: `LP001 / Long Potato`
- Reçete kodu: `LP001-REC`
- Revizyon 00: `ARSIV`
- Revizyon 01: `AKTIF`
- Geçerlilik tarihi: `20.07.2027`
- Bir parti: `20.412 kg`
- Proses suyu: `10.700 kg`
- Stoklu hammadde toplamı: `9.712 kg`
- Gerçek formül satırı: `16`
- Uydurulmuş gerçek reçete içeriği: `YOK`

## Üretilen Kontrollü Kataloglar

- `catalogs/REDBOX_OS_TICARI_BASLANGIC_KATALOGU.csv`
- `catalogs/REDBOX_OS_TICARI_BASLANGIC_KATALOGU.xlsx`
- CSV SHA-256: `37c71313e82b993527371fc9bb9cc1187e06c64d3bc9a621745145a15cfa6f36`
- XLSX SHA-256: `0c53cef72a96b878d372ed0a7e99e07f75f57be6d7e11419a929b4833fe971fc`

## Teknik Kabul

- CSV dry-run: `PASS`
- XLSX dry-run: `PASS`
- CSV/XLSX özet eşitliği: `PASS`
- Hata sayısı: `0`
- Uyarı sayısı: `0`
- Fresh-install sandbox atomik import: `PASS`
- Sandbox ürün sayısı: `1`
- Sandbox reçete/revizyon sayısı: `2`
- Sandbox reçete kalemi sayısı: `16`
- Her ürün için aktif reçete sayısı: `1`
- İçerik SHA-256: `64 karakter / PASS`
- Import audit kaydı: `PASS`
- Sandbox SQLite integrity: `ok`
- Sandbox foreign key violation: `0`
- Rollback regresyon sözleşmesi: `PASS`
- 61 ürün kapasite dry-run testi: `PASS`
- 61 ürün atomik import testi: `PASS`

## Görsel Kabul

- `RECETE_KATALOGU`: `PASS`
- `ALAN_ACIKLAMALARI`: `PASS`
- `HAMMADDE_REFERANSI`: `PASS`
- Türkçe karakterler: `PASS`
- Uzun reçete ve hammadde adları: `KIRPILMA YOK`
- Sayısal gösterim: `0.000`
- Filtre ve sabit başlık: `AKTIF`

## Güvenlik ve Veri Koruma

- Canlı DB’ye katalog importu yapılmadı.
- Canlı DB yalnız read-only kaynak olarak kullanıldı.
- Gerçek katalog geçici fresh-install sandbox içinde doğrulandı.
- `build/`, `dist/`, `release/` klasörlerine dokunulmadı.
