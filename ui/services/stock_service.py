from database.raw_material_stock_engine import (
    hammadde_stok_ozeti,
)


class StockService:

    def kritik_stoklar(self):
        return [
            {
                "ad": row["hammadde"],
                "kalan": float(row["kalan_kg"]),
            }
            for row in hammadde_stok_ozeti()
        ]
