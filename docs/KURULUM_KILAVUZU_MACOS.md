# REDBOX OS macOS Kurulum Kılavuzu

Sürüm: 1.0.0

## Gereksinimler

- Desteklenen güncel bir macOS sürümü
- Kurulum ve uygulama verileri için yeterli disk alanı
- İlk kurulumda yönetici hesabı oluşturacak yetkili kişi

## DMG ile kurulum

1. REDBOX_OS sürümlü DMG dosyasını açın.
2. REDBOX OS uygulamasını Applications kısayoluna sürükleyin.
3. Applications klasöründen REDBOX OS uygulamasını açın.
4. Firma profili ve ilk yönetici kurulumunu tamamlayın.
5. Lisans Merkezi üzerinden lisans talep dosyasını oluşturun.

## Uygulama verileri

Paketlenmiş macOS uygulaması verileri şu kullanıcı dizininde tutar:

    ~/Library/Application Support/REDBOX_OS/

Bu dizin içinde canlı veritabanı, yedekler, kurtarma dosyaları, loglar ve çökme raporları bulunur. Uygulama paketi güncellendiğinde bu dizin korunur.

## Güncelleme

Yeni REDBOX OS.app dosyasını Applications klasöründeki eski uygulamanın yerine koyun. Uygulama verisi uygulama paketinin dışında tutulduğu için mevcut işletme kayıtları korunur. Güncellemeden önce doğrulanmış yedek alın.

## Güvenlik notu

Genel ticari dağıtım için paket Apple Developer ID ile imzalanmalı ve Apple notarizasyonundan geçirilmelidir. İç kabul paketleri ad-hoc imzalı olabilir.
