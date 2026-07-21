from contextlib import contextmanager
from datetime import datetime
import uuid

from database.audit_engine import denetim_kaydi_ekle


def _required(value, field):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} boş olamaz.")
    return text


def _optional(value):
    text = str(value or "").strip()
    return text or None


def _optional_id(value, field):
    if value in (None, ""):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} geçersiz.") from exc
    if result <= 0:
        raise ValueError(f"{field} pozitif olmalıdır.")
    return result


def _number(value, field, minimum=0, maximum=None):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} sayısal olmalıdır.") from exc
    if result < minimum:
        raise ValueError(f"{field} en az {minimum} olmalıdır.")
    if maximum is not None and result > maximum:
        raise ValueError(f"{field} en fazla {maximum} olmalıdır.")
    return result


def _choice(value, allowed, field):
    code = _required(value, field).upper()
    if code not in allowed:
        raise ValueError(f"Geçersiz {field}: {code}")
    return code


@contextmanager
def _atomic(conn):
    name = f"gfs3_{uuid.uuid4().hex}"
    conn.execute(f"SAVEPOINT {name}")
    try:
        yield
    except Exception:
        conn.execute(f"ROLLBACK TO {name}")
        conn.execute(f"RELEASE {name}")
        raise
    else:
        conn.execute(f"RELEASE {name}")


def _audit(
    conn,
    record_type,
    record_id,
    description,
    user,
    value,
    session_id=None,
):
    denetim_kaydi_ekle(
        conn,
        modul="GFS_DENETIM",
        islem="OLUSTURMA",
        kullanici=user,
        kayit_turu=record_type,
        kayit_id=record_id,
        aciklama=description,
        yeni_deger=value,
        oturum_id=session_id,
    )


def ic_denetim_olustur(
    conn, veri, kullanici=None, oturum_id=None
):
    code = _required(veri.get("denetim_kodu"), "Denetim kodu")
    date = _required(veri.get("denetim_tarihi"), "Denetim tarihi")
    scope = _required(veri.get("kapsam"), "Denetim kapsamı")
    auditor = _optional_id(
        veri.get("bas_denetci_personel_id"),
        "Baş denetçi",
    )
    status = _choice(
        veri.get("durum", "PLANLANDI"),
        {"PLANLANDI", "DEVAM_EDIYOR", "RAPORLANDI", "KAPALI", "IPTAL"},
        "denetim durumu",
    )
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_ic_denetimleri (
                denetim_kodu, denetim_tarihi, kapsam,
                bas_denetci_personel_id, bulgu_sayisi,
                kritik_bulgu_sayisi, sonuc, durum, kapanis_tarihi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code, date, scope, auditor,
                int(_number(veri.get("bulgu_sayisi", 0), "Bulgu sayısı")),
                int(_number(
                    veri.get("kritik_bulgu_sayisi", 0),
                    "Kritik bulgu sayısı",
                )),
                _optional(veri.get("sonuc")),
                status,
                _optional(veri.get("kapanis_tarihi")),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "IC_DENETIM", row_id,
            "İç denetim kaydı oluşturuldu.",
            kullanici, {"denetim_kodu": code, "durum": status},
            oturum_id,
        )
    return row_id


def musteri_sikayeti_kaydet(
    conn, veri, kullanici=None, oturum_id=None
):
    code = _required(veri.get("sikayet_kodu"), "Şikâyet kodu")
    date = _required(veri.get("bildirim_tarihi"), "Bildirim tarihi")
    category = _required(veri.get("kategori"), "Kategori")
    description = _required(veri.get("aciklama"), "Açıklama")
    severity = _choice(
        veri.get("onem_derecesi", "ORTA"),
        {"DUSUK", "ORTA", "YUKSEK", "KRITIK"},
        "önem derecesi",
    )
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_musteri_sikayetleri (
                sikayet_kodu, musteri_id, bildirim_tarihi,
                urun_id, lot_kodu, kategori, aciklama,
                onem_derecesi, kok_neden, aksiyon,
                yanit_tarihi, durum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                _optional_id(veri.get("musteri_id"), "Müşteri"),
                date,
                _optional_id(veri.get("urun_id"), "Ürün"),
                _optional(veri.get("lot_kodu")),
                category,
                description,
                severity,
                _optional(veri.get("kok_neden")),
                _optional(veri.get("aksiyon")),
                _optional(veri.get("yanit_tarihi")),
                _choice(
                    veri.get("durum", "ACIK"),
                    {"ACIK", "INCELEMEDE", "AKSIYONDA", "KAPALI"},
                    "şikâyet durumu",
                ),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "MUSTERI_SIKAYETI", row_id,
            "Müşteri şikâyeti kaydedildi.",
            kullanici,
            {"sikayet_kodu": code, "onem_derecesi": severity},
            oturum_id,
        )
    return row_id


def laboratuvar_numunesi_kaydet(
    conn, veri, kullanici=None, oturum_id=None
):
    code = _required(veri.get("numune_kodu"), "Numune kodu")
    date = _required(veri.get("numune_tarihi"), "Numune tarihi")
    sample_type = _required(veri.get("numune_turu"), "Numune türü")
    analyses = _required(veri.get("analizler"), "Analizler")
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_laboratuvar_numuneleri (
                numune_kodu, numune_tarihi, numune_turu,
                urun_id, lot_kodu, laboratuvar, analizler,
                sonuc, uygun, rapor_referansi, durum, sonuc_tarihi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code, date, sample_type,
                _optional_id(veri.get("urun_id"), "Ürün"),
                _optional(veri.get("lot_kodu")),
                _optional(veri.get("laboratuvar")),
                analyses,
                _optional(veri.get("sonuc")),
                None if veri.get("uygun") is None
                else int(bool(veri.get("uygun"))),
                _optional(veri.get("rapor_referansi")),
                _choice(
                    veri.get("durum", "BEKLIYOR"),
                    {"BEKLIYOR", "ANALIZDE", "SONUCLANDI", "IPTAL"},
                    "numune durumu",
                ),
                _optional(veri.get("sonuc_tarihi")),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "LABORATUVAR_NUMUNESI", row_id,
            "Laboratuvar numunesi kaydedildi.",
            kullanici, {"numune_kodu": code, "numune_turu": sample_type},
            oturum_id,
        )
    return row_id


def urun_durumu_kaydet(
    conn, veri, kullanici=None, oturum_id=None
):
    lot = _required(veri.get("lot_kodu"), "Lot kodu")
    status = _choice(
        veri.get("durum"),
        {"KARANTINA", "BLOKE", "SERBEST", "IADE", "IMHA"},
        "ürün durumu",
    )
    date = _required(veri.get("karar_tarihi"), "Karar tarihi")
    amount = veri.get("miktar_kg")
    amount = None if amount in (None, "") else _number(
        amount, "Miktar", 0
    )
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_urun_durum_kayitlari (
                urun_id, lot_kodu, durum, karar_tarihi,
                neden, miktar_kg, karar_veren_personel_id,
                onceki_durum, kanit_referansi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _optional_id(veri.get("urun_id"), "Ürün"),
                lot, status, date,
                _optional(veri.get("neden")),
                amount,
                _optional_id(
                    veri.get("karar_veren_personel_id"),
                    "Karar veren personel",
                ),
                _optional(veri.get("onceki_durum")),
                _optional(veri.get("kanit_referansi")),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "URUN_DURUM_KARARI", row_id,
            "Ürün karantina/bloke/serbest bırakma kararı kaydedildi.",
            kullanici, {"lot_kodu": lot, "durum": status},
            oturum_id,
        )
    return row_id


def yonetim_gozden_gecirme_kaydet(
    conn, veri, kullanici=None, oturum_id=None
):
    code = _required(veri.get("toplanti_kodu"), "Toplantı kodu")
    date = _required(veri.get("toplanti_tarihi"), "Toplantı tarihi")
    period = _required(veri.get("donem"), "Dönem")
    attendees = _required(veri.get("katilimcilar"), "Katılımcılar")
    agenda = _required(veri.get("gundem"), "Gündem")
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_yonetim_gozden_gecirmeleri (
                toplantı_kodu, toplantı_tarihi, donem,
                katilimcilar, gundem, girdiler, kararlar,
                aksiyonlar, sonraki_toplanti_tarihi, durum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code, date, period, attendees, agenda,
                _optional(veri.get("girdiler")),
                _optional(veri.get("kararlar")),
                _optional(veri.get("aksiyonlar")),
                _optional(veri.get("sonraki_toplanti_tarihi")),
                _choice(
                    veri.get("durum", "PLANLANDI"),
                    {"PLANLANDI", "TAMAMLANDI", "AKSIYON_TAKIBI", "KAPALI"},
                    "toplantı durumu",
                ),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "YONETIM_GOZDEN_GECIRME", row_id,
            "Yönetimin gözden geçirmesi kaydedildi.",
            kullanici, {"toplanti_kodu": code, "donem": period},
            oturum_id,
        )
    return row_id


def tedarikci_riski_degerlendir(
    conn, veri, kullanici=None, oturum_id=None
):
    supplier_id = _optional_id(
        veri.get("tedarikci_id"), "Tedarikçi"
    )
    if supplier_id is None:
        raise ValueError("Tedarikçi boş olamaz.")
    quality = _number(veri.get("kalite_puani"), "Kalite puanı", 0, 100)
    delivery = _number(
        veri.get("teslimat_puani"), "Teslimat puanı", 0, 100
    )
    safety = _number(
        veri.get("gida_guvenligi_puani"),
        "Gıda güvenliği puanı", 0, 100
    )
    total = round(quality * 0.40 + delivery * 0.20 + safety * 0.40, 2)
    level = (
        "DUSUK" if total >= 80
        else "ORTA" if total >= 60
        else "YUKSEK" if total >= 40
        else "KRITIK"
    )
    approval = (
        "ONAYLI" if level == "DUSUK"
        else "KOSULLU" if level == "ORTA"
        else "ASKIDA" if level == "YUKSEK"
        else "RED"
    )
    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_tedarikci_riskleri (
                tedarikci_id, degerlendirme_tarihi,
                kalite_puani, teslimat_puani,
                gida_guvenligi_puani, toplam_risk_puani,
                risk_seviyesi, onay_durumu,
                aksiyon_plani, sonraki_degerlendirme_tarihi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                supplier_id,
                _required(
                    veri.get("degerlendirme_tarihi"),
                    "Değerlendirme tarihi",
                ),
                quality, delivery, safety, total, level, approval,
                _optional(veri.get("aksiyon_plani")),
                _optional(veri.get("sonraki_degerlendirme_tarihi")),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "TEDARIKCI_RISKI", row_id,
            "Tedarikçi risk değerlendirmesi oluşturuldu.",
            kullanici,
            {
                "tedarikci_id": supplier_id,
                "toplam_risk_puani": total,
                "risk_seviyesi": level,
            },
            oturum_id,
        )
    return row_id


def mock_recall_kaydet(
    conn, veri, kullanici=None, oturum_id=None
):
    code = _required(veri.get("test_kodu"), "Test kodu")
    start_text = _required(
        veri.get("baslangic_zamani"), "Başlangıç zamanı"
    )
    end_text = _required(veri.get("bitis_zamani"), "Bitiş zamanı")
    try:
        start = datetime.strptime(start_text, "%d.%m.%Y %H:%M:%S")
        end = datetime.strptime(end_text, "%d.%m.%Y %H:%M:%S")
    except ValueError as exc:
        raise ValueError(
            "Mock recall zamanı GG.AA.YYYY SS:DD:SS olmalıdır."
        ) from exc
    duration = (end - start).total_seconds() / 60
    if duration < 0:
        raise ValueError("Bitiş zamanı başlangıçtan önce olamaz.")
    target = _number(veri.get("hedef_miktar"), "Hedef miktar", 0)
    traced = _number(veri.get("izlenen_miktar"), "İzlenen miktar", 0)
    rate = round((traced / target * 100) if target else 0, 2)
    success = int(rate >= 95 and duration <= 120)

    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO gfs_mock_recall_testleri (
                test_kodu, test_tarihi, urun_id, lot_kodu,
                baslangic_zamani, bitis_zamani, sure_dakika,
                hedef_miktar, izlenen_miktar, basari_orani,
                sonuc, basarili, iyilestirme_aksiyonu
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                _required(veri.get("test_tarihi"), "Test tarihi"),
                _optional_id(veri.get("urun_id"), "Ürün"),
                _required(veri.get("lot_kodu"), "Lot kodu"),
                start_text, end_text, duration,
                target, traced, rate,
                _optional(veri.get("sonuc")),
                success,
                _optional(veri.get("iyilestirme_aksiyonu")),
            ),
        )
        row_id = cursor.lastrowid
        _audit(
            conn, "MOCK_RECALL", row_id,
            "Mock recall testi kaydedildi.",
            kullanici,
            {
                "test_kodu": code,
                "sure_dakika": duration,
                "basari_orani": rate,
                "basarili": bool(success),
            },
            oturum_id,
        )
    return row_id


def denetim_zekasi_ozeti(conn):
    queries = {
        "acik_denetim": """
            SELECT COUNT(*) FROM gfs_ic_denetimleri
            WHERE durum NOT IN ('KAPALI', 'IPTAL')
        """,
        "acik_sikayet": """
            SELECT COUNT(*) FROM gfs_musteri_sikayetleri
            WHERE durum != 'KAPALI'
        """,
        "bekleyen_numune": """
            SELECT COUNT(*) FROM gfs_laboratuvar_numuneleri
            WHERE durum IN ('BEKLIYOR', 'ANALIZDE')
        """,
        "bloke_lot": """
            SELECT COUNT(*) FROM gfs_urun_durum_kayitlari
            WHERE durum IN ('KARANTINA', 'BLOKE')
        """,
        "riskli_tedarikci": """
            SELECT COUNT(*) FROM gfs_tedarikci_riskleri
            WHERE risk_seviyesi IN ('YUKSEK', 'KRITIK')
        """,
        "basarisiz_recall": """
            SELECT COUNT(*) FROM gfs_mock_recall_testleri
            WHERE basarili = 0
        """,
    }
    return {
        key: int(conn.execute(sql).fetchone()[0])
        for key, sql in queries.items()
    }
