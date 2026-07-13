from database.db import get_connection


class DashboardService:

    def __init__(self):
        self.conn = get_connection()

    def toplam_uretim(self):
        row = self.conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(net_uretim_kg),
                    0
                )
            FROM uretim
            """
        ).fetchone()

        return float(row[0])

    def toplam_paketleme(self):
        row = self.conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(paketlenen_kg),
                    0
                )
            FROM paketleme
            """
        ).fetchone()

        return float(row[0])

    def toplam_sevkiyat(self):
        row = self.conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(sevk_kg),
                    0
                )
            FROM sevkiyat_kalemleri
            """
        ).fetchone()

        return float(row[0])
