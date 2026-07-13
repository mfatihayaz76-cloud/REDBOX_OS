import math

from database.db import get_connection
from database.finished_stock_engine import mamul_stok_ozeti
from database.raw_material_stock_engine import hammadde_stok_ozeti


class OrderCalculatorService:

    PACKAGE_RULES = {
        500: {
            "label": "500 g",
            "packages_per_case": 32,
        },
        2500: {
            "label": "2.5 kg",
            "packages_per_case": 10,
        },
    }

    def calculate(
        self,
        packages_500=0,
        packages_2500=0,
    ):
        inputs = {
            500: self._non_negative_int(
                packages_500,
                "500 g paket adedi",
            ),
            2500: self._non_negative_int(
                packages_2500,
                "2.5 kg paket adedi",
            ),
        }

        if not any(inputs.values()):
            raise ValueError(
                "En az bir sipariş miktarı girilmelidir."
            )

        finished_stock = self._finished_stock_by_package()
        order_lines = []

        total_order_kg = 0.0
        total_available_kg = 0.0
        total_allocated_kg = 0.0
        production_required_kg = 0.0

        for grams in (500, 2500):
            rule = self.PACKAGE_RULES[grams]
            ordered_packages = inputs[grams]
            available_packages = finished_stock.get(
                grams,
                0
            )
            allocated_packages = min(
                ordered_packages,
                available_packages
            )
            production_packages = max(
                0,
                ordered_packages - available_packages
            )

            order_kg = (
                ordered_packages * grams / 1000.0
            )
            available_kg = (
                available_packages * grams / 1000.0
            )
            allocated_kg = (
                allocated_packages * grams / 1000.0
            )
            required_kg = (
                production_packages * grams / 1000.0
            )

            total_order_kg += order_kg
            total_available_kg += available_kg
            total_allocated_kg += allocated_kg
            production_required_kg += required_kg

            order_lines.append(
                {
                    "grams": grams,
                    "package": rule["label"],
                    "packages_per_case":
                        rule["packages_per_case"],
                    "ordered_packages":
                        ordered_packages,
                    "order_kg":
                        order_kg,
                    "available_packages":
                        available_packages,
                    "available_kg":
                        available_kg,
                    "allocated_packages":
                        allocated_packages,
                    "allocated_kg":
                        allocated_kg,
                    "production_packages":
                        production_packages,
                    "production_kg":
                        required_kg,
                }
            )

        recipe = self._active_recipe()

        if production_required_kg > 0:
            batch_count = math.ceil(
                production_required_kg
                / recipe["batch_theoretical_kg"]
            )
        else:
            batch_count = 0

        theoretical_production_kg = (
            batch_count
            * recipe["batch_theoretical_kg"]
        )
        estimated_surplus_kg = max(
            0.0,
            theoretical_production_kg
            - production_required_kg
        )

        raw_stock = {
            row["hammadde"]: float(row["kalan_kg"])
            for row in hammadde_stok_ozeti()
        }

        raw_materials = []
        raw_materials_sufficient = True

        for item in recipe["items"]:
            required_kg = (
                float(item["per_batch_kg"])
                * batch_count
            )
            available_kg = raw_stock.get(
                item["name"],
                0.0
            )
            shortage_kg = max(
                0.0,
                required_kg - available_kg
            )

            if shortage_kg > 0.000001:
                raw_materials_sufficient = False

            raw_materials.append(
                {
                    "name": item["name"],
                    "per_batch_kg":
                        float(item["per_batch_kg"]),
                    "required_kg": required_kg,
                    "available_kg": available_kg,
                    "shortage_kg": shortage_kg,
                    "sufficient":
                        shortage_kg <= 0.000001,
                }
            )

        stocked_per_batch_kg = sum(
            item["per_batch_kg"]
            for item in recipe["items"]
        )
        process_water_per_batch_kg = max(
            0.0,
            recipe["batch_theoretical_kg"]
            - stocked_per_batch_kg
        )
        process_water_required_kg = (
            process_water_per_batch_kg
            * batch_count
        )

        if production_required_kg <= 0.000001:
            status = "MAMUL STOK SİPARİŞİ KARŞILIYOR"
        elif raw_materials_sufficient:
            status = "ÜRETİME UYGUN"
        else:
            status = "HAMMADDE EKSİK"

        return {
            "order_lines": order_lines,
            "total_order_kg": total_order_kg,
            "total_available_kg": total_available_kg,
            "total_allocated_kg": total_allocated_kg,
            "production_required_kg":
                production_required_kg,
            "recipe_name": recipe["name"],
            "recipe_revision": recipe["revision"],
            "batch_theoretical_kg":
                recipe["batch_theoretical_kg"],
            "batch_count": batch_count,
            "theoretical_production_kg":
                theoretical_production_kg,
            "estimated_surplus_kg":
                estimated_surplus_kg,
            "process_water_per_batch_kg":
                process_water_per_batch_kg,
            "process_water_required_kg":
                process_water_required_kg,
            "raw_materials": raw_materials,
            "raw_materials_sufficient":
                raw_materials_sufficient,
            "status": status,
        }

    def _finished_stock_by_package(self):
        totals = {
            500: 0,
            2500: 0,
        }

        for row in mamul_stok_ozeti():
            grams = int(row["ambalaj_gram"])

            if grams in totals:
                totals[grams] += int(
                    row["kalan_paket_adedi"]
                )

        return totals

    def _active_recipe(self):
        conn = get_connection()

        try:
            recipe = conn.execute("""
                SELECT
                    id,
                    ad,
                    parti_teorik_kg,
                    revizyon_no
                FROM receteler
                WHERE aktif = 1
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if recipe is None:
                raise ValueError(
                    "Aktif reçete bulunamadı."
                )

            rows = conn.execute("""
                SELECT
                    h.ad,
                    rk.miktar_kg
                FROM recete_kalemleri rk
                JOIN hammaddeler h
                  ON h.id = rk.hammadde_id
                WHERE rk.recete_id = ?
                  AND h.aktif = 1
                ORDER BY h.id
            """, (
                recipe["id"],
            )).fetchall()

            if not rows:
                raise ValueError(
                    "Aktif reçetede hammadde bulunamadı."
                )

            return {
                "name": recipe["ad"],
                "revision":
                    recipe["revizyon_no"] or "-",
                "batch_theoretical_kg":
                    float(recipe["parti_teorik_kg"]),
                "items": [
                    {
                        "name": row["ad"],
                        "per_batch_kg":
                            float(row["miktar_kg"]),
                    }
                    for row in rows
                ],
            }

        finally:
            conn.close()

    @staticmethod
    def _non_negative_int(value, field):
        text = str(value).strip()

        if text == "":
            return 0

        try:
            number = int(text)
        except ValueError as error:
            raise ValueError(
                f"{field} tam sayı olmalıdır."
            ) from error

        if number < 0:
            raise ValueError(
                f"{field} negatif olamaz."
            )

        return number
