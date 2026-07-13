    def ana_sayfa(self):
        self.show_page(
            "ANA SAYFA",
            "REDBOX Gıda 2026 operasyon kontrol merkezi"
        )

        yil = "2026"

        conn = get_connection()

        try:
            uretim_kayitlari = conn.execute("""
                SELECT
                    uretim_tarihi,
                    urun_lot_no,
                    net_uretim_kg
                FROM uretim
                ORDER BY id
            """).fetchall()

            paketleme_kayitlari = conn.execute("""
                SELECT
                    p.paketleme_tarihi,
                    p.paketlenen_kg,
                    p.paketleme_firesi_kg
                FROM paketleme p
                ORDER BY p.id
            """).fetchall()

            sevkiyat_kayitlari = conn.execute("""
                SELECT
                    s.id,
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.sevk_koli_adedi,
                    s.sevk_acik_paket_adedi,
                    COALESCE(
                        SUM(sk.sevk_kg),
                        0
                    ) AS toplam_kg
                FROM sevkiyat s
                LEFT JOIN sevkiyat_kalemleri sk
                  ON sk.sevkiyat_id = s.id
                GROUP BY
                    s.id,
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.sevk_koli_adedi,
                    s.sevk_acik_paket_adedi
                ORDER BY s.id
            """).fetchall()

            hammadde_stoklari = conn.execute("""
                SELECT
                    h.id,
                    h.ad,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN dk.kabul_durumu = 'KABUL'
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
                              ON dk2.id = uhl.depo_kabul_id
                            WHERE dk2.hammadde_id = h.id
                        ),
                        0
                    ) AS kalan_kg
                FROM hammaddeler h
                LEFT JOIN depo_kabul dk
                  ON dk.hammadde_id = h.id
                WHERE h.aktif = 1
                GROUP BY
                    h.id,
                    h.ad
                ORDER BY h.id
            """).fetchall()

            son_uretim = conn.execute("""
                SELECT
                    uretim_tarihi,
                    urun_lot_no,
                    net_uretim_kg
                FROM uretim
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            son_sevkiyat = conn.execute("""
                SELECT
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.sevk_koli_adedi,
                    s.sevk_acik_paket_adedi,
                    COALESCE(
                        SUM(sk.sevk_kg),
                        0
                    ) AS toplam_kg
                FROM sevkiyat s
                LEFT JOIN sevkiyat_kalemleri sk
                  ON sk.sevkiyat_id = s.id
                GROUP BY
                    s.id,
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.sevk_koli_adedi,
                    s.sevk_acik_paket_adedi
                ORDER BY s.id DESC
                LIMIT 1
            """).fetchone()

        finally:
            conn.close()

        def tarih_yili(tarih_text):
            try:
                return datetime.strptime(
                    tarih_text,
                    "%d.%m.%Y"
                ).strftime("%Y")
            except (ValueError, TypeError):
                return None

        yil_uretim_kg = sum(
            float(row["net_uretim_kg"] or 0)
            for row in uretim_kayitlari
            if tarih_yili(
                row["uretim_tarihi"]
            ) == yil
        )

        yil_paketleme = [
            row
            for row in paketleme_kayitlari
            if tarih_yili(
                row["paketleme_tarihi"]
            ) == yil
        ]

        yil_paketli_kg = sum(
            float(row["paketlenen_kg"] or 0)
            for row in yil_paketleme
        )

        yil_paket_fire_kg = sum(
            float(
                row["paketleme_firesi_kg"] or 0
            )
            for row in yil_paketleme
        )

        yil_sevkiyatlari = [
            row
            for row in sevkiyat_kayitlari
            if tarih_yili(
                row["sevkiyat_tarihi"]
            ) == yil
        ]

        yil_sevk_kg = sum(
            float(row["toplam_kg"] or 0)
            for row in yil_sevkiyatlari
        )

        yil_musteriler = {
            row["musteri"]
            for row in yil_sevkiyatlari
            if row["musteri"]
        }

        mamul_stoklar = mamul_stok_ozeti()

        stok_500_rows = [
            row
            for row in mamul_stoklar
            if row["ambalaj_gram"] == 500
        ]

        stok_2500_rows = [
            row
            for row in mamul_stoklar
            if row["ambalaj_gram"] == 2500
        ]

        stok_500_paket = sum(
            int(row["kalan_paket_adedi"] or 0)
            for row in stok_500_rows
        )

        stok_500_koli = sum(
            int(row["tam_koli"] or 0)
            for row in stok_500_rows
        )

        stok_500_acik = sum(
            int(row["acik_paket"] or 0)
            for row in stok_500_rows
        )

        stok_500_kg = sum(
            float(row["kalan_kg"] or 0)
            for row in stok_500_rows
        )

        stok_2500_paket = sum(
            int(row["kalan_paket_adedi"] or 0)
            for row in stok_2500_rows
        )

        stok_2500_koli = sum(
            int(row["tam_koli"] or 0)
            for row in stok_2500_rows
        )

        stok_2500_acik = sum(
            int(row["acik_paket"] or 0)
            for row in stok_2500_rows
        )

        stok_2500_kg = sum(
            float(row["kalan_kg"] or 0)
            for row in stok_2500_rows
        )

        toplam_mamul_kg = sum(
            float(row["kalan_kg"] or 0)
            for row in mamul_stoklar
        )

        aktif_stok_lotu = len(
            mamul_stoklar
        )

        ana = ctk.CTkScrollableFrame(
            self.content,
            label_text=""
        )
        ana.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30)
        )

        ctk.CTkLabel(
            ana,
            text="CANLI MAMUL DEPO STOKU",
            font=("Arial", 22, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 10)
        )

        mamul_cards = ctk.CTkFrame(
            ana,
            fg_color="transparent"
        )
        mamul_cards.pack(
            fill="x",
            padx=5,
            pady=(0, 15)
        )

        mamul_data = [
            (
                "500 g MAMUL",
                (
                    f"{stok_500_paket} paket\n"
                    f"{stok_500_kg:.3f} kg\n"
                    f"{stok_500_koli} koli + "
                    f"{stok_500_acik} açık"
                )
            ),
            (
                "2.5 kg MAMUL",
                (
                    f"{stok_2500_paket} paket\n"
                    f"{stok_2500_kg:.3f} kg\n"
                    f"{stok_2500_koli} koli + "
                    f"{stok_2500_acik} açık"
                )
            ),
            (
                "TOPLAM MAMUL STOK",
                f"{toplam_mamul_kg:.3f} kg"
            ),
            (
                "AKTİF STOK LOTU",
                str(aktif_stok_lotu)
            ),
        ]

        for baslik, deger in mamul_data:
            kart = ctk.CTkFrame(
                mamul_cards,
                height=150
            )
            kart.pack(
                side="left",
                fill="both",
                expand=True,
                padx=7
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=baslik,
                font=("Arial", 13, "bold")
            ).pack(
                pady=(22, 8)
            )

            ctk.CTkLabel(
                kart,
                text=deger,
                font=("Arial", 20, "bold"),
                justify="center"
            ).pack()

        ctk.CTkLabel(
            ana,
            text="2026 OPERASYON KPI",
            font=("Arial", 22, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(15, 10)
        )

        operasyon_cards = ctk.CTkFrame(
            ana,
            fg_color="transparent"
        )
        operasyon_cards.pack(
            fill="x",
            padx=5,
            pady=(0, 15)
        )

        operasyon_data = [
            (
                "NET ÜRETİM",
                f"{yil_uretim_kg:.3f} kg"
            ),
            (
                "PAKETLİ MAMUL",
                f"{yil_paketli_kg:.3f} kg"
            ),
            (
                "PAKETLEME FİRESİ",
                f"{yil_paket_fire_kg:.3f} kg"
            ),
            (
                "SEVKİYAT",
                f"{yil_sevk_kg:.3f} kg"
            ),
            (
                "SEVK NOKTASI",
                str(len(yil_musteriler))
            ),
        ]

        for baslik, deger in operasyon_data:
            kart = ctk.CTkFrame(
                operasyon_cards,
                height=125
            )
            kart.pack(
                side="left",
                fill="both",
                expand=True,
                padx=5
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=baslik,
                font=("Arial", 12, "bold")
            ).pack(
                pady=(22, 8)
            )

            ctk.CTkLabel(
                kart,
                text=deger,
                font=("Arial", 21, "bold")
            ).pack()

        alt = ctk.CTkFrame(
            ana,
            fg_color="transparent"
        )
        alt.pack(
            fill="x",
            padx=5,
            pady=(10, 15)
        )

        hareket = ctk.CTkFrame(alt)
        hareket.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(7, 4)
        )

        ctk.CTkLabel(
            hareket,
            text="SON OPERASYON HAREKETLERİ",
            font=("Arial", 18, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 15)
        )

        if son_uretim:
            son_uretim_metin = (
                "SON ÜRETİM\n"
                f'{son_uretim["uretim_tarihi"]} | '
                f'{son_uretim["urun_lot_no"]}\n'
                f'{son_uretim["net_uretim_kg"]:.3f} kg'
            )
        else:
            son_uretim_metin = (
                "SON ÜRETİM\n"
                "Üretim kaydı yok."
            )

        ctk.CTkLabel(
            hareket,
            text=son_uretim_metin,
            justify="left",
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18)
        )

        if son_sevkiyat:
            son_sevk_metin = (
                "SON SEVKİYAT\n"
                f'{son_sevkiyat["sevkiyat_tarihi"]} | '
                f'{son_sevkiyat["musteri"]}\n'
                f'{son_sevkiyat["sevk_koli_adedi"]} koli + '
                f'{son_sevkiyat["sevk_acik_paket_adedi"]} '
                f'açık paket | '
                f'{son_sevkiyat["toplam_kg"]:.3f} kg'
            )
        else:
            son_sevk_metin = (
                "SON SEVKİYAT\n"
                "Sevkiyat kaydı yok."
            )

        ctk.CTkLabel(
            hareket,
            text=son_sevk_metin,
            justify="left",
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

        kritik = ctk.CTkFrame(alt)
        kritik.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(4, 7)
        )

        ctk.CTkLabel(
            kritik,
            text="HAMMADDE STOK DURUMU",
            font=("Arial", 18, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 15)
        )

        if hammadde_stoklari:
            stok_satirlari = []

            for row in hammadde_stoklari:
                kalan = float(
                    row["kalan_kg"] or 0
                )

                if kalan <= 0:
                    durum = "STOK YOK"
                else:
                    durum = f"{kalan:.3f} kg"

                stok_satirlari.append(
                    f'{row["ad"]}: {durum}'
                )

            stok_metin = "\n".join(
                stok_satirlari
            )
        else:
            stok_metin = (
                "Hammadde stok kaydı bulunamadı."
            )

        ctk.CTkLabel(
            kritik,
            text=stok_metin,
            justify="left",
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )
