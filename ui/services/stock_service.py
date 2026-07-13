from database.db import get_connection


class StockService:

    def __init__(self):
        self.conn = get_connection()

    def kritik_stoklar(self):

        rows = self.conn.execute(
            """
            SELECT
                h.ad,
                COALESCE(
                    SUM(
                        CASE
                            WHEN dk.kabul_durumu='KABUL'
                            THEN dk.miktar_kg
                            ELSE 0
                        END
                    ),
                    0
                )
                -
                COALESCE(
                    (
                        SELECT
                            SUM(
                                uhl.kullanilan_miktar_kg
                            )
                        FROM uretim_hammadde_lotlari uhl
                        JOIN depo_kabul dk2
                          ON dk2.id=uhl.depo_kabul_id
                        WHERE dk2.hammadde_id=h.id
                    ),
                    0
                ) AS kalan
            FROM hammaddeler h
            LEFT JOIN depo_kabul dk
              ON dk.hammadde_id=h.id
            WHERE h.aktif=1
            GROUP BY h.id,h.ad
            ORDER BY kalan ASC
            """
        ).fetchall()

        return [
            {
                "ad": r["ad"],
                "kalan": float(r["kalan"])
            }
            for r in rows
        ]
