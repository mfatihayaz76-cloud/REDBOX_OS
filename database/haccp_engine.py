from datetime import datetime

from database.audit_engine import denetim_kaydi_ekle


HAZARD_TYPES = {
    "BIYOLOJIK", "KIMYASAL", "FIZIKSEL", "ALERJEN"
}
CONTROL_CLASSES = {"CCP", "OPRP", "PRP"}
LIMIT_OPERATORS = {"MIN", "MAX", "ARALIK", "ESIT", "NITEL"}
SIGNIFICANT_RISK_SCORE = 12


def _text(value, name, required=True):
    value = str(value or "").strip()
    if required and not value:
        raise ValueError(f"{name} boş olamaz.")
    return value


def _id(value, name):
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} geçersiz.") from exc
    if value < 1:
        raise ValueError(f"{name} geçersiz.")
    return value


def _now(value=None):
    return value or datetime.now().astimezone().isoformat()


def _audit(
    conn, action, record_type, record_id, description,
    user=None, old=None, new=None, session_id=None,
):
    denetim_kaydi_ekle(
        conn,
        modul="HACCP",
        islem=action,
        kullanici=user,
        kayit_turu=record_type,
        kayit_id=record_id,
        aciklama=description,
        eski_deger=old,
        yeni_deger=new,
        oturum_id=session_id,
    )


def haccp_plani_olustur(
    conn, plan, kullanici=None, oturum_id=None,
):
    plan = dict(plan or {})
    code = _text(plan.get("plan_kodu"), "Plan kodu")
    product_id = _id(plan.get("urun_id"), "Ürün")
    name = _text(plan.get("ad"), "Plan adı")
    description = _text(
        plan.get("urun_aciklamasi"), "Ürün açıklaması"
    )
    intended_use = _text(
        plan.get("amaclanan_kullanim"),
        "Amaçlanan kullanım",
    )
    preparer_id = _id(
        plan.get("hazirlayan_personel_id"),
        "Hazırlayan personel",
    )
    now = _now(plan.get("simdi"))

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO haccp_planlari (
                plan_kodu, urun_id, ad, urun_aciklamasi,
                amaclanan_kullanim, hedef_tuketici,
                kullanim_kisitlari, revizyon_no, durum,
                hazirlayan_personel_id,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'TASLAK', ?, ?, ?)
            """,
            (
                code, product_id, name, description,
                intended_use,
                _text(
                    plan.get("hedef_tuketici"),
                    "Hedef tüketici",
                    False,
                ) or None,
                _text(
                    plan.get("kullanim_kisitlari"),
                    "Kullanım kısıtları",
                    False,
                ) or None,
                preparer_id, now, now,
            ),
        )
        plan_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_PLANI", plan_id,
            f"HACCP planı oluşturuldu: {code}",
            kullanici,
            new={"plan_kodu": code, "durum": "TASLAK"},
            session_id=oturum_id,
        )
    return plan_id


def proses_adimi_ekle(
    conn, plan_id, adim, kullanici=None, oturum_id=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    adim = dict(adim or {})
    number = _id(adim.get("adim_no"), "Proses sıra no")
    name = _text(adim.get("ad"), "Proses adımı")
    now = _now(adim.get("simdi"))

    with conn:
        plan = conn.execute(
            "SELECT durum FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if plan is None:
            raise ValueError("HACCP planı bulunamadı.")
        if plan[0] not in {"TASLAK", "INCELEMEDE"}:
            raise ValueError("Onaylı plan değiştirilemez.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_proses_adimlari (
                plan_id, adim_no, ad, aciklama,
                girdiler, ciktilar, sorumlu_rol,
                yerinde_dogrulandi,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                plan_id, number, name,
                _text(adim.get("aciklama"), "Açıklama", False)
                or None,
                _text(adim.get("girdiler"), "Girdiler", False)
                or None,
                _text(adim.get("ciktilar"), "Çıktılar", False)
                or None,
                _text(
                    adim.get("sorumlu_rol"),
                    "Sorumlu rol",
                    False,
                ) or None,
                now, now,
            ),
        )
        step_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_PROSES_ADIMI",
            step_id, f"Proses adımı eklendi: {name}",
            kullanici,
            new={"plan_id": plan_id, "adim_no": number},
            session_id=oturum_id,
        )
    return step_id


def tehlike_olustur(
    conn, tehlike, kullanici=None, oturum_id=None,
):
    tehlike = dict(tehlike or {})
    code = _text(tehlike.get("tehlike_kodu"), "Tehlike kodu")
    name = _text(tehlike.get("ad"), "Tehlike adı")
    hazard_type = _text(
        tehlike.get("tehlike_turu"), "Tehlike türü"
    ).upper()
    if hazard_type not in HAZARD_TYPES:
        raise ValueError(f"Geçersiz tehlike türü: {hazard_type}")
    description = _text(
        tehlike.get("aciklama"), "Tehlike açıklaması"
    )
    now = _now(tehlike.get("simdi"))

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO haccp_tehlikeleri (
                tehlike_kodu, ad, tehlike_turu,
                aciklama, kaynak, aktif,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                code, name, hazard_type, description,
                _text(tehlike.get("kaynak"), "Kaynak", False)
                or None,
                now, now,
            ),
        )
        hazard_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_TEHLIKESI",
            hazard_id, f"Tehlike oluşturuldu: {code}",
            kullanici,
            new={"tehlike_turu": hazard_type},
            session_id=oturum_id,
        )
    return hazard_id


def tehlike_degerlendir(
    conn, plan_id, proses_adimi_id, tehlike_id,
    degerlendirme, kullanici=None, oturum_id=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    step_id = _id(proses_adimi_id, "Proses adımı")
    hazard_id = _id(tehlike_id, "Tehlike")
    data = dict(degerlendirme or {})

    try:
        probability = int(data.get("olasilik"))
        severity = int(data.get("siddet"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Olasılık ve şiddet tam sayı olmalı.") from exc

    if probability not in range(1, 6):
        raise ValueError("Olasılık 1–5 arasında olmalıdır.")
    if severity not in range(1, 6):
        raise ValueError("Şiddet 1–5 arasında olmalıdır.")

    reason = _text(data.get("gerekce"), "Gerekçe")
    controls = _text(
        data.get("kontrol_onlemleri"), "Kontrol önlemleri"
    )
    score = probability * severity
    significant = int(score >= SIGNIFICANT_RISK_SCORE)
    now = _now(data.get("simdi"))

    with conn:
        step = conn.execute(
            """
            SELECT plan_id FROM haccp_proses_adimlari
            WHERE id = ?
            """,
            (step_id,),
        ).fetchone()
        if step is None or int(step[0]) != plan_id:
            raise ValueError("Proses adımı plana ait değil.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_tehlike_degerlendirmeleri (
                plan_id, proses_adimi_id, tehlike_id,
                olasilik, siddet, risk_puani,
                onemli_tehlike, gerekce, kontrol_onlemleri,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, step_id, hazard_id,
                probability, severity, score, significant,
                reason, controls, now, now,
            ),
        )
        assessment_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA",
            "HACCP_TEHLIKE_DEGERLENDIRMESI",
            assessment_id, "Tehlike riski değerlendirildi.",
            kullanici,
            new={
                "risk_puani": score,
                "onemli_tehlike": bool(significant),
            },
            session_id=oturum_id,
        )
    return assessment_id


def kontrol_noktasi_belirle(
    conn, degerlendirme_id, kontrol,
    kullanici=None, oturum_id=None,
):
    assessment_id = _id(
        degerlendirme_id, "Tehlike değerlendirmesi"
    )
    data = dict(kontrol or {})
    code = _text(data.get("kontrol_kodu"), "Kontrol kodu")
    classification = _text(
        data.get("sinif"), "Kontrol sınıfı"
    ).upper()
    if classification not in CONTROL_CLASSES:
        raise ValueError(
            f"Geçersiz kontrol sınıfı: {classification}"
        )
    reason = _text(
        data.get("karar_gerekcesi"), "Karar gerekçesi"
    )
    now = _now(data.get("simdi"))

    with conn:
        assessment = conn.execute(
            """
            SELECT onemli_tehlike
            FROM haccp_tehlike_degerlendirmeleri
            WHERE id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if assessment is None:
            raise ValueError("Tehlike değerlendirmesi bulunamadı.")
        if (
            classification in {"CCP", "OPRP"}
            and int(assessment[0]) != 1
        ):
            raise ValueError(
                "CCP/OPRP yalnız önemli tehlikeye atanabilir."
            )

        cursor = conn.execute(
            """
            INSERT INTO haccp_kontrol_noktalari (
                degerlendirme_id, kontrol_kodu, sinif,
                karar_agaci_cevaplari, karar_gerekcesi,
                aktif, kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                assessment_id, code, classification,
                _text(
                    data.get("karar_agaci_cevaplari"),
                    "Karar ağacı",
                    False,
                ) or None,
                reason, now, now,
            ),
        )
        control_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_KONTROL_NOKTASI",
            control_id, f"Kontrol noktası belirlendi: {code}",
            kullanici,
            new={
                "degerlendirme_id": assessment_id,
                "sinif": classification,
            },
            session_id=oturum_id,
        )
    return control_id


def kritik_limit_ekle(
    conn, kontrol_noktasi_id, limit,
    kullanici=None, oturum_id=None,
):
    control_id = _id(
        kontrol_noktasi_id, "Kontrol noktası"
    )
    data = dict(limit or {})
    parameter = _text(
        data.get("parametre"), "Kritik limit parametresi"
    )
    operator = _text(
        data.get("operator"), "Limit operatörü"
    ).upper()
    if operator not in LIMIT_OPERATORS:
        raise ValueError(f"Geçersiz limit operatörü: {operator}")

    lower = data.get("alt_limit")
    upper = data.get("ust_limit")
    target = _text(
        data.get("hedef_deger"), "Hedef değer", False
    ) or None

    if operator == "MIN" and lower is None:
        raise ValueError("MIN için alt limit gereklidir.")
    if operator == "MAX" and upper is None:
        raise ValueError("MAX için üst limit gereklidir.")
    if operator == "ARALIK" and (
        lower is None or upper is None
    ):
        raise ValueError(
            "ARALIK için alt ve üst limit gereklidir."
        )
    if operator in {"ESIT", "NITEL"} and target is None:
        raise ValueError(
            f"{operator} için hedef değer gereklidir."
        )

    basis = _text(
        data.get("bilimsel_dayanak"), "Bilimsel dayanak"
    )
    now = _now(data.get("simdi"))

    with conn:
        control = conn.execute(
            """
            SELECT id FROM haccp_kontrol_noktalari
            WHERE id = ? AND aktif = 1
            """,
            (control_id,),
        ).fetchone()
        if control is None:
            raise ValueError("Aktif kontrol noktası bulunamadı.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_kritik_limitleri (
                kontrol_noktasi_id, parametre, operator,
                alt_limit, ust_limit, hedef_deger, birim,
                bilimsel_dayanak, aktif,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                control_id, parameter, operator,
                lower, upper, target,
                _text(data.get("birim"), "Birim", False)
                or None,
                basis, now, now,
            ),
        )
        limit_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_KRITIK_LIMITI",
            limit_id, f"Kritik limit eklendi: {parameter}",
            kullanici,
            new={
                "kontrol_noktasi_id": control_id,
                "operator": operator,
            },
            session_id=oturum_id,
        )
    return limit_id


def akis_dogrula(
    conn, plan_id, dogrulayan_personel_id, dogrulama,
    kullanici=None, oturum_id=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    verifier_id = _id(
        dogrulayan_personel_id, "Doğrulayan personel"
    )
    data = dict(dogrulama or {})
    result = _text(
        data.get("sonuc"), "Doğrulama sonucu"
    ).upper()
    if result not in {"UYGUN", "UYGUN_DEGIL"}:
        raise ValueError(
            f"Geçersiz doğrulama sonucu: {result}"
        )
    now = _now(data.get("simdi"))

    with conn:
        plan = conn.execute(
            "SELECT id FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if plan is None:
            raise ValueError("HACCP planı bulunamadı.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_akis_dogrulamalari (
                plan_id, dogrulama_tarihi,
                dogrulayan_personel_id, sonuc,
                bulgular, aksiyonlar, kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, now, verifier_id, result,
                _text(data.get("bulgular"), "Bulgular", False)
                or None,
                _text(data.get("aksiyonlar"), "Aksiyonlar", False)
                or None,
                now,
            ),
        )
        verification_id = cursor.lastrowid
        if result == "UYGUN":
            conn.execute(
                """
                UPDATE haccp_proses_adimlari
                SET yerinde_dogrulandi = 1,
                    guncelleme_zamani = ?
                WHERE plan_id = ?
                """,
                (now, plan_id),
            )
        _audit(
            conn, "DURUM_DEGISIKLIGI",
            "HACCP_AKIS_DOGRULAMASI",
            verification_id,
            f"HACCP akışı doğrulandı: {result}",
            kullanici,
            new={"plan_id": plan_id, "sonuc": result},
            session_id=oturum_id,
        )
    return verification_id


def plani_onayla(
    conn, plan_id, onaylayan_personel_id,
    kullanici=None, oturum_id=None, simdi=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    approver_id = _id(
        onaylayan_personel_id, "Onaylayan personel"
    )
    now = _now(simdi)

    with conn:
        plan = conn.execute(
            "SELECT durum FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if plan is None:
            raise ValueError("HACCP planı bulunamadı.")
        if plan[0] not in {"TASLAK", "INCELEMEDE"}:
            raise ValueError("Plan onaylanabilir durumda değil.")

        flow_ok = conn.execute(
            """
            SELECT COUNT(*) FROM haccp_akis_dogrulamalari
            WHERE plan_id = ? AND sonuc = 'UYGUN'
            """,
            (plan_id,),
        ).fetchone()[0]
        if flow_ok < 1:
            raise ValueError(
                "Yerinde akış doğrulaması gereklidir."
            )

        step_count = conn.execute(
            """
            SELECT COUNT(*) FROM haccp_proses_adimlari
            WHERE plan_id = ? AND yerinde_dogrulandi = 1
            """,
            (plan_id,),
        ).fetchone()[0]
        if step_count < 1:
            raise ValueError(
                "Doğrulanmış proses adımı gereklidir."
            )

        assessment_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM haccp_tehlike_degerlendirmeleri
            WHERE plan_id = ?
            """,
            (plan_id,),
        ).fetchone()[0]
        if assessment_count < 1:
            raise ValueError(
                "Tehlike değerlendirmesi gereklidir."
            )

        missing_control = conn.execute(
            """
            SELECT COUNT(*)
            FROM haccp_tehlike_degerlendirmeleri AS d
            LEFT JOIN haccp_kontrol_noktalari AS k
              ON k.degerlendirme_id = d.id
             AND k.aktif = 1
            WHERE d.plan_id = ?
              AND d.onemli_tehlike = 1
              AND k.id IS NULL
            """,
            (plan_id,),
        ).fetchone()[0]
        if missing_control:
            raise ValueError(
                "Önemli tehlikenin kontrol noktası eksik."
            )

        incomplete = conn.execute(
            """
            SELECT COUNT(*)
            FROM haccp_kontrol_noktalari AS k
            JOIN haccp_tehlike_degerlendirmeleri AS d
              ON d.id = k.degerlendirme_id
            WHERE d.plan_id = ?
              AND k.sinif IN ('CCP', 'OPRP')
              AND (
                  NOT EXISTS (
                      SELECT 1
                      FROM haccp_kritik_limitleri AS l
                      WHERE l.kontrol_noktasi_id = k.id
                        AND l.aktif = 1
                  )
                  OR NOT EXISTS (
                      SELECT 1
                      FROM haccp_izleme_planlari AS i
                      WHERE i.kontrol_noktasi_id = k.id
                        AND i.aktif = 1
                  )
              )
            """,
            (plan_id,),
        ).fetchone()[0]
        if incomplete:
            raise ValueError(
                "CCP/OPRP kritik limiti veya izleme planı eksik."
            )

        conn.execute(
            """
            UPDATE haccp_planlari
            SET durum = 'ONAYLI',
                onaylayan_personel_id = ?,
                onay_zamani = ?,
                guncelleme_zamani = ?
            WHERE id = ?
            """,
            (approver_id, now, now, plan_id),
        )
        _audit(
            conn, "DURUM_DEGISIKLIGI", "HACCP_PLANI",
            plan_id, "HACCP planı onaylandı.",
            kullanici,
            old={"durum": plan[0]},
            new={"durum": "ONAYLI"},
            session_id=oturum_id,
        )
    return plan_id

def izleme_plani_ekle(
    conn, kontrol_noktasi_id, izleme,
    kullanici=None, oturum_id=None,
):
    control_id = _id(
        kontrol_noktasi_id, "Kontrol noktası"
    )
    data = dict(izleme or {})
    parameter = _text(
        data.get("izlenecek_parametre"),
        "İzlenecek parametre",
    )
    method = _text(data.get("yontem"), "İzleme yöntemi")
    frequency = _text(data.get("siklik"), "İzleme sıklığı")
    role = _text(data.get("sorumlu_rol"), "Sorumlu rol")
    form = _text(data.get("kayit_formu"), "Kayıt formu")
    deviation_action = _text(
        data.get("sapmada_yapilacaklar"),
        "Sapmada yapılacaklar",
    )
    now = _now(data.get("simdi"))

    with conn:
        control = conn.execute(
            """
            SELECT id FROM haccp_kontrol_noktalari
            WHERE id = ? AND aktif = 1
            """,
            (control_id,),
        ).fetchone()
        if control is None:
            raise ValueError("Aktif kontrol noktası bulunamadı.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_izleme_planlari (
                kontrol_noktasi_id, izlenecek_parametre,
                yontem, siklik, sorumlu_rol, kayit_formu,
                sapmada_yapilacaklar, aktif,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                control_id, parameter, method, frequency,
                role, form, deviation_action, now, now,
            ),
        )
        monitoring_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_IZLEME_PLANI",
            monitoring_id, "HACCP izleme planı eklendi.",
            kullanici,
            new={"kontrol_noktasi_id": control_id},
            session_id=oturum_id,
        )
    return monitoring_id


def sapma_kaydet(
    conn, kontrol_noktasi_id, sapma,
    kullanici=None, oturum_id=None,
):
    control_id = _id(
        kontrol_noktasi_id, "Kontrol noktası"
    )
    data = dict(sapma or {})
    detected_at = _text(
        data.get("tespit_zamani"), "Tespit zamanı"
    )
    description = _text(
        data.get("aciklama"), "Sapma açıklaması"
    )
    product_decision = _text(
        data.get("urun_karari"), "Ürün kararı"
    ).upper()
    correction = _text(data.get("duzeltme"), "Düzeltme")
    responsible_id = data.get("sorumlu_personel_id")
    if responsible_id is not None:
        responsible_id = _id(
            responsible_id, "Sorumlu personel"
        )
    nonconformity_id = data.get("kalite_uygunsuzluk_id")
    if nonconformity_id is not None:
        nonconformity_id = _id(
            nonconformity_id, "Kalite uygunsuzluğu"
        )
    now = _now(data.get("simdi"))

    with conn:
        control = conn.execute(
            """
            SELECT id FROM haccp_kontrol_noktalari
            WHERE id = ? AND aktif = 1
            """,
            (control_id,),
        ).fetchone()
        if control is None:
            raise ValueError("Aktif kontrol noktası bulunamadı.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_sapmalari (
                kontrol_noktasi_id, tespit_zamani,
                tespit_degeri, aciklama, urun_karari,
                duzeltme, kok_neden,
                kalite_uygunsuzluk_id,
                sorumlu_personel_id, durum,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACIK', ?, ?)
            """,
            (
                control_id, detected_at,
                _text(
                    data.get("tespit_degeri"),
                    "Tespit değeri",
                    False,
                ) or None,
                description, product_decision, correction,
                _text(
                    data.get("kok_neden"),
                    "Kök neden",
                    False,
                ) or None,
                nonconformity_id, responsible_id, now, now,
            ),
        )
        deviation_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_SAPMASI",
            deviation_id, "HACCP sapması kaydedildi.",
            kullanici,
            new={
                "kontrol_noktasi_id": control_id,
                "urun_karari": product_decision,
                "durum": "ACIK",
            },
            session_id=oturum_id,
        )
    return deviation_id


def dogrulama_kaydet(
    conn, plan_id, dogrulama,
    kullanici=None, oturum_id=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    data = dict(dogrulama or {})
    verification_type = _text(
        data.get("dogrulama_turu"), "Doğrulama türü"
    ).upper()
    allowed_types = {
        "PLAN", "AKIS", "IZLEME",
        "KALIBRASYON", "IC_DENETIM",
    }
    if verification_type not in allowed_types:
        raise ValueError(
            f"Geçersiz doğrulama türü: {verification_type}"
        )
    result = _text(
        data.get("sonuc"), "Doğrulama sonucu"
    ).upper()
    if result not in {"UYGUN", "UYGUN_DEGIL"}:
        raise ValueError(
            f"Geçersiz doğrulama sonucu: {result}"
        )
    verifier_id = _id(
        data.get("dogrulayan_personel_id"),
        "Doğrulayan personel",
    )
    verification_date = _text(
        data.get("dogrulama_tarihi"),
        "Doğrulama tarihi",
    )
    now = _now(data.get("simdi"))

    with conn:
        plan = conn.execute(
            "SELECT id FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if plan is None:
            raise ValueError("HACCP planı bulunamadı.")

        cursor = conn.execute(
            """
            INSERT INTO haccp_dogrulamalari (
                plan_id, dogrulama_turu,
                dogrulama_tarihi,
                dogrulayan_personel_id, sonuc,
                bulgular, aksiyonlar,
                sonraki_dogrulama_tarihi,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, verification_type,
                verification_date, verifier_id, result,
                _text(
                    data.get("bulgular"),
                    "Bulgular",
                    False,
                ) or None,
                _text(
                    data.get("aksiyonlar"),
                    "Aksiyonlar",
                    False,
                ) or None,
                _text(
                    data.get("sonraki_dogrulama_tarihi"),
                    "Sonraki doğrulama",
                    False,
                ) or None,
                now, now,
            ),
        )
        verification_id = cursor.lastrowid
        _audit(
            conn, "OLUSTURMA", "HACCP_DOGRULAMASI",
            verification_id,
            f"HACCP doğrulaması: {verification_type}",
            kullanici,
            new={"sonuc": result, "plan_id": plan_id},
            session_id=oturum_id,
        )
    return verification_id


def plan_revizyonu_olustur(
    conn, plan_id, revizyon,
    kullanici=None, oturum_id=None,
):
    plan_id = _id(plan_id, "HACCP planı")
    data = dict(revizyon or {})
    new_code = _text(
        data.get("plan_kodu"), "Yeni plan kodu"
    )
    reason = _text(
        data.get("revizyon_nedeni"), "Revizyon nedeni"
    )
    preparer_id = _id(
        data.get("hazirlayan_personel_id"),
        "Hazırlayan personel",
    )
    now = _now(data.get("simdi"))

    with conn:
        old = conn.execute(
            """
            SELECT urun_id, ad, urun_aciklamasi,
                   amaclanan_kullanim, hedef_tuketici,
                   kullanim_kisitlari, revizyon_no, durum
            FROM haccp_planlari
            WHERE id = ?
            """,
            (plan_id,),
        ).fetchone()
        if old is None:
            raise ValueError("HACCP planı bulunamadı.")
        if old[7] != "ONAYLI":
            raise ValueError(
                "Yalnız onaylı HACCP planı revize edilebilir."
            )

        cursor = conn.execute(
            """
            INSERT INTO haccp_planlari (
                plan_kodu, urun_id, ad,
                urun_aciklamasi, amaclanan_kullanim,
                hedef_tuketici, kullanim_kisitlari,
                revizyon_no, durum, onceki_plan_id,
                hazirlayan_personel_id,
                kayit_zamani, guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'TASLAK', ?, ?, ?, ?)
            """,
            (
                new_code, old[0], old[1], old[2], old[3],
                old[4], old[5], int(old[6]) + 1,
                plan_id, preparer_id, now, now,
            ),
        )
        revision_id = cursor.lastrowid

        conn.execute(
            """
            UPDATE haccp_planlari
            SET durum = 'ARSIV',
                guncelleme_zamani = ?
            WHERE id = ?
            """,
            (now, plan_id),
        )
        _audit(
            conn, "DURUM_DEGISIKLIGI", "HACCP_PLANI",
            plan_id, f"HACCP planı revize edildi: {reason}",
            kullanici,
            old={"durum": "ONAYLI"},
            new={
                "durum": "ARSIV",
                "yeni_plan_id": revision_id,
            },
            session_id=oturum_id,
        )
        _audit(
            conn, "OLUSTURMA", "HACCP_PLANI",
            revision_id, f"HACCP revizyonu oluşturuldu: {reason}",
            kullanici,
            new={
                "onceki_plan_id": plan_id,
                "revizyon_no": int(old[6]) + 1,
            },
            session_id=oturum_id,
        )
    return revision_id
