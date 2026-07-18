from database.db import get_connection


class ProductService:

    def aktif_urunler(self):
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    urun_kodu,
                    urun_adi,
                    kategori,
                    birim,
                    saklama_sicakligi
                FROM urunler
                WHERE aktif = 1
                ORDER BY urun_adi COLLATE NOCASE
                """
            ).fetchall()

            return [
                {
                    "id": int(row["id"]),
                    "kod": row["urun_kodu"],
                    "ad": row["urun_adi"],
                    "kategori": row["kategori"],
                    "birim": row["birim"],
                    "saklama_sicakligi": row[
                        "saklama_sicakligi"
                    ],
                }
                for row in rows
            ]

        finally:
            conn.close()

    def aktif_urun_map(self):
        return {
            f'{urun["kod"]} | {urun["ad"]}': urun["id"]
            for urun in self.aktif_urunler()
        }

    def urun_getir(self, urun_id):
        conn = get_connection()

        try:
            row = conn.execute(
                """
                SELECT
                    id,
                    urun_kodu,
                    urun_adi,
                    kategori,
                    barkod,
                    birim,
                    raf_omru_gun,
                    saklama_sicakligi,
                    aktif,
                    aciklama
                FROM urunler
                WHERE id = ?
                LIMIT 1
                """,
                (urun_id,),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

        finally:
            conn.close()
