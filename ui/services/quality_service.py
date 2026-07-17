from datetime import datetime

from database.db import get_connection
from database.quality_engine import (
    kalite_ozeti,
    uygunsuzluklari_getir,
)


class QualityService:

    def dashboard_verisi(self, limit=8):
        conn = get_connection()

        try:
            summary = kalite_ozeti(conn)
            rows = uygunsuzluklari_getir(
                conn,
                limit=5000,
            )
        finally:
            conn.close()

        bugun = datetime.now().date()
        alerts = []

        for row in rows:
            if row["durum"] in {"KAPALI", "IPTAL"}:
                continue

            gecikmis = False

            if row["hedef_tarih"]:
                hedef = datetime.strptime(
                    row["hedef_tarih"],
                    "%d.%m.%Y",
                ).date()
                gecikmis = hedef < bugun

            if (
                row["onem_derecesi"] == "KRITIK"
                or gecikmis
            ):
                alerts.append(
                    {
                        "kayit_no": row["kayit_no"],
                        "baslik": row["baslik"],
                        "onem": row["onem_derecesi"],
                        "durum": row["durum"],
                        "hedef_tarih": (
                            row["hedef_tarih"] or "-"
                        ),
                        "gecikmis": gecikmis,
                    }
                )

        alerts.sort(
            key=lambda item: (
                not item["gecikmis"],
                item["onem"] != "KRITIK",
                item["kayit_no"],
            )
        )

        return {
            "toplam": int(summary["toplam"] or 0),
            "acik": int(summary["acik"] or 0),
            "kritik": int(summary["kritik"] or 0),
            "geciken": int(summary["geciken"] or 0),
            "alerts": alerts[:max(1, int(limit))],
        }
