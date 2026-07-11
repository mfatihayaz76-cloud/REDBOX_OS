from database.cleaning_engine import get_cleaning_report_dataset
from collections import Counter
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


BASE_DIR = Path(__file__).resolve().parent.parent

EXPORTS_DIR = Path.home() / "Downloads"

EXPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


NORMAL_FONT_ADAYLARI = [
    Path(
        "/System/Library/Fonts/"
        "Supplemental/Arial.ttf"
    ),
    Path(
        "/Library/Fonts/Arial.ttf"
    ),
]


BOLD_FONT_ADAYLARI = [
    Path(
        "/System/Library/Fonts/"
        "Supplemental/Arial Bold.ttf"
    ),
    Path(
        "/Library/Fonts/Arial Bold.ttf"
    ),
]


def _font_bul(adaylar):
    for path in adaylar:
        if path.exists():
            return path

    return None


def pdf_fontlarini_hazirla():
    normal_font = _font_bul(
        NORMAL_FONT_ADAYLARI
    )

    bold_font = _font_bul(
        BOLD_FONT_ADAYLARI
    )

    if normal_font is None:
        raise RuntimeError(
            "Türkçe uyumlu Arial normal font bulunamadı."
        )

    if bold_font is None:
        raise RuntimeError(
            "Türkçe uyumlu Arial bold font bulunamadı."
        )

    if "RedboxNormal" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(
                "RedboxNormal",
                str(normal_font)
            )
        )

    if "RedboxBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(
                "RedboxBold",
                str(bold_font)
            )
        )

    pdfmetrics.registerFontFamily(
        "RedboxFont",
        normal="RedboxNormal",
        bold="RedboxBold",
    )


def pdf_stilleri():
    pdf_fontlarini_hazirla()

    styles = getSampleStyleSheet()

    return {
        "firma": ParagraphStyle(
            "RedboxFirma",
            parent=styles["Title"],
            fontName="RedboxBold",
            fontSize=20,
            leading=25,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "rapor_baslik": ParagraphStyle(
            "RedboxRaporBaslik",
            parent=styles["Heading1"],
            fontName="RedboxBold",
            fontSize=16,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=15,
        ),
        "bolum": ParagraphStyle(
            "RedboxBolum",
            parent=styles["Heading2"],
            fontName="RedboxBold",
            fontSize=13,
            leading=17,
            alignment=TA_LEFT,
            spaceBefore=10,
            spaceAfter=7,
        ),
        "govde": ParagraphStyle(
            "RedboxGovde",
            parent=styles["BodyText"],
            fontName="RedboxNormal",
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
        ),
        "govde_bold": ParagraphStyle(
            "RedboxGovdeBold",
            parent=styles["BodyText"],
            fontName="RedboxBold",
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
        ),
        "kucuk": ParagraphStyle(
            "RedboxKucuk",
            parent=styles["BodyText"],
            fontName="RedboxNormal",
            fontSize=7,
            leading=10,
            alignment=TA_LEFT,
        ),
    }


def pdf_metin(deger):
    if deger is None:
        return "-"

    return escape(
        str(deger)
    )


def pdf_dosya_adi(rapor_tipi, referans=None):
    zaman = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    parcalar = [
        "REDBOX",
        str(rapor_tipi).strip().upper(),
    ]

    if referans:
        temiz = (
            str(referans)
            .strip()
            .upper()
            .replace(" ", "_")
            .replace("/", "-")
            .replace("\\", "-")
        )

        parcalar.append(
            temiz
        )

    parcalar.append(
        zaman
    )

    return "_".join(
        parcalar
    ) + ".pdf"


def pdf_yolu(rapor_tipi, referans=None):
    return EXPORTS_DIR / pdf_dosya_adi(
        rapor_tipi=rapor_tipi,
        referans=referans,
    )


def pdf_sayfa_altligi(canvas, doc):
    canvas.saveState()

    canvas.setFont(
        "RedboxNormal",
        7
    )

    canvas.drawString(
        40,
        22,
        "REDBOX GIDA"
    )

    canvas.drawRightString(
        A4[0] - 40,
        22,
        f"Sayfa {doc.page}"
    )

    canvas.restoreState()


def pdf_dokuman_olustur(dosya_yolu):
    pdf_fontlarini_hazirla()

    return SimpleDocTemplate(
        str(dosya_yolu),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=38,
        bottomMargin=38,
        title="REDBOX GIDA RAPORU",
        author="REDBOX GIDA",
    )


def pdf_rapor_basligi(
    story,
    rapor_adi,
    referans=None,
):
    styles = pdf_stilleri()

    story.append(
        Paragraph(
            "REDBOX GIDA",
            styles["firma"]
        )
    )

    story.append(
        Paragraph(
            pdf_metin(rapor_adi),
            styles["rapor_baslik"]
        )
    )

    if referans:
        story.append(
            Paragraph(
                (
                    "<b>Rapor Referansı:</b> "
                    + pdf_metin(referans)
                ),
                styles["govde"]
            )
        )

    story.append(
        Paragraph(
            (
                "<b>Rapor Oluşturma Zamanı:</b> "
                + datetime.now().strftime(
                    "%d.%m.%Y %H:%M:%S"
                )
            ),
            styles["govde"]
        )
    )

    story.append(
        Spacer(
            1,
            12
        )
    )


def pdf_bolum_basligi(story, baslik):
    styles = pdf_stilleri()

    story.append(
        Paragraph(
            pdf_metin(baslik),
            styles["bolum"]
        )
    )


def pdf_bilgi_satiri(
    story,
    etiket,
    deger,
):
    styles = pdf_stilleri()

    story.append(
        Paragraph(
            (
                "<b>"
                + pdf_metin(etiket)
                + ":</b> "
                + pdf_metin(deger)
            ),
            styles["govde"]
        )
    )


def pdf_tablo(
    story,
    basliklar,
    satirlar,
    kolon_genislikleri=None,
):
    styles = pdf_stilleri()

    veri = []

    veri.append(
        [
            Paragraph(
                pdf_metin(baslik),
                styles["govde_bold"]
            )
            for baslik in basliklar
        ]
    )

    for satir in satirlar:
        veri.append(
            [
                Paragraph(
                    pdf_metin(deger),
                    styles["kucuk"]
                )
                for deger in satir
            ]
        )

    tablo = Table(
        veri,
        colWidths=kolon_genislikleri,
        repeatRows=1,
        hAlign="LEFT",
    )

    tablo.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#D9D9D9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.black,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(
        tablo
    )

    story.append(
        Spacer(
            1,
            10
        )
    )


def pdf_build(doc, story):
    doc.build(
        story,
        onFirstPage=pdf_sayfa_altligi,
        onLaterPages=pdf_sayfa_altligi,
    )



def hammadde_kabul_pdf_olustur(conn, depo_kabul_id):
    kayit = conn.execute(
        """
        SELECT
            dk.id,
            dk.kabul_tarihi,
            h.ad AS hammadde,
            COALESCE(
                t.tedarikci_adi,
                dk.tedarikci
            ) AS tedarikci,
            dk.tedarikci_lot_no,
            dk.uretim_tarihi,
            dk.skt_tett,
            dk.miktar_kg,
            dk.kabul_durumu,
            dk.aciklama,
            dk.kayit_zamani
        FROM depo_kabul dk
        JOIN hammaddeler h
            ON h.id = dk.hammadde_id
        LEFT JOIN tedarikciler t
            ON t.id = dk.tedarikci_id
        WHERE dk.id = ?
        """,
        (depo_kabul_id,)
    ).fetchone()

    if kayit is None:
        raise ValueError(
            "Hammadde kabul kaydı bulunamadı."
        )

    referans = (
        f"KABUL-{kayit['id']}-"
        f"{kayit['tedarikci_lot_no']}"
    )

    dosya = pdf_yolu(
        "HAMMADDE_KABUL",
        referans
    )

    doc = pdf_dokuman_olustur(dosya)
    story = []

    pdf_rapor_basligi(
        story,
        "HAMMADDE KABUL RAPORU",
        referans
    )

    pdf_bolum_basligi(
        story,
        "Kabul Bilgileri"
    )

    bilgiler = [
        ("Kabul Kayıt ID", kayit["id"]),
        ("Kabul Tarihi", kayit["kabul_tarihi"]),
        ("Hammadde", kayit["hammadde"]),
        ("Tedarikçi", kayit["tedarikci"]),
        (
            "Tedarikçi Lot No",
            kayit["tedarikci_lot_no"]
        ),
        ("Üretim Tarihi", kayit["uretim_tarihi"]),
        ("SKT / TETT", kayit["skt_tett"]),
        (
            "Kabul Miktarı",
            f"{kayit['miktar_kg']:.3f} kg"
        ),
        ("Kabul Durumu", kayit["kabul_durumu"]),
        ("Kayıt Zamanı", kayit["kayit_zamani"]),
    ]

    for etiket, deger in bilgiler:
        pdf_bilgi_satiri(
            story,
            etiket,
            deger
        )

    pdf_bolum_basligi(
        story,
        "Açıklama / Tarihsel Veri Notu"
    )

    pdf_bilgi_satiri(
        story,
        "Açıklama",
        kayit["aciklama"] or "-"
    )

    pdf_build(doc, story)

    return dosya


def uretim_pdf_olustur(conn, uretim_id):
    uretim = conn.execute(
        """
        SELECT
            u.id,
            u.uretim_tarihi,
            u.urun_lot_no,
            u.parti_sayisi,
            u.teorik_uretim_kg,
            u.uretim_firesi_kg,
            u.net_uretim_kg,
            u.personel_1,
            u.personel_2,
            u.aciklama,
            u.kayit_zamani,
            ur.recete_id
        FROM uretim u
        LEFT JOIN uretim_recete ur
            ON ur.uretim_id = u.id
        WHERE u.id = ?
        """,
        (uretim_id,)
    ).fetchone()

    if uretim is None:
        raise ValueError(
            "Üretim kaydı bulunamadı."
        )

    lotlar = conn.execute(
        """
        SELECT
            h.ad AS hammadde,
            dk.tedarikci_lot_no,
            COALESCE(
                t.tedarikci_adi,
                dk.tedarikci
            ) AS tedarikci,
            dk.kabul_tarihi,
            uhl.kullanilan_miktar_kg
        FROM uretim_hammadde_lotlari uhl
        JOIN depo_kabul dk
            ON dk.id = uhl.depo_kabul_id
        JOIN hammaddeler h
            ON h.id = dk.hammadde_id
        LEFT JOIN tedarikciler t
            ON t.id = dk.tedarikci_id
        WHERE uhl.uretim_id = ?
        ORDER BY h.id, dk.id
        """,
        (uretim_id,)
    ).fetchall()

    referans = uretim["urun_lot_no"]

    dosya = pdf_yolu(
        "URETIM",
        referans
    )

    doc = pdf_dokuman_olustur(dosya)
    story = []

    pdf_rapor_basligi(
        story,
        "ÜRETİM RAPORU",
        referans
    )

    pdf_bolum_basligi(
        story,
        "Üretim ve Kütle Dengesi"
    )

    bilgiler = [
        ("Üretim Kayıt ID", uretim["id"]),
        ("Üretim Tarihi", uretim["uretim_tarihi"]),
        ("Ürün Lot No", uretim["urun_lot_no"]),
        ("Parti Sayısı", uretim["parti_sayisi"]),
        (
            "Teorik Üretim",
            f"{uretim['teorik_uretim_kg']:.3f} kg"
        ),
        (
            "Üretim Firesi",
            f"{uretim['uretim_firesi_kg']:.3f} kg"
        ),
        (
            "Net Üretim",
            f"{uretim['net_uretim_kg']:.3f} kg"
        ),
        ("Reçete ID", uretim["recete_id"]),
        ("Personel 1", uretim["personel_1"]),
        ("Personel 2", uretim["personel_2"]),
        ("Kayıt Zamanı", uretim["kayit_zamani"]),
        ("Açıklama", uretim["aciklama"] or "-"),
    ]

    for etiket, deger in bilgiler:
        pdf_bilgi_satiri(
            story,
            etiket,
            deger
        )

    pdf_bolum_basligi(
        story,
        "Gerçek Hammadde Lot Tüketimleri"
    )

    satirlar = [
        [
            row["hammadde"],
            row["tedarikci_lot_no"],
            row["tedarikci"],
            row["kabul_tarihi"],
            f"{row['kullanilan_miktar_kg']:.3f}",
        ]
        for row in lotlar
    ]

    pdf_tablo(
        story,
        [
            "Hammadde",
            "Lot No",
            "Tedarikçi",
            "Kabul Tarihi",
            "Kullanılan kg",
        ],
        satirlar,
        [105, 85, 105, 75, 75]
    )

    pdf_build(doc, story)

    return dosya


def paketleme_pdf_olustur(conn, paketleme_id):
    kayit = conn.execute(
        """
        SELECT
            p.id,
            p.paketleme_tarihi,
            u.urun_lot_no,
            p.ambalaj_gram,
            p.paket_adedi,
            p.koli_ici_adet,
            p.paketlenen_kg,
            p.paketleme_firesi_kg,
            p.aciklama,
            p.kayit_zamani
        FROM paketleme p
        JOIN uretim u
            ON u.id = p.uretim_id
        WHERE p.id = ?
        """,
        (paketleme_id,)
    ).fetchone()

    if kayit is None:
        raise ValueError(
            "Paketleme kaydı bulunamadı."
        )

    referans = (
        f"{kayit['urun_lot_no']}-"
        f"{kayit['ambalaj_gram']}G-"
        f"P{kayit['id']}"
    )

    dosya = pdf_yolu(
        "PAKETLEME",
        referans
    )

    doc = pdf_dokuman_olustur(dosya)
    story = []

    pdf_rapor_basligi(
        story,
        "PAKETLEME RAPORU",
        referans
    )

    pdf_bolum_basligi(
        story,
        "Paketleme ve Kütle Dengesi"
    )

    bilgiler = [
        ("Paketleme Kayıt ID", kayit["id"]),
        (
            "Paketleme Tarihi",
            kayit["paketleme_tarihi"]
        ),
        ("Ürün Lot No", kayit["urun_lot_no"]),
        (
            "Ambalaj Formatı",
            f"{kayit['ambalaj_gram']} g"
        ),
        ("Paket Adedi", kayit["paket_adedi"]),
        ("Koli İçi Adet", kayit["koli_ici_adet"]),
        (
            "Paketlenen Miktar",
            f"{kayit['paketlenen_kg']:.3f} kg"
        ),
        (
            "Paketleme Firesi",
            f"{kayit['paketleme_firesi_kg']:.3f} kg"
        ),
        ("Kayıt Zamanı", kayit["kayit_zamani"]),
        ("Açıklama", kayit["aciklama"] or "-"),
    ]

    for etiket, deger in bilgiler:
        pdf_bilgi_satiri(
            story,
            etiket,
            deger
        )

    pdf_build(doc, story)

    return dosya


def sevkiyat_pdf_olustur(conn, sevkiyat_id):
    sevkiyat = conn.execute(
        """
        SELECT
            s.id,
            s.sevkiyat_tarihi,
            COALESCE(
                m.musteri_adi,
                s.musteri
            ) AS musteri,
            s.sevk_koli_adedi,
            s.sevk_acik_paket_adedi,
            s.arac_plaka,
            s.belge_no,
            s.soguk_zincir,
            s.aciklama,
            s.kayit_zamani
        FROM sevkiyat s
        LEFT JOIN musteriler m
            ON m.id = s.musteri_id
        WHERE s.id = ?
        """,
        (sevkiyat_id,)
    ).fetchone()

    if sevkiyat is None:
        raise ValueError(
            "Sevkiyat kaydı bulunamadı."
        )

    kalemler = conn.execute(
        """
        SELECT
            u.urun_lot_no,
            p.paketleme_tarihi,
            p.ambalaj_gram,
            p.koli_ici_adet,
            sk.paket_adedi,
            sk.sevk_kg
        FROM sevkiyat_kalemleri sk
        JOIN paketleme p
            ON p.id = sk.paketleme_id
        JOIN uretim u
            ON u.id = p.uretim_id
        WHERE sk.sevkiyat_id = ?
        ORDER BY sk.id
        """,
        (sevkiyat_id,)
    ).fetchall()

    referans = (
        sevkiyat["belge_no"]
        or f"SEVKIYAT-{sevkiyat['id']}"
    )

    dosya = pdf_yolu(
        "SEVKIYAT",
        referans
    )

    doc = pdf_dokuman_olustur(dosya)
    story = []

    pdf_rapor_basligi(
        story,
        "SEVKİYAT RAPORU",
        referans
    )

    pdf_bolum_basligi(
        story,
        "Sevkiyat Bilgileri"
    )

    bilgiler = [
        ("Sevkiyat Kayıt ID", sevkiyat["id"]),
        (
            "Sevkiyat Tarihi",
            sevkiyat["sevkiyat_tarihi"]
        ),
        ("Müşteri", sevkiyat["musteri"]),
        (
            "Sevk Koli Adedi",
            sevkiyat["sevk_koli_adedi"]
        ),
        (
            "Açık Paket Adedi",
            sevkiyat["sevk_acik_paket_adedi"]
        ),
        ("Araç Plaka", sevkiyat["arac_plaka"] or "-"),
        ("Belge No", sevkiyat["belge_no"] or "-"),
        (
            "Soğuk Zincir",
            (
                "EVET"
                if sevkiyat["soguk_zincir"]
                else "HAYIR"
            )
        ),
        ("Kayıt Zamanı", sevkiyat["kayit_zamani"]),
        ("Açıklama", sevkiyat["aciklama"] or "-"),
    ]

    for etiket, deger in bilgiler:
        pdf_bilgi_satiri(
            story,
            etiket,
            deger
        )

    pdf_bolum_basligi(
        story,
        "Sevk Edilen Ürün Lotları"
    )

    satirlar = [
        [
            row["urun_lot_no"],
            row["paketleme_tarihi"],
            f"{row['ambalaj_gram']} g",
            row["koli_ici_adet"],
            row["paket_adedi"],
            f"{row['sevk_kg']:.3f}",
        ]
        for row in kalemler
    ]

    pdf_tablo(
        story,
        [
            "Ürün Lot",
            "Paketleme",
            "Format",
            "Koli İçi",
            "Paket",
            "Sevk kg",
        ],
        satirlar,
        [80, 75, 60, 60, 60, 70]
    )

    toplam_paket = sum(
        row["paket_adedi"]
        for row in kalemler
    )

    toplam_kg = sum(
        row["sevk_kg"]
        for row in kalemler
    )

    pdf_bolum_basligi(
        story,
        "Sevkiyat Kütle Özeti"
    )

    pdf_bilgi_satiri(
        story,
        "Toplam Sevk Paketi",
        toplam_paket
    )

    pdf_bilgi_satiri(
        story,
        "Toplam Sevk Miktarı",
        f"{toplam_kg:.3f} kg"
    )

    pdf_build(doc, story)

    return dosya


def izlenebilirlik_pdf_olustur(conn, uretim_id):
    styles = pdf_stilleri()

    uretim = conn.execute("""
        SELECT
            u.id,
            u.uretim_tarihi,
            u.urun_lot_no,
            u.parti_sayisi,
            u.teorik_uretim_kg,
            u.uretim_firesi_kg,
            u.net_uretim_kg,
            u.personel_1,
            u.personel_2,
            u.aciklama,
            r.ad AS recete_adi
        FROM uretim u
        LEFT JOIN uretim_recete ur
          ON ur.uretim_id = u.id
        LEFT JOIN receteler r
          ON r.id = ur.recete_id
        WHERE u.id = ?
    """, (
        uretim_id,
    )).fetchone()

    if uretim is None:
        raise ValueError(
            "Üretim lotu bulunamadı."
        )

    hammaddeler = conn.execute("""
        SELECT
            h.ad AS hammadde,
            dk.tedarikci,
            dk.tedarikci_lot_no,
            dk.kabul_tarihi,
            dk.uretim_tarihi,
            dk.skt_tett,
            uhl.kullanilan_miktar_kg
        FROM uretim_hammadde_lotlari uhl
        JOIN depo_kabul dk
          ON dk.id = uhl.depo_kabul_id
        JOIN hammaddeler h
          ON h.id = dk.hammadde_id
        WHERE uhl.uretim_id = ?
        ORDER BY
            h.ad,
            dk.id
    """, (
        uretim_id,
    )).fetchall()

    paketlemeler = conn.execute("""
        SELECT
            id,
            paketleme_tarihi,
            ambalaj_gram,
            paket_adedi,
            paketlenen_kg,
            paketleme_firesi_kg,
            koli_ici_adet,
            aciklama
        FROM paketleme
        WHERE uretim_id = ?
        ORDER BY id
    """, (
        uretim_id,
    )).fetchall()

    sevkiyatlar = conn.execute("""
        SELECT
            s.id,
            s.sevkiyat_tarihi,
            COALESCE(
                m.musteri_adi,
                s.musteri
            ) AS musteri,
            s.arac_plaka,
            s.belge_no,
            s.soguk_zincir,
            p.ambalaj_gram,
            p.koli_ici_adet,
            SUM(sk.paket_adedi) AS toplam_paket,
            SUM(sk.sevk_kg) AS toplam_kg
        FROM sevkiyat s
        JOIN sevkiyat_kalemleri sk
          ON sk.sevkiyat_id = s.id
        JOIN paketleme p
          ON p.id = sk.paketleme_id
        LEFT JOIN musteriler m
          ON m.id = s.musteri_id
        WHERE p.uretim_id = ?
        GROUP BY
            s.id,
            s.sevkiyat_tarihi,
            m.musteri_adi,
            s.musteri,
            s.arac_plaka,
            s.belge_no,
            s.soguk_zincir,
            p.ambalaj_gram,
            p.koli_ici_adet
        ORDER BY
            s.id,
            p.ambalaj_gram
    """, (
        uretim_id,
    )).fetchall()

    dosya = pdf_yolu(
        "IZLENEBILIRLIK",
        uretim["urun_lot_no"]
    )

    doc = pdf_dokuman_olustur(
        dosya
    )

    story = []

    pdf_rapor_basligi(
        story,
        "İZLENEBİLİRLİK VE GERİ ÇAĞIRMA RAPORU",
        uretim["urun_lot_no"]
    )

    pdf_bolum_basligi(
        story,
        "1. ÜRÜN LOTU VE ÜRETİM"
    )

    pdf_bilgi_satiri(
        story,
        "Ürün Lotu",
        uretim["urun_lot_no"]
    )

    pdf_bilgi_satiri(
        story,
        "Üretim Tarihi",
        uretim["uretim_tarihi"]
    )

    pdf_bilgi_satiri(
        story,
        "Reçete",
        uretim["recete_adi"] or "-"
    )

    pdf_bilgi_satiri(
        story,
        "Parti Sayısı",
        uretim["parti_sayisi"]
    )

    pdf_bilgi_satiri(
        story,
        "Teorik Üretim",
        f'{uretim["teorik_uretim_kg"]:.3f} kg'
    )

    pdf_bilgi_satiri(
        story,
        "Üretim Firesi",
        f'{uretim["uretim_firesi_kg"]:.3f} kg'
    )

    pdf_bilgi_satiri(
        story,
        "Net Üretim",
        f'{uretim["net_uretim_kg"]:.3f} kg'
    )

    pdf_bilgi_satiri(
        story,
        "Personel",
        (
            f'{uretim["personel_1"] or "-"} / '
            f'{uretim["personel_2"] or "-"}'
        )
    )

    if uretim["aciklama"]:
        pdf_bilgi_satiri(
            story,
            "Üretim Açıklaması",
            uretim["aciklama"]
        )

    pdf_bolum_basligi(
        story,
        "2. HAMMADDE VE TEDARİKÇİ LOT ZİNCİRİ"
    )

    if hammaddeler:
        hammadde_satirlari = []

        for row in hammaddeler:
            hammadde_satirlari.append(
                [
                    row["hammadde"],
                    row["tedarikci"],
                    row["tedarikci_lot_no"],
                    row["kabul_tarihi"],
                    row["uretim_tarihi"] or "-",
                    row["skt_tett"] or "-",
                    (
                        f'{row["kullanilan_miktar_kg"]:.3f}'
                    ),
                ]
            )

        pdf_tablo(
            story,
            [
                "Hammadde",
                "Tedarikçi",
                "Lot No",
                "Kabul",
                "ÜRT",
                "SKT/TETT",
                "Kullanılan Kg",
            ],
            hammadde_satirlari,
            [
                85,
                75,
                75,
                55,
                55,
                60,
                65,
            ]
        )
    else:
        story.append(
            Paragraph(
                (
                    "Bu üretim lotuna bağlı "
                    "hammadde lot tüketim kaydı yok."
                ),
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "3. PAKETLEME ZİNCİRİ"
    )

    if paketlemeler:
        paketleme_satirlari = []

        for row in paketlemeler:
            koli_ici = (
                row["koli_ici_adet"]
                or 0
            )

            if koli_ici > 0:
                tam_koli = (
                    row["paket_adedi"]
                    // koli_ici
                )

                acik_paket = (
                    row["paket_adedi"]
                    % koli_ici
                )
            else:
                tam_koli = 0
                acik_paket = row["paket_adedi"]

            if row["ambalaj_gram"] == 500:
                ambalaj = "500 g"
            elif row["ambalaj_gram"] == 2500:
                ambalaj = "2.5 kg"
            else:
                ambalaj = (
                    f'{row["ambalaj_gram"]} g'
                )

            paketleme_satirlari.append(
                [
                    row["paketleme_tarihi"],
                    ambalaj,
                    row["paket_adedi"],
                    tam_koli,
                    acik_paket,
                    f'{row["paketlenen_kg"]:.3f}',
                    (
                        f'{row["paketleme_firesi_kg"]:.3f}'
                    ),
                ]
            )

        pdf_tablo(
            story,
            [
                "Tarih",
                "Ambalaj",
                "Paket",
                "Tam Koli",
                "Açık",
                "Paketlenen Kg",
                "Fire Kg",
            ],
            paketleme_satirlari,
            [
                70,
                60,
                50,
                55,
                45,
                80,
                60,
            ]
        )
    else:
        story.append(
            Paragraph(
                "Bu ürün lotuna bağlı paketleme kaydı yok.",
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "4. SEVKİYAT VE MÜŞTERİ ZİNCİRİ"
    )

    if sevkiyatlar:
        sevkiyat_satirlari = []

        for row in sevkiyatlar:
            soguk = (
                "EVET"
                if row["soguk_zincir"]
                else "HAYIR"
            )

            koli_ici = (
                row["koli_ici_adet"]
                or 0
            )

            if koli_ici > 0:
                sevk_koli = (
                    row["toplam_paket"]
                    // koli_ici
                )

                sevk_acik = (
                    row["toplam_paket"]
                    % koli_ici
                )
            else:
                sevk_koli = 0
                sevk_acik = row["toplam_paket"]

            sevkiyat_satirlari.append(
                [
                    row["sevkiyat_tarihi"],
                    row["musteri"],
                    sevk_koli,
                    sevk_acik,
                    row["toplam_paket"],
                    f'{row["toplam_kg"]:.3f}',
                    row["arac_plaka"] or "-",
                    row["belge_no"] or "-",
                    soguk,
                ]
            )

        pdf_tablo(
            story,
            [
                "Tarih",
                "Müşteri",
                "Koli",
                "Açık",
                "Paket",
                "Kg",
                "Plaka",
                "Belge",
                "Soğuk",
            ],
            sevkiyat_satirlari,
            [
                55,
                80,
                35,
                35,
                40,
                50,
                55,
                55,
                40,
            ]
        )
    else:
        story.append(
            Paragraph(
                (
                    "Bu ürün lotuna bağlı "
                    "sevkiyat kaydı yok."
                ),
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "5. GERİ ÇAĞIRMA DEĞERLENDİRMESİ"
    )

    musteri_sayisi = len(
        {
            row["musteri"]
            for row in sevkiyatlar
        }
    )

    toplam_sevk_kg = sum(
        (
            row["toplam_kg"]
            or 0
        )
        for row in sevkiyatlar
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Ürün Lotu",
        uretim["urun_lot_no"]
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Sevkiyat Sayısı",
        len(sevkiyatlar)
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Müşteri / Sevk Noktası",
        musteri_sayisi
    )

    pdf_bilgi_satiri(
        story,
        "Toplam Sevk Edilen Miktar",
        f"{toplam_sevk_kg:.3f} kg"
    )

    pdf_bilgi_satiri(
        story,
        "İzlenebilirlik Sonucu",
        (
            "Ürün lotu bazında üretim, hammadde, "
            "paketleme ve sevkiyat zinciri "
            "veritabanı kayıtlarından oluşturulmuştur."
        )
    )

    story.append(
        Spacer(
            1,
            25
        )
    )

    pdf_tablo(
        story,
        [
            "Hazırlayan",
            "Kontrol Eden",
            "Tarih / İmza",
        ],
        [
            [
                "Fatih Ayaz",
                "",
                "",
            ]
        ],
        [
            170,
            170,
            150,
        ]
    )

    pdf_build(
        doc,
        story
    )

    return dosya


def geri_cagirma_pdf_olustur(conn, depo_kabul_id):
    styles = pdf_stilleri()

    hammadde_lotu = conn.execute("""
        SELECT
            dk.id,
            dk.kabul_tarihi,
            dk.tedarikci,
            dk.tedarikci_lot_no,
            dk.uretim_tarihi,
            dk.skt_tett,
            dk.miktar_kg,
            dk.kabul_durumu,
            dk.aciklama,
            h.ad AS hammadde
        FROM depo_kabul dk
        JOIN hammaddeler h
          ON h.id = dk.hammadde_id
        WHERE dk.id = ?
    """, (
        depo_kabul_id,
    )).fetchone()

    if hammadde_lotu is None:
        raise ValueError(
            "Hammadde lot kaydı bulunamadı."
        )

    uretimler = conn.execute("""
        SELECT
            u.id,
            u.uretim_tarihi,
            u.urun_lot_no,
            u.parti_sayisi,
            u.teorik_uretim_kg,
            u.uretim_firesi_kg,
            u.net_uretim_kg,
            uhl.kullanilan_miktar_kg
        FROM uretim_hammadde_lotlari uhl
        JOIN uretim u
          ON u.id = uhl.uretim_id
        WHERE uhl.depo_kabul_id = ?
        ORDER BY u.id
    """, (
        depo_kabul_id,
    )).fetchall()

    paketlemeler = conn.execute("""
        SELECT
            u.id AS uretim_id,
            u.urun_lot_no,
            p.id AS paketleme_id,
            p.paketleme_tarihi,
            p.ambalaj_gram,
            p.paket_adedi,
            p.koli_ici_adet,
            p.paketlenen_kg,
            p.paketleme_firesi_kg
        FROM uretim_hammadde_lotlari uhl
        JOIN uretim u
          ON u.id = uhl.uretim_id
        JOIN paketleme p
          ON p.uretim_id = u.id
        WHERE uhl.depo_kabul_id = ?
        ORDER BY
            u.id,
            p.id
    """, (
        depo_kabul_id,
    )).fetchall()

    sevkiyatlar = conn.execute("""
        SELECT
            s.id AS sevkiyat_id,
            s.sevkiyat_tarihi,
            COALESCE(
                m.musteri_adi,
                s.musteri
            ) AS musteri,
            s.arac_plaka,
            s.belge_no,
            s.soguk_zincir,
            p.ambalaj_gram,
            p.koli_ici_adet,
            u.urun_lot_no,
            SUM(sk.paket_adedi) AS toplam_paket,
            SUM(sk.sevk_kg) AS toplam_kg
        FROM uretim_hammadde_lotlari uhl
        JOIN uretim u
          ON u.id = uhl.uretim_id
        JOIN paketleme p
          ON p.uretim_id = u.id
        JOIN sevkiyat_kalemleri sk
          ON sk.paketleme_id = p.id
        JOIN sevkiyat s
          ON s.id = sk.sevkiyat_id
        LEFT JOIN musteriler m
          ON m.id = s.musteri_id
        WHERE uhl.depo_kabul_id = ?
        GROUP BY
            s.id,
            s.sevkiyat_tarihi,
            m.musteri_adi,
            s.musteri,
            s.arac_plaka,
            s.belge_no,
            s.soguk_zincir,
            p.ambalaj_gram,
            p.koli_ici_adet,
            u.urun_lot_no
        ORDER BY
            s.id,
            u.urun_lot_no,
            p.ambalaj_gram
    """, (
        depo_kabul_id,
    )).fetchall()

    dosya = pdf_yolu(
        "GERI_CAGIRMA",
        hammadde_lotu["tedarikci_lot_no"]
    )

    doc = pdf_dokuman_olustur(
        dosya
    )

    story = []

    pdf_rapor_basligi(
        story,
        "TERS İZLENEBİLİRLİK VE GERİ ÇAĞIRMA RAPORU",
        hammadde_lotu["tedarikci_lot_no"]
    )

    pdf_bolum_basligi(
        story,
        "1. HAMMADDE / TEDARİKÇİ LOTU"
    )

    pdf_bilgi_satiri(
        story,
        "Hammadde",
        hammadde_lotu["hammadde"]
    )

    pdf_bilgi_satiri(
        story,
        "Tedarikçi",
        hammadde_lotu["tedarikci"] or "-"
    )

    pdf_bilgi_satiri(
        story,
        "Tedarikçi Lot No",
        hammadde_lotu["tedarikci_lot_no"]
    )

    pdf_bilgi_satiri(
        story,
        "Kabul Tarihi",
        hammadde_lotu["kabul_tarihi"]
    )

    pdf_bilgi_satiri(
        story,
        "Üretim Tarihi",
        hammadde_lotu["uretim_tarihi"] or "-"
    )

    pdf_bilgi_satiri(
        story,
        "SKT / TETT",
        hammadde_lotu["skt_tett"] or "-"
    )

    pdf_bilgi_satiri(
        story,
        "Kabul Miktarı",
        f'{hammadde_lotu["miktar_kg"]:.3f} kg'
    )

    pdf_bilgi_satiri(
        story,
        "Kabul Durumu",
        hammadde_lotu["kabul_durumu"]
    )

    if hammadde_lotu["aciklama"]:
        pdf_bilgi_satiri(
            story,
            "Açıklama",
            hammadde_lotu["aciklama"]
        )

    pdf_bolum_basligi(
        story,
        "2. ETKİLENEN ÜRETİM LOTLARI"
    )

    if uretimler:
        satirlar = []

        for row in uretimler:
            satirlar.append(
                [
                    row["uretim_tarihi"],
                    row["urun_lot_no"],
                    row["parti_sayisi"],
                    f'{row["kullanilan_miktar_kg"]:.3f}',
                    f'{row["net_uretim_kg"]:.3f}',
                ]
            )

        pdf_tablo(
            story,
            [
                "Üretim Tarihi",
                "Ürün Lotu",
                "Parti",
                "Kullanılan Kg",
                "Net Üretim Kg",
            ],
            satirlar,
            [
                90,
                110,
                55,
                90,
                95,
            ]
        )

    else:
        story.append(
            Paragraph(
                (
                    "Bu hammadde lotunun kullanıldığı "
                    "üretim kaydı bulunmamaktadır."
                ),
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "3. ETKİLENEN PAKETLEME KAYITLARI"
    )

    if paketlemeler:
        satirlar = []

        for row in paketlemeler:
            koli_ici = row["koli_ici_adet"] or 0

            if koli_ici > 0:
                tam_koli = (
                    row["paket_adedi"]
                    // koli_ici
                )

                acik_paket = (
                    row["paket_adedi"]
                    % koli_ici
                )
            else:
                tam_koli = 0
                acik_paket = row["paket_adedi"]

            if row["ambalaj_gram"] == 500:
                ambalaj = "500 g"
            elif row["ambalaj_gram"] == 2500:
                ambalaj = "2.5 kg"
            else:
                ambalaj = (
                    f'{row["ambalaj_gram"]} g'
                )

            satirlar.append(
                [
                    row["urun_lot_no"],
                    row["paketleme_tarihi"],
                    ambalaj,
                    row["paket_adedi"],
                    tam_koli,
                    acik_paket,
                    f'{row["paketlenen_kg"]:.3f}',
                ]
            )

        pdf_tablo(
            story,
            [
                "Ürün Lotu",
                "Tarih",
                "Ambalaj",
                "Paket",
                "Koli",
                "Açık",
                "Kg",
            ],
            satirlar,
            [
                90,
                70,
                60,
                50,
                45,
                45,
                65,
            ]
        )

    else:
        story.append(
            Paragraph(
                (
                    "Etkilenen üretim lotlarına bağlı "
                    "paketleme kaydı bulunmamaktadır."
                ),
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "4. ETKİLENEN MÜŞTERİ VE SEVKİYATLAR"
    )

    if sevkiyatlar:
        satirlar = []

        for row in sevkiyatlar:
            soguk = (
                "EVET"
                if row["soguk_zincir"]
                else "HAYIR"
            )

            satirlar.append(
                [
                    row["sevkiyat_tarihi"],
                    row["urun_lot_no"],
                    row["musteri"],
                    row["toplam_paket"],
                    f'{row["toplam_kg"]:.3f}',
                    row["arac_plaka"] or "-",
                    row["belge_no"] or "-",
                    soguk,
                ]
            )

        pdf_tablo(
            story,
            [
                "Tarih",
                "Ürün Lotu",
                "Müşteri",
                "Paket",
                "Kg",
                "Plaka",
                "Belge",
                "Soğuk",
            ],
            satirlar,
            [
                55,
                75,
                75,
                40,
                45,
                55,
                55,
                40,
            ]
        )

    else:
        story.append(
            Paragraph(
                (
                    "Etkilenen ürün lotlarına bağlı "
                    "sevkiyat kaydı bulunmamaktadır."
                ),
                styles["govde"]
            )
        )

    pdf_bolum_basligi(
        story,
        "5. GERİ ÇAĞIRMA ETKİ ANALİZİ"
    )

    urun_lotlari = {
        row["urun_lot_no"]
        for row in uretimler
    }

    musteriler = {
        row["musteri"]
        for row in sevkiyatlar
    }

    sevkiyat_idleri = {
        row["sevkiyat_id"]
        for row in sevkiyatlar
    }

    toplam_kullanilan = sum(
        (
            row["kullanilan_miktar_kg"]
            or 0
        )
        for row in uretimler
    )

    toplam_sevk_kg = sum(
        (
            row["toplam_kg"]
            or 0
        )
        for row in sevkiyatlar
    )

    pdf_bilgi_satiri(
        story,
        "Kaynak Hammadde Lotu",
        hammadde_lotu["tedarikci_lot_no"]
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Ürün Lotu Sayısı",
        len(urun_lotlari)
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Paketleme Kaydı",
        len(paketlemeler)
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Sevkiyat Sayısı",
        len(sevkiyat_idleri)
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Müşteri / Sevk Noktası",
        len(musteriler)
    )

    pdf_bilgi_satiri(
        story,
        "Hammadde Lotundan Kullanılan",
        f"{toplam_kullanilan:.3f} kg"
    )

    pdf_bilgi_satiri(
        story,
        "Etkilenen Lotlardan Sevk Edilen",
        f"{toplam_sevk_kg:.3f} kg"
    )

    sonuc = (
        "Bu hammadde lotu üretimde kullanılmıştır. "
        "Yukarıdaki ürün lotları ve bunlara bağlı "
        "sevkiyat noktaları geri çağırma kapsamı "
        "değerlendirmesine alınmalıdır."
        if uretimler
        else
        "Bu hammadde lotuna bağlı üretim tüketimi "
        "bulunmadığından mevcut sistem kayıtlarına göre "
        "etkilenen ürün lotu veya müşteri yoktur."
    )

    pdf_bilgi_satiri(
        story,
        "Sistem Değerlendirmesi",
        sonuc
    )

    story.append(
        Spacer(
            1,
            25
        )
    )

    pdf_tablo(
        story,
        [
            "Hazırlayan",
            "Kontrol Eden",
            "Tarih / İmza",
        ],
        [
            [
                "Fatih Ayaz",
                "",
                "",
            ]
        ],
        [
            170,
            170,
            150,
        ]
    )

    pdf_build(
        doc,
        story
    )

    return dosya

def temizlik_pdf_olustur(
    conn,
    target_date,
):
    rows = get_cleaning_report_dataset(
        conn,
        target_date,
    )

    if not rows:
        raise ValueError(
            "Seçilen tarih için temizlik rapor kaydı bulunamadı."
        )

    referans = target_date

    dosya = pdf_yolu(
        "TEMIZLIK",
        referans
    )

    doc = pdf_dokuman_olustur(
        dosya
    )

    story = []

    pdf_rapor_basligi(
        story,
        "TEMİZLİK TAKİP RAPORU",
        referans
    )

    durum_sayilari = Counter(
        row["durum"]
        for row in rows
    )

    pdf_bolum_basligi(
        story,
        "Rapor Özeti"
    )

    pdf_bilgi_satiri(
        story,
        "Rapor Tarihi",
        target_date
    )

    pdf_bilgi_satiri(
        story,
        "Toplam Planlı Görev",
        len(rows)
    )

    for durum in (
        "GECIKEN",
        "BEKLEYEN",
        "GELECEK",
        "TAMAMLANDI",
    ):
        pdf_bilgi_satiri(
            story,
            durum,
            durum_sayilari.get(
                durum,
                0,
            )
        )

    pdf_bolum_basligi(
        story,
        "Planlı Temizlik Görevleri"
    )

    satirlar = [
        [
            row["planlanan_tarih"],
            row["kat_adi"],
            row["alan_adi"],
            row["ekipman_adi"] or "-",
            row["gorev_adi"],
            row["periyot"],
            row["durum"],
            row["urun_lot_no"] or "-",
        ]
        for row in rows
    ]

    pdf_tablo(
        story,
        [
            "Planlanan",
            "Kat",
            "Alan",
            "Ekipman",
            "Görev",
            "Periyot",
            "Durum",
            "Ürün Lot",
        ],
        satirlar,
        [
            58,
            50,
            68,
            68,
            92,
            58,
            58,
            62,
        ]
    )

    pdf_bolum_basligi(
        story,
        "Gerçekleşme ve Kontrol Kayıtları"
    )

    gerceklesme_satirlari = [
        [
            row["planlanan_tarih"],
            row["gorev_adi"],
            row["tamamlanma_tarihi"] or "-",
            row["uygulayan"] or "-",
            row["kontrol_eden"] or "-",
            row["gerceklesme_durumu"] or "-",
            row["aciklama"] or "-",
        ]
        for row in rows
        if row["gerceklesme_id"] is not None
    ]

    if gerceklesme_satirlari:
        pdf_tablo(
            story,
            [
                "Planlanan",
                "Görev",
                "Tamamlanma",
                "Uygulayan",
                "Kontrol",
                "Durum",
                "Açıklama",
            ],
            gerceklesme_satirlari,
            [
                60,
                100,
                70,
                75,
                75,
                60,
                75,
            ]
        )
    else:
        pdf_bilgi_satiri(
            story,
            "Gerçekleşme Kaydı",
            "Seçilen rapor kapsamındaki görevler için tamamlanma kaydı yok."
        )

    pdf_build(
        doc,
        story
    )

    return dosya
