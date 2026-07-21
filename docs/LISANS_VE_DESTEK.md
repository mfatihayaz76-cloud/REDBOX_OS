# REDBOX OS Lisans ve Destek

Sürüm: 1.1.0
Build: 2

## Demo lisansı

Demo kurulumu aktivasyon kodu gerektirmez. İlk kurulumda `DEMO`
seçildiğinde 30 günlük kullanım otomatik başlar. Kalan gün giriş
ekranında ve Lisans Merkezi'nde gösterilir.

## Ticari çevrimdışı lisans akışı

1. İlk kurulumda `GERCEK` modunu seçin.
2. Firma profilini eksiksiz tamamlayın.
3. Lisans Merkezi'nde lisans talebini JSON olarak dışa aktarın.
4. Dosyayı yetkili REDBOX lisans otoritesine iletin.
5. Bu firma ve cihaz için verilen imzalı RBX1 lisansını yapıştırın.
6. Bilgileri kontrol edip açık onay kutusunu işaretleyin.
7. Lisansı etkinleştirip durumu yenileyin.

Demo kullanımından ticari kullanıma geçerken de aynı RBX1 işlemi
uygulanır. Ticari lisans demo erişiminden önceliklidir.

Talep dosyası ham cihaz kimliği taşımaz; firma ve cihazın SHA-256
parmak izlerini içerir. Özel imzalama anahtarı uygulama, DMG veya
USB teslim klasörüne kesinlikle konulmaz.

## Cihaz bağı

Her Mac kendi lisans talebini üretir. Başka Mac için düzenlenmiş RBX1
lisansı kullanılamaz. Cihaz değişiminde yeni talep ve yeni lisans
gerekir.

## Destek talebi

Şunları paylaşın:

- REDBOX OS sürümü ve build numarası
- macOS sürümü
- Sorunun oluştuğu ekran ve zaman
- Gerekliyse ilgili log veya çökme raporu

Parola, ham RBX1 içeriği, özel anahtar veya gereksiz işletme verisi
paylaşmayın.

Log konumu:

    ~/Library/Application Support/REDBOX_OS/logs/
