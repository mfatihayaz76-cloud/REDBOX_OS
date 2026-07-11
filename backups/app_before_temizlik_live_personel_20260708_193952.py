import customtkinter as ctk
import subprocess
from tkinter import messagebox
from datetime import datetime

from database.db import init_database, get_connection
from database.stock_engine import uretim_stok_isle
from database.finished_stock_engine import (
    mamul_stok_ozeti,
    ambalaj_stok_toplami,
    sevkiyat_stok_dus,
)

from database.report_engine import izlenebilirlik_pdf_olustur, geri_cagirma_pdf_olustur

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

init_database()


class RedboxOS(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("REDBOX OS")
        self.geometry("1380x820")
        self.minsize(1180, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=245, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX OS",
            font=("Arial", 28, "bold")
        ).grid(row=0, column=0, padx=25, pady=(35, 5))

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX GIDA",
            font=("Arial", 13)
        ).grid(row=1, column=0, padx=25, pady=(0, 30))

        menu = [
            ("ANA SAYFA", self.ana_sayfa),
            ("DEPO KABUL", self.depo_kabul),
            ("ÜRETİM", self.uretim),
            ("PAKETLEME", self.paketleme),
            ("STOK", self.stok),
            ("SEVKİYAT", self.sevkiyat),
            ("SEVKİYAT RAPORU", self.sevkiyat_raporu),
            ("İZLENEBİLİRLİK", self.izlenebilirlik),
            ("PERSONEL", self.personel),
            ("TEMİZLİK", self.temizlik),
        ]

        for index, (text, command) in enumerate(menu, start=2):
            ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=44,
                width=205,
                anchor="w",
                font=("Arial", 14, "bold")
            ).grid(row=index, column=0, padx=20, pady=5)

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX OS • ÇEKİRDEK v0.2",
            font=("Arial", 11)
        ).grid(row=11, column=0, padx=20, pady=20)

        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")

        self.ana_sayfa()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_page(self, title, subtitle):
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text=title,
            font=("Arial", 34, "bold")
        ).pack(anchor="w", padx=45, pady=(35, 5))

        ctk.CTkLabel(
            self.content,
            text=subtitle,
            font=("Arial", 16)
        ).pack(anchor="w", padx=45, pady=(0, 20))

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

    def uretim_kutle_dengesi_getir(
        self,
        parti_sayisi
    ):
        conn = get_connection()

        try:
            recete = conn.execute("""
                SELECT
                    id,
                    parti_teorik_kg
                FROM receteler
                WHERE aktif = 1
                ORDER BY id
                LIMIT 1
            """).fetchone()

            if recete is None:
                raise ValueError(
                    "Aktif reçete bulunamadı."
                )

            stoklu = conn.execute("""
                SELECT
                    COALESCE(
                        SUM(miktar_kg),
                        0
                    ) AS toplam
                FROM recete_kalemleri
                WHERE recete_id = ?
            """, (
                recete["id"],
            )).fetchone()["toplam"]

            su = conn.execute("""
                SELECT deger
                FROM sistem_ayarlari
                WHERE anahtar = ?
            """, (
                "PARTI_PROSES_SUYU_KG",
            )).fetchone()

            if su is None:
                raise ValueError(
                    "PARTI_PROSES_SUYU_KG "
                    "sistem ayarı bulunamadı."
                )

            stoklu_parti = float(stoklu)
            su_parti = float(su["deger"])
            teorik_parti = float(
                recete["parti_teorik_kg"]
            )

            hesaplanan_parti = (
                stoklu_parti
                + su_parti
            )

            if abs(
                hesaplanan_parti
                - teorik_parti
            ) >= 0.000001:
                raise ValueError(
                    "Reçete kütle dengesi hatalı. "
                    f"Stoklu: {stoklu_parti:.3f} kg, "
                    f"Su: {su_parti:.3f} kg, "
                    f"Toplam: {hesaplanan_parti:.3f} kg, "
                    f"Teorik: {teorik_parti:.3f} kg"
                )

            return {
                "stoklu_parti_kg":
                    stoklu_parti,
                "su_parti_kg":
                    su_parti,
                "teorik_parti_kg":
                    teorik_parti,
                "stoklu_toplam_kg":
                    stoklu_parti * parti_sayisi,
                "su_toplam_kg":
                    su_parti * parti_sayisi,
                "teorik_toplam_kg":
                    teorik_parti * parti_sayisi,
            }

        finally:
            conn.close()


    def stok(self):
        self.show_page(
            "STOK",
            "Lot bazlı canlı mamul depo ve ambalaj stok görünümü"
        )

        stoklar = mamul_stok_ozeti()

        aktif_stoklar = [
            row
            for row in stoklar
            if row["kalan_paket_adedi"] > 0
        ]

        toplam_500_paket = sum(
            row["kalan_paket_adedi"]
            for row in aktif_stoklar
            if row["ambalaj_gram"] == 500
        )

        toplam_2500_paket = sum(
            row["kalan_paket_adedi"]
            for row in aktif_stoklar
            if row["ambalaj_gram"] == 2500
        )

        toplam_500_kg = sum(
            float(row["kalan_kg"])
            for row in aktif_stoklar
            if row["ambalaj_gram"] == 500
        )

        toplam_2500_kg = sum(
            float(row["kalan_kg"])
            for row in aktif_stoklar
            if row["ambalaj_gram"] == 2500
        )

        toplam_mamul_kg = sum(
            float(row["kalan_kg"])
            for row in aktif_stoklar
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

        ozet_frame = ctk.CTkFrame(
            ana,
            fg_color="transparent"
        )
        ozet_frame.pack(
            fill="x",
            padx=5,
            pady=(5, 20)
        )

        ozet_data = [
            (
                "500 g MAMUL",
                (
                    f"{toplam_500_paket} paket\n"
                    f"{toplam_500_kg:.3f} kg"
                )
            ),
            (
                "2.5 kg MAMUL",
                (
                    f"{toplam_2500_paket} paket\n"
                    f"{toplam_2500_kg:.3f} kg"
                )
            ),
            (
                "TOPLAM MAMUL STOK",
                f"{toplam_mamul_kg:.3f} kg"
            ),
            (
                "AKTİF STOK LOTU",
                str(len(aktif_stoklar))
            ),
        ]

        for baslik, deger in ozet_data:
            kart = ctk.CTkFrame(
                ozet_frame,
                height=120
            )
            kart.pack(
                side="left",
                expand=True,
                fill="both",
                padx=6
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
                font=("Arial", 22, "bold")
            ).pack()

        ctk.CTkLabel(
            ana,
            text="LOT BAZLI MAMUL DEPO STOKU",
            font=("Arial", 22, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 12)
        )

        if not aktif_stoklar:
            bos_kart = ctk.CTkFrame(ana)
            bos_kart.pack(
                fill="x",
                padx=10,
                pady=5
            )

            ctk.CTkLabel(
                bos_kart,
                text="Aktif mamul depo stoku bulunmuyor.",
                font=("Arial", 16)
            ).pack(
                anchor="w",
                padx=20,
                pady=20
            )

            return

        for row in aktif_stoklar:
            ambalaj = (
                "500 g"
                if row["ambalaj_gram"] == 500
                else "2.5 kg"
                if row["ambalaj_gram"] == 2500
                else f'{row["ambalaj_gram"]} g'
            )

            kart = ctk.CTkFrame(ana)
            kart.pack(
                fill="x",
                padx=10,
                pady=6
            )

            ust = ctk.CTkFrame(
                kart,
                fg_color="transparent"
            )
            ust.pack(
                fill="x",
                padx=20,
                pady=(15, 5)
            )

            ctk.CTkLabel(
                ust,
                text=f'LOT {row["urun_lot_no"]}',
                font=("Arial", 19, "bold")
            ).pack(
                side="left"
            )

            ctk.CTkLabel(
                ust,
                text=ambalaj,
                font=("Arial", 17, "bold")
            ).pack(
                side="right"
            )

            bilgi = (
                f'MEVCUT STOK: '
                f'{row["kalan_paket_adedi"]} paket    |    '
                f'TAM KOLİ: {row["tam_koli"]}    |    '
                f'AÇIK PAKET: {row["acik_paket"]}    |    '
                f'STOK KG: {row["kalan_kg"]:.3f} kg'
            )

            ctk.CTkLabel(
                kart,
                text=bilgi,
                justify="left",
                font=("Arial", 15)
            ).pack(
                anchor="w",
                padx=20,
                pady=(5, 15)
            )


    def depo_kabul(self):
        self.show_page(
            "DEPO KABUL",
            "Hammadde kabul ve tedarikçi lot kayıtları"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        form = ctk.CTkFrame(ana_frame, width=410)
        form.pack(side="left", fill="y", padx=(10, 5), pady=10)
        form.pack_propagate(False)

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        ctk.CTkLabel(
            form,
            text="YENİ HAMMADDE KABULÜ",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        conn = get_connection()
        hammaddeler = conn.execute(
            "SELECT id, ad FROM hammaddeler WHERE aktif = 1 ORDER BY id"
        ).fetchall()
        conn.close()

        self.hammadde_map = {row["ad"]: row["id"] for row in hammaddeler}

        self.kabul_tarihi = self.form_entry(
            form, "Kabul Tarihi", datetime.now().strftime("%d.%m.%Y")
        )

        ctk.CTkLabel(form, text="Hammadde").pack(
            anchor="w", padx=25, pady=(5, 2)
        )
        self.hammadde_secim = ctk.CTkOptionMenu(
            form,
            values=list(self.hammadde_map.keys()),
            width=350
        )
        self.hammadde_secim.pack(padx=25, pady=(0, 8))

        ctk.CTkLabel(
            form,
            text="Tedarikçi"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        conn = get_connection()

        tedarikciler = conn.execute("""
            SELECT
                id,
                tedarikci_adi
            FROM tedarikciler
            WHERE aktif = 1
            ORDER BY tedarikci_adi
        """).fetchall()

        conn.close()

        self.tedarikci_map = {
            row["tedarikci_adi"]: row["id"]
            for row in tedarikciler
        }

        self.tedarikci = ctk.CTkComboBox(
            form,
            values=(
                list(self.tedarikci_map.keys())
                if self.tedarikci_map
                else [""]
            ),
            width=350
        )

        self.tedarikci.pack(
            padx=25,
            pady=(0, 5)
        )

        self.tedarikci.set("")

        self.lot_no = self.form_entry(form, "Tedarikçi Lot No")
        self.urt = self.form_entry(form, "Üretim Tarihi")
        self.skt = self.form_entry(form, "SKT / TETT")
        self.miktar = self.form_entry(form, "Miktar (kg)")
        self.aciklama = self.form_entry(form, "Açıklama")

        ctk.CTkButton(
            form,
            text="KABUL KAYDINI KAYDET",
            command=self.depo_kabul_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(padx=25, pady=(15, 8))

        ctk.CTkButton(
            form,
            text="FORMU TEMİZLE",
            command=self.depo_form_temizle,
            height=38,
            width=350,
            fg_color="gray35"
        ).pack(padx=25, pady=(0, 15))

        ctk.CTkLabel(
            liste,
            text="SON DEPO KABUL KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.kabul_liste_frame = ctk.CTkScrollableFrame(liste)
        self.kabul_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.depo_kabul_listele()

    def form_entry(self, parent, label, default=""):
        ctk.CTkLabel(parent, text=label).pack(
            anchor="w", padx=25, pady=(5, 2)
        )

        entry = ctk.CTkEntry(parent, width=350)
        entry.pack(padx=25, pady=(0, 5))

        if default:
            entry.insert(0, default)

        return entry

    def depo_kabul_kaydet(self):
        try:
            tarih = self.kabul_tarihi.get().strip()
            hammadde_adi = self.hammadde_secim.get().strip()
            tedarikci = self.tedarikci.get().strip()
            lot_no = self.lot_no.get().strip()
            urt = self.urt.get().strip()
            skt = self.skt.get().strip()
            miktar_text = self.miktar.get().strip().replace(",", ".")
            aciklama = self.aciklama.get().strip()

            if not tarih:
                raise ValueError("Kabul tarihi boş bırakılamaz.")

            if not hammadde_adi:
                raise ValueError("Hammadde seçilmelidir.")

            if not lot_no:
                raise ValueError("Tedarikçi lot numarası zorunludur.")

            if not miktar_text:
                raise ValueError("Miktar girilmelidir.")

            miktar_kg = float(miktar_text)

            if miktar_kg <= 0:
                raise ValueError("Miktar 0'dan büyük olmalıdır.")

            hammadde_id = self.hammadde_map[hammadde_adi]

            conn = get_connection()

            try:
                tekrar_lot = conn.execute("""
                    SELECT
                        dk.id,
                        dk.kabul_tarihi,
                        dk.tedarikci,
                        dk.miktar_kg
                    FROM depo_kabul dk
                    WHERE dk.hammadde_id = ?
                      AND UPPER(
                            TRIM(dk.tedarikci_lot_no)
                          ) = UPPER(TRIM(?))
                    ORDER BY dk.id DESC
                    LIMIT 1
                """, (
                    hammadde_id,
                    lot_no
                )).fetchone()

                if tekrar_lot:
                    devam = messagebox.askyesno(
                        "Tekrar Eden Hammadde Lotu",
                        (
                            "Bu hammadde ve tedarikçi lotu "
                            "daha önce kabul edilmiş.\n\n"
                            f'Önceki Kabul Tarihi: '
                            f'{tekrar_lot["kabul_tarihi"]}\n'
                            f'Tedarikçi: '
                            f'{tekrar_lot["tedarikci"] or "-"}\n'
                            f'Miktar: '
                            f'{tekrar_lot["miktar_kg"]:.3f} kg\n\n'
                            "Aynı tedarikçi lotundan yeni bir "
                            "depo kabulü ise DEVAM EDİN.\n"
                            "Yanlışlıkla tekrar giriş ise "
                            "HAYIR seçin."
                        )
                    )

                    if not devam:
                        return

                tedarikci_id = None

                if tedarikci:
                    tedarikci_karti = conn.execute("""
                        SELECT
                            id
                        FROM tedarikciler
                        WHERE UPPER(TRIM(tedarikci_adi)) =
                              UPPER(TRIM(?))
                        LIMIT 1
                    """, (
                        tedarikci,
                    )).fetchone()

                    if tedarikci_karti:
                        tedarikci_id = (
                            tedarikci_karti["id"]
                        )
                    else:
                        cursor = conn.execute("""
                            INSERT INTO tedarikciler (
                                tedarikci_adi,
                                aktif,
                                kayit_zamani
                            )
                            VALUES (?, 1, ?)
                        """, (
                            tedarikci,
                            datetime.now().isoformat(
                                timespec="seconds"
                            )
                        ))

                        tedarikci_id = cursor.lastrowid

                        print(
                            "TEDARIKCI KARTI ACILDI:",
                            tedarikci,
                            "| ID:",
                            tedarikci_id
                        )

                conn.execute("""
                    INSERT INTO depo_kabul (
                        kabul_tarihi,
                        hammadde_id,
                        tedarikci,
                        tedarikci_id,
                        tedarikci_lot_no,
                        uretim_tarihi,
                        skt_tett,
                        miktar_kg,
                        kabul_durumu,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        'KABUL', ?, ?
                    )
                """, (
                    tarih,
                    hammadde_id,
                    tedarikci,
                    tedarikci_id,
                    lot_no,
                    urt,
                    skt,
                    miktar_kg,
                    aciklama,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                ))

                conn.commit()

            except Exception as db_hata:
                conn.rollback()

                if (
                    "UNIQUE constraint failed: "
                    "uretim.urun_lot_no"
                    in str(db_hata)
                ):
                    raise ValueError(
                        "Bu ürün lot numarası daha önce "
                        "kullanılmıştır.\n\n"
                        "Her üretim kaydı için benzersiz "
                        "bir ürün lot numarası girilmelidir."
                    ) from db_hata

                raise

            finally:
                conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Hammadde kabul kaydı başarıyla kaydedildi."
            )

            self.depo_form_temizle()
            self.depo_kabul_listele()

        except ValueError as hata:
            messagebox.showerror("Kayıt Hatası", str(hata))

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Kayıt yapılamadı:\n{hata}"
            )

    def depo_form_temizle(self):
        alanlar = [
            self.tedarikci,
            self.lot_no,
            self.urt,
            self.skt,
            self.miktar,
            self.aciklama
        ]

        for alan in alanlar:
            alan.delete(0, "end")

    def depo_kabul_listele(self):
        for widget in self.kabul_liste_frame.winfo_children():
            widget.destroy()

        conn = get_connection()
        kayitlar = conn.execute("""
            SELECT
                dk.id,
                dk.kabul_tarihi,
                h.ad AS hammadde,
                dk.tedarikci,
                dk.tedarikci_lot_no,
                dk.miktar_kg
            FROM depo_kabul dk
            JOIN hammaddeler h ON h.id = dk.hammadde_id
            ORDER BY dk.id DESC
            LIMIT 100
        """).fetchall()
        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.kabul_liste_frame,
                text="Henüz depo kabul kaydı bulunmuyor."
            ).pack(pady=30)
            return

        for kayit in kayitlar:
            satir = ctk.CTkFrame(self.kabul_liste_frame)
            satir.pack(fill="x", padx=5, pady=4)

            bilgi = (
                f'{kayit["kabul_tarihi"]}  •  '
                f'{kayit["hammadde"]}\n'
                f'Lot: {kayit["tedarikci_lot_no"]}  •  '
                f'{kayit["miktar_kg"]:.3f} kg'
            )

            if kayit["tedarikci"]:
                bilgi += f'  •  {kayit["tedarikci"]}'

            ctk.CTkLabel(
                satir,
                text=bilgi,
                justify="left",
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=12,
                pady=10
            )

            ctk.CTkButton(
                satir,
                text="SİL",
                width=65,
                fg_color="gray35",
                command=lambda kayit_id=kayit["id"]:
                    self.depo_kabul_sil(kayit_id)
            ).pack(side="right", padx=10)

    def depo_kabul_sil(self, kayit_id):
        cevap = messagebox.askyesno(
            "Kayıt Silme",
            "Bu depo kabul kaydı silinsin mi?\n\n"
            "Bağlı üretim kaydı varsa sistem silmeye izin vermeyecektir."
        )

        if not cevap:
            return

        try:
            conn = get_connection()
            conn.execute(
                "DELETE FROM depo_kabul WHERE id = ?",
                (kayit_id,)
            )
            conn.commit()
            conn.close()

            self.depo_kabul_listele()

        except Exception as hata:
            messagebox.showerror(
                "Silme Hatası",
                f"Kayıt silinemedi:\n{hata}"
            )

    def uretim(self):
        self.show_page(
            "ÜRETİM",
            "Parti hesabı, üretim firesi ve ürün lot kayıtları"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        form = ctk.CTkScrollableFrame(
            ana_frame,
            width=410,
            label_text=""
        )
        form.pack(
            side="left",
            fill="y",
            padx=(10, 5),
            pady=10
        )

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(5, 10),
            pady=10
        )

        ctk.CTkLabel(
            form,
            text="YENİ ÜRETİM KAYDI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.uretim_tarihi = self.form_entry(
            form,
            "Üretim Tarihi",
            datetime.now().strftime("%d.%m.%Y")
        )

        self.urun_lot_no = self.form_entry(
            form,
            "Ürün Lot No"
        )

        self.parti_sayisi = self.form_entry(
            form,
            "Parti Sayısı"
        )

        self.parti_sayisi.bind(
            "<KeyRelease>",
            self.uretim_hesapla
        )

        self.uretim_firesi = self.form_entry(
            form,
            "Üretim Firesi (kg)",
            "0"
        )

        self.uretim_firesi.bind(
            "<KeyRelease>",
            self.uretim_hesapla
        )

        ctk.CTkLabel(
            form,
            text="ÜRETİM KÜTLE DENGESİ",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 2)
        )

        self.stoklu_hammadde_label = ctk.CTkLabel(
            form,
            text="STOKLU HAMMADDE: 0.000 kg",
            font=("Arial", 15, "bold")
        )
        self.stoklu_hammadde_label.pack(
            anchor="w",
            padx=25,
            pady=(3, 2)
        )

        self.proses_suyu_label = ctk.CTkLabel(
            form,
            text="PROSES SUYU: 0.000 kg",
            font=("Arial", 15, "bold")
        )
        self.proses_suyu_label.pack(
            anchor="w",
            padx=25,
            pady=2
        )

        ctk.CTkLabel(
            form,
            text="TEORİK ÜRETİM",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(12, 2)
        )

        self.teorik_label = ctk.CTkLabel(
            form,
            text="0.000 kg",
            font=("Arial", 24, "bold")
        )
        self.teorik_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            form,
            text="NET ÜRETİM",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        self.net_label = ctk.CTkLabel(
            form,
            text="0.000 kg",
            font=("Arial", 24, "bold")
        )
        self.net_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.uretim_aciklama = self.form_entry(
            form,
            "Açıklama"
        )

        ctk.CTkButton(
            form,
            text="ÜRETİM KAYDINI KAYDET",
            command=self.uretim_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(padx=25, pady=(15, 15))

        ctk.CTkLabel(
            liste,
            text="SON ÜRETİM KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.uretim_liste_frame = ctk.CTkScrollableFrame(liste)
        self.uretim_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.uretim_listele()

    def uretim_hesapla(self, event=None):
        try:
            parti_text = (
                self.parti_sayisi
                .get()
                .strip()
            )

            fire_text = (
                self.uretim_firesi
                .get()
                .strip()
                .replace(",", ".")
            )

            parti = (
                int(parti_text)
                if parti_text
                else 0
            )

            fire = (
                float(fire_text)
                if fire_text
                else 0.0
            )

            if parti < 0:
                raise ValueError(
                    "Parti sayısı negatif olamaz."
                )

            if fire < 0:
                raise ValueError(
                    "Üretim firesi negatif olamaz."
                )

            denge = (
                self.uretim_kutle_dengesi_getir(
                    parti
                )
            )

            stoklu = float(
                denge["stoklu_toplam_kg"]
            )

            proses_suyu = float(
                denge["su_toplam_kg"]
            )

            teorik = float(
                denge["teorik_toplam_kg"]
            )

            net = teorik - fire

            if net < 0:
                raise ValueError(
                    "Üretim firesi teorik "
                    "üretimden büyük olamaz."
                )

            self.stoklu_hammadde_label.configure(
                text=(
                    "STOKLU HAMMADDE: "
                    f"{stoklu:.3f} kg"
                )
            )

            self.proses_suyu_label.configure(
                text=(
                    "PROSES SUYU: "
                    f"{proses_suyu:.3f} kg"
                )
            )

            self.teorik_label.configure(
                text=f"{teorik:.3f} kg"
            )

            self.net_label.configure(
                text=f"{net:.3f} kg"
            )

        except ValueError:
            self.stoklu_hammadde_label.configure(
                text="STOKLU HAMMADDE: HATALI DEĞER"
            )

            self.proses_suyu_label.configure(
                text="PROSES SUYU: HATALI DEĞER"
            )

            self.teorik_label.configure(
                text="HATALI DEĞER"
            )

            self.net_label.configure(
                text="HATALI DEĞER"
            )

    def uretim_kaydet(self):
        try:
            tarih = self.uretim_tarihi.get().strip()
            lot_no = self.urun_lot_no.get().strip()
            parti_text = self.parti_sayisi.get().strip()
            fire_text = self.uretim_firesi.get().strip().replace(",", ".")
            aciklama = self.uretim_aciklama.get().strip()

            if not tarih:
                raise ValueError("Üretim tarihi boş bırakılamaz.")

            if not lot_no:
                raise ValueError("Ürün lot numarası zorunludur.")

            if not parti_text:
                raise ValueError("Parti sayısı girilmelidir.")

            parti = int(parti_text)
            fire = float(fire_text) if fire_text else 0.0

            if parti <= 0:
                raise ValueError("Parti sayısı 0'dan büyük olmalıdır.")

            if fire < 0:
                raise ValueError("Üretim firesi negatif olamaz.")

            conn_recete = get_connection()

            try:
                recete = conn_recete.execute("""
                    SELECT parti_teorik_kg
                    FROM receteler
                    WHERE aktif = 1
                    ORDER BY id DESC
                    LIMIT 1
                """).fetchone()
            finally:
                conn_recete.close()

            if recete is None:
                raise ValueError("Aktif üretim reçetesi bulunamadı.")

            parti_teorik_kg = float(recete["parti_teorik_kg"])
            teorik = parti * parti_teorik_kg
            net = teorik - fire

            if net < 0:
                raise ValueError(
                    "Üretim firesi teorik üretimden büyük olamaz."
                )

            conn = get_connection()

            try:
                conn.execute("BEGIN")

                cursor = conn.execute("""
                    INSERT INTO uretim (
                        uretim_tarihi,
                        urun_lot_no,
                        parti_sayisi,
                        teorik_uretim_kg,
                        uretim_firesi_kg,
                        net_uretim_kg,
                        personel_1,
                        personel_2,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    lot_no,
                    parti,
                    teorik,
                    fire,
                    net,
                    "Fatih Ayaz",
                    "Eda Ayaz",
                    aciklama,
                    datetime.now().isoformat(timespec="seconds")
                ))

                uretim_id = cursor.lastrowid

                uretim_stok_isle(
                    conn,
                    uretim_id,
                    parti
                )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Üretim kaydı, reçete ve hammadde lot tüketimleri başarıyla kaydedildi."
            )

            self.uretim()

        except ValueError as hata:
            messagebox.showerror(
                "Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Üretim kaydı yapılamadı:\n{hata}"
            )

    def uretim_listele(self):
        for widget in self.uretim_liste_frame.winfo_children():
            widget.destroy()

        conn = get_connection()

        kayitlar = conn.execute("""
            SELECT
                id,
                uretim_tarihi,
                urun_lot_no,
                parti_sayisi,
                teorik_uretim_kg,
                uretim_firesi_kg,
                net_uretim_kg
            FROM uretim
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()

        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.uretim_liste_frame,
                text="Henüz üretim kaydı bulunmuyor."
            ).pack(pady=30)
            return

        for kayit in kayitlar:
            satir = ctk.CTkFrame(
                self.uretim_liste_frame
            )
            satir.pack(
                fill="x",
                padx=5,
                pady=4
            )

            bilgi = (
                f'{kayit["uretim_tarihi"]}  •  '
                f'LOT {kayit["urun_lot_no"]}\n'
                f'{kayit["parti_sayisi"]} parti  •  '
                f'Teorik: {kayit["teorik_uretim_kg"]:.3f} kg  •  '
                f'Fire: {kayit["uretim_firesi_kg"]:.3f} kg  •  '
                f'Net: {kayit["net_uretim_kg"]:.3f} kg'
            )

            ctk.CTkLabel(
                satir,
                text=bilgi,
                justify="left",
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=12,
                pady=10
            )

            ctk.CTkButton(
                satir,
                text="SİL",
                width=65,
                fg_color="gray35",
                command=lambda kayit_id=kayit["id"]:
                    self.uretim_sil(kayit_id)
            ).pack(
                side="right",
                padx=10
            )

    def uretim_sil(self, kayit_id):
        cevap = messagebox.askyesno(
            "Üretim Kaydı Silme",
            "Bu üretim kaydı silinsin mi?\n\n"
            "Bağlı paketleme veya lot kaydı varsa "
            "sistem silmeye izin vermeyebilir."
        )

        if not cevap:
            return

        try:
            conn = get_connection()

            conn.execute(
                "DELETE FROM uretim WHERE id = ?",
                (kayit_id,)
            )

            conn.commit()
            conn.close()

            self.uretim_listele()

        except Exception as hata:
            messagebox.showerror(
                "Silme Hatası",
                f"Üretim kaydı silinemedi:\n{hata}"
            )

    def paketleme(self):
        self.show_page(
            "PAKETLEME",
            "Üretim lotuna bağlı 500 g ve 2.5 kg paketleme kayıtları"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30)
        )

        form = ctk.CTkScrollableFrame(
            ana_frame,
            width=410,
            label_text=""
        )
        form.pack(
            side="left",
            fill="y",
            padx=(10, 5),
            pady=10
        )

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(5, 10),
            pady=10
        )

        ctk.CTkLabel(
            form,
            text="YENİ PAKETLEME KAYDI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.paketleme_tarihi = self.form_entry(
            form,
            "Paketleme Tarihi",
            datetime.now().strftime("%d.%m.%Y")
        )

        ctk.CTkLabel(
            form,
            text="Üretim Lotu"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        conn = get_connection()

        uretimler = conn.execute("""
            SELECT
                id,
                urun_lot_no,
                net_uretim_kg
            FROM uretim
            ORDER BY id DESC
        """).fetchall()

        conn.close()

        self.paketleme_uretim_map = {
            f'{row["urun_lot_no"]} | {row["net_uretim_kg"]:.3f} kg':
            row["id"]
            for row in uretimler
        }

        lot_degerleri = list(
            self.paketleme_uretim_map.keys()
        )

        self.paketleme_lot_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=lot_degerleri if lot_degerleri else [""],
            command=self.paketleme_lot_degisti,
            state="readonly"
        )
        self.paketleme_lot_secim.pack(
            padx=25,
            pady=(0, 10)
        )
        self.paketleme_lot_secim.set("")

        self.paketleme_stok_label = ctk.CTkLabel(
            form,
            text=(
                "NET ÜRETİM: 0.000 kg\n"
                "PAKETLENEN: 0.000 kg\n"
                "PAKETLEME FİRESİ: 0.000 kg\n"
                "KALAN: 0.000 kg"
            ),
            justify="left",
            font=("Arial", 14, "bold")
        )
        self.paketleme_stok_label.pack(
            anchor="w",
            padx=25,
            pady=(5, 15)
        )

        ctk.CTkLabel(
            form,
            text="Ambalaj"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        self.ambalaj_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=["500 g", "2.5 kg"],
            command=self.paketleme_hesapla
        )
        self.ambalaj_secim.pack(
            padx=25,
            pady=(0, 5)
        )
        self.ambalaj_secim.set("500 g")

        self.paket_adedi = self.form_entry(
            form,
            "Paket Adedi"
        )

        self.paket_adedi.bind(
            "<KeyRelease>",
            self.paketleme_hesapla
        )

        self.koli_ici_adet = self.form_entry(
            form,
            "Koli İçi Paket Adedi"
        )

        self.koli_ici_adet.bind(
            "<KeyRelease>",
            self.paketleme_hesapla
        )

        self.paketleme_firesi = self.form_entry(
            form,
            "Paketleme Firesi (kg)",
            "0"
        )

        self.paketleme_firesi.bind(
            "<KeyRelease>",
            self.paketleme_hesapla
        )

        ctk.CTkLabel(
            form,
            text="BU KAYITTA PAKETLENEN",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 2)
        )

        self.paketlenen_kg_label = ctk.CTkLabel(
            form,
            text="0.000 kg",
            font=("Arial", 24, "bold")
        )
        self.paketlenen_kg_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.koli_ozet_label = ctk.CTkLabel(
            form,
            text=(
                "TAM KOLİ: 0\n"
                "AÇIK PAKET: 0"
            ),
            justify="left",
            font=("Arial", 14, "bold")
        )
        self.koli_ozet_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.paketleme_aciklama = self.form_entry(
            form,
            "Açıklama"
        )

        ctk.CTkButton(
            form,
            text="PAKETLEME KAYDINI KAYDET",
            command=self.paketleme_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(
            padx=25,
            pady=(15, 15)
        )

        ctk.CTkLabel(
            liste,
            text="SON PAKETLEME KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.paketleme_liste_frame = ctk.CTkScrollableFrame(
            liste
        )
        self.paketleme_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.paketleme_listele()


    def paketleme_lot_ozeti(self, uretim_id):
        conn = get_connection()

        try:
            sonuc = conn.execute("""
                SELECT
                    u.id,
                    u.urun_lot_no,
                    u.net_uretim_kg,
                    COALESCE(
                        SUM(p.paketlenen_kg),
                        0
                    ) AS paketlenen_kg,
                    COALESCE(
                        SUM(p.paketleme_firesi_kg),
                        0
                    ) AS paketleme_firesi_kg
                FROM uretim u
                LEFT JOIN paketleme p
                  ON p.uretim_id = u.id
                WHERE u.id = ?
                GROUP BY
                    u.id,
                    u.urun_lot_no,
                    u.net_uretim_kg
            """, (uretim_id,)).fetchone()

            if sonuc is None:
                raise ValueError(
                    "Üretim lotu bulunamadı."
                )

            net = float(
                sonuc["net_uretim_kg"]
            )
            paketlenen = float(
                sonuc["paketlenen_kg"]
            )
            fire = float(
                sonuc["paketleme_firesi_kg"]
            )
            kalan = net - paketlenen - fire

            return {
                "net": net,
                "paketlenen": paketlenen,
                "fire": fire,
                "kalan": kalan,
            }

        finally:
            conn.close()


    def paketleme_lot_degisti(self, secim=None):
        try:
            secim = (
                secim
                or self.paketleme_lot_secim.get().strip()
            )

            if not secim:
                return

            uretim_id = self.paketleme_uretim_map[
                secim
            ]

            ozet = self.paketleme_lot_ozeti(
                uretim_id
            )

            self.paketleme_stok_label.configure(
                text=(
                    f'NET ÜRETİM: {ozet["net"]:.3f} kg\n'
                    f'PAKETLENEN: {ozet["paketlenen"]:.3f} kg\n'
                    f'PAKETLEME FİRESİ: {ozet["fire"]:.3f} kg\n'
                    f'KALAN: {ozet["kalan"]:.3f} kg'
                )
            )

        except Exception as hata:
            self.paketleme_stok_label.configure(
                text=f"LOT BİLGİSİ ALINAMADI: {hata}"
            )


    def paketleme_hesapla(self, event=None):
        try:
            ambalaj = self.ambalaj_secim.get().strip()
            adet_text = self.paket_adedi.get().strip()
            koli_ici_text = self.koli_ici_adet.get().strip()

            adet = int(adet_text) if adet_text else 0
            koli_ici = (
                int(koli_ici_text)
                if koli_ici_text
                else 0
            )

            if adet < 0:
                raise ValueError(
                    "Paket adedi negatif olamaz."
                )

            if koli_ici < 0:
                raise ValueError(
                    "Koli içi adet negatif olamaz."
                )

            if ambalaj == "500 g":
                ambalaj_kg = 0.500
            elif ambalaj == "2.5 kg":
                ambalaj_kg = 2.500
            else:
                raise ValueError(
                    "Geçerli ambalaj seçilmelidir."
                )

            paketlenen_kg = adet * ambalaj_kg

            self.paketlenen_kg_label.configure(
                text=f"{paketlenen_kg:.3f} kg"
            )

            if koli_ici > 0:
                tam_koli = adet // koli_ici
                acik_paket = adet % koli_ici
            else:
                tam_koli = 0
                acik_paket = adet

            self.koli_ozet_label.configure(
                text=(
                    f"TAM KOLİ: {tam_koli}\n"
                    f"AÇIK PAKET: {acik_paket}"
                )
            )

        except ValueError:
            self.paketlenen_kg_label.configure(
                text="HATALI DEĞER"
            )
            self.koli_ozet_label.configure(
                text=(
                    "TAM KOLİ: HATALI\n"
                    "AÇIK PAKET: HATALI"
                )
            )


    def paketleme_kaydet(self):
        try:
            tarih = self.paketleme_tarihi.get().strip()
            lot_secim = self.paketleme_lot_secim.get().strip()
            ambalaj = self.ambalaj_secim.get().strip()
            adet_text = self.paket_adedi.get().strip()
            koli_ici_text = self.koli_ici_adet.get().strip()
            fire_text = (
                self.paketleme_firesi
                .get()
                .strip()
                .replace(",", ".")
            )
            aciklama = (
                self.paketleme_aciklama.get().strip()
            )

            if not tarih:
                raise ValueError(
                    "Paketleme tarihi boş bırakılamaz."
                )

            if lot_secim not in self.paketleme_uretim_map:
                raise ValueError(
                    "Geçerli üretim lotu seçilmelidir."
                )

            if not adet_text:
                raise ValueError(
                    "Paket adedi girilmelidir."
                )

            adet = int(adet_text)

            if adet <= 0:
                raise ValueError(
                    "Paket adedi 0'dan büyük olmalıdır."
                )

            if not koli_ici_text:
                raise ValueError(
                    "Koli içi paket adedi girilmelidir."
                )

            koli_ici = int(koli_ici_text)

            if koli_ici <= 0:
                raise ValueError(
                    "Koli içi paket adedi 0'dan büyük olmalıdır."
                )

            fire = float(fire_text) if fire_text else 0.0

            if fire < 0:
                raise ValueError(
                    "Paketleme firesi negatif olamaz."
                )

            if ambalaj == "500 g":
                ambalaj_gram = 500
            elif ambalaj == "2.5 kg":
                ambalaj_gram = 2500
            else:
                raise ValueError(
                    "Geçerli ambalaj seçilmelidir."
                )

            paketlenen_kg = (
                adet * ambalaj_gram / 1000
            )

            uretim_id = self.paketleme_uretim_map[
                lot_secim
            ]

            conn = get_connection()

            try:
                conn.execute("BEGIN IMMEDIATE")

                sonuc = conn.execute("""
                    SELECT
                        u.net_uretim_kg,
                        COALESCE(
                            SUM(p.paketlenen_kg),
                            0
                        ) AS paketlenen_kg,
                        COALESCE(
                            SUM(p.paketleme_firesi_kg),
                            0
                        ) AS fire_kg
                    FROM uretim u
                    LEFT JOIN paketleme p
                      ON p.uretim_id = u.id
                    WHERE u.id = ?
                    GROUP BY
                        u.id,
                        u.net_uretim_kg
                """, (uretim_id,)).fetchone()

                if sonuc is None:
                    raise ValueError(
                        "Üretim lotu bulunamadı."
                    )

                kalan = (
                    float(sonuc["net_uretim_kg"])
                    - float(sonuc["paketlenen_kg"])
                    - float(sonuc["fire_kg"])
                )

                toplam_hareket = paketlenen_kg + fire

                if toplam_hareket > kalan + 0.000001:
                    raise ValueError(
                        "Paketleme miktarı kalan ürünü aşıyor.\n"
                        f"Kalan ürün: {kalan:.3f} kg\n"
                        f"Bu kayıt: {toplam_hareket:.3f} kg"
                    )

                conn.execute("""
                    INSERT INTO paketleme (
                        paketleme_tarihi,
                        uretim_id,
                        ambalaj_gram,
                        paket_adedi,
                        koli_ici_adet,
                        paketlenen_kg,
                        paketleme_firesi_kg,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    uretim_id,
                    ambalaj_gram,
                    adet,
                    koli_ici,
                    paketlenen_kg,
                    fire,
                    aciklama,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                ))

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Paketleme kaydı başarıyla kaydedildi."
            )

            self.paketleme()

        except ValueError as hata:
            messagebox.showerror(
                "Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Paketleme kaydı yapılamadı:\n{hata}"
            )


    def paketleme_listele(self):
        for widget in (
            self.paketleme_liste_frame.winfo_children()
        ):
            widget.destroy()

        conn = get_connection()

        kayitlar = conn.execute("""
            SELECT
                p.id,
                p.paketleme_tarihi,
                u.urun_lot_no,
                p.ambalaj_gram,
                p.paket_adedi,
                p.koli_ici_adet,
                p.paketlenen_kg,
                p.paketleme_firesi_kg
            FROM paketleme p
            JOIN uretim u
              ON u.id = p.uretim_id
            ORDER BY p.id DESC
            LIMIT 100
        """).fetchall()

        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.paketleme_liste_frame,
                text="Henüz paketleme kaydı yok."
            ).pack(pady=20)
            return

        for kayit in kayitlar:
            kart = ctk.CTkFrame(
                self.paketleme_liste_frame
            )
            kart.pack(
                fill="x",
                padx=5,
                pady=5
            )

            ambalaj = (
                "500 g"
                if kayit["ambalaj_gram"] == 500
                else "2.5 kg"
                if kayit["ambalaj_gram"] == 2500
                else f'{kayit["ambalaj_gram"]} g'
            )

            koli_ici = kayit["koli_ici_adet"]

            if koli_ici and int(koli_ici) > 0:
                tam_koli = (
                    int(kayit["paket_adedi"])
                    // int(koli_ici)
                )
                acik_paket = (
                    int(kayit["paket_adedi"])
                    % int(koli_ici)
                )
                koli_bilgi = (
                    f"{tam_koli} koli + "
                    f"{acik_paket} açık paket"
                )
            else:
                koli_bilgi = "Koli bilgisi yok"

            metin = (
                f'{kayit["paketleme_tarihi"]} | '
                f'LOT {kayit["urun_lot_no"]}\n'
                f'{ambalaj} × {kayit["paket_adedi"]} adet | '
                f'{koli_bilgi}\n'
                f'{kayit["paketlenen_kg"]:.3f} kg | '
                f'Fire {kayit["paketleme_firesi_kg"]:.3f} kg'
            )

            ctk.CTkLabel(
                kart,
                text=metin,
                justify="left"
            ).pack(
                anchor="w",
                padx=15,
                pady=12
            )

    def sevkiyat(self):
        self.show_page(
            "SEVKİYAT",
            "Mamul depo stokundan koli ve paket bazlı sevkiyat"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30)
        )

        form = ctk.CTkScrollableFrame(
            ana_frame,
            width=410,
            label_text=""
        )
        form.pack(
            side="left",
            fill="y",
            padx=(10, 5),
            pady=10
        )

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(5, 10),
            pady=10
        )

        ctk.CTkLabel(
            form,
            text="YENİ SEVKİYAT KAYDI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.sevkiyat_tarihi = self.form_entry(
            form,
            "Sevkiyat Tarihi",
            datetime.now().strftime("%d.%m.%Y")
        )

        ctk.CTkLabel(
            form,
            text="Müşteri / Sevk Noktası"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        conn = get_connection()

        musteriler = conn.execute("""
            SELECT
                id,
                musteri_adi
            FROM musteriler
            WHERE aktif = 1
            ORDER BY musteri_adi
        """).fetchall()

        conn.close()

        self.sevkiyat_musteri_map = {
            row["musteri_adi"]: row["id"]
            for row in musteriler
        }

        self.sevkiyat_musteri = ctk.CTkComboBox(
            form,
            width=350,
            values=(
                list(self.sevkiyat_musteri_map.keys())
                if self.sevkiyat_musteri_map
                else [""]
            )
        )
        self.sevkiyat_musteri.pack(
            padx=25,
            pady=(0, 5)
        )
        self.sevkiyat_musteri.set("")

        self.sevkiyat_plaka = self.form_entry(
            form,
            "Araç Plaka"
        )

        self.sevkiyat_belge_no = self.form_entry(
            form,
            "İrsaliye / Belge No"
        )

        ctk.CTkLabel(
            form,
            text="Mamul Stok / Ürün Lotu"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        stoklar = [
            row
            for row in mamul_stok_ozeti()
            if row["kalan_paket_adedi"] > 0
        ]

        self.sevkiyat_stok_map = {}

        for row in stoklar:
            ambalaj = (
                "500 g"
                if row["ambalaj_gram"] == 500
                else "2.5 kg"
                if row["ambalaj_gram"] == 2500
                else f'{row["ambalaj_gram"]} g'
            )

            anahtar = (
                f'{row["urun_lot_no"]} | '
                f'{ambalaj} | '
                f'{row["kalan_paket_adedi"]} paket'
            )

            self.sevkiyat_stok_map[anahtar] = row

        stok_degerleri = list(
            self.sevkiyat_stok_map.keys()
        )

        self.sevkiyat_stok_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=(
                stok_degerleri
                if stok_degerleri
                else [""]
            ),
            command=self.sevkiyat_stok_degisti,
            state="readonly"
        )
        self.sevkiyat_stok_secim.pack(
            padx=25,
            pady=(0, 10)
        )
        self.sevkiyat_stok_secim.set("")

        self.sevkiyat_stok_label = ctk.CTkLabel(
            form,
            text=(
                "MEVCUT STOK: 0 paket\n"
                "TAM KOLİ: 0\n"
                "AÇIK PAKET: 0\n"
                "STOK KG: 0.000 kg"
            ),
            justify="left",
            font=("Arial", 14, "bold")
        )
        self.sevkiyat_stok_label.pack(
            anchor="w",
            padx=25,
            pady=(5, 15)
        )

        self.sevk_koli_adedi = self.form_entry(
            form,
            "Sevk Koli Adedi",
            "0"
        )
        self.sevk_koli_adedi.bind(
            "<KeyRelease>",
            self.sevkiyat_hesapla
        )

        self.sevk_acik_paket = self.form_entry(
            form,
            "Sevk Açık Paket Adedi",
            "0"
        )
        self.sevk_acik_paket.bind(
            "<KeyRelease>",
            self.sevkiyat_hesapla
        )

        ctk.CTkLabel(
            form,
            text="SEVKİYAT HESABI",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 2)
        )

        self.sevkiyat_hesap_label = ctk.CTkLabel(
            form,
            text=(
                "TOPLAM PAKET: 0\n"
                "SEVK KG: 0.000 kg"
            ),
            justify="left",
            font=("Arial", 20, "bold")
        )
        self.sevkiyat_hesap_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            form,
            text="Soğuk Zincir"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        self.soguk_zincir_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=["EVET", "HAYIR"],
            state="readonly"
        )
        self.soguk_zincir_secim.pack(
            padx=25,
            pady=(0, 5)
        )
        self.soguk_zincir_secim.set("EVET")

        self.sevkiyat_aciklama = self.form_entry(
            form,
            "Açıklama"
        )

        ctk.CTkButton(
            form,
            text="SEVKİYAT KAYDINI KAYDET",
            command=self.sevkiyat_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(
            padx=25,
            pady=(15, 15)
        )

        ctk.CTkLabel(
            liste,
            text="SON SEVKİYAT KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.sevkiyat_liste_frame = ctk.CTkScrollableFrame(
            liste
        )
        self.sevkiyat_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.sevkiyat_listele()


    def sevkiyat_stok_degisti(self, secim=None):
        try:
            secim = (
                secim
                or self.sevkiyat_stok_secim.get().strip()
            )

            if not secim:
                return

            stok = self.sevkiyat_stok_map[secim]

            self.sevkiyat_stok_label.configure(
                text=(
                    f'MEVCUT STOK: '
                    f'{stok["kalan_paket_adedi"]} paket\n'
                    f'TAM KOLİ: {stok["tam_koli"]}\n'
                    f'AÇIK PAKET: {stok["acik_paket"]}\n'
                    f'STOK KG: {stok["kalan_kg"]:.3f} kg'
                )
            )

            self.sevkiyat_hesapla()

        except Exception as hata:
            self.sevkiyat_stok_label.configure(
                text=f"STOK BİLGİSİ ALINAMADI: {hata}"
            )


    def sevkiyat_hesapla(self, event=None):
        try:
            secim = self.sevkiyat_stok_secim.get().strip()

            koli_text = self.sevk_koli_adedi.get().strip()
            acik_text = self.sevk_acik_paket.get().strip()

            koli = int(koli_text) if koli_text else 0
            acik = int(acik_text) if acik_text else 0

            if koli < 0 or acik < 0:
                raise ValueError(
                    "Sevkiyat miktarı negatif olamaz."
                )

            if secim not in self.sevkiyat_stok_map:
                toplam_paket = 0
                sevk_kg = 0.0
            else:
                stok = self.sevkiyat_stok_map[secim]

                koli_ici = stok["koli_ici_adet"]

                if koli > 0 and koli_ici <= 0:
                    raise ValueError(
                        "Bu stokta koli içi paket bilgisi yok."
                    )

                toplam_paket = (
                    koli * koli_ici
                    + acik
                )

                sevk_kg = (
                    toplam_paket
                    * stok["ambalaj_gram"]
                    / 1000
                )

            self.sevkiyat_hesap_label.configure(
                text=(
                    f"TOPLAM PAKET: {toplam_paket}\n"
                    f"SEVK KG: {sevk_kg:.3f} kg"
                )
            )

        except ValueError:
            self.sevkiyat_hesap_label.configure(
                text=(
                    "TOPLAM PAKET: HATALI\n"
                    "SEVK KG: HATALI"
                )
            )


    def sevkiyat_kaydet(self):
        try:
            tarih = self.sevkiyat_tarihi.get().strip()
            musteri = self.sevkiyat_musteri.get().strip()
            plaka = (
                self.sevkiyat_plaka
                .get()
                .strip()
                .upper()
            )
            belge_no = (
                self.sevkiyat_belge_no
                .get()
                .strip()
                .upper()
            )
            secim = self.sevkiyat_stok_secim.get().strip()

            koli_text = self.sevk_koli_adedi.get().strip()
            acik_text = self.sevk_acik_paket.get().strip()

            soguk_zincir_text = (
                self.soguk_zincir_secim.get().strip()
            )

            aciklama = (
                self.sevkiyat_aciklama.get().strip()
            )

            if not tarih:
                raise ValueError(
                    "Sevkiyat tarihi boş bırakılamaz."
                )

            if not musteri:
                raise ValueError(
                    "Müşteri adı zorunludur."
                )

            if secim not in self.sevkiyat_stok_map:
                raise ValueError(
                    "Geçerli mamul stok seçilmelidir."
                )

            koli = int(koli_text) if koli_text else 0
            acik = int(acik_text) if acik_text else 0

            if koli < 0 or acik < 0:
                raise ValueError(
                    "Sevkiyat miktarı negatif olamaz."
                )

            stok = self.sevkiyat_stok_map[secim]

            koli_ici = stok["koli_ici_adet"]

            if koli > 0 and koli_ici <= 0:
                raise ValueError(
                    "Seçilen stokta koli içi bilgisi yok."
                )

            toplam_paket = (
                koli * koli_ici
                + acik
            )

            if toplam_paket <= 0:
                raise ValueError(
                    "Sevk miktarı 0'dan büyük olmalıdır."
                )

            if toplam_paket > stok["kalan_paket_adedi"]:
                raise ValueError(
                    "Sevkiyat miktarı mamul depo stokunu aşıyor.\n"
                    f'Mevcut stok: '
                    f'{stok["kalan_paket_adedi"]} paket\n'
                    f'Sevk talebi: {toplam_paket} paket'
                )

            soguk_zincir = (
                1
                if soguk_zincir_text == "EVET"
                else 0
            )

            conn = get_connection()

            try:
                conn.execute("BEGIN IMMEDIATE")

                musteri_row = conn.execute("""
                    SELECT id
                    FROM musteriler
                    WHERE musteri_adi = ?
                """, (
                    musteri,
                )).fetchone()

                if musteri_row is None:
                    musteri_id = conn.execute("""
                        INSERT INTO musteriler (
                            musteri_adi,
                            aktif,
                            kayit_zamani
                        )
                        VALUES (?, 1, ?)
                    """, (
                        musteri,
                        datetime.now().isoformat(
                            timespec="seconds"
                        )
                    )).lastrowid
                else:
                    musteri_id = musteri_row["id"]

                sevkiyat_id = conn.execute("""
                    INSERT INTO sevkiyat (
                        sevkiyat_tarihi,
                        musteri,
                        musteri_id,
                        arac_plaka,
                        belge_no,
                        sevk_koli_adedi,
                        sevk_acik_paket_adedi,
                        soguk_zincir,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    musteri,
                    musteri_id,
                    plaka,
                    belge_no,
                    koli,
                    acik,
                    soguk_zincir,
                    aciklama,
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )).lastrowid

                sevkiyat_stok_dus(
                    conn=conn,
                    sevkiyat_id=sevkiyat_id,
                    uretim_id=stok["uretim_id"],
                    ambalaj_gram=stok["ambalaj_gram"],
                    paket_adedi=toplam_paket
                )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Sevkiyat kaydı başarıyla kaydedildi."
            )

            self.sevkiyat()

        except ValueError as hata:
            messagebox.showerror(
                "Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Sevkiyat kaydı yapılamadı:\n{hata}"
            )


    def sevkiyat_listele(self):
        for widget in (
            self.sevkiyat_liste_frame.winfo_children()
        ):
            widget.destroy()

        conn = get_connection()

        kayitlar = conn.execute("""
            SELECT
                s.id,
                s.sevkiyat_tarihi,
                s.musteri,
                s.arac_plaka,
                s.belge_no,
                s.soguk_zincir,
                s.aciklama,
                SUM(sk.paket_adedi) AS toplam_paket,
                SUM(sk.sevk_kg) AS toplam_kg,
                COUNT(DISTINCT u.urun_lot_no) AS lot_sayisi
            FROM sevkiyat s
            JOIN sevkiyat_kalemleri sk
              ON sk.sevkiyat_id = s.id
            JOIN paketleme p
              ON p.id = sk.paketleme_id
            JOIN uretim u
              ON u.id = p.uretim_id
            GROUP BY
                s.id,
                s.sevkiyat_tarihi,
                s.musteri,
                s.arac_plaka,
                s.belge_no,
                s.soguk_zincir,
                s.aciklama
            ORDER BY s.id DESC
            LIMIT 100
        """).fetchall()

        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.sevkiyat_liste_frame,
                text="Henüz sevkiyat kaydı yok."
            ).pack(pady=20)
            return

        for kayit in kayitlar:
            kart = ctk.CTkFrame(
                self.sevkiyat_liste_frame
            )
            kart.pack(
                fill="x",
                padx=5,
                pady=5
            )

            soguk = (
                "EVET"
                if kayit["soguk_zincir"]
                else "HAYIR"
            )

            plaka = (
                kayit["arac_plaka"]
                if kayit["arac_plaka"]
                else "-"
            )

            belge_no = (
                kayit["belge_no"]
                if kayit["belge_no"]
                else "-"
            )

            metin = (
                f'{kayit["sevkiyat_tarihi"]} | '
                f'{kayit["musteri"]}\n'
                f'{kayit["toplam_paket"]} paket | '
                f'{kayit["toplam_kg"]:.3f} kg | '
                f'{kayit["lot_sayisi"]} lot\n'
                f'Araç Plaka: {plaka}\n'
                f'Belge No: {belge_no}\n'
                f'Soğuk Zincir: {soguk}'
            )

            ctk.CTkLabel(
                kart,
                text=metin,
                justify="left"
            ).pack(
                anchor="w",
                padx=15,
                pady=12
            )

    def sevkiyat_raporu(self):
        self.show_page(
            "SEVKİYAT RAPORU",
            "Tarih aralığı ve müşteri bazlı sevkiyat analizi"
        )

        filtre = ctk.CTkFrame(self.content)
        filtre.pack(
            fill="x",
            padx=40,
            pady=(0, 10)
        )

        self.rapor_baslangic = self.form_entry(
            filtre,
            "Başlangıç Tarihi",
            "01.01.2026"
        )

        self.rapor_bitis = self.form_entry(
            filtre,
            "Bitiş Tarihi",
            datetime.now().strftime("%d.%m.%Y")
        )

        conn = get_connection()

        musteriler = conn.execute("""
            SELECT
                id,
                musteri_adi
            FROM musteriler
            WHERE aktif = 1
            ORDER BY musteri_adi
        """).fetchall()

        conn.close()

        self.rapor_musteri_map = {
            row["musteri_adi"]: row["id"]
            for row in musteriler
        }

        ctk.CTkLabel(
            filtre,
            text="Müşteri"
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2)
        )

        musteri_degerleri = [
            "TÜMÜ",
            *self.rapor_musteri_map.keys()
        ]

        self.rapor_musteri_secim = ctk.CTkComboBox(
            filtre,
            width=350,
            values=musteri_degerleri,
            state="readonly"
        )
        self.rapor_musteri_secim.pack(
            padx=25,
            pady=(0, 10)
        )
        self.rapor_musteri_secim.set("TÜMÜ")

        ctk.CTkButton(
            filtre,
            text="RAPORU GETİR",
            command=self.sevkiyat_raporu_getir,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(
            padx=25,
            pady=(10, 15)
        )

        self.sevkiyat_rapor_sonuc = ctk.CTkScrollableFrame(
            self.content
        )
        self.sevkiyat_rapor_sonuc.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30)
        )


    def sevkiyat_raporu_getir(self):
        try:
            baslangic_text = (
                self.rapor_baslangic.get().strip()
            )
            bitis_text = (
                self.rapor_bitis.get().strip()
            )
            musteri_secim = (
                self.rapor_musteri_secim.get().strip()
            )

            try:
                baslangic = datetime.strptime(
                    baslangic_text,
                    "%d.%m.%Y"
                )
                bitis = datetime.strptime(
                    bitis_text,
                    "%d.%m.%Y"
                )
            except ValueError:
                raise ValueError(
                    "Tarihler GG.AA.YYYY formatında olmalıdır."
                )

            if baslangic > bitis:
                raise ValueError(
                    "Başlangıç tarihi bitiş tarihinden "
                    "sonra olamaz."
                )

            for widget in (
                self.sevkiyat_rapor_sonuc.winfo_children()
            ):
                widget.destroy()

            conn = get_connection()

            try:
                sevkiyatlar = conn.execute("""
                    SELECT
                        s.id,
                        s.sevkiyat_tarihi,
                        s.musteri,
                        s.musteri_id,
                        s.arac_plaka,
                        s.belge_no,
                        s.sevk_koli_adedi,
                        s.sevk_acik_paket_adedi,
                        s.soguk_zincir,
                        COALESCE(
                            SUM(sk.paket_adedi),
                            0
                        ) AS toplam_paket,
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
                        s.musteri_id,
                        s.arac_plaka,
                        s.belge_no,
                        s.sevk_koli_adedi,
                        s.sevk_acik_paket_adedi,
                        s.soguk_zincir
                    ORDER BY s.id
                """).fetchall()

                detaylar = conn.execute("""
                    SELECT
                        s.id AS sevkiyat_id,
                        u.urun_lot_no,
                        p.ambalaj_gram,
                        p.koli_ici_adet,
                        sk.paket_adedi,
                        sk.sevk_kg
                    FROM sevkiyat_kalemleri sk
                    JOIN sevkiyat s
                      ON s.id = sk.sevkiyat_id
                    JOIN paketleme p
                      ON p.id = sk.paketleme_id
                    JOIN uretim u
                      ON u.id = p.uretim_id
                    ORDER BY
                        s.id,
                        sk.id
                """).fetchall()

            finally:
                conn.close()

            detay_map = {}

            for row in detaylar:
                detay_map.setdefault(
                    row["sevkiyat_id"],
                    []
                ).append(row)

            filtreli = []

            for row in sevkiyatlar:
                try:
                    tarih = datetime.strptime(
                        row["sevkiyat_tarihi"],
                        "%d.%m.%Y"
                    )
                except ValueError:
                    continue

                if not (
                    baslangic <= tarih <= bitis
                ):
                    continue

                if (
                    musteri_secim != "TÜMÜ"
                    and row["musteri"] != musteri_secim
                ):
                    continue

                filtreli.append(row)

            if not filtreli:
                ctk.CTkLabel(
                    self.sevkiyat_rapor_sonuc,
                    text=(
                        "Seçilen tarih aralığında "
                        "sevkiyat kaydı bulunamadı."
                    ),
                    font=("Arial", 16, "bold")
                ).pack(pady=30)

                return

            toplam_sevkiyat = len(filtreli)

            musteri_adlari = {
                row["musteri"]
                for row in filtreli
            }

            toplam_koli = sum(
                int(row["sevk_koli_adedi"] or 0)
                for row in filtreli
            )

            toplam_acik = sum(
                int(
                    row[
                        "sevk_acik_paket_adedi"
                    ] or 0
                )
                for row in filtreli
            )

            toplam_paket = sum(
                int(row["toplam_paket"] or 0)
                for row in filtreli
            )

            toplam_kg = sum(
                float(row["toplam_kg"] or 0)
                for row in filtreli
            )

            ctk.CTkLabel(
                self.sevkiyat_rapor_sonuc,
                text="RAPOR ÖZETİ",
                font=("Arial", 22, "bold")
            ).pack(
                anchor="w",
                padx=15,
                pady=(15, 10)
            )

            ozet = ctk.CTkFrame(
                self.sevkiyat_rapor_sonuc
            )
            ozet.pack(
                fill="x",
                padx=10,
                pady=(0, 15)
            )

            ozet_metin = (
                f"SEVKİYAT SAYISI: {toplam_sevkiyat}\n"
                f"SEVK EDİLEN NOKTA: "
                f"{len(musteri_adlari)}\n"
                f"TOPLAM KOLİ: {toplam_koli}\n"
                f"AÇIK PAKET: {toplam_acik}\n"
                f"TOPLAM PAKET: {toplam_paket}\n"
                f"TOPLAM KG: {toplam_kg:.3f} kg"
            )

            ctk.CTkLabel(
                ozet,
                text=ozet_metin,
                justify="left",
                font=("Arial", 17, "bold")
            ).pack(
                anchor="w",
                padx=20,
                pady=15
            )

            ctk.CTkLabel(
                self.sevkiyat_rapor_sonuc,
                text="MÜŞTERİ / SEVK NOKTASI SONUÇLARI",
                font=("Arial", 22, "bold")
            ).pack(
                anchor="w",
                padx=15,
                pady=(10, 10)
            )

            musteri_gruplari = {}

            for row in filtreli:
                musteri_gruplari.setdefault(
                    row["musteri"],
                    []
                ).append(row)

            for musteri, kayitlar in sorted(
                musteri_gruplari.items()
            ):
                tarihler = [
                    datetime.strptime(
                        row["sevkiyat_tarihi"],
                        "%d.%m.%Y"
                    )
                    for row in kayitlar
                ]

                musteri_koli = sum(
                    int(
                        row["sevk_koli_adedi"] or 0
                    )
                    for row in kayitlar
                )

                musteri_acik = sum(
                    int(
                        row[
                            "sevk_acik_paket_adedi"
                        ] or 0
                    )
                    for row in kayitlar
                )

                musteri_paket = sum(
                    int(row["toplam_paket"] or 0)
                    for row in kayitlar
                )

                musteri_kg = sum(
                    float(row["toplam_kg"] or 0)
                    for row in kayitlar
                )

                ambalaj_toplam = {}
                lotlar = set()

                for row in kayitlar:
                    for detay in detay_map.get(
                        row["id"],
                        []
                    ):
                        gram = detay["ambalaj_gram"]

                        ambalaj_toplam[gram] = (
                            ambalaj_toplam.get(
                                gram,
                                0
                            )
                            + int(
                                detay["paket_adedi"]
                            )
                        )

                        lotlar.add(
                            detay["urun_lot_no"]
                        )

                ambalaj_satirlari = []

                for gram, adet in sorted(
                    ambalaj_toplam.items()
                ):
                    ambalaj = (
                        "500 g"
                        if gram == 500
                        else "2.5 kg"
                        if gram == 2500
                        else f"{gram} g"
                    )

                    ambalaj_satirlari.append(
                        f"{ambalaj} PAKET: {adet}"
                    )

                kart = ctk.CTkFrame(
                    self.sevkiyat_rapor_sonuc
                )
                kart.pack(
                    fill="x",
                    padx=10,
                    pady=5
                )

                metin = (
                    f"{musteri}\n"
                    f"İlk Sevkiyat: "
                    f"{min(tarihler).strftime('%d.%m.%Y')}\n"
                    f"Son Sevkiyat: "
                    f"{max(tarihler).strftime('%d.%m.%Y')}\n"
                    f"Sevkiyat Sayısı: {len(kayitlar)}\n"
                    f"Toplam Koli: {musteri_koli}\n"
                    f"Açık Paket: {musteri_acik}\n"
                    f"Toplam Paket: {musteri_paket}\n"
                    + "\n".join(ambalaj_satirlari)
                    + "\n"
                    f"Toplam Kg: {musteri_kg:.3f} kg\n"
                    f"Lotlar: "
                    f"{', '.join(sorted(lotlar))}"
                )

                ctk.CTkLabel(
                    kart,
                    text=metin,
                    justify="left",
                    font=("Arial", 14)
                ).pack(
                    anchor="w",
                    padx=20,
                    pady=15
                )

            ctk.CTkLabel(
                self.sevkiyat_rapor_sonuc,
                text="SEVKİYAT DETAYLARI",
                font=("Arial", 22, "bold")
            ).pack(
                anchor="w",
                padx=15,
                pady=(20, 10)
            )

            for row in sorted(
                filtreli,
                key=lambda x: datetime.strptime(
                    x["sevkiyat_tarihi"],
                    "%d.%m.%Y"
                ),
                reverse=True
            ):
                sevk_detaylari = detay_map.get(
                    row["id"],
                    []
                )

                detay_satirlari = []

                for detay in sevk_detaylari:
                    gram = detay["ambalaj_gram"]

                    ambalaj = (
                        "500 g"
                        if gram == 500
                        else "2.5 kg"
                        if gram == 2500
                        else f"{gram} g"
                    )

                    detay_satirlari.append(
                        f'Lot {detay["urun_lot_no"]} | '
                        f'{ambalaj} | '
                        f'{detay["paket_adedi"]} paket | '
                        f'{detay["sevk_kg"]:.3f} kg'
                    )

                plaka = (
                    row["arac_plaka"]
                    if row["arac_plaka"]
                    else "-"
                )

                belge = (
                    row["belge_no"]
                    if row["belge_no"]
                    else "-"
                )

                soguk = (
                    "EVET"
                    if row["soguk_zincir"]
                    else "HAYIR"
                )

                kart = ctk.CTkFrame(
                    self.sevkiyat_rapor_sonuc
                )
                kart.pack(
                    fill="x",
                    padx=10,
                    pady=5
                )

                metin = (
                    f'{row["sevkiyat_tarihi"]} | '
                    f'{row["musteri"]}\n'
                    f'{row["sevk_koli_adedi"]} koli + '
                    f'{row["sevk_acik_paket_adedi"]} '
                    f'açık paket\n'
                    f'Araç Plaka: {plaka} | '
                    f'Belge No: {belge}\n'
                    f'Soğuk Zincir: {soguk}\n'
                    + "\n".join(detay_satirlari)
                )

                ctk.CTkLabel(
                    kart,
                    text=metin,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=20,
                    pady=15
                )

        except ValueError as hata:
            messagebox.showerror(
                "Rapor Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Sevkiyat raporu oluşturulamadı:\n{hata}"
            )


    def izlenebilirlik(self):
        self.show_page(
            "İZLENEBİLİRLİK",
            "Ürün lotundan hammaddeye ve müşteriye tam lot zinciri"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30)
        )

        ust = ctk.CTkFrame(ana_frame)
        ust.pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        ctk.CTkLabel(
            ust,
            text="ÜRÜN LOTU",
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 5)
        )

        conn = get_connection()

        lotlar = conn.execute("""
            SELECT
                id,
                urun_lot_no,
                uretim_tarihi,
                net_uretim_kg
            FROM uretim
            ORDER BY id DESC
        """).fetchall()

        conn.close()

        self.izlenebilirlik_lot_map = {}

        for row in lotlar:
            anahtar = (
                f'{row["urun_lot_no"]} | '
                f'{row["uretim_tarihi"]} | '
                f'{row["net_uretim_kg"]:.3f} kg'
            )

            self.izlenebilirlik_lot_map[
                anahtar
            ] = row["id"]

        lot_degerleri = list(
            self.izlenebilirlik_lot_map.keys()
        )

        self.izlenebilirlik_lot_secim = ctk.CTkComboBox(
            ust,
            width=500,
            values=(
                lot_degerleri
                if lot_degerleri
                else [""]
            ),
            state="readonly"
        )

        self.izlenebilirlik_lot_secim.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.izlenebilirlik_lot_secim.set("")

        ctk.CTkButton(
            ust,
            text="ÜRÜN LOTUNDAN İLERİ İZLE",
            command=self.izlenebilirlik_getir,
            width=500,
            height=45,
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 20)
        )

        ctk.CTkLabel(
            ust,
            text="HAMMADDE LOTU / GERİ ÇAĞIRMA İZİ",
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 5)
        )

        conn = get_connection()

        hammadde_lotlari = conn.execute("""
            SELECT
                dk.id,
                h.ad AS hammadde,
                dk.tedarikci_lot_no,
                dk.kabul_tarihi,
                dk.tedarikci
            FROM depo_kabul dk
            JOIN hammaddeler h
              ON h.id = dk.hammadde_id
            ORDER BY dk.id DESC
        """).fetchall()

        conn.close()

        self.geri_cagirma_lot_map = {}

        for row in hammadde_lotlari:
            anahtar = (
                f'{row["hammadde"]} | '
                f'LOT: {row["tedarikci_lot_no"]} | '
                f'{row["kabul_tarihi"]}'
            )

            self.geri_cagirma_lot_map[
                anahtar
            ] = row["id"]

        geri_lot_degerleri = list(
            self.geri_cagirma_lot_map.keys()
        )

        self.geri_cagirma_lot_secim = ctk.CTkComboBox(
            ust,
            width=500,
            values=(
                geri_lot_degerleri
                if geri_lot_degerleri
                else [""]
            ),
            state="readonly"
        )

        self.geri_cagirma_lot_secim.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.geri_cagirma_lot_secim.set("")

        ctk.CTkButton(
            ust,
            text="HAMMADDE LOTUNDAN GERİ ÇAĞIRMA İZİNİ GETİR",
            command=self.geri_cagirma_izi_getir,
            width=500,
            height=45,
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 20)
        )

        ctk.CTkButton(
            ust,
            text="İZLENEBİLİRLİK PDF RAPORU OLUŞTUR",
            command=self.izlenebilirlik_pdf_raporu,
            width=500,
            height=45,
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 20)
        )

        ctk.CTkButton(
            ust,
            text="GERİ ÇAĞIRMA PDF RAPORU OLUŞTUR",
            command=self.geri_cagirma_pdf_raporu,
            width=500,
            height=45,
            font=("Arial", 14, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 20)
        )

        self.izlenebilirlik_sonuc_frame = (
            ctk.CTkScrollableFrame(
                ana_frame
            )
        )

        self.izlenebilirlik_sonuc_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(5, 10)
        )

        ctk.CTkLabel(
            self.izlenebilirlik_sonuc_frame,
            text=(
                "İzlenebilirlik zincirini görmek için "
                "bir ürün lotu seçin."
            ),
            font=("Arial", 16)
        ).pack(
            pady=30
        )


    def izlenebilirlik_getir(self):
        try:
            secim = (
                self.izlenebilirlik_lot_secim
                .get()
                .strip()
            )

            if (
                secim
                not in self.izlenebilirlik_lot_map
            ):
                raise ValueError(
                    "Geçerli ürün lotu seçilmelidir."
                )

            uretim_id = (
                self.izlenebilirlik_lot_map[
                    secim
                ]
            )

            for widget in (
                self.izlenebilirlik_sonuc_frame
                .winfo_children()
            ):
                widget.destroy()

            conn = get_connection()

            try:
                uretim = conn.execute("""
                    SELECT
                        u.*,
                        r.ad AS recete_adi
                    FROM uretim u
                    LEFT JOIN uretim_recete ur
                      ON ur.uretim_id = u.id
                    LEFT JOIN receteler r
                      ON r.id = ur.recete_id
                    WHERE u.id = ?
                """, (
                    uretim_id,
                )).fetchone()

                hammaddeler = conn.execute("""
                    SELECT
                        h.ad AS hammadde_adi,
                        dk.tedarikci,
                        dk.tedarikci_lot_no,
                        dk.uretim_tarihi,
                        dk.skt_tett,
                        uhl.kullanilan_miktar_kg
                    FROM uretim_hammadde_lotlari uhl
                    JOIN depo_kabul dk
                      ON dk.id = uhl.depo_kabul_id
                    JOIN hammaddeler h
                      ON h.id = dk.hammadde_id
                    WHERE uhl.uretim_id = ?
                    ORDER BY
                        h.id,
                        dk.id
                """, (
                    uretim_id,
                )).fetchall()

                paketlemeler = conn.execute("""
                    SELECT
                        p.id,
                        p.paketleme_tarihi,
                        p.ambalaj_gram,
                        p.paket_adedi,
                        p.koli_ici_adet,
                        p.paketlenen_kg,
                        p.paketleme_firesi_kg
                    FROM paketleme p
                    WHERE p.uretim_id = ?
                    ORDER BY p.id
                """, (
                    uretim_id,
                )).fetchall()

                sevkiyatlar = conn.execute("""
                    SELECT
                        s.id,
                        s.sevkiyat_tarihi,
                        s.musteri,
                        s.arac_plaka,
                        s.belge_no,
                        s.soguk_zincir,
                        SUM(sk.paket_adedi)
                            AS toplam_paket,
                        SUM(sk.sevk_kg)
                            AS toplam_kg
                    FROM sevkiyat s
                    JOIN sevkiyat_kalemleri sk
                      ON sk.sevkiyat_id = s.id
                    JOIN paketleme p
                      ON p.id = sk.paketleme_id
                    WHERE p.uretim_id = ?
                    GROUP BY
                        s.id,
                        s.sevkiyat_tarihi,
                        s.musteri,
                        s.arac_plaka,
                        s.belge_no,
                        s.soguk_zincir
                    ORDER BY s.id
                """, (
                    uretim_id,
                )).fetchall()

            finally:
                conn.close()

            if not uretim:
                raise ValueError(
                    "Üretim kaydı bulunamadı."
                )

            self.izlenebilirlik_baslik(
                "1. ÜRÜN LOTU VE ÜRETİM"
            )

            uretim_metin = (
                f'ÜRÜN LOTU: '
                f'{uretim["urun_lot_no"]}\n'
                f'ÜRETİM TARİHİ: '
                f'{uretim["uretim_tarihi"]}\n'
                f'REÇETE: '
                f'{uretim["recete_adi"] or "-"}\n'
                f'PARTİ SAYISI: '
                f'{uretim["parti_sayisi"]}\n'
                f'TEORİK ÜRETİM: '
                f'{uretim["teorik_uretim_kg"]:.3f} kg\n'
                f'ÜRETİM FİRESİ: '
                f'{uretim["uretim_firesi_kg"]:.3f} kg\n'
                f'NET ÜRETİM: '
                f'{uretim["net_uretim_kg"]:.3f} kg\n'
                f'PERSONEL: '
                f'{uretim["personel_1"] or "-"} / '
                f'{uretim["personel_2"] or "-"}'
            )

            self.izlenebilirlik_kart(
                uretim_metin
            )

            self.izlenebilirlik_baslik(
                "2. HAMMADDE LOT ZİNCİRİ"
            )

            if hammaddeler:
                for row in hammaddeler:
                    metin = (
                        f'{row["hammadde_adi"]}\n'
                        f'Tedarikçi: '
                        f'{row["tedarikci"] or "-"}\n'
                        f'Tedarikçi Lot No: '
                        f'{row["tedarikci_lot_no"]}\n'
                        f'ÜRT: '
                        f'{row["uretim_tarihi"] or "-"} | '
                        f'SKT/TETT: '
                        f'{row["skt_tett"] or "-"}\n'
                        f'Kullanılan: '
                        f'{row["kullanilan_miktar_kg"]:.3f} kg'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "HAMMADDE LOT TÜKETİM KAYDI YOK"
                )

            self.izlenebilirlik_baslik(
                "3. PAKETLEME"
            )

            if paketlemeler:
                for row in paketlemeler:
                    ambalaj = (
                        "500 g"
                        if row["ambalaj_gram"] == 500
                        else "2.5 kg"
                        if row["ambalaj_gram"] == 2500
                        else (
                            f'{row["ambalaj_gram"]} g'
                        )
                    )

                    koli_ici = (
                        row["koli_ici_adet"]
                        or 0
                    )

                    if koli_ici > 0:
                        tam_koli = (
                            row["paket_adedi"]
                            // koli_ici
                        )

                        acik_paket = (
                            row["paket_adedi"]
                            % koli_ici
                        )
                    else:
                        tam_koli = 0
                        acik_paket = (
                            row["paket_adedi"]
                        )

                    metin = (
                        f'PAKETLEME TARİHİ: '
                        f'{row["paketleme_tarihi"]}\n'
                        f'AMBALAJ: {ambalaj}\n'
                        f'PAKET ADEDİ: '
                        f'{row["paket_adedi"]}\n'
                        f'TAM KOLİ: {tam_koli}\n'
                        f'AÇIK PAKET: {acik_paket}\n'
                        f'PAKETLENEN: '
                        f'{row["paketlenen_kg"]:.3f} kg\n'
                        f'PAKETLEME FİRESİ: '
                        f'{row["paketleme_firesi_kg"]:.3f} kg'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "PAKETLEME KAYDI YOK"
                )

            self.izlenebilirlik_baslik(
                "4. SEVKİYAT VE MÜŞTERİ ZİNCİRİ"
            )

            if sevkiyatlar:
                for row in sevkiyatlar:
                    soguk = (
                        "EVET"
                        if row["soguk_zincir"]
                        else "HAYIR"
                    )

                    metin = (
                        f'SEVKİYAT TARİHİ: '
                        f'{row["sevkiyat_tarihi"]}\n'
                        f'MÜŞTERİ: '
                        f'{row["musteri"]}\n'
                        f'PAKET: '
                        f'{row["toplam_paket"]}\n'
                        f'SEVK KG: '
                        f'{row["toplam_kg"]:.3f} kg\n'
                        f'ARAÇ PLAKA: '
                        f'{row["arac_plaka"] or "-"}\n'
                        f'BELGE NO: '
                        f'{row["belge_no"] or "-"}\n'
                        f'SOĞUK ZİNCİR: {soguk}'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "BU ÜRÜN LOTUNA BAĞLI SEVKİYAT YOK"
                )

        except ValueError as hata:
            messagebox.showerror(
                "İzlenebilirlik Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "İzlenebilirlik zinciri "
                    f"oluşturulamadı:\n{hata}"
                )
            )


    def geri_cagirma_izi_getir(self):
        try:
            secim = (
                self.geri_cagirma_lot_secim
                .get()
                .strip()
            )

            if secim not in self.geri_cagirma_lot_map:
                raise ValueError(
                    "Geçerli bir hammadde lotu seçilmelidir."
                )

            depo_kabul_id = (
                self.geri_cagirma_lot_map[secim]
            )

            for widget in (
                self.izlenebilirlik_sonuc_frame
                .winfo_children()
            ):
                widget.destroy()

            conn = get_connection()

            try:
                hammadde_lotu = conn.execute("""
                    SELECT
                        dk.id,
                        dk.kabul_tarihi,
                        dk.tedarikci,
                        dk.tedarikci_lot_no,
                        dk.uretim_tarihi,
                        dk.skt_tett,
                        dk.miktar_kg,
                        dk.kabul_durumu,
                        h.ad AS hammadde
                    FROM depo_kabul dk
                    JOIN hammaddeler h
                      ON h.id = dk.hammadde_id
                    WHERE dk.id = ?
                """, (
                    depo_kabul_id,
                )).fetchone()

                uretimler = conn.execute("""
                    SELECT
                        u.id,
                        u.uretim_tarihi,
                        u.urun_lot_no,
                        u.parti_sayisi,
                        u.net_uretim_kg,
                        uhl.kullanilan_miktar_kg
                    FROM uretim_hammadde_lotlari uhl
                    JOIN uretim u
                      ON u.id = uhl.uretim_id
                    WHERE uhl.depo_kabul_id = ?
                    ORDER BY u.id
                """, (
                    depo_kabul_id,
                )).fetchall()

                uretim_idleri = [
                    row["id"]
                    for row in uretimler
                ]

                paketlemeler = []

                sevkiyatlar = []

                if uretim_idleri:
                    yerler = ",".join(
                        "?"
                        for _ in uretim_idleri
                    )

                    paketlemeler = conn.execute(
                        f"""
                        SELECT
                            p.id,
                            p.uretim_id,
                            p.paketleme_tarihi,
                            p.ambalaj_gram,
                            p.paket_adedi,
                            p.koli_ici_adet,
                            p.paketlenen_kg,
                            u.urun_lot_no
                        FROM paketleme p
                        JOIN uretim u
                          ON u.id = p.uretim_id
                        WHERE p.uretim_id IN ({yerler})
                        ORDER BY p.id
                        """,
                        tuple(uretim_idleri)
                    ).fetchall()

                    sevkiyatlar = conn.execute(
                        f"""
                        SELECT
                            s.id,
                            s.sevkiyat_tarihi,
                            s.musteri,
                            s.arac_plaka,
                            s.belge_no,
                            s.soguk_zincir,
                            sk.paket_adedi,
                            sk.sevk_kg,
                            u.urun_lot_no,
                            p.ambalaj_gram
                        FROM sevkiyat_kalemleri sk
                        JOIN sevkiyat s
                          ON s.id = sk.sevkiyat_id
                        JOIN paketleme p
                          ON p.id = sk.paketleme_id
                        JOIN uretim u
                          ON u.id = p.uretim_id
                        WHERE p.uretim_id IN ({yerler})
                        ORDER BY s.id
                        """,
                        tuple(uretim_idleri)
                    ).fetchall()

            finally:
                conn.close()

            self.izlenebilirlik_baslik(
                "GERİ ÇAĞIRMA / TERS İZLENEBİLİRLİK"
            )

            if not hammadde_lotu:
                self.izlenebilirlik_kart(
                    "HAMMADDE LOT KAYDI BULUNAMADI"
                )
                return

            lot_metin = (
                f'HAMMADDE: '
                f'{hammadde_lotu["hammadde"]}\n'
                f'TEDARİKÇİ: '
                f'{hammadde_lotu["tedarikci"]}\n'
                f'TEDARİKÇİ LOT NO: '
                f'{hammadde_lotu["tedarikci_lot_no"]}\n'
                f'KABUL TARİHİ: '
                f'{hammadde_lotu["kabul_tarihi"]}\n'
                f'ÜRETİM TARİHİ: '
                f'{hammadde_lotu["uretim_tarihi"] or "-"}\n'
                f'SKT / TETT: '
                f'{hammadde_lotu["skt_tett"] or "-"}\n'
                f'KABUL MİKTARI: '
                f'{hammadde_lotu["miktar_kg"]:.3f} kg\n'
                f'KABUL DURUMU: '
                f'{hammadde_lotu["kabul_durumu"]}'
            )

            self.izlenebilirlik_kart(
                lot_metin
            )

            self.izlenebilirlik_baslik(
                "1. ETKİLENEN ÜRETİM LOTLARI"
            )

            if uretimler:
                for row in uretimler:
                    metin = (
                        f'ÜRÜN LOTU: '
                        f'{row["urun_lot_no"]}\n'
                        f'ÜRETİM TARİHİ: '
                        f'{row["uretim_tarihi"]}\n'
                        f'PARTİ SAYISI: '
                        f'{row["parti_sayisi"]}\n'
                        f'NET ÜRETİM: '
                        f'{row["net_uretim_kg"]:.3f} kg\n'
                        f'BU HAMMADDE LOTUNDAN KULLANILAN: '
                        f'{row["kullanilan_miktar_kg"]:.3f} kg'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "BU HAMMADDE LOTU HENÜZ "
                    "HERHANGİ BİR ÜRETİMDE KULLANILMAMIŞ"
                )

            self.izlenebilirlik_baslik(
                "2. ETKİLENEN PAKETLEMELER"
            )

            if paketlemeler:
                for row in paketlemeler:
                    ambalaj = (
                        "500 g"
                        if row["ambalaj_gram"] == 500
                        else "2.5 kg"
                        if row["ambalaj_gram"] == 2500
                        else f'{row["ambalaj_gram"]} g'
                    )

                    koli_ici = (
                        row["koli_ici_adet"] or 0
                    )

                    if koli_ici > 0:
                        tam_koli = (
                            row["paket_adedi"]
                            // koli_ici
                        )

                        acik_paket = (
                            row["paket_adedi"]
                            % koli_ici
                        )
                    else:
                        tam_koli = 0
                        acik_paket = row["paket_adedi"]

                    metin = (
                        f'ÜRÜN LOTU: '
                        f'{row["urun_lot_no"]}\n'
                        f'PAKETLEME TARİHİ: '
                        f'{row["paketleme_tarihi"]}\n'
                        f'AMBALAJ: {ambalaj}\n'
                        f'PAKET: '
                        f'{row["paket_adedi"]}\n'
                        f'TAM KOLİ: {tam_koli}\n'
                        f'AÇIK PAKET: {acik_paket}\n'
                        f'PAKETLENEN: '
                        f'{row["paketlenen_kg"]:.3f} kg'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "ETKİLENEN PAKETLEME KAYDI YOK"
                )

            self.izlenebilirlik_baslik(
                "3. ETKİLENEN SEVKİYAT VE MÜŞTERİLER"
            )

            if sevkiyatlar:
                for row in sevkiyatlar:
                    soguk = (
                        "EVET"
                        if row["soguk_zincir"]
                        else "HAYIR"
                    )

                    ambalaj = (
                        "500 g"
                        if row["ambalaj_gram"] == 500
                        else "2.5 kg"
                        if row["ambalaj_gram"] == 2500
                        else f'{row["ambalaj_gram"]} g'
                    )

                    metin = (
                        f'ÜRÜN LOTU: '
                        f'{row["urun_lot_no"]}\n'
                        f'SEVKİYAT TARİHİ: '
                        f'{row["sevkiyat_tarihi"]}\n'
                        f'MÜŞTERİ: '
                        f'{row["musteri"]}\n'
                        f'AMBALAJ: {ambalaj}\n'
                        f'SEVK PAKET: '
                        f'{row["paket_adedi"]}\n'
                        f'SEVK KG: '
                        f'{row["sevk_kg"]:.3f} kg\n'
                        f'ARAÇ PLAKA: '
                        f'{row["arac_plaka"] or "-"}\n'
                        f'BELGE NO: '
                        f'{row["belge_no"] or "-"}\n'
                        f'SOĞUK ZİNCİR: {soguk}'
                    )

                    self.izlenebilirlik_kart(
                        metin
                    )
            else:
                self.izlenebilirlik_kart(
                    "ETKİLENEN SEVKİYAT / MÜŞTERİ YOK"
                )

        except ValueError as hata:
            messagebox.showerror(
                "Geri Çağırma İzi Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Geri çağırma izi "
                    f"oluşturulamadı:\n{hata}"
                )
            )


    def geri_cagirma_pdf_raporu(self):
        conn = None

        try:
            secim = (
                self.geri_cagirma_lot_secim
                .get()
                .strip()
            )

            if secim not in self.geri_cagirma_lot_map:
                raise ValueError(
                    "Geri çağırma PDF raporu için "
                    "geçerli bir hammadde lotu seçilmelidir."
                )

            depo_kabul_id = self.geri_cagirma_lot_map[
                secim
            ]

            conn = get_connection()

            pdf = geri_cagirma_pdf_olustur(
                conn,
                depo_kabul_id
            )

            subprocess.run(
                [
                    "open",
                    "-R",
                    str(pdf.resolve())
                ],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Geri çağırma PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Geri Çağırma PDF Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Geri çağırma PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


    def izlenebilirlik_pdf_raporu(self):
        conn = None

        try:
            secim = (
                self.izlenebilirlik_lot_secim
                .get()
                .strip()
            )

            if secim not in self.izlenebilirlik_lot_map:
                raise ValueError(
                    "PDF raporu için geçerli "
                    "bir ürün lotu seçilmelidir."
                )

            uretim_id = self.izlenebilirlik_lot_map[
                secim
            ]

            conn = get_connection()

            pdf = izlenebilirlik_pdf_olustur(
                conn,
                uretim_id
            )

            subprocess.run(
                [
                    "open",
                    "-R",
                    str(pdf.resolve())
                ],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "İzlenebilirlik PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "PDF Rapor Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "İzlenebilirlik PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


    def izlenebilirlik_baslik(self, metin):
        ctk.CTkLabel(
            self.izlenebilirlik_sonuc_frame,
            text=metin,
            font=("Arial", 20, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(20, 8)
        )


    def izlenebilirlik_kart(self, metin):
        kart = ctk.CTkFrame(
            self.izlenebilirlik_sonuc_frame
        )

        kart.pack(
            fill="x",
            padx=15,
            pady=5
        )

        ctk.CTkLabel(
            kart,
            text=metin,
            justify="left",
            font=("Arial", 14)
        ).pack(
            anchor="w",
            padx=20,
            pady=15
        )

    def temizlik(self):
        self.show_page(
            "TEMİZLİK",
            "Alan ve ekipman temizlik kayıtları"
        )

        form = ctk.CTkFrame(
            self.content
        )
        form.pack(
            fill="x",
            padx=20,
            pady=(10, 10)
        )

        ctk.CTkLabel(
            form,
            text="YENİ TEMİZLİK KAYDI",
            font=("Arial", 20, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            padx=15,
            pady=(15, 10)
        )

        ctk.CTkLabel(
            form,
            text="Tarih"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_tarih = ctk.CTkEntry(
            form,
            width=220
        )
        self.temizlik_tarih.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )
        self.temizlik_tarih.insert(
            0,
            datetime.now().strftime("%d.%m.%Y")
        )

        ctk.CTkLabel(
            form,
            text="Alan / Ekipman"
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_alan = ctk.CTkEntry(
            form,
            width=260
        )
        self.temizlik_alan.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            form,
            text="Uygulayan"
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_uygulayan = ctk.CTkOptionMenu(
            form,
            values=[
                "Fatih Ayaz",
                "Eda Ayaz"
            ]
        )
        self.temizlik_uygulayan.grid(
            row=2,
            column=2,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )
        self.temizlik_uygulayan.set(
            "Fatih Ayaz"
        )

        ctk.CTkLabel(
            form,
            text="Kontrol Eden"
        ).grid(
            row=1,
            column=3,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_kontrol = ctk.CTkOptionMenu(
            form,
            values=[
                "Fatih Ayaz",
                "Eda Ayaz"
            ]
        )
        self.temizlik_kontrol.grid(
            row=2,
            column=3,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )
        self.temizlik_kontrol.set(
            "Eda Ayaz"
        )

        ctk.CTkLabel(
            form,
            text="Yapılan İşlem"
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_islem = ctk.CTkEntry(
            form
        )
        self.temizlik_islem.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            form,
            text="Durum"
        ).grid(
            row=3,
            column=3,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_durum = ctk.CTkOptionMenu(
            form,
            values=[
                "UYGUN",
                "UYGUN DEĞİL"
            ]
        )
        self.temizlik_durum.grid(
            row=4,
            column=3,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )
        self.temizlik_durum.set(
            "UYGUN"
        )

        ctk.CTkLabel(
            form,
            text="Açıklama"
        ).grid(
            row=5,
            column=0,
            columnspan=4,
            sticky="w",
            padx=15,
            pady=5
        )

        self.temizlik_aciklama = ctk.CTkEntry(
            form
        )
        self.temizlik_aciklama.grid(
            row=6,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )

        for column in range(4):
            form.grid_columnconfigure(
                column,
                weight=1
            )

        buton_frame = ctk.CTkFrame(
            form,
            fg_color="transparent"
        )
        buton_frame.grid(
            row=7,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=15,
            pady=(5, 15)
        )

        ctk.CTkButton(
            buton_frame,
            text="TEMİZLİK KAYDINI KAYDET",
            command=self.temizlik_kaydet
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            buton_frame,
            text="FORMU TEMİZLE",
            command=self.temizlik_form_temizle
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            self.content,
            text="TEMİZLİK KAYITLARI",
            font=("Arial", 20, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(10, 5)
        )

        self.temizlik_liste_frame = (
            ctk.CTkScrollableFrame(
                self.content
            )
        )
        self.temizlik_liste_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        self.temizlik_listele()


    def temizlik_kaydet(self):
        conn = None

        try:
            tarih = (
                self.temizlik_tarih
                .get()
                .strip()
            )

            alan = (
                self.temizlik_alan
                .get()
                .strip()
            )

            yapilan_islem = (
                self.temizlik_islem
                .get()
                .strip()
            )

            uygulayan = (
                self.temizlik_uygulayan
                .get()
                .strip()
            )

            kontrol_eden = (
                self.temizlik_kontrol
                .get()
                .strip()
            )

            durum = (
                self.temizlik_durum
                .get()
                .strip()
            )

            aciklama = (
                self.temizlik_aciklama
                .get()
                .strip()
            )

            if not tarih:
                raise ValueError(
                    "Temizlik tarihi zorunludur."
                )

            try:
                datetime.strptime(
                    tarih,
                    "%d.%m.%Y"
                )
            except ValueError:
                raise ValueError(
                    "Tarih GG.AA.YYYY formatında olmalıdır."
                )

            if not alan:
                raise ValueError(
                    "Alan / ekipman zorunludur."
                )

            if not yapilan_islem:
                raise ValueError(
                    "Yapılan işlem zorunludur."
                )

            if uygulayan not in [
                "Fatih Ayaz",
                "Eda Ayaz"
            ]:
                raise ValueError(
                    "Geçerli uygulayan personel seçilmelidir."
                )

            if kontrol_eden not in [
                "Fatih Ayaz",
                "Eda Ayaz"
            ]:
                raise ValueError(
                    "Geçerli kontrol eden personel seçilmelidir."
                )

            if durum not in [
                "UYGUN",
                "UYGUN DEĞİL"
            ]:
                raise ValueError(
                    "Geçerli temizlik durumu seçilmelidir."
                )

            conn = get_connection()

            conn.execute(
                """
                INSERT INTO temizlik (
                    tarih,
                    alan_ekipman,
                    yapilan_islem,
                    uygulayan,
                    kontrol_eden,
                    durum,
                    aciklama,
                    kayit_zamani
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    datetime(
                        'now',
                        'localtime'
                    )
                )
                """,
                (
                    tarih,
                    alan,
                    yapilan_islem,
                    uygulayan,
                    kontrol_eden,
                    durum,
                    aciklama,
                )
            )

            conn.commit()

            messagebox.showinfo(
                "REDBOX OS",
                "Temizlik kaydı başarıyla kaydedildi."
            )

            self.temizlik_form_temizle()
            self.temizlik_listele()

        except ValueError as hata:
            messagebox.showerror(
                "Temizlik Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Temizlik kaydı oluşturulamadı:\n"
                    f"{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


    def temizlik_form_temizle(self):
        self.temizlik_tarih.delete(
            0,
            "end"
        )
        self.temizlik_tarih.insert(
            0,
            datetime.now().strftime("%d.%m.%Y")
        )

        self.temizlik_alan.delete(
            0,
            "end"
        )

        self.temizlik_islem.delete(
            0,
            "end"
        )

        self.temizlik_aciklama.delete(
            0,
            "end"
        )

        self.temizlik_uygulayan.set(
            "Fatih Ayaz"
        )

        self.temizlik_kontrol.set(
            "Eda Ayaz"
        )

        self.temizlik_durum.set(
            "UYGUN"
        )


    def temizlik_listele(self):
        for widget in (
            self.temizlik_liste_frame
            .winfo_children()
        ):
            widget.destroy()

        conn = None

        try:
            conn = get_connection()

            rows = conn.execute(
                """
                SELECT
                    id,
                    tarih,
                    alan_ekipman,
                    yapilan_islem,
                    uygulayan,
                    kontrol_eden,
                    durum,
                    aciklama,
                    kayit_zamani
                FROM temizlik
                ORDER BY
                    substr(tarih, 7, 4) DESC,
                    substr(tarih, 4, 2) DESC,
                    substr(tarih, 1, 2) DESC,
                    id DESC
                """
            ).fetchall()

            if not rows:
                ctk.CTkLabel(
                    self.temizlik_liste_frame,
                    text=(
                        "Henüz temizlik kaydı bulunmuyor."
                    ),
                    font=("Arial", 15)
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=15
                )

                return

            for row in rows:
                kart = ctk.CTkFrame(
                    self.temizlik_liste_frame
                )
                kart.pack(
                    fill="x",
                    padx=5,
                    pady=5
                )

                bilgi = (
                    f"{row['tarih']}  |  "
                    f"{row['alan_ekipman']}\n"
                    f"İŞLEM: {row['yapilan_islem']}\n"
                    f"UYGULAYAN: {row['uygulayan']}  |  "
                    f"KONTROL: "
                    f"{row['kontrol_eden'] or '-'}  |  "
                    f"DURUM: {row['durum']}"
                )

                if row["aciklama"]:
                    bilgi += (
                        f"\nAÇIKLAMA: "
                        f"{row['aciklama']}"
                    )

                ctk.CTkLabel(
                    kart,
                    text=bilgi,
                    justify="left",
                    anchor="w",
                    font=("Arial", 14)
                ).pack(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=15,
                    pady=12
                )

                ctk.CTkButton(
                    kart,
                    text="SİL",
                    width=80,
                    command=lambda temizlik_id=row["id"]: (
                        self.temizlik_sil(
                            temizlik_id
                        )
                    )
                ).pack(
                    side="right",
                    padx=15,
                    pady=12
                )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Temizlik kayıtları okunamadı:\n"
                    f"{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


    def temizlik_sil(self, temizlik_id):
        onay = messagebox.askyesno(
            "Temizlik Kaydı Sil",
            (
                "Seçili temizlik kaydı silinecek.\n\n"
                "Devam edilsin mi?"
            )
        )

        if not onay:
            return

        conn = None

        try:
            conn = get_connection()

            cursor = conn.execute(
                """
                DELETE FROM temizlik
                WHERE id = ?
                """,
                (
                    temizlik_id,
                )
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    "Silinecek temizlik kaydı bulunamadı."
                )

            conn.commit()

            messagebox.showinfo(
                "REDBOX OS",
                "Temizlik kaydı silindi."
            )

            self.temizlik_listele()

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Temizlik Silme Hatası",
                str(hata)
            )

        finally:
            if conn is not None:
                conn.close()


    def aktif_personelleri_getir(self):
        conn = None

        try:
            conn = get_connection()

            rows = conn.execute(
                """
                SELECT
                    ad_soyad
                FROM personeller
                WHERE aktif = 1
                ORDER BY
                    ad_soyad COLLATE NOCASE
                """
            ).fetchall()

            return [
                row["ad_soyad"]
                for row in rows
            ]

        finally:
            if conn is not None:
                conn.close()


    def personel(self):
        self.show_page(
            "PERSONEL",
            "Personel kayıt ve aktiflik yönetimi"
        )

        form = ctk.CTkFrame(
            self.content
        )

        form.pack(
            fill="x",
            padx=20,
            pady=(20, 10)
        )

        ctk.CTkLabel(
            form,
            text="YENİ PERSONEL KAYDI",
            font=("Arial", 20, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            padx=15,
            pady=(15, 20)
        )

        ctk.CTkLabel(
            form,
            text="Ad Soyad"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=15
        )

        ctk.CTkLabel(
            form,
            text="Görev"
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=15
        )

        ctk.CTkLabel(
            form,
            text="Açıklama"
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=15
        )

        self.personel_ad = ctk.CTkEntry(
            form,
            width=280
        )

        self.personel_ad.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(5, 15)
        )

        self.personel_gorev = ctk.CTkEntry(
            form,
            width=280
        )

        self.personel_gorev.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=15,
            pady=(5, 15)
        )

        self.personel_aciklama = ctk.CTkEntry(
            form,
            width=420
        )

        self.personel_aciklama.grid(
            row=2,
            column=2,
            sticky="ew",
            padx=15,
            pady=(5, 15)
        )

        ctk.CTkButton(
            form,
            text="PERSONELİ KAYDET",
            command=self.personel_kaydet
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 15)
        )

        ctk.CTkButton(
            form,
            text="FORMU TEMİZLE",
            command=self.personel_form_temizle
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=15,
            pady=(0, 15)
        )

        form.grid_columnconfigure(
            0,
            weight=1
        )

        form.grid_columnconfigure(
            1,
            weight=1
        )

        form.grid_columnconfigure(
            2,
            weight=2
        )

        ctk.CTkLabel(
            self.content,
            text="PERSONEL KAYITLARI",
            font=("Arial", 22, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        self.personel_liste_frame = (
            ctk.CTkScrollableFrame(
                self.content
            )
        )

        self.personel_liste_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(5, 20)
        )

        self.personel_listele()


    def personel_kaydet(self):
        conn = None

        try:
            ad_soyad = (
                self.personel_ad
                .get()
                .strip()
            )

            gorev = (
                self.personel_gorev
                .get()
                .strip()
            )

            aciklama = (
                self.personel_aciklama
                .get()
                .strip()
            )

            if not ad_soyad:
                raise ValueError(
                    "Ad soyad zorunludur."
                )

            ad_soyad = " ".join(
                ad_soyad.split()
            )

            conn = get_connection()

            conn.execute(
                """
                INSERT INTO personeller (
                    ad_soyad,
                    gorev,
                    aktif,
                    aciklama,
                    kayit_zamani
                )
                VALUES (?, ?, 1, ?, ?)
                """,
                (
                    ad_soyad,
                    gorev or None,
                    aciklama or None,
                    datetime.now().strftime(
                        "%d.%m.%Y %H:%M:%S"
                    )
                )
            )

            conn.commit()

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Personel başarıyla kaydedildi.\n\n"
                    f"{ad_soyad}"
                )
            )

            self.personel_form_temizle()
            self.personel_listele()

        except ValueError as hata:
            messagebox.showerror(
                "Personel Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            hata_metni = str(hata)

            if (
                "UNIQUE constraint failed"
                in hata_metni
            ):
                messagebox.showerror(
                    "Personel Kayıt Hatası",
                    (
                        "Bu personel zaten kayıtlıdır."
                    )
                )
            else:
                messagebox.showerror(
                    "Sistem Hatası",
                    (
                        "Personel kaydedilemedi:\n"
                        f"{hata}"
                    )
                )

        finally:
            if conn is not None:
                conn.close()


    def personel_form_temizle(self):
        self.personel_ad.delete(
            0,
            "end"
        )

        self.personel_gorev.delete(
            0,
            "end"
        )

        self.personel_aciklama.delete(
            0,
            "end"
        )


    def personel_aktiflik_degistir(
        self,
        personel_id,
        mevcut_aktif
    ):
        conn = None

        try:
            yeni_aktif = (
                0
                if mevcut_aktif == 1
                else 1
            )

            conn = get_connection()

            if yeni_aktif == 0:
                aktif_sayi = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM personeller
                    WHERE aktif = 1
                    """
                ).fetchone()[0]

                if aktif_sayi <= 1:
                    raise ValueError(
                        "Sistemde en az bir aktif "
                        "personel bulunmalıdır."
                    )

            conn.execute(
                """
                UPDATE personeller
                SET aktif = ?
                WHERE id = ?
                """,
                (
                    yeni_aktif,
                    personel_id
                )
            )

            conn.commit()

            self.personel_listele()

        except ValueError as hata:
            messagebox.showerror(
                "Personel Durum Hatası",
                str(hata)
            )

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Personel durumu "
                    "değiştirilemedi:\n"
                    f"{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


    def personel_listele(self):
        conn = None

        try:
            for widget in (
                self.personel_liste_frame
                .winfo_children()
            ):
                widget.destroy()

            conn = get_connection()

            rows = conn.execute(
                """
                SELECT
                    id,
                    ad_soyad,
                    gorev,
                    aktif,
                    aciklama
                FROM personeller
                ORDER BY
                    aktif DESC,
                    ad_soyad COLLATE NOCASE
                """
            ).fetchall()

            if not rows:
                ctk.CTkLabel(
                    self.personel_liste_frame,
                    text=(
                        "Henüz personel kaydı "
                        "bulunmuyor."
                    )
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=15
                )

                return

            for row in rows:
                kart = ctk.CTkFrame(
                    self.personel_liste_frame
                )

                kart.pack(
                    fill="x",
                    padx=5,
                    pady=5
                )

                durum = (
                    "AKTİF"
                    if row["aktif"] == 1
                    else "PASİF"
                )

                metin = (
                    f'{row["ad_soyad"]}\n'
                    f'GÖREV: '
                    f'{row["gorev"] or "-"}  |  '
                    f'DURUM: {durum}'
                )

                if row["aciklama"]:
                    metin += (
                        "\nAÇIKLAMA: "
                        + row["aciklama"]
                    )

                ctk.CTkLabel(
                    kart,
                    text=metin,
                    justify="left",
                    font=("Arial", 14)
                ).pack(
                    side="left",
                    anchor="w",
                    padx=20,
                    pady=15
                )

                buton_metni = (
                    "PASİFE AL"
                    if row["aktif"] == 1
                    else "AKTİF ET"
                )

                ctk.CTkButton(
                    kart,
                    text=buton_metni,
                    width=120,
                    command=lambda
                    personel_id=row["id"],
                    mevcut_aktif=row["aktif"]:
                    self.personel_aktiflik_degistir(
                        personel_id,
                        mevcut_aktif
                    )
                ).pack(
                    side="right",
                    padx=20,
                    pady=15
                )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Personel listesi "
                    "yüklenemedi:\n"
                    f"{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()


if __name__ == "__main__":
    app = RedboxOS()
    app.mainloop()
