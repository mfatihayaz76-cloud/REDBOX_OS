from datetime import datetime
from database.db import get_connection


def mamul_stok_lotlari(conn=None):
    kendi_baglanti = conn is None

    if kendi_baglanti:
        conn = get_connection()

    try:
        return conn.execute("""
            SELECT
                u.id AS uretim_id,
                u.urun_lot_no,
                p.ambalaj_gram,
                p.koli_ici_adet,
                SUM(p.paket_adedi) AS giris_paket_adedi,
                COALESCE(
                    (
                        SELECT SUM(sk.paket_adedi)
                        FROM sevkiyat_kalemleri sk
                        JOIN paketleme px
                          ON px.id = sk.paketleme_id
                        WHERE px.uretim_id = u.id
                          AND px.ambalaj_gram = p.ambalaj_gram
                    ),
                    0
                ) AS cikis_paket_adedi
            FROM paketleme p
            JOIN uretim u
              ON u.id = p.uretim_id
            GROUP BY
                u.id,
                u.urun_lot_no,
                p.ambalaj_gram,
                p.koli_ici_adet
            ORDER BY
                u.id,
                p.ambalaj_gram
        """).fetchall()

    finally:
        if kendi_baglanti:
            conn.close()


def mamul_stok_ozeti(conn=None):
    satirlar = mamul_stok_lotlari(conn)

    sonuc = []

    for row in satirlar:
        giris = int(row["giris_paket_adedi"])
        cikis = int(row["cikis_paket_adedi"])
        kalan = giris - cikis

        if kalan < 0:
            raise RuntimeError(
                "Negatif mamul stok tespit edildi: "
                f'{row["urun_lot_no"]} / '
                f'{row["ambalaj_gram"]} g'
            )

        koli_ici = (
            int(row["koli_ici_adet"])
            if row["koli_ici_adet"]
            else 0
        )

        if koli_ici > 0:
            tam_koli = kalan // koli_ici
            acik_paket = kalan % koli_ici
        else:
            tam_koli = 0
            acik_paket = kalan

        ambalaj_gram = int(row["ambalaj_gram"])

        sonuc.append({
            "uretim_id": row["uretim_id"],
            "urun_lot_no": row["urun_lot_no"],
            "ambalaj_gram": ambalaj_gram,
            "koli_ici_adet": koli_ici,
            "giris_paket_adedi": giris,
            "cikis_paket_adedi": cikis,
            "kalan_paket_adedi": kalan,
            "tam_koli": tam_koli,
            "acik_paket": acik_paket,
            "kalan_kg": (
                kalan * ambalaj_gram / 1000
            ),
        })

    return sonuc


def ambalaj_stok_toplami(ambalaj_gram, conn=None):
    satirlar = mamul_stok_ozeti(conn)

    toplam_paket = 0
    toplam_kg = 0.0

    for row in satirlar:
        if row["ambalaj_gram"] == ambalaj_gram:
            toplam_paket += row["kalan_paket_adedi"]
            toplam_kg += row["kalan_kg"]

    return {
        "ambalaj_gram": ambalaj_gram,
        "toplam_paket": toplam_paket,
        "toplam_kg": toplam_kg,
    }


def lot_ambalaj_stoklari(
    uretim_id,
    ambalaj_gram,
    conn=None
):
    kendi_baglanti = conn is None

    if kendi_baglanti:
        conn = get_connection()

    try:
        return conn.execute("""
            SELECT
                p.id AS paketleme_id,
                p.paketleme_tarihi,
                p.kayit_zamani,
                p.paket_adedi AS giris_paket_adedi,
                p.koli_ici_adet,
                COALESCE(
                    SUM(sk.paket_adedi),
                    0
                ) AS cikis_paket_adedi
            FROM paketleme p
            LEFT JOIN sevkiyat_kalemleri sk
              ON sk.paketleme_id = p.id
            WHERE p.uretim_id = ?
              AND p.ambalaj_gram = ?
            GROUP BY
                p.id,
                p.paketleme_tarihi,
                p.kayit_zamani,
                p.paket_adedi,
                p.koli_ici_adet
            ORDER BY
                p.id ASC
        """, (
            uretim_id,
            ambalaj_gram
        )).fetchall()

    finally:
        if kendi_baglanti:
            conn.close()


def sevkiyat_stok_dus(
    conn,
    sevkiyat_id,
    uretim_id,
    ambalaj_gram,
    paket_adedi
):
    if paket_adedi <= 0:
        raise ValueError(
            "Sevk paket adedi 0'dan büyük olmalıdır."
        )

    stoklar = lot_ambalaj_stoklari(
        uretim_id,
        ambalaj_gram,
        conn
    )

    toplam_kalan = sum(
        int(row["giris_paket_adedi"])
        - int(row["cikis_paket_adedi"])
        for row in stoklar
    )

    if paket_adedi > toplam_kalan:
        raise ValueError(
            "Sevkiyat miktarı mamul depo stokunu aşıyor.\n"
            f"Mevcut stok: {toplam_kalan} paket\n"
            f"Sevk talebi: {paket_adedi} paket"
        )

    kalan_talep = paket_adedi
    dagitim = []

    for row in stoklar:
        if kalan_talep <= 0:
            break

        paketleme_kalan = (
            int(row["giris_paket_adedi"])
            - int(row["cikis_paket_adedi"])
        )

        if paketleme_kalan <= 0:
            continue

        dusulecek = min(
            paketleme_kalan,
            kalan_talep
        )

        sevk_kg = (
            dusulecek * ambalaj_gram / 1000
        )

        conn.execute("""
            INSERT INTO sevkiyat_kalemleri (
                sevkiyat_id,
                paketleme_id,
                paket_adedi,
                sevk_kg
            )
            VALUES (?, ?, ?, ?)
        """, (
            sevkiyat_id,
            row["paketleme_id"],
            dusulecek,
            sevk_kg
        ))

        dagitim.append({
            "paketleme_id": row["paketleme_id"],
            "paket_adedi": dusulecek,
            "sevk_kg": sevk_kg,
        })

        kalan_talep -= dusulecek

    if kalan_talep != 0:
        raise RuntimeError(
            "Mamul stok dağıtım motoru sevkiyatı "
            "tam dağıtamadı."
        )

    return dagitim



def mamul_stok_hareketi_ekle(
    conn,
    paketleme_id,
    hareket_tarihi,
    hareket_tipi,
    yon,
    paket_adedi,
    aciklama=None,
):
    izinli_tipler = {
        "PAKETLEME",
        "SEVKIYAT",
        "TARIHSEL_KAPANIS",
        "IADE",
        "IMHA",
        "SAYIM_DUZELTME",
    }

    izinli_yonler = {
        "GIRIS",
        "CIKIS",
    }

    hareket_tipi = (
        str(hareket_tipi)
        .strip()
        .upper()
    )

    yon = (
        str(yon)
        .strip()
        .upper()
    )

    paket_adedi = int(
        paket_adedi
    )

    if hareket_tipi not in izinli_tipler:
        raise ValueError(
            "Geçersiz mamul stok hareket tipi."
        )

    if yon not in izinli_yonler:
        raise ValueError(
            "Geçersiz mamul stok hareket yönü."
        )

    if paket_adedi <= 0:
        raise ValueError(
            "Mamul stok hareket paket adedi "
            "0'dan büyük olmalıdır."
        )

    paketleme = conn.execute("""
        SELECT
            id,
            paket_adedi
        FROM paketleme
        WHERE id = ?
    """, (
        paketleme_id,
    )).fetchone()

    if paketleme is None:
        raise ValueError(
            "Paketleme kaydı bulunamadı."
        )

    if yon == "CIKIS":
        sevk_cikis = 0

        hareket_net = conn.execute("""
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN yon='GIRIS'
                        THEN paket_adedi
                        WHEN yon='CIKIS'
                        THEN -paket_adedi
                        ELSE 0
                    END
                ),
                0
            )
            FROM mamul_stok_hareketleri
            WHERE paketleme_id=?
        """, (
            paketleme_id,
        )).fetchone()[0]

        kalan = int(hareket_net) - int(sevk_cikis)

        if paket_adedi > kalan:
            raise ValueError(
                "Mamul stok hareketi mevcut "
                "paket stokunu aşıyor.\n"
                f"Mevcut stok: {kalan} paket\n"
                f"Hareket talebi: "
                f"{paket_adedi} paket"
            )

    conn.execute("""
        INSERT INTO mamul_stok_hareketleri (
            hareket_tarihi,
            paketleme_id,
            hareket_tipi,
            yon,
            paket_adedi,
            aciklama,
            kayit_zamani
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        hareket_tarihi,
        paketleme_id,
        hareket_tipi,
        yon,
        paket_adedi,
        aciklama,
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    ))


def sevkiyat_hareketi_ekle(
    conn,
    paketleme_id,
    hareket_tarihi,
    paket_adedi,
    aciklama=None,
):
    return mamul_stok_hareketi_ekle(
        conn=conn,
        paketleme_id=paketleme_id,
        hareket_tarihi=hareket_tarihi,
        hareket_tipi="SEVKIYAT",
        yon="CIKIS",
        paket_adedi=paket_adedi,
        aciklama=aciklama,
    )
