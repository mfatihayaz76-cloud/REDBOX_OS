from contextlib import contextmanager
from datetime import datetime
import uuid

from database.audit_engine import denetim_kaydi_ekle


PROGRAM_TYPES = {
    "ALERJEN",
    "KALIBRASYON",
    "BAKIM_ARIZA",
    "ZARARLI_MUCADELESI",
    "EGITIM_YETKINLIK",
    "TACCP",
    "VACCP",
}
PROGRAM_STATUSES = {"TASLAK", "AKTIF", "ASKIDA", "ARSIV"}
ACTION_STATUSES = {
    "ACIK",
    "DEVAM_EDIYOR",
    "DOGRULAMADA",
    "KAPALI",
    "IPTAL",
}
EQUIPMENT_TYPES = {"OLCUM", "URETIM", "DEPOLAMA", "DIGER"}
EQUIPMENT_STATUSES = {
    "AKTIF",
    "BAKIMDA",
    "ARIZALI",
    "KULLANIM_DISI",
}
RISK_TYPES = {"TACCP", "VACCP"}
RISK_STATUSES = {"ACIK", "KONTROL_ALTINDA", "KAPALI"}


def _now():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _required(value, field_name):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} boş olamaz.")
    return text


def _optional(value):
    text = str(value or "").strip()
    return text or None


def _positive_id(value, field_name):
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} geçerli bir kimlik olmalıdır."
        ) from exc
    if result <= 0:
        raise ValueError(
            f"{field_name} pozitif olmalıdır."
        )
    return result


def _optional_id(value, field_name):
    if value in (None, ""):
        return None
    return _positive_id(value, field_name)


def _choice(value, allowed, field_name):
    code = _required(value, field_name).upper()
    if code not in allowed:
        raise ValueError(f"Geçersiz {field_name}: {code}")
    return code


def _flag(value):
    return 1 if bool(value) else 0


def _number(value, field_name, minimum=None, maximum=None):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} sayısal olmalıdır."
        ) from exc
    if minimum is not None and result < minimum:
        raise ValueError(
            f"{field_name} en az {minimum} olmalıdır."
        )
    if maximum is not None and result > maximum:
        raise ValueError(
            f"{field_name} en fazla {maximum} olmalıdır."
        )
    return result


@contextmanager
def _atomic(conn):
    savepoint = f"prp_{uuid.uuid4().hex}"
    conn.execute(f"SAVEPOINT {savepoint}")
    try:
        yield
    except Exception:
        conn.execute(f"ROLLBACK TO {savepoint}")
        conn.execute(f"RELEASE {savepoint}")
        raise
    else:
        conn.execute(f"RELEASE {savepoint}")


def _require_row(conn, table, row_id, label):
    row = conn.execute(
        f'SELECT * FROM "{table}" WHERE id = ?',
        (row_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"{label} bulunamadı: {row_id}")
    return row


def _audit(
    conn,
    action,
    record_type,
    record_id,
    description,
    user,
    new_value=None,
    old_value=None,
    session_id=None,
):
    denetim_kaydi_ekle(
        conn,
        modul="PRP",
        islem=action,
        kullanici=user,
        kayit_turu=record_type,
        kayit_id=record_id,
        aciklama=description,
        eski_deger=old_value,
        yeni_deger=new_value,
        oturum_id=session_id,
    )


def prp_programi_olustur(
    conn,
    veri,
    kullanici=None,
    oturum_id=None,
):
    code = _required(veri.get("program_kodu"), "Program kodu")
    program_type = _choice(
        veri.get("program_turu"),
        PROGRAM_TYPES,
        "program türü",
    )
    title = _required(veri.get("baslik"), "Program başlığı")
    status = _choice(
        veri.get("durum", "TASLAK"),
        PROGRAM_STATUSES,
        "program durumu",
    )
    scope = _optional(veri.get("kapsam"))
    responsible_id = _optional_id(
        veri.get("sorumlu_personel_id"),
        "Sorumlu personel",
    )
    start_date = _optional(veri.get("baslangic_tarihi"))
    review_date = _optional(veri.get("gozden_gecirme_tarihi"))
    now = _now()

    with _atomic(conn):
        cursor = conn.execute(
            """
            INSERT INTO prp_programlari (
                program_kodu,
                program_turu,
                baslik,
                kapsam,
                sorumlu_personel_id,
                baslangic_tarihi,
                gozden_gecirme_tarihi,
                durum,
                olusturma_zamani,
                guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                program_type,
                title,
                scope,
                responsible_id,
                start_date,
                review_date,
                status,
                now,
                now,
            ),
        )
        program_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_PROGRAMI",
            program_id,
            "Ön gereksinim programı oluşturuldu.",
            kullanici,
            new_value={
                "program_kodu": code,
                "program_turu": program_type,
                "baslik": title,
                "durum": status,
            },
            session_id=oturum_id,
        )

    return program_id


def prp_kaydi_ekle(
    conn,
    program_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    program_id = _positive_id(program_id, "Program")
    record_type = _required(veri.get("kayit_turu"), "Kayıt türü")
    record_date = _required(
        veri.get("kayit_tarihi"),
        "Kayıt tarihi",
    )
    title = _required(veri.get("baslik"), "Kayıt başlığı")
    responsible_id = _optional_id(
        veri.get("sorumlu_personel_id"),
        "Sorumlu personel",
    )

    with _atomic(conn):
        _require_row(
            conn,
            "prp_programlari",
            program_id,
            "PRP programı",
        )
        cursor = conn.execute(
            """
            INSERT INTO prp_kayitlari (
                program_id,
                kayit_turu,
                kayit_tarihi,
                baslik,
                aciklama,
                sonuc,
                uygunsuzluk_var,
                sorumlu_personel_id,
                kanit_referansi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                program_id,
                record_type,
                record_date,
                title,
                _optional(veri.get("aciklama")),
                _optional(veri.get("sonuc")),
                _flag(veri.get("uygunsuzluk_var", False)),
                responsible_id,
                _optional(veri.get("kanit_referansi")),
            ),
        )
        record_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_KAYDI",
            record_id,
            "Ön gereksinim program kaydı oluşturuldu.",
            kullanici,
            new_value={
                "program_id": program_id,
                "kayit_turu": record_type,
                "baslik": title,
            },
            session_id=oturum_id,
        )

    return record_id


def prp_aksiyonu_ekle(
    conn,
    kayit_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    record_id = _positive_id(kayit_id, "PRP kaydı")
    action = _required(veri.get("aksiyon"), "Aksiyon")
    responsible_id = _optional_id(
        veri.get("sorumlu_personel_id"),
        "Sorumlu personel",
    )
    status = _choice(
        veri.get("durum", "ACIK"),
        ACTION_STATUSES,
        "aksiyon durumu",
    )

    with _atomic(conn):
        _require_row(
            conn,
            "prp_kayitlari",
            record_id,
            "PRP kaydı",
        )
        cursor = conn.execute(
            """
            INSERT INTO prp_aksiyonlari (
                kayit_id,
                aksiyon,
                sorumlu_personel_id,
                hedef_tarih,
                tamamlanma_tarihi,
                durum,
                etkinlik_sonucu
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                action,
                responsible_id,
                _optional(veri.get("hedef_tarih")),
                _optional(veri.get("tamamlanma_tarihi")),
                status,
                _optional(veri.get("etkinlik_sonucu")),
            ),
        )
        action_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_AKSIYONU",
            action_id,
            "PRP düzeltici aksiyonu oluşturuldu.",
            kullanici,
            new_value={
                "kayit_id": record_id,
                "aksiyon": action,
                "durum": status,
            },
            session_id=oturum_id,
        )

    return action_id



def _require_program_type(
    conn,
    program_id,
    allowed_types,
):
    row = _require_row(
        conn,
        "prp_programlari",
        program_id,
        "PRP programı",
    )
    program_type = row["program_turu"]
    if program_type not in allowed_types:
        expected = ", ".join(sorted(allowed_types))
        raise ValueError(
            f"Bu işlem yalnızca {expected} programında yapılabilir."
        )
    return row


def alerjen_matrisi_kaydet(
    conn,
    program_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    program_id = _positive_id(program_id, "Program")
    product_id = _optional_id(veri.get("urun_id"), "Ürün")
    allergen_code = _required(
        veri.get("alerjen_kodu"),
        "Alerjen kodu",
    ).upper()

    with _atomic(conn):
        _require_program_type(conn, program_id, {"ALERJEN"})
        cursor = conn.execute(
            """
            INSERT INTO prp_alerjen_matrisi (
                program_id,
                urun_id,
                alerjen_kodu,
                icerir,
                capraz_bulasma_riski,
                kontrol_onlemi,
                etiket_beyani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                program_id,
                product_id,
                allergen_code,
                _flag(veri.get("icerir", False)),
                _flag(veri.get("capraz_bulasma_riski", False)),
                _optional(veri.get("kontrol_onlemi")),
                _optional(veri.get("etiket_beyani")),
            ),
        )
        matrix_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_ALERJEN_MATRISI",
            matrix_id,
            "Alerjen matrisi kaydı oluşturuldu.",
            kullanici,
            new_value={
                "program_id": program_id,
                "urun_id": product_id,
                "alerjen_kodu": allergen_code,
            },
            session_id=oturum_id,
        )

    return matrix_id


def ekipman_kaydet(
    conn,
    program_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    program_id = _positive_id(program_id, "Program")
    equipment_code = _required(
        veri.get("ekipman_kodu"),
        "Ekipman kodu",
    )
    equipment_name = _required(
        veri.get("ekipman_adi"),
        "Ekipman adı",
    )
    equipment_type = _choice(
        veri.get("ekipman_turu"),
        EQUIPMENT_TYPES,
        "ekipman türü",
    )
    status = _choice(
        veri.get("durum", "AKTIF"),
        EQUIPMENT_STATUSES,
        "ekipman durumu",
    )

    with _atomic(conn):
        _require_program_type(
            conn,
            program_id,
            {"KALIBRASYON", "BAKIM_ARIZA"},
        )
        cursor = conn.execute(
            """
            INSERT INTO prp_ekipmanlari (
                program_id,
                ekipman_kodu,
                ekipman_adi,
                ekipman_turu,
                konum,
                son_islem_tarihi,
                sonraki_islem_tarihi,
                durum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                program_id,
                equipment_code,
                equipment_name,
                equipment_type,
                _optional(veri.get("konum")),
                _optional(veri.get("son_islem_tarihi")),
                _optional(veri.get("sonraki_islem_tarihi")),
                status,
            ),
        )
        equipment_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_EKIPMANI",
            equipment_id,
            "PRP ekipman kaydı oluşturuldu.",
            kullanici,
            new_value={
                "program_id": program_id,
                "ekipman_kodu": equipment_code,
                "ekipman_turu": equipment_type,
                "durum": status,
            },
            session_id=oturum_id,
        )

    return equipment_id


def egitim_katilimi_kaydet(
    conn,
    program_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    program_id = _positive_id(program_id, "Program")
    personnel_id = _positive_id(
        veri.get("personel_id"),
        "Personel",
    )
    training_code = _required(
        veri.get("egitim_kodu"),
        "Eğitim kodu",
    )
    training_name = _required(
        veri.get("egitim_adi"),
        "Eğitim adı",
    )
    training_date = _required(
        veri.get("egitim_tarihi"),
        "Eğitim tarihi",
    )
    score = veri.get("puan")
    if score in (None, ""):
        score = None
    else:
        score = _number(score, "Puan", 0, 100)

    with _atomic(conn):
        _require_program_type(
            conn,
            program_id,
            {"EGITIM_YETKINLIK"},
        )
        cursor = conn.execute(
            """
            INSERT INTO prp_egitim_katilimlari (
                program_id,
                personel_id,
                egitim_kodu,
                egitim_adi,
                egitim_tarihi,
                gecerlilik_tarihi,
                puan,
                yetkin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                program_id,
                personnel_id,
                training_code,
                training_name,
                training_date,
                _optional(veri.get("gecerlilik_tarihi")),
                score,
                _flag(veri.get("yetkin", False)),
            ),
        )
        participation_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_EGITIM_KATILIMI",
            participation_id,
            "Eğitim ve yetkinlik kaydı oluşturuldu.",
            kullanici,
            new_value={
                "program_id": program_id,
                "personel_id": personnel_id,
                "egitim_kodu": training_code,
                "yetkin": bool(veri.get("yetkin", False)),
            },
            session_id=oturum_id,
        )

    return participation_id


def risk_degerlendir(
    conn,
    program_id,
    veri,
    kullanici=None,
    oturum_id=None,
):
    program_id = _positive_id(program_id, "Program")
    risk_type = _choice(
        veri.get("risk_turu"),
        RISK_TYPES,
        "risk türü",
    )
    asset = _required(
        veri.get("varlik_veya_surec"),
        "Varlık veya süreç",
    )
    threat = _required(
        veri.get("tehdit_veya_zafiyet"),
        "Tehdit veya zafiyet",
    )
    probability = int(
        _number(veri.get("olasilik"), "Olasılık", 1, 5)
    )
    impact = int(
        _number(veri.get("etki"), "Etki", 1, 5)
    )
    risk_score = probability * impact
    residual = veri.get("kalan_risk")
    if residual in (None, ""):
        residual = None
    else:
        residual = int(
            _number(residual, "Kalan risk", 1, 25)
        )
    status = _choice(
        veri.get("durum", "ACIK"),
        RISK_STATUSES,
        "risk durumu",
    )

    with _atomic(conn):
        _require_program_type(conn, program_id, {risk_type})
        cursor = conn.execute(
            """
            INSERT INTO prp_risk_degerlendirmeleri (
                program_id,
                risk_turu,
                varlik_veya_surec,
                tehdit_veya_zafiyet,
                olasilik,
                etki,
                risk_puani,
                kontrol_onlemleri,
                kalan_risk,
                durum,
                gozden_gecirme_tarihi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                program_id,
                risk_type,
                asset,
                threat,
                probability,
                impact,
                risk_score,
                _optional(veri.get("kontrol_onlemleri")),
                residual,
                status,
                _optional(veri.get("gozden_gecirme_tarihi")),
            ),
        )
        risk_id = cursor.lastrowid
        _audit(
            conn,
            "OLUSTURMA",
            "PRP_RISK_DEGERLENDIRMESI",
            risk_id,
            "TACCP/VACCP risk değerlendirmesi oluşturuldu.",
            kullanici,
            new_value={
                "program_id": program_id,
                "risk_turu": risk_type,
                "olasilik": probability,
                "etki": impact,
                "risk_puani": risk_score,
            },
            session_id=oturum_id,
        )

    return risk_id


def prp_programlarini_getir(
    conn,
    program_turu=None,
    durum=None,
    arama=None,
    limit=500,
):
    where = []
    params = []

    if program_turu:
        where.append("program_turu = ?")
        params.append(
            _choice(
                program_turu,
                PROGRAM_TYPES,
                "program türü",
            )
        )
    if durum:
        where.append("durum = ?")
        params.append(
            _choice(durum, PROGRAM_STATUSES, "program durumu")
        )
    if arama:
        search = f"%{str(arama).strip()}%"
        where.append(
            """
            (
                program_kodu LIKE ?
                OR baslik LIKE ?
                OR COALESCE(kapsam, '') LIKE ?
            )
            """
        )
        params.extend((search, search, search))

    limit = max(1, min(int(limit), 5000))
    where_sql = (
        " WHERE " + " AND ".join(where)
        if where
        else ""
    )
    return conn.execute(
        """
        SELECT
            p.*,
            pe.ad_soyad AS sorumlu_adi,
            (
                SELECT COUNT(*)
                FROM prp_kayitlari k
                WHERE k.program_id = p.id
            ) AS kayit_sayisi
        FROM prp_programlari p
        LEFT JOIN personeller pe
            ON pe.id = p.sorumlu_personel_id
        """
        + where_sql
        + " ORDER BY p.id DESC LIMIT ?",
        (*params, limit),
    ).fetchall()


def prp_ozeti(conn):
    result = {
        "toplam_program": 0,
        "aktif_program": 0,
        "acik_aksiyon": 0,
        "yuksek_risk": 0,
    }
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS toplam,
            SUM(CASE WHEN durum = 'AKTIF' THEN 1 ELSE 0 END)
                AS aktif
        FROM prp_programlari
        """
    ).fetchone()
    result["toplam_program"] = int(row[0] or 0)
    result["aktif_program"] = int(row[1] or 0)
    result["acik_aksiyon"] = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM prp_aksiyonlari
            WHERE durum NOT IN ('KAPALI', 'IPTAL')
            """
        ).fetchone()[0]
    )
    result["yuksek_risk"] = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM prp_risk_degerlendirmeleri
            WHERE risk_puani >= 15
              AND durum != 'KAPALI'
            """
        ).fetchone()[0]
    )
    return result
