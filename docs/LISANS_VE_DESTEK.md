# REDBOX OS Lisans ve Destek

Sürüm: 1.0.0

## Çevrimdışı lisans akışı

1. Sistem Yönetim Merkezi’nde gerçek firma profilini tamamlayın.
2. Lisans Merkezi’ni açın.
3. Lisans talep dosyasını dışa aktarın.
4. Talep dosyasını yetkili REDBOX lisans otoritesine iletin.
5. Verilen imzalı RBX1 lisansını Lisans Merkezi’ne yapıştırın.
6. Firma ve cihaz bilgilerini kontrol edip açık onay verin.
7. Lisansı etkinleştirin ve durumu yenileyin.

Talep dosyası ham cihaz kimliği taşımaz; firma ve cihazın SHA-256 parmak izlerini içerir. Özel imzalama anahtarı uygulama paketine dahil edilmez.

## Destek talebi hazırlama

Destek talebinde şu bilgileri paylaşın:

- REDBOX OS sürümü ve build numarası
- İşletim sistemi sürümü
- Sorunun oluştuğu ekran ve işlem
- Hatanın zamanı
- Gerekliyse ilgili log veya çökme raporu

Parola, ham lisans anahtarı, özel anahtar veya işletmenin gereksiz kişisel/ticari verilerini paylaşmayın.

## Log ve çökme raporları

macOS konumu:

    ~/Library/Application Support/REDBOX_OS/logs/

Çökme raporları `logs/crashes` altındadır. Bu dosyaları yalnız yetkili destek kanalıyla paylaşın.
