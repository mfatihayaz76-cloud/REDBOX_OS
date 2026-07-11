from datetime import date, datetime, timedelta


DATE_FORMAT = "%d.%m.%Y"

SUPPORTED_PERIODS = {
    "GUNLUK",
    "URETIM_SONRASI",
    "HAFTALIK",
    "AYLIK",
    "YILLIK",
}


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()

    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value

    return datetime.strptime(
        str(value),
        DATE_FORMAT
    ).date()


def _format_date(value):
    return value.strftime(DATE_FORMAT)


def _period_window(target_date, period):
    target = _parse_date(target_date)

    if period == "GUNLUK":
        return target, target

    if period == "HAFTALIK":
        start = target - timedelta(
            days=target.weekday()
        )
        end = start + timedelta(days=6)
        return start, end

    if period == "AYLIK":
        start = target.replace(day=1)

        if start.month == 12:
            next_month = start.replace(
                year=start.year + 1,
                month=1
            )
        else:
            next_month = start.replace(
                month=start.month + 1
            )

        end = next_month - timedelta(days=1)
        return start, end

    if period == "YILLIK":
        start = target.replace(
            month=1,
            day=1
        )
        end = target.replace(
            month=12,
            day=31
        )
        return start, end

    if period == "URETIM_SONRASI":
        return target, target

    raise ValueError(
        f"Desteklenmeyen temizlik periyodu: {period}"
    )


def _task_status(
    target_date,
    period,
    today=None,
):
    target = _parse_date(target_date)

    if today is None:
        today_value = date.today()
    else:
        today_value = _parse_date(today)

    start, end = _period_window(
        target,
        period,
    )

    if today_value < start:
        return {
            "durum": "GELECEK",
            "donem_baslangic_tarihi": _format_date(
                start
            ),
            "donem_bitis_tarihi": _format_date(
                end
            ),
        }

    if today_value > end:
        return {
            "durum": "GECIKEN",
            "donem_baslangic_tarihi": _format_date(
                start
            ),
            "donem_bitis_tarihi": _format_date(
                end
            ),
        }

    return {
        "durum": "BEKLEYEN",
        "donem_baslangic_tarihi": _format_date(
            start
        ),
        "donem_bitis_tarihi": _format_date(
            end
        ),
    }

def _completion_exists(
    conn,
    plan_id,
    target_date,
    period,
    uretim_id=None,
):
    if period == "URETIM_SONRASI":
        if uretim_id is None:
            return False

        row = conn.execute(
            """
            SELECT 1
            FROM temizlik_gerceklesmeleri
            WHERE plan_id = ?
              AND uretim_id = ?
              AND durum = 'TAMAMLANDI'
            LIMIT 1
            """,
            (
                plan_id,
                uretim_id,
            ),
        ).fetchone()

        return row is not None

    start, end = _period_window(
        target_date,
        period,
    )

    row = conn.execute(
        """
        SELECT 1
        FROM temizlik_gerceklesmeleri
        WHERE plan_id = ?
          AND durum = 'TAMAMLANDI'
          AND tamamlanma_tarihi IS NOT NULL
          AND substr(tamamlanma_tarihi, 7, 4)
              || '-'
              || substr(tamamlanma_tarihi, 4, 2)
              || '-'
              || substr(tamamlanma_tarihi, 1, 2)
              BETWEEN ? AND ?
        LIMIT 1
        """,
        (
            plan_id,
            start.isoformat(),
            end.isoformat(),
        ),
    ).fetchone()

    return row is not None


def get_due_cleaning_tasks(
    conn,
    target_date,
):
    target = _parse_date(target_date)
    target_text = _format_date(target)

    plans = conn.execute(
        """
        SELECT
            p.id AS plan_id,
            p.gorev_adi,
            p.talimat,
            p.periyot,
            p.uretimle_iliskili,
            k.id AS kat_id,
            k.kat_kodu,
            k.kat_adi,
            k.sira_no AS kat_sira_no,
            a.id AS alan_id,
            a.alan_kodu,
            a.alan_adi,
            a.sira_no AS alan_sira_no,
            e.id AS ekipman_id,
            e.ekipman_kodu,
            e.ekipman_adi
        FROM temizlik_planlari p
        JOIN temizlik_katlar k
          ON k.id = p.kat_id
        JOIN temizlik_alanlari a
          ON a.id = p.alan_id
        LEFT JOIN temizlik_ekipmanlari e
          ON e.id = p.ekipman_id
        WHERE p.aktif = 1
          AND k.aktif = 1
          AND a.aktif = 1
          AND (
                e.id IS NULL
                OR e.aktif = 1
          )
        ORDER BY
            k.sira_no,
            a.sira_no,
            p.id
        """
    ).fetchall()

    productions = conn.execute(
        """
        SELECT
            id,
            uretim_tarihi,
            urun_lot_no
        FROM uretim
        WHERE uretim_tarihi = ?
        ORDER BY id
        """,
        (target_text,),
    ).fetchall()

    tasks = []

    for plan in plans:
        period = plan["periyot"]

        if period not in SUPPORTED_PERIODS:
            raise ValueError(
                "Desteklenmeyen aktif temizlik "
                f"periyodu: {period}"
            )

        status = _task_status(
            target,
            period,
        )

        base = {
            "plan_id": plan["plan_id"],
            "gorev_adi": plan["gorev_adi"],
            "talimat": plan["talimat"],
            "periyot": period,
            "durum": status["durum"],
            "donem_baslangic_tarihi": status[
                "donem_baslangic_tarihi"
            ],
            "donem_bitis_tarihi": status[
                "donem_bitis_tarihi"
            ],
            "uretimle_iliskili": bool(
                plan["uretimle_iliskili"]
            ),
            "kat_id": plan["kat_id"],
            "kat_kodu": plan["kat_kodu"],
            "kat_adi": plan["kat_adi"],
            "alan_id": plan["alan_id"],
            "alan_kodu": plan["alan_kodu"],
            "alan_adi": plan["alan_adi"],
            "ekipman_id": plan["ekipman_id"],
            "ekipman_kodu": plan["ekipman_kodu"],
            "ekipman_adi": plan["ekipman_adi"],
            "planlanan_tarih": target_text,
        }

        if period == "URETIM_SONRASI":
            for production in productions:
                if _completion_exists(
                    conn,
                    plan["plan_id"],
                    target,
                    period,
                    production["id"],
                ):
                    continue

                task = dict(base)
                task["uretim_id"] = production["id"]
                task["urun_lot_no"] = (
                    production["urun_lot_no"]
                )
                tasks.append(task)

            continue

        if _completion_exists(
            conn,
            plan["plan_id"],
            target,
            period,
        ):
            continue

        task = dict(base)
        task["uretim_id"] = None
        task["urun_lot_no"] = None
        tasks.append(task)

    return tasks


def get_due_cleaning_summary(
    conn,
    target_date,
):
    tasks = get_due_cleaning_tasks(
        conn,
        target_date,
    )

    summary = {
        "TOPLAM": len(tasks),
        "GUNLUK": 0,
        "URETIM_SONRASI": 0,
        "HAFTALIK": 0,
        "AYLIK": 0,
        "YILLIK": 0,
    }

    for task in tasks:
        summary[task["periyot"]] += 1

    return summary

def get_cleaning_report_dataset(
    conn,
    target_date,
    today=None,
):
    target = _parse_date(target_date)
    target_text = _format_date(target)

    plan_rows = conn.execute(
        """
        SELECT
            p.id AS plan_id,
            p.gorev_adi,
            p.talimat,
            p.periyot,
            p.uretimle_iliskili,
            k.id AS kat_id,
            k.kat_kodu,
            k.kat_adi,
            k.sira_no AS kat_sira_no,
            a.id AS alan_id,
            a.alan_kodu,
            a.alan_adi,
            a.sira_no AS alan_sira_no,
            e.id AS ekipman_id,
            e.ekipman_kodu,
            e.ekipman_adi,
            e.sira_no AS ekipman_sira_no,
            e.urun_temas
        FROM temizlik_planlari AS p
        JOIN temizlik_katlar AS k
          ON k.id = p.kat_id
        JOIN temizlik_alanlari AS a
          ON a.id = p.alan_id
        LEFT JOIN temizlik_ekipmanlari AS e
          ON e.id = p.ekipman_id
        WHERE p.aktif = 1
          AND k.aktif = 1
          AND a.aktif = 1
          AND (
              e.id IS NULL
              OR e.aktif = 1
          )
        ORDER BY
            k.sira_no,
            a.sira_no,
            COALESCE(e.sira_no, 0),
            p.id
        """
    ).fetchall()

    completion_rows = conn.execute(
        """
        SELECT
            g.id AS gerceklesme_id,
            g.plan_id,
            g.planlanan_tarih,
            g.tamamlanma_tarihi,
            g.uretim_id,
            g.uygulayan,
            g.kontrol_eden,
            g.durum AS gerceklesme_durumu,
            g.aciklama,
            g.kayit_zamani,
            u.uretim_tarihi,
            u.urun_lot_no
        FROM temizlik_gerceklesmeleri AS g
        LEFT JOIN uretim AS u
          ON u.id = g.uretim_id
        WHERE g.planlanan_tarih = ?
        ORDER BY
            g.plan_id,
            COALESCE(g.uretim_id, 0),
            g.id
        """,
        (target_text,),
    ).fetchall()

    completion_map = {}

    for row in completion_rows:
        row_dict = dict(row)
        key = (
            row_dict["plan_id"],
            row_dict["planlanan_tarih"],
            row_dict["uretim_id"],
        )

        if key in completion_map:
            raise ValueError(
                "Temizlik raporu için yinelenen gerçekleşme kaydı bulundu."
            )

        completion_map[key] = row_dict

    due_tasks = get_due_cleaning_tasks(
        conn,
        target_text,
    )

    due_map = {}

    for task in due_tasks:
        key = (
            task["plan_id"],
            task["planlanan_tarih"],
            task["uretim_id"],
        )

        if key in due_map:
            raise ValueError(
                "Temizlik raporu için yinelenen planlı görev bulundu."
            )

        due_map[key] = task

    production_rows = conn.execute(
        """
        SELECT
            id,
            uretim_tarihi,
            urun_lot_no
        FROM uretim
        WHERE uretim_tarihi = ?
        ORDER BY id
        """,
        (target_text,),
    ).fetchall()

    production_map = {
        row["id"]: dict(row)
        for row in production_rows
    }

    report_rows = []

    for plan_row in plan_rows:
        plan = dict(plan_row)

        if plan["uretimle_iliskili"]:
            matching_tasks = [
                task
                for task in due_tasks
                if task["plan_id"] == plan["plan_id"]
            ]

            matching_completions = [
                row
                for row in completion_rows
                if row["plan_id"] == plan["plan_id"]
            ]

            row_keys = {
                (
                    plan["plan_id"],
                    target_text,
                    task["uretim_id"],
                )
                for task in matching_tasks
            }

            row_keys.update(
                (
                    plan["plan_id"],
                    target_text,
                    row["uretim_id"],
                )
                for row in matching_completions
            )

            if not row_keys:
                continue
        else:
            row_keys = {
                (
                    plan["plan_id"],
                    target_text,
                    None,
                )
            }

        for key in sorted(
            row_keys,
            key=lambda value: (
                value[0],
                value[2] or 0,
            ),
        ):
            task = due_map.get(key)
            completion = completion_map.get(key)

            if completion is not None:
                status = {
                    "durum": "TAMAMLANDI",
                    "donem_baslangic_tarihi": (
                        task["donem_baslangic_tarihi"]
                        if task is not None
                        else _format_date(
                            _period_window(
                                target,
                                plan["periyot"],
                            )[0]
                        )
                    ),
                    "donem_bitis_tarihi": (
                        task["donem_bitis_tarihi"]
                        if task is not None
                        else _format_date(
                            _period_window(
                                target,
                                plan["periyot"],
                            )[1]
                        )
                    ),
                }
            elif task is not None:
                status = {
                    "durum": task["durum"],
                    "donem_baslangic_tarihi": (
                        task["donem_baslangic_tarihi"]
                    ),
                    "donem_bitis_tarihi": (
                        task["donem_bitis_tarihi"]
                    ),
                }
            else:
                status = _task_status(
                    target,
                    plan["periyot"],
                    today=today,
                )

            production = (
                production_map.get(key[2])
                if key[2] is not None
                else None
            )

            if production is None and completion is not None:
                if completion["uretim_id"] is not None:
                    production = {
                        "id": completion["uretim_id"],
                        "uretim_tarihi": completion["uretim_tarihi"],
                        "urun_lot_no": completion["urun_lot_no"],
                    }

            report_rows.append(
                {
                    "rapor_satir_anahtari": key,
                    "plan_id": plan["plan_id"],
                    "gorev_adi": plan["gorev_adi"],
                    "talimat": plan["talimat"],
                    "periyot": plan["periyot"],
                    "uretimle_iliskili": bool(
                        plan["uretimle_iliskili"]
                    ),
                    "kat_id": plan["kat_id"],
                    "kat_kodu": plan["kat_kodu"],
                    "kat_adi": plan["kat_adi"],
                    "alan_id": plan["alan_id"],
                    "alan_kodu": plan["alan_kodu"],
                    "alan_adi": plan["alan_adi"],
                    "ekipman_id": plan["ekipman_id"],
                    "ekipman_kodu": plan["ekipman_kodu"],
                    "ekipman_adi": plan["ekipman_adi"],
                    "urun_temas": (
                        bool(plan["urun_temas"])
                        if plan["urun_temas"] is not None
                        else None
                    ),
                    "planlanan_tarih": target_text,
                    "uretim_id": key[2],
                    "urun_lot_no": (
                        production["urun_lot_no"]
                        if production is not None
                        else None
                    ),
                    "durum": status["durum"],
                    "donem_baslangic_tarihi": (
                        status["donem_baslangic_tarihi"]
                    ),
                    "donem_bitis_tarihi": (
                        status["donem_bitis_tarihi"]
                    ),
                    "gerceklesme_id": (
                        completion["gerceklesme_id"]
                        if completion is not None
                        else None
                    ),
                    "tamamlanma_tarihi": (
                        completion["tamamlanma_tarihi"]
                        if completion is not None
                        else None
                    ),
                    "uygulayan": (
                        completion["uygulayan"]
                        if completion is not None
                        else None
                    ),
                    "kontrol_eden": (
                        completion["kontrol_eden"]
                        if completion is not None
                        else None
                    ),
                    "gerceklesme_durumu": (
                        completion["gerceklesme_durumu"]
                        if completion is not None
                        else None
                    ),
                    "aciklama": (
                        completion["aciklama"]
                        if completion is not None
                        else None
                    ),
                    "kayit_zamani": (
                        completion["kayit_zamani"]
                        if completion is not None
                        else None
                    ),
                }
            )

    return report_rows

def complete_cleaning_task(
    conn,
    plan_id,
    planlanan_tarih,
    uygulayan,
    kontrol_eden,
    aciklama=None,
    uretim_id=None,
):
    target = _parse_date(planlanan_tarih)
    target_text = _format_date(target)

    try:
        plan_id = int(plan_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Geçersiz temizlik plan ID."
        ) from exc

    uygulayan = str(
        uygulayan or ""
    ).strip()
    kontrol_eden = str(
        kontrol_eden or ""
    ).strip()

    if not uygulayan:
        raise ValueError(
            "Uygulayan personel zorunludur."
        )

    if not kontrol_eden:
        raise ValueError(
            "Kontrol eden personel zorunludur."
        )

    if uygulayan == kontrol_eden:
        raise ValueError(
            "Uygulayan ve kontrol eden aynı personel olamaz."
        )

    if aciklama is None:
        aciklama_text = None
    else:
        aciklama_text = str(
            aciklama
        ).strip() or None

    plan = conn.execute(
        """
        SELECT
            id,
            periyot,
            uretimle_iliskili,
            aktif
        FROM temizlik_planlari
        WHERE id = ?
        LIMIT 1
        """,
        (plan_id,),
    ).fetchone()

    if plan is None:
        raise ValueError(
            "Temizlik planı bulunamadı."
        )

    period = plan["periyot"]

    if period not in SUPPORTED_PERIODS:
        raise ValueError(
            "Desteklenmeyen temizlik periyodu: "
            f"{period}"
        )

    if not bool(plan["aktif"]):
        raise ValueError(
            "Pasif temizlik planı tamamlanamaz."
        )

    production_linked = bool(
        plan["uretimle_iliskili"]
    )

    if period == "URETIM_SONRASI":
        if not production_linked:
            raise ValueError(
                "Üretim sonrası plan bağlantısı tutarsız."
            )

        if uretim_id is None:
            raise ValueError(
                "Üretim sonrası temizlik için üretim ID zorunludur."
            )

        try:
            uretim_id = int(
                uretim_id
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Geçersiz üretim ID."
            ) from exc

        production = conn.execute(
            """
            SELECT
                id,
                uretim_tarihi
            FROM uretim
            WHERE id = ?
            LIMIT 1
            """,
            (uretim_id,),
        ).fetchone()

        if production is None:
            raise ValueError(
                "Bağlı üretim kaydı bulunamadı."
            )

        if production["uretim_tarihi"] != target_text:
            raise ValueError(
                "Üretim tarihi ile planlanan temizlik tarihi uyuşmuyor."
            )

    else:
        if production_linked:
            raise ValueError(
                "Temizlik planı üretim bağlantısı tutarsız."
            )

        if uretim_id is not None:
            raise ValueError(
                "Bu temizlik görevi üretime bağlanamaz."
            )

    if _completion_exists(
        conn,
        plan_id,
        target,
        period,
        uretim_id,
    ):
        raise ValueError(
            "Bu temizlik görevi ilgili dönem için zaten tamamlandı."
        )

    cursor = conn.execute(
        """
        INSERT INTO temizlik_gerceklesmeleri (
            plan_id,
            planlanan_tarih,
            tamamlanma_tarihi,
            uretim_id,
            uygulayan,
            kontrol_eden,
            durum,
            aciklama
        )
        VALUES (?, ?, ?, ?, ?, ?, 'TAMAMLANDI', ?)
        """,
        (
            plan_id,
            target_text,
            target_text,
            uretim_id,
            uygulayan,
            kontrol_eden,
            aciklama_text,
        ),
    )

    return cursor.lastrowid

