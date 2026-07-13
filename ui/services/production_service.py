from database.db import get_connection


class ProductionService:

    def __init__(self):
        self.conn = get_connection()

    def son_uretimler(self, limit=10):

        rows = self.conn.execute(
            """
            SELECT
                uretim_tarihi,
                urun_lot_no,
                net_uretim_kg
            FROM uretim
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        sonuc = []

        for row in rows:
            sonuc.append(
                {
                    "tarih": row["uretim_tarihi"],
                    "lot": row["urun_lot_no"],
                    "kg": float(row["net_uretim_kg"]),
                }
            )

        return sonuc
