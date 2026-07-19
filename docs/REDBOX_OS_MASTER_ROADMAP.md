# REDBOX OS — MASTER PRODUCT ROADMAP

Durum tarihi: 19.07.2026
Ürün sahibi: Fatih Ayaz
Teknik çalışma adı: Atlas
Ana hedef: REDBOX OS'u gıda üretimi, HACCP, kalite, denetim ve izlenebilirlik alanında dünya seviyesinde ticari bir işletim sistemi haline getirmek.

---

## 1. Değiştirilemez Ürün Yönü

REDBOX OS aşağıdaki alanlara odaklanır:

- Gıda üretimi
- HACCP ve ön gereksinim programları
- Hammadde ve mamul izlenebilirliği
- Reçete ve revizyon yönetimi
- Paketleme ve sevkiyat
- Stok ve lot yönetimi
- Temizlik ve hijyen
- Kalite, uygunsuzluk ve CAPA
- Denetim kayıtları
- Yapay zekâ, sensör ve kamera destekli takip

Cari, muhasebe, kasa, banka, tahsilat ve finans yönetimi REDBOX OS içine alınmaz. Bu alan ayrı bir ticari ürün olarak geliştirilir. Gerekirse iki ürün ileride kontrollü API ile entegre edilir.

---

## 2. Çalışma Yönetimi Kuralları

1. Aynı anda yalnızca bir aktif sprint yürütülür.
2. Aktif sprint kabul testleri tamamlanmadan başka sprint açılmaz.
3. Yeni fikirler ana yönü değiştirmez; ürün backlog'una kaydedilir.
4. Yeni fikir yalnızca aşağıdaki durumlardan birinde mevcut sprintin önüne alınabilir:
   - Veri kaybı riski
   - Güvenlik açığı
   - Yasal veya denetim açısından kritik hata
   - Sonradan sistemi yeniden yazdıracak mimari engel
5. Her değişiklikten önce otomatik kaynak ve veritabanı yedeği alınır.
6. Canlı veritabanında kontrolsüz test yazması yapılmaz.
7. Yazma testleri sandbox veya geçici veritabanında yürütülür.
8. Her değişiklikten sonra `py_compile`, sözleşme testi, foreign-key ve integrity kontrolü yapılır.
9. Her sprint ayrı Git branch'inde geliştirilir.
10. Sprint; commit, main birleşimi, GitHub push ve branch temizliğiyle kapanır.
11. Gerçek olmayan üretim, reçete, lot veya denetim verisi canlı sisteme eklenmez.
12. Yaklaşık 20 dakikalık yoğun çalışma bloklarından sonra ara verilir.

---

## 3. Tamamlanan Ana Temeller

### Operasyon çekirdeği

- Depo kabul
- Hammadde FIFO
- Üretim
- Paketleme
- Mamul stok
- Sevkiyat
- İzlenebilirlik
- Geri çağırma raporu
- Temizlik planları ve gerçekleşmeleri
- Kalite ve CAPA
- Audit log
- Kullanıcı ve yetkilendirme
- Rol bazlı menü ve dashboard

### Çoklu ürün ve reçete altyapısı

- `urunler` ürün kartları
- Reçetenin ürüne bağlanması
- Üretimin ürüne bağlanması
- Paketlemenin ürüne bağlanması
- Sevkiyatın ürüne bağlanması
- Ürün başına tek aktif reçete
- Reçete revizyon geçmişi
- Reçete oluşturma
- Reçete düzenleme
- Kullanılmamış revizyonu silme
- Üretimde kullanılan reçeteyi koruma
- Revizyon karşılaştırma
- Parti toplamı ve kütle dengesi

### Ticari paket altyapısı

- `REDBOX_OS.spec`
- PyInstaller
- Yazılabilir paketlenmiş veritabanı yolu
- macOS paketleme temeli
- `requirements.txt`
- `.python-version`
- README
- Sürüm temeli `v1.0.0`

### Global food safety foundation — şema sürümü 9

- Kontrollü dokümanlar
- Doküman revizyonları
- Dijital onaylar
- Kanıt dosyaları
- Entegrasyon cihazları
- Sensör/kamera/mobil/API olayları
- 6/6 foundation sözleşme testi
- 6/6 audit sözleşme testi

---

## 4. Mevcut Canlı Otorite

- Aktif ürün: 1
- Ürün kodu: LP001
- Ürün: Long Potato
- Toplam reçete revizyonu: 2
- Aktif reçete: 1
- Reçete kalemi: 16
- Şema sürümü: 9
- Canlı operasyon verileri korunmaktadır.

Bu aşamada 60+ reçete henüz canlı sistemde oluşturulmamıştır.

---

## 5. AKTİF ANA HAT — COMMERCIAL RECIPE CATALOG

Branch:

`feature/commercial-recipe-import`

### Sprint CRC-1 — Reçete katalog sözleşmesi

Durum: **TAMAMLANDI**

Amaç:

60'tan fazla ürün/reçeteyi güvenli, tekrar üretilebilir ve doğrulanabilir biçimde yönetebilecek veri sözleşmesini tamamlamak.

Yapılacaklar:

- Ürün kodu standardı
- Reçete kodu standardı
- Ürün–reçete bağlantı doğrulaması
- Birim ve miktar doğrulaması
- Parti teorik toplam kontrolü
- Reçete kütle dengesi
- Aynı ürün için tek aktif reçete
- Revizyon numarası standardı
- Geçerlilik tarihi
- Reçete durum yaşam döngüsü
- Taslak, inceleme, onay, aktif, pasif ve arşiv durumları
- Reçete onay yetkisi
- Toplu katalog dry-run doğrulaması
- Hata halinde tam rollback
- Canlı yazma öncesi ayrıntılı ön izleme

Kabul ölçütü:

- 60+ reçetelik sandbox katalog testi
- Yinelenen ürün/reçete reddi
- Eksik hammadde reddi
- Negatif veya sıfır miktar reddi
- Kütle dengesi hatası reddi
- Aynı üründe ikinci aktif reçete reddi
- Canlı veritabanı değişmeden dry-run raporu
- Foreign-key ihlali sıfır
- SQLite integrity `ok`

Önemli:

Gerçek reçete içeriği ve miktarları Fatih Ayaz tarafından sağlanan yetkili kaynak olmadan uydurulmaz. Önce 60+ reçeteyi taşıyabilecek motor ve şablon hazırlanır.

### Sprint CRC-2 — Toplu ürün/reçete içe aktarma

Durum: **TAMAMLANDI**

- Standart CSV/XLSX şablonu
- Ürün kartı alanları
- Reçete başlık alanları
- Reçete kalemleri
- Hammadde eşleştirme
- Ön kontrol raporu
- Satır bazlı hata raporu
- Atomik içe aktarma
- Tek işlemde rollback
- Import audit log
- Import sonuç özeti

### Sprint CRC-3 — Reçete merkezi profesyonel ekranı

Durum: **TAMAMLANDI — 20.07.2026**

- Ürün filtresi
- Reçete durumu filtresi
- Revizyon geçmişi
- Aktif reçete rozeti
- Kütle dengesi göstergesi
- Hammadde sayısı
- Toplu katalog arama
- Reçete karşılaştırma
- Kontrollü onay
- PDF reçete föyü
- Dijital onay ve audit bağlantısı
- SHA-256 içerik bütünlüğü ve stale-hash koruması
- Kontrollü PDF oluşturma audit kaydı
- PDF otomatik açma ve duyarlı alt işlem çubuğu
- İki sayfalı profesyonel PDF yerleşimi
- Canlı Reçete ID 10 PDF üretim ve görsel kabulü
- CRC-3 tam regresyon: 54/54 PASS
- SQLite integrity: ok
- Foreign key violation: 0

### Sprint CRC-4 — Ticari başlangıç kataloğu

- Yetkili reçete kaynağının alınması
- 60+ reçetenin dry-run kontrolü
- Hata listesinin temizlenmesi
- Sandbox import
- Kabul raporu
- Kontrollü canlı/fresh-install katalog üretimi
- Her ürün için tek aktif reçete doğrulaması

---

## 6. TİCARİ PAKET KAPANIŞ HATTI

### Sprint COM-1 — Firma ve ilk kurulum

- Firma profili
- Tesis bilgileri
- İlk yönetici hesabı
- İlk çalıştırma sihirbazı
- Demo ve gerçek kullanım ayrımı
- Fresh-install başlangıç verisi

### Sprint COM-2 — Lisanslama

- Lisans anahtarı
- Firma/cihaz bağlantısı
- Süreli ve süresiz lisans
- Lisans doğrulama
- Grace period
- Çevrimdışı lisans senaryosu
- Lisans audit kayıtları

### Sprint COM-3 — Yedekleme ve kurtarma

- Otomatik zamanlanmış yedek
- Yedek doğrulama
- Saklama politikası
- Kontrollü geri yükleme
- Geri yükleme öncesi emniyet yedeği
- Yedekleme audit kayıtları

### Sprint COM-4 — Dağıtım paketi

- Temiz macOS build
- Uygulama simgesi
- DMG
- Fresh-install testi
- Upgrade testi
- Uygulama verisi konumu
- Çökme/log klasörü
- Sürüm bilgisi
- Kullanıcı kılavuzu
- Kurulum kılavuzu
- Lisans ve destek belgeleri

### Sprint COM-5 — Ticari final acceptance

- Temiz cihaz kurulumu
- İlk kullanıcı oluşturma
- 60+ reçete katalog testi
- Üretim–paketleme–sevkiyat tam tur testi
- İzlenebilirlik ve geri çağırma testi
- Yetki testi
- Audit testi
- Yedek/geri yükleme testi
- PDF testi
- Performans testi
- Final release etiketi

---

## 7. GLOBAL FOOD SAFETY GELİŞTİRME HATTI

Bu hat ticari reçete ve paket kapanışı tamamlandıktan sonra yürütülür.

### GFS-1 — HACCP Engine

- Ürün açıklaması ve amaçlanan kullanım
- Proses akış şeması
- Akış şeması yerinde doğrulama
- Tehlike kütüphanesi
- Biyolojik, kimyasal, fiziksel ve alerjen tehlikeler
- Olasılık ve şiddet puanlaması
- Kontrol önlemleri
- CCP/OPRP belirleme
- Kritik limitler
- İzleme planı
- Sapma yönetimi
- Düzeltici faaliyet
- Doğrulama
- HACCP plan revizyonu

### GFS-2 — Ön gereksinim programları

- Alerjen yönetimi
- Kalibrasyon
- Bakım ve arıza
- Zararlı mücadelesi
- Eğitim ve yetkinlik
- Gıda savunması/TACCP
- Gıda sahteciliği/VACCP

### GFS-3 — Denetim zekâsı

- İç denetim
- Müşteri şikâyeti
- Numune ve laboratuvar
- Ürün karantina/bloke/serbest bırakma
- Yönetimin gözden geçirmesi
- Tedarikçi risk puanlama
- Mock recall süre ve başarı ölçümü

---

## 8. CONNECTED FACTORY HATTI

### CF-1 — Mobil istemci ve API

- Güvenli API
- Mobil kimlik doğrulama
- Yetki
- Offline kayıt kuyruğu
- Senkronizasyon
- Çakışma çözümü
- Fotoğraflı kanıt
- Mobil audit

### CF-2 — Sensör entegrasyonu

- Sıcaklık sensörleri
- Soğuk oda takibi
- Eşik ve alarm
- Veri kesintisi algılama
- Kalibrasyon bağlantısı
- Otomatik uygunsuzluk taslağı

### CF-3 — Kamera ve yapay zekâ

- Bone, önlük ve hijyen kontrolü
- Yetkisiz alan girişi
- Hijyen bariyeri kullanımı
- Soğuk oda kapısı
- Tehlikeli davranışlar
- Ürün ve ambalaj görsel kalite kontrolü
- Olay kanıtı
- İnsan onayı
- CAPA bağlantısı
- Gizlilik ve saklama politikası

---

## 9. Fikir Backlog Yönetimi

Fatih Ayaz tarafından çalışma sırasında belirtilen yeni fikirler:

1. Önce ürün yönüyle karşılaştırılır.
2. Finans/cari kapsamındaysa ayrı ürüne taşınır.
3. REDBOX OS kapsamındaysa uygun sprint başlığına eklenir.
4. Aktif sprinti durdurmaz.
5. Mimari engelse yalnız altyapı seviyesi ele alınır.
6. Gerçek geliştirme sırası bu master roadmap'e göre korunur.

---

## 10. Sıradaki Kesin İşlem

`CRC-4 — Ticari başlangıç kataloğu`

Başka modül açılmayacaktır. CRC-1 reçete katalog sözleşmesi, CRC-2 atomik CSV/XLSX import motoru ve CRC-3 profesyonel reçete merkezi tamamlanmıştır. Sıradaki çalışma yalnız Fatih Ayaz tarafından sağlanacak yetkili gerçek reçete verileriyle 60+ ticari başlangıç kataloğunun dry-run, hata temizleme, sandbox import ve kontrollü kabul süreci üzerinde yürütülecektir. Yetkili kaynak olmadan gerçek reçete içeriği üretilmeyecek veya uydurulmayacaktır.
