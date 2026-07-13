from database.db import get_connection


class ShipmentService:

    def son_sevkiyatlar(self, limit=10):
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    sevkiyat_tarihi,
                    musteri,
                    sevk_koli_adedi
                FROM sevkiyat
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

            return [
                {
                    "tarih": row["sevkiyat_tarihi"],
                    "musteri": row["musteri"],
                    "koli": int(
                        row["sevk_koli_adedi"] or 0
                    ),
                }
                for row in rows
            ]

        finally:
            conn.close()
