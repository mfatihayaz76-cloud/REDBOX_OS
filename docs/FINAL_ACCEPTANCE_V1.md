# REDBOX OS V1 - Final Kabul Raporu

**Kabul tarihi:** 17.07.2026
**Şirket:** REDBOX Gıda Sanayi ve Tic. Ltd. Şti.
**Sürüm adayı:** v1.0.0
**Şema sürümü:** 4

## Kabul Sonucu

REDBOX OS aktif uygulama kaynakları, canlı veritabanı, operasyon
matematiği, ekranlar, PDF raporları, yedekleme ve geri yükleme
bakımından final kabul testini başarıyla tamamladı.

## Kaynak Doğrulaması

- Aktif `app.py`, `database/` ve `ui/` Python kaynakları derlendi.
- Derleme hatası: 0
- Aktif uygulama açılışı: başarılı
- Tüm ana ekranlar: başarılı
- Dashboard Kalite/CAPA uyarıları: başarılı
- Kalite/CAPA boş kayıt davranışı: başarılı

## Veritabanı Sağlığı

- SQLite integrity: `ok`
- Foreign key ihlali: `0`
- Şema sürümü: `4`
- Uygulama tablosu: `29`
- Test üretimi `test11`: kontrollü olarak kaldırıldı
- Gerçek üretim lotu `270712`: korundu

## Operasyon Mutabakatı

- Üretim kaydı: `12`
- Toplam parti: `122`
- Net üretim: `2390.264 kg`
- Paketleme kaydı: `13`
- Paketlenen ürün: `4084 paket / 2362.000 kg`
- Paketleme firesi: `7.852 kg`
- Sevkiyat kaydı: `8`
- Sevk edilen ürün: `4064 paket / 2352.000 kg`
- Negatif hammadde stoku: `0`
- Operasyonel ilişki/orphan hatası: `0`
- Paket gramaj sözleşme hatası: `0`
- Koli içi adet sözleşme hatası: `0`

## Açık Yarı Mamul

Gerçek `270712` ürün lotuna ait `20.412 kg` üretim henüz
paketlenmemiştir. Bu kayıt test verisi değildir ve canlı sistemde
korunmuştur.

## PDF Kabulü

Aşağıdaki raporlar oluşturulmuş ve görsel olarak doğrulanmıştır:

- Genel Stok
- Üretim
- Paketleme
- Sevkiyat
- İzlenebilirlik ve Geri Çağırma
- Temizlik

Tüm raporlar A4 boyutunda açılmış; tablo taşması, kesilme veya
okunamayan karakter tespit edilmemiştir.

## Final Yedek

- Dosya: `REDBOX_OS_V1_FINAL_20260717_220115.db`
- SHA256:
  `4e31fc34bcd39c0ca169f405d4085f05f18dd6489e2cbd89ceab18aedb1eb748`
- Geri yükleme kopyası SHA eşleşmesi: başarılı
- Geri yükleme integrity: `ok`
- Geri yükleme foreign key ihlali: `0`

## Kabul Kararı

REDBOX OS v1.0.0, REDBOX Gıda'nın 2026 operasyon kayıtlarında
kullanıma hazırdır.

**Hazırlayan / Sistem Sorumlusu:** Fatih Ayaz
