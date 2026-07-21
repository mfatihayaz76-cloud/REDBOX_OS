# REDBOX OS macOS Kurulum Kılavuzu

Sürüm: 1.1.0
Build: 2
Veritabanı şeması: 17

## Gereksinimler

- Desteklenen güncel macOS sürümü
- Kurulum ve uygulama verileri için yeterli disk alanı
- İlk yönetici hesabını oluşturacak yetkili kişi

## DMG ile kurulum

1. `REDBOX_OS-1.1.0-2.dmg` dosyasını açın.
2. `REDBOX OS.app` uygulamasını `Applications` kısayoluna sürükleyin.
3. Uygulamayı Applications klasöründen açın.
4. macOS güvenlik uyarısı gösterirse paketin yetkili kaynaktan
   geldiğini ve SHA-256 değerini doğrulayın.
5. Demo için `DEMO`, ticari kurulum için `GERCEK` modunu seçin.
6. Firma, tesis ve ilk yönetici kurulumunu tamamlayın.

## Demo kurulumu

`DEMO` seçildiğinde 30 günlük süre kod girmeden otomatik başlar.
Başka bir Mac için önceden üretilmiş lisans dosyası kullanılmaz.
Demo süresi cihaza yapılan ilk demo kurulumuna göre takip edilir.

## Ticari kurulum

`GERCEK` modunda Lisans Merkezi'nden talep JSON dosyasını dışa
aktarın. Yetkili REDBOX lisans otoritesinin bu firma ve Mac için
ürettiği RBX1 lisansını uygulamaya yapıştırıp açık onay vererek
etkinleştirin.

## Uygulama verileri

Kullanıcı verileri uygulama paketinin dışında tutulur:

    ~/Library/Application Support/REDBOX_OS/

Bu dizin canlı DB, yedek, kurtarma ve log dosyalarını içerir. DMG
içindeki uygulama hiçbir gerçek işletme verisi taşımaz.

## Güncelleme

1. Uygulama içinden doğrulanmış yedek alın.
2. REDBOX OS'yi kapatın.
3. Yeni uygulamayı Applications klasöründeki eski sürümün üzerine
   kopyalayın.
4. İlk açılıştaki otomatik şema yükseltmesinin tamamlanmasını bekleyin.
5. Lisans ve veri bütünlüğünü kontrol edin.

## İmzalama notu

Genel ticari dağıtım için Apple Developer ID imzası ve notarizasyon
önerilir. Ad-hoc imzalı iç/demo paketlerinde Gatekeeper uyarısı
görülebilir.
