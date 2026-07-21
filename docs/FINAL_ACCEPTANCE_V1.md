# REDBOX OS 1.0.0 — Ticari Final Kabul Raporu

**Kabul tarihi:** 21.07.2026
**Ürün:** REDBOX OS
**Şirket:** REDBOX Gıda Sanayi ve Tic. Ltd. Şti.
**Sürüm:** 1.0.0
**Build:** 1
**Veritabanı şeması:** 13
**Kabul sonucu:** PASS

## Kabul Özeti

REDBOX OS 1.0.0; temiz kurulum, ilk kullanıcı oluşturma,
61 ürünlük ticari reçete kataloğu, üretim–paketleme–sevkiyat
tam turu, ileri ve geri izlenebilirlik, yetkilendirme, audit,
yedekleme/geri yükleme, PDF ve performans kriterlerini
başarıyla tamamladı.

Kabul işlemleri geçici sandbox veritabanlarında veya salt-okunur
kontrollerle yürütüldü. Canlı veritabanının SHA-256 değeri kabul
öncesinde ve sonrasında değişmedi.

## Otomatik Kabul Kanıtı

- Kabul formatı: `REDBOX_COMMERCIAL_ACCEPTANCE_V1`
- Yol haritası kriteri: `10 / 10`
- Test modülü: `15`
- Başarılı test: `135`
- Test çıkış kodu: `0`
- Kabul raporu:
  `release/com5/REDBOX_OS-1.0.0-1-commercial-acceptance.json`
- Kabul raporu SHA-256:
  `7616d6f06cef0e5f7838f1adef83796a0a59d7c2ed714ce763c68fdcdaaa955e`

## Yol Haritası Kriterleri

| Kriter | Sonuç |
|---|---|
| Temiz cihaz / fresh-install sözleşmesi | PASS |
| İlk kullanıcı oluşturma | PASS |
| 60+ reçete katalog testi | PASS — 61 ürün |
| Üretim–paketleme–sevkiyat tam turu | PASS |
| İzlenebilirlik ve geri çağırma | PASS |
| Yetki kontrolleri | PASS |
| Audit sözleşmesi | PASS |
| Yedekleme ve geri yükleme | PASS |
| PDF üretimi | PASS |
| Performans | PASS |

## Veritabanı Güvenliği

- Şema sürümü: `13`
- SQLite integrity: `ok`
- Foreign key ihlali: `0`
- Canlı DB SHA-256:
  `9fde8ad78ad8018da865c3e62dc78fe4d0b6fcf323ef54c90c6f6eed7ce428be`
- Canlı DB korundu: `True`
- Performans probu: salt-okunur
- Performans tekrar sayısı: `100`

Canlı operasyon adetleri bu rapora sabit değer olarak yazılmamıştır.
Böylece işletme verisinin doğal değişimi yanlış bir kabul hatası olarak
değerlendirilmez.

## Performans Sonucu

| Ölçüm | Sonuç | Kabul limiti |
|---|---:|---:|
| Medyan | 0.074209 ms | 50 ms |
| P95 | 0.079996 ms | 150 ms |
| Maksimum | 1.186157 ms | 300 ms |

## Dağıtım Paketi

- DMG: `release/com4/REDBOX_OS-1.0.0-1.dmg`
- DMG SHA-256:
  `b3919087e9e2632006140e4e29806ae7208e2a167bd691b10c3169dbed82cd1b`
- DMG SHA eşleşmesi: `True`
- `hdiutil verify` çıkış kodu: `0`
- Fresh-install veritabanı: şema 13, gerçek veri içermiyor
- Uygulama verisi: macOS Application Support altında
- İmza modu: ad-hoc
- Notarization: uygulanmadı

Ad-hoc imzalı paket kontrollü kurulum ve kabul için doğrulanmıştır.
Genel internet dağıtımı öncesinde Apple Developer ID ile imzalama ve
Apple notarization işlemleri ayrıca tamamlanmalıdır.

## Yedekleme ve Kurtarma

- Doğrulanmış manuel ve otomatik yedek sözleşmeleri: PASS
- Kontrollü geri yükleme hazırlığı: PASS
- Başlangıç öncesi atomik geri yükleme: PASS
- Audit hatasında güvenli geri dönüş: PASS
- Canlı veritabanı koruması: PASS

## Final Sürüm Etiketi

Hedef sürüm etiketi `v1.0.0` olarak belirlenmiştir. Etiket, bu raporu
ve COM-5 kaynaklarını içeren commit ana dala birleştirildikten ve uzak
depo eşitliği doğrulandıktan sonra uygulanacaktır. Kabul yürütücüsü
etiket veya uzak depo yazma işlemi yapmaz.

## Kabul Kararı

REDBOX OS 1.0.0, doğrulanan macOS ortamında kontrollü ticari kullanıma
hazırdır. Apple Developer ID imzası ve notarization tamamlanmadan paket
genel internet dağıtımına açılmamalıdır.

**Hazırlayan / Sistem Sorumlusu:** Fatih Ayaz
