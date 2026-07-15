import tkinter as tk
import customtkinter as ctk
import subprocess
import sys
from tkinter import messagebox, ttk
from datetime import datetime

from database.db import init_database, get_connection
from database.stock_engine import (
    uretim_stok_isle,
    lot_parti_plani_oner,
)
from database.finished_stock_engine import (
    mamul_stok_ozeti,
    ambalaj_stok_toplami,
    mamul_stok_hareketi_ekle,
    sevkiyat_hareketi_ekle,
    sevkiyat_stok_dus,
)

from database.report_engine import (
    izlenebilirlik_pdf_olustur,
    geri_cagirma_pdf_olustur,
    hammadde_kabul_pdf_olustur,
    uretim_pdf_olustur,
    paketleme_pdf_olustur,
    sevkiyat_pdf_olustur,
    temizlik_pdf_olustur,
    stok_pdf_olustur,
)

from database.raw_material_stock_engine import (
    hammadde_stok_ozeti,
    hammadde_lot_stoklari,
    hammadde_toplam_stok_kg,
)
from database.cleaning_engine import (
    get_due_cleaning_tasks,
    get_due_cleaning_summary,
    complete_cleaning_task,
)
from ui.system import SystemPage
from ui.pages.dashboard_page import DashboardPage
from ui.controllers.dashboard_controller import DashboardController
from ui.order_calculator import OrderCalculatorWindow
from ui.login import authenticate_user

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RedboxOS(ctk.CTk):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.formul_yetkili = (
            bool(current_user.get("yonetici"))
            and current_user.get("ad_soyad") == "Fatih Ayaz"
            and current_user.get("kullanici_adi", "").lower() == "fatih"
        )
        self.title("REDBOX OS")
        self.geometry("1380x820")

        if sys.platform == "darwin":
            try:
                self.tk.createcommand(
                    "::tk::mac::ReopenApplication",
                    self._macos_dock_reopen,
                )
            except Exception:
                pass
        self.minsize(1180, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_visible = True

        self.sidebar = ctk.CTkFrame(
            self,
            width=245,
            corner_radius=0
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.sidebar.grid_rowconfigure(13, weight=1)

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
            *(
                [("REÇETE", self.recete)]
                if self.formul_yetkili
                else []
            ),
            ("PERSONEL", self.personel),
            ("TEMİZLİK", self.temizlik),
            ("SİSTEM", self.sistem),
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
            text=f'AKTİF: {self.current_user["ad_soyad"]}',
            font=("Arial", 11, "bold"),
            text_color="#22C55E",
        ).grid(
            row=14,
            column=0,
            padx=20,
            pady=(12, 2),
        )

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX OS • ÇEKİRDEK v0.3",
            font=("Arial", 11)
        ).grid(
            row=15,
            column=0,
            padx=20,
            pady=(2, 16),
        )

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0
        )
        self.content.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.sidebar_toggle = ctk.CTkButton(
            self,
            text="◀",
            width=34,
            height=30,
            corner_radius=6,
            command=self.toggle_sidebar,
            font=("Arial", 14, "bold")
        )
        self.sidebar_toggle.place(
            x=205,
            y=8
        )
        self.sidebar_toggle.lift()

        self._context_menu_widget = None
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(
            label="Kes",
            command=lambda: self._context_menu_event("<<Cut>>")
        )
        self._context_menu.add_command(
            label="Kopyala",
            command=lambda: self._context_menu_event("<<Copy>>")
        )
        self._context_menu.add_command(
            label="Yapıştır",
            command=lambda: self._context_menu_event("<<Paste>>")
        )
        self._context_menu.add_separator()
        self._context_menu.add_command(
            label="Tümünü Seç",
            command=lambda: self._context_menu_event("<<SelectAll>>")
        )

        self.bind_class(
            "Entry",
            "<Button-2>",
            self._show_context_menu,
            add="+"
        )
        self.bind_class(
            "Entry",
            "<Button-3>",
            self._show_context_menu,
            add="+"
        )

        self.ana_sayfa()

    def _macos_dock_reopen(self):
        self.deiconify()
        self.after(
            50,
            lambda: (
                self.lift(),
                self.focus_force(),
            ),
        )

    def formul_erisim_kontrolu(self):
        if self.formul_yetkili:
            return True

        messagebox.showerror(
            "Yetkisiz Erişim",
            (
                "1 parti üretim formülü yalnızca "
                "Fatih Ayaz hesabına açıktır."
            ),
        )
        return False

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
            self.sidebar_toggle.configure(text="☰")
            self.sidebar_toggle.place(
                relx=1.0,
                x=-45,
                y=8
            )
        else:
            self.sidebar.grid()
            self.sidebar_visible = True
            self.sidebar_toggle.configure(text="◀")
            self.sidebar_toggle.place(
                relx=0.0,
                x=205,
                y=8
            )

        self.sidebar_toggle.lift()

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

        dashboard = DashboardPage(
            self.content,
            quick_actions=[
                ("GENEL STOK", self.stok),
                ("HAMMADDE STOK", self.stok),
                ("DEPO KABUL", self.depo_kabul),
                ("YENİ ÜRETİM", self.uretim),
                ("SİPARİŞ HESAPLA", self.siparis_hesapla),
            ],
        )
        dashboard.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(0, 25)
        )

        controller = DashboardController()
        data = controller.load()

        recent = []

        for row in data.get("recent_production", []):
            recent.append(
                (
                    "ÜRETİM  |  "
                    f'{row["tarih"]}  |  '
                    f'LOT {row["lot"]}  |  '
                    f'{row["kg"]:.3f} kg'
                )
            )

        for row in data.get("recent_shipment", []):
            recent.append(
                (
                    "SEVKİYAT  |  "
                    f'{row["tarih"]}  |  '
                    f'{row["musteri"]}  |  '
                    f'{row["koli"]} koli'
                )
            )

        critical_stock = [
            (
                f'{row["ad"]}: '
                f'{row["kalan"]:.3f} kg'
            )
            for row in data.get("critical_stock", [])
            if float(row["kalan"]) <= 50.0
        ]

        dashboard.load_data(
            production=float(data.get("production", 0.0)),
            packaging=float(data.get("packaging", 0.0)),
            shipment=float(data.get("shipment", 0.0)),
            critical=len(critical_stock),
            recent=recent[:12],
            stock=critical_stock,
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
            analiz = {}

            kalemler = conn.execute("""
                SELECT
                    h.ad,
                    rk.miktar_kg
                FROM recete_kalemleri rk
                JOIN hammaddeler h
                  ON h.id = rk.hammadde_id
                WHERE rk.recete_id = ?
                ORDER BY h.id
            """, (
                recete["id"],
            )).fetchall()

            for row in kalemler:
                analiz[row["ad"]] = (
                    float(row["miktar_kg"]) * parti_sayisi
                )

            analiz["Proses Suyu"] = (
                su_parti * parti_sayisi
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
                    "analiz": analiz,
                }
    

        finally:
            conn.close()


    def stok(self):
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text="STOK",
            font=("Arial", 30, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 5)
        )

        ctk.CTkLabel(
            self.content,
            text="Canlı mamul ve hammadde depo stok durumu",
            font=("Arial", 15)
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 15)
        )

        stock_actions = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        stock_actions.pack(
            fill="x",
            padx=25,
            pady=(0, 10)
        )

        ctk.CTkButton(
            stock_actions,
            text="GENEL STOK PDF",
            command=self.genel_stok_pdf_raporu,
            width=170,
            height=40,
            font=("Arial", 13, "bold")
        ).pack(
            side="right"
        )

        scroll = ctk.CTkScrollableFrame(self.content)
        scroll.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        def section_title(text):
            ctk.CTkLabel(
                scroll,
                text=text,
                font=("Arial", 21, "bold")
            ).pack(
                anchor="w",
                padx=10,
                pady=(22, 10)
            )

        def summary_card(text):
            frame = ctk.CTkFrame(
                scroll,
                corner_radius=8
            )
            frame.pack(
                fill="x",
                padx=10,
                pady=(0, 10)
            )

            ctk.CTkLabel(
                frame,
                text=text,
                font=("Arial", 16, "bold"),
                anchor="w"
            ).pack(
                fill="x",
                padx=18,
                pady=14
            )

        def data_table(headers, rows, weights):
            table = ctk.CTkFrame(
                scroll,
                corner_radius=8
            )
            table.pack(
                fill="x",
                padx=10,
                pady=(0, 10)
            )

            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Redbox.Treeview",
                background="#2b2b2b",
                fieldbackground="#2b2b2b",
                foreground="#e5e7eb",
                rowheight=38,
                borderwidth=0,
                font=("Arial", 12)
            )
            style.configure(
                "Redbox.Treeview.Heading",
                background="#343434",
                foreground="#e5e7eb",
                relief="flat",
                font=("Arial", 12, "bold")
            )
            style.map(
                "Redbox.Treeview",
                background=[("selected", "#1f6aa5")],
                foreground=[("selected", "#ffffff")]
            )

            columns = tuple(
                f"column_{index}"
                for index in range(len(headers))
            )

            tree = ttk.Treeview(
                table,
                columns=columns,
                show="headings",
                style="Redbox.Treeview",
                height=max(1, len(rows)),
                selectmode="browse"
            )

            for index, (
                column,
                header,
                weight
            ) in enumerate(
                zip(columns, headers, weights)
            ):
                anchor = "e" if index > 0 else "w"

                tree.heading(
                    column,
                    text=header,
                    anchor=anchor
                )
                tree.column(
                    column,
                    anchor=anchor,
                    width=weight * 55,
                    minwidth=80,
                    stretch=True
                )

            tree.tag_configure(
                "even",
                background="#292929"
            )
            tree.tag_configure(
                "odd",
                background="#303030"
            )

            if rows:
                for row_index, values in enumerate(rows):
                    tree.insert(
                        "",
                        "end",
                        values=values,
                        tags=(
                            "even"
                            if row_index % 2 == 0
                            else "odd",
                        )
                    )
            else:
                empty_values = [
                    "Gösterilecek aktif stok kaydı yok."
                ] + [""] * (len(headers) - 1)

                tree.insert(
                    "",
                    "end",
                    values=empty_values,
                    tags=("even",)
                )

            tree.pack(
                fill="x",
                expand=True,
                padx=8,
                pady=8
            )

        mamul_rows = [
            row
            for row in mamul_stok_ozeti()
            if int(row["kalan_paket_adedi"]) > 0
        ]

        mamul_toplam_kg = sum(
            float(row["kalan_kg"])
            for row in mamul_rows
        )
        mamul_toplam_paket = sum(
            int(row["kalan_paket_adedi"])
            for row in mamul_rows
        )

        section_title("CANLI MAMUL STOK")
        summary_card(
            f"TOPLAM MAMUL STOK: {mamul_toplam_kg:.3f} KG"
            f"   |   TOPLAM PAKET: {mamul_toplam_paket}"
        )

        data_table(
            (
                "ÜRÜN LOTU",
                "AMBALAJ",
                "PAKET",
                "TAM KOLİ",
                "AÇIK PAKET",
                "KALAN KG",
            ),
            [
                (
                    row["urun_lot_no"],
                    f'{row["ambalaj_gram"]} G',
                    row["kalan_paket_adedi"],
                    row["tam_koli"],
                    row["acik_paket"],
                    f'{float(row["kalan_kg"]):.3f}',
                )
                for row in mamul_rows
            ],
            (3, 2, 2, 2, 2, 2)
        )

        hammadde_rows = hammadde_stok_ozeti()
        hammadde_toplam = hammadde_toplam_stok_kg()
        pozitif_hammadde = sum(
            1
            for row in hammadde_rows
            if float(row["kalan_kg"]) > 0.000001
        )

        section_title("CANLI HAMMADDE STOK")
        summary_card(
            f"TOPLAM HAMMADDE STOK: {hammadde_toplam:.3f} KG"
            f"   |   POZİTİF STOK KALEMİ: {pozitif_hammadde}"
        )

        hammadde_table_rows = []

        for row in hammadde_rows:
            kalan = float(row["kalan_kg"])

            if kalan > 0.000001:
                durum = "STOK VAR"
            elif kalan < -0.000001:
                durum = "NEGATİF STOK"
            else:
                durum = "STOK YOK"

            hammadde_table_rows.append(
                (
                    row["hammadde"],
                    f'{float(row["kabul_kg"]):.3f}',
                    f'{float(row["tuketim_kg"]):.3f}',
                    f"{kalan:.3f}",
                    durum,
                )
            )

        data_table(
            (
                "HAMMADDE",
                "KABUL KG",
                "TÜKETİM KG",
                "KALAN KG",
                "DURUM",
            ),
            hammadde_table_rows,
            (4, 2, 2, 2, 2)
        )

        lot_rows = hammadde_lot_stoklari(
            sadece_pozitif=True
        )

        section_title("HAMMADDE LOT BAZLI STOK")

        data_table(
            (
                "HAMMADDE",
                "TEDARİKÇİ LOTU",
                "KABUL KG",
                "TÜKETİM KG",
                "KALAN KG",
            ),
            [
                (
                    row["hammadde"],
                    row["tedarikci_lot_no"],
                    f'{float(row["kabul_kg"]):.3f}',
                    f'{float(row["tuketim_kg"]):.3f}',
                    f'{float(row["kalan_kg"]):.3f}',
                )
                for row in lot_rows
            ],
            (4, 3, 2, 2, 2)
        )

    def genel_stok_pdf_raporu(self):
        conn = None

        try:
            conn = get_connection()

            pdf = stok_pdf_olustur(
                conn
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Genel stok PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except Exception as hata:
            messagebox.showerror(
                "Genel Stok PDF Hatası",
                (
                    "Genel stok PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

    def siparis_hesapla(self):
        OrderCalculatorWindow(self)

    def depo_kabul(self):
        self.show_page(
            "DEPO KABUL",
            "Hammadde kabul, tedarikçi ve lot yönetimi",
        )

        main = ctk.CTkFrame(
            self.content,
            fg_color="transparent",
        )
        main.pack(
            fill="both",
            expand=True,
            padx=32,
            pady=(0, 25),
        )

        summary = ctk.CTkFrame(
            main,
            fg_color="transparent",
        )
        summary.pack(
            fill="x",
            pady=(5, 12),
        )

        self.depo_ozet_labels = {}

        cards = (
            ("kayit", "TOPLAM KABUL", "0"),
            ("miktar", "TOPLAM MİKTAR", "0.000 kg"),
            ("hammadde", "AKTİF HAMMADDE", "0"),
            ("son", "SON KABUL", "-"),
        )

        for key, title, value in cards:
            card = ctk.CTkFrame(
                summary,
                height=92,
                corner_radius=12,
            )
            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=6,
            )
            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 11, "bold"),
                text_color="#9CA3AF",
            ).pack(
                anchor="w",
                padx=18,
                pady=(16, 4),
            )

            label = ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 22, "bold"),
            )
            label.pack(
                anchor="w",
                padx=18,
            )
            self.depo_ozet_labels[key] = label

        toolbar = ctk.CTkFrame(
            main,
            corner_radius=10,
        )
        toolbar.pack(
            fill="x",
            pady=(0, 10),
        )

        self.depo_arama = ctk.CTkEntry(
            toolbar,
            width=270,
            height=38,
            placeholder_text=(
                "Hammadde, tedarikçi veya lot ara..."
            ),
        )
        self.depo_arama.pack(
            side="left",
            padx=(12, 6),
            pady=12,
        )
        self.depo_arama.bind(
            "<KeyRelease>",
            lambda _event: self.depo_kabul_listele(),
        )

        conn = get_connection()
        try:
            hammadde_rows = conn.execute("""
                SELECT ad
                FROM hammaddeler
                WHERE aktif = 1
                ORDER BY id
            """).fetchall()
        finally:
            conn.close()

        hammadde_values = [
            "TÜM HAMMADDELER",
            *[row["ad"] for row in hammadde_rows],
        ]

        self.depo_hammadde_filtre = ctk.CTkOptionMenu(
            toolbar,
            values=hammadde_values,
            width=190,
            height=38,
            command=lambda _value: self.depo_kabul_listele(),
        )
        self.depo_hammadde_filtre.set("TÜM HAMMADDELER")
        self.depo_hammadde_filtre.pack(
            side="left",
            padx=6,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="FİLTREYİ TEMİZLE",
            width=135,
            height=38,
            fg_color="#4B5563",
            command=self.depo_kabul_filtre_temizle,
        ).pack(
            side="left",
            padx=6,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="+ YENİ DEPO KABUL",
            width=175,
            height=38,
            font=("Arial", 12, "bold"),
            command=self.depo_kabul_formu_ac,
        ).pack(
            side="right",
            padx=12,
            pady=12,
        )

        self.kabul_liste_frame = ctk.CTkFrame(
            main,
            corner_radius=10,
        )
        self.kabul_liste_frame.pack(
            fill="both",
            expand=True,
        )

        self.depo_kabul_ozet_guncelle()
        self.depo_kabul_listele()

    def depo_kabul_ozet_guncelle(self):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS kayit_sayisi,
                    COALESCE(SUM(miktar_kg), 0) AS toplam_kg,
                    COUNT(DISTINCT hammadde_id) AS hammadde_sayisi
                FROM depo_kabul
                WHERE kabul_durumu = 'KABUL'
            """).fetchone()

            son = conn.execute("""
                SELECT kabul_tarihi
                FROM depo_kabul
                WHERE kabul_durumu = 'KABUL'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()
        finally:
            conn.close()

        self.depo_ozet_labels["kayit"].configure(
            text=str(int(row["kayit_sayisi"])),
        )
        self.depo_ozet_labels["miktar"].configure(
            text=f'{float(row["toplam_kg"]):.3f} kg',
        )
        self.depo_ozet_labels["hammadde"].configure(
            text=str(int(row["hammadde_sayisi"])),
        )
        self.depo_ozet_labels["son"].configure(
            text=son["kabul_tarihi"] if son else "-",
        )

    def depo_kabul_filtre_temizle(self):
        self.depo_arama.delete(0, "end")
        self.depo_hammadde_filtre.set("TÜM HAMMADDELER")
        self.depo_kabul_listele()

    def depo_kabul_formu_ac(self):
        self.depo_form_pencere = ctk.CTkToplevel(self)
        self.depo_form_pencere.title(
            "REDBOX OS — Yeni Depo Kabul",
        )
        self.depo_form_pencere.geometry("560x760")
        self.depo_form_pencere.minsize(520, 680)
        self.depo_form_pencere.transient(self)
        self.depo_form_pencere.grab_set()

        form = ctk.CTkScrollableFrame(
            self.depo_form_pencere,
            corner_radius=12,
        )
        form.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=25,
        )

        ctk.CTkLabel(
            form,
            text="YENİ HAMMADDE KABULÜ",
            font=("Arial", 22, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(38, 4),
        )

        ctk.CTkLabel(
            form,
            text=(
                "Tedarikçi, lot, tarih ve miktar bilgilerini "
                "eksiksiz girin."
            ),
            text_color="#9CA3AF",
            font=("Arial", 12),
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 18),
        )

        conn = get_connection()
        try:
            hammaddeler = conn.execute("""
                SELECT id, ad
                FROM hammaddeler
                WHERE aktif = 1
                ORDER BY id
            """).fetchall()

            tedarikciler = conn.execute("""
                SELECT id, tedarikci_adi
                FROM tedarikciler
                WHERE aktif = 1
                ORDER BY tedarikci_adi
            """).fetchall()
        finally:
            conn.close()

        self.hammadde_map = {
            row["ad"]: row["id"]
            for row in hammaddeler
        }
        self.tedarikci_map = {
            row["tedarikci_adi"]: row["id"]
            for row in tedarikciler
        }

        self.kabul_tarihi = self.form_entry(
            form,
            "Kabul Tarihi",
            datetime.now().strftime("%d.%m.%Y"),
        )

        ctk.CTkLabel(
            form,
            text="Hammadde",
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2),
        )
        self.hammadde_secim = ctk.CTkOptionMenu(
            form,
            values=list(self.hammadde_map.keys()),
            width=350,
        )
        self.hammadde_secim.pack(
            padx=25,
            pady=(0, 8),
        )

        ctk.CTkLabel(
            form,
            text="Tedarikçi",
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 2),
        )
        self.tedarikci = ctk.CTkComboBox(
            form,
            values=(
                list(self.tedarikci_map.keys())
                if self.tedarikci_map
                else [""]
            ),
            width=350,
        )
        self.tedarikci.pack(
            padx=25,
            pady=(0, 5),
        )
        self.tedarikci.set("")

        self.lot_no = self.form_entry(
            form,
            "Tedarikçi Lot No",
        )
        self.urt = self.form_entry(
            form,
            "Üretim Tarihi",
        )
        self.skt = self.form_entry(
            form,
            "SKT / TETT",
        )
        self.miktar = self.form_entry(
            form,
            "Miktar (kg)",
        )
        self.aciklama = self.form_entry(
            form,
            "Açıklama",
        )

        ctk.CTkButton(
            form,
            text="KABUL KAYDINI KAYDET",
            command=self.depo_kabul_kaydet,
            height=46,
            width=350,
            font=("Arial", 14, "bold"),
        ).pack(
            padx=25,
            pady=(18, 8),
        )

        ctk.CTkButton(
            form,
            text="FORMU TEMİZLE",
            command=self.depo_form_temizle,
            height=38,
            width=350,
            fg_color="#4B5563",
        ).pack(
            padx=25,
            pady=(0, 20),
        )

        self.update_idletasks()
        x = (
            self.winfo_x()
            + max(
                (self.winfo_width() - 560) // 2,
                0,
            )
        )
        y = (
            self.winfo_y()
            + max(
                (self.winfo_height() - 760) // 2,
                20,
            )
        )
        self.depo_form_pencere.geometry(
            f"560x760+{x}+{y}"
        )
        self.depo_form_pencere.after(
            150,
            self.depo_form_pencere.focus_force,
        )

    def _show_context_menu(self, event):
        self._context_menu_widget = event.widget

        try:
            self._context_menu.tk_popup(
                event.x_root,
                event.y_root
            )
        finally:
            self._context_menu.grab_release()

        return "break"

    def _context_menu_event(self, virtual_event):
        widget = self._context_menu_widget

        if widget is None:
            return

        try:
            widget.event_generate(virtual_event)
        except Exception:
            pass

    def form_entry(self, parent, label, default=""):
        ctk.CTkLabel(
            parent,
            text=label,
            width=350,
            anchor="w",
        ).pack(
            pady=(5, 2)
        )

        entry = ctk.CTkEntry(parent, width=350)
        entry.pack(pady=(0, 5))

        if default:
            entry.insert(0, default)

        return entry

    def calisma_suresi_hesapla(
        self,
        baslama_saati,
        bitis_saati,
        islem_adi,
    ):
        if not baslama_saati or not bitis_saati:
            raise ValueError(
                f"{islem_adi} başlangıç ve bitiş "
                "saatleri zorunludur."
            )

        try:
            baslangic = datetime.strptime(
                baslama_saati,
                "%H:%M",
            )
            bitis = datetime.strptime(
                bitis_saati,
                "%H:%M",
            )
        except ValueError:
            raise ValueError(
                f"{islem_adi} saatleri SS:DD "
                "formatında girilmelidir."
            )

        sure_dakika = int(
            (bitis - baslangic).total_seconds() / 60
        )

        if sure_dakika <= 0:
            raise ValueError(
                f"{islem_adi} bitiş saati başlangıç "
                "saatinden sonra olmalıdır."
            )

        return sure_dakika

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
            self.depo_kabul_ozet_guncelle()
            self.depo_kabul_listele()

            if (
                hasattr(self, "depo_form_pencere")
                and self.depo_form_pencere.winfo_exists()
            ):
                self.depo_form_pencere.destroy()

        except ValueError as hata:
            messagebox.showerror("Kayıt Hatası", str(hata))

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Kayıt yapılamadı:\n{hata}"
            )

    def depo_form_temizle(self):
        self.tedarikci.set("")

        alanlar = [
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

        search = (
            self.depo_arama.get().strip()
            if hasattr(self, "depo_arama")
            else ""
        )
        material = (
            self.depo_hammadde_filtre.get().strip()
            if hasattr(self, "depo_hammadde_filtre")
            else "TÜM HAMMADDELER"
        )

        where = []
        params = []

        if search:
            like = f"%{search}%"
            where.append("""
                (
                    h.ad LIKE ?
                    OR COALESCE(dk.tedarikci, '') LIKE ?
                    OR dk.tedarikci_lot_no LIKE ?
                )
            """)
            params.extend((like, like, like))

        if material and material != "TÜM HAMMADDELER":
            where.append("h.ad = ?")
            params.append(material)

        where_sql = (
            "WHERE " + " AND ".join(where)
            if where
            else ""
        )

        conn = get_connection()
        try:
            kayitlar = conn.execute(f"""
                SELECT
                    dk.id,
                    dk.kabul_tarihi,
                    h.ad AS hammadde,
                    dk.tedarikci,
                    dk.tedarikci_lot_no,
                    dk.uretim_tarihi,
                    dk.skt_tett,
                    dk.miktar_kg,
                    dk.kabul_durumu
                FROM depo_kabul dk
                JOIN hammaddeler h
                  ON h.id = dk.hammadde_id
                {where_sql}
                ORDER BY dk.id DESC
                LIMIT 250
            """, params).fetchall()
        finally:
            conn.close()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Redbox.Treeview",
            background="#282828",
            fieldbackground="#282828",
            foreground="#E5E7EB",
            rowheight=40,
            borderwidth=0,
            font=("Arial", 11),
        )
        style.configure(
            "Redbox.Treeview.Heading",
            background="#343434",
            foreground="#F3F4F6",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Redbox.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        header = ctk.CTkFrame(
            self.kabul_liste_frame,
            fg_color="transparent",
        )
        header.pack(
            fill="x",
            padx=12,
            pady=(12, 6),
        )

        self.kabul_kayit_sayisi = ctk.CTkLabel(
            header,
            text=f"GÖSTERİLEN KAYIT: {len(kayitlar)}",
            font=("Arial", 12, "bold"),
        )
        self.kabul_kayit_sayisi.pack(
            side="left",
            padx=4,
        )

        ctk.CTkLabel(
            header,
            text=(
                "Satıra çift tıklayın: Kabul PDF"
            ),
            font=("Arial", 11),
            text_color="#9CA3AF",
        ).pack(
            side="left",
            padx=15,
        )

        ctk.CTkButton(
            header,
            text="SEÇİLİ PDF",
            width=105,
            height=32,
            command=self.depo_kabul_secili_pdf,
        ).pack(
            side="right",
            padx=4,
        )

        ctk.CTkButton(
            header,
            text="SEÇİLİ KAYDI SİL",
            width=140,
            height=32,
            fg_color="#4B5563",
            command=self.depo_kabul_secili_sil,
        ).pack(
            side="right",
            padx=4,
        )

        tree_area = ctk.CTkFrame(
            self.kabul_liste_frame,
            fg_color="transparent",
        )
        tree_area.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(4, 12),
        )
        tree_area.grid_rowconfigure(0, weight=1)
        tree_area.grid_columnconfigure(0, weight=1)

        columns = (
            "id",
            "tarih",
            "hammadde",
            "tedarikci",
            "lot",
            "urt",
            "skt",
            "miktar",
            "durum",
        )

        self.kabul_tree = ttk.Treeview(
            tree_area,
            columns=columns,
            show="headings",
            style="Redbox.Treeview",
            selectmode="browse",
        )

        headings = (
            ("id", "ID", 55, "center", False),
            ("tarih", "KABUL TARİHİ", 125, "w", False),
            ("hammadde", "HAMMADDE", 155, "w", True),
            ("tedarikci", "TEDARİKÇİ", 145, "w", True),
            ("lot", "LOT NO", 125, "w", True),
            ("urt", "ÜRETİM", 95, "center", False),
            ("skt", "SKT / TETT", 95, "center", False),
            ("miktar", "MİKTAR (KG)", 120, "e", False),
            ("durum", "DURUM", 85, "center", False),
        )

        for column, title, width, anchor, stretch in headings:
            self.kabul_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.kabul_tree.column(
                column,
                width=width,
                minwidth=50,
                anchor=anchor,
                stretch=stretch,
            )

        self.kabul_tree.tag_configure(
            "even",
            background="#292929",
        )
        self.kabul_tree.tag_configure(
            "odd",
            background="#303030",
        )
        self.kabul_tree.tag_configure(
            "accepted",
            foreground="#D1FAE5",
        )

        for index, kayit in enumerate(kayitlar):
            row_tag = "even" if index % 2 == 0 else "odd"

            self.kabul_tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["id"],
                    kayit["kabul_tarihi"],
                    kayit["hammadde"],
                    kayit["tedarikci"] or "-",
                    kayit["tedarikci_lot_no"],
                    kayit["uretim_tarihi"] or "-",
                    kayit["skt_tett"] or "-",
                    f'{float(kayit["miktar_kg"]):.3f}',
                    kayit["kabul_durumu"],
                ),
                tags=(
                    row_tag,
                    "accepted"
                    if kayit["kabul_durumu"] == "KABUL"
                    else row_tag,
                ),
            )

        vertical = ttk.Scrollbar(
            tree_area,
            orient="vertical",
            command=self.kabul_tree.yview,
        )
        horizontal = ttk.Scrollbar(
            tree_area,
            orient="horizontal",
            command=self.kabul_tree.xview,
        )
        self.kabul_tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.kabul_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.kabul_tree.bind(
            "<Double-1>",
            lambda _event: self.depo_kabul_secili_pdf(),
        )

    def depo_kabul_secili_pdf(self):
        secim = self.kabul_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "PDF için tablodan bir kayıt seçin.",
            )
            return

        self.hammadde_kabul_pdf_raporu(
            int(secim[0]),
        )

    def depo_kabul_secili_sil(self):
        secim = self.kabul_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "Silmek için tablodan bir kayıt seçin."
            )
            return

        self.depo_kabul_sil(
            int(secim[0])
        )

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

            self.depo_kabul_ozet_guncelle()
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
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.uretim_form_panel = form

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.uretim_liste_panel = liste

        ctk.CTkButton(
            form,
            text="← KAYITLARA DÖN",
            width=160,
            height=36,
            fg_color="#4B5563",
            command=self.uretim_liste_goster,
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 0),
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

        self.uretim_baslama_saati = self.form_entry(
            form,
            "Üretim Başlama Saati (SS:DD)",
            datetime.now().strftime("%H:%M"),
        )

        self.uretim_bitis_saati = self.form_entry(
            form,
            "Üretim Bitiş Saati (SS:DD)",
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

        ctk.CTkLabel(
            form,
            text="HAMMADDE ANALİZİ",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(10,2)
        )

        self.analiz_frame = ctk.CTkFrame(form)
        self.analiz_frame.pack(
            fill="x",
            padx=25,
            pady=(0,10)
        )

        self.analiz_labels = {}

        for ad in (
            "Patates Unu",
            "Nişasta",
            "Mısır Unu",
            "Metilselüloz Benecel A4M E461",
            "Tavuk Çeşnisi",
            "Sarımsak Tozu",
            "Karabiber",
            "Tuz",
            "Proses Suyu",
        ):
            lbl = ctk.CTkLabel(
                self.analiz_frame,
                text=f"{ad}: 0.000 kg",
                anchor="w",
                justify="left",
                font=("Arial",11)
            )
            lbl.pack(
                fill="x",
                pady=1
            )
            self.analiz_labels[ad] = lbl


        aktif_personeller = (
            self.yetkili_personelleri_getir(
                "URETIM"
            )
        )

        if not aktif_personeller:
            aktif_personeller = [
                "AKTİF PERSONEL YOK"
            ]

        ctk.CTkLabel(
            form,
            text="Personel 1"
        ).pack(
            anchor="w",
            padx=25,
            pady=(8, 2)
        )

        self.uretim_personel_1 = (
            ctk.CTkOptionMenu(
                form,
                values=aktif_personeller
            )
        )

        self.uretim_personel_1.pack(
            fill="x",
            padx=25,
            pady=(0, 8)
        )

        self.uretim_personel_1.set(
            aktif_personeller[0]
        )

        ctk.CTkLabel(
            form,
            text="Personel 2"
        ).pack(
            anchor="w",
            padx=25,
            pady=(2, 2)
        )

        self.uretim_personel_2 = (
            ctk.CTkOptionMenu(
                form,
                values=aktif_personeller
            )
        )

        self.uretim_personel_2.pack(
            fill="x",
            padx=25,
            pady=(0, 8)
        )

        if len(aktif_personeller) > 1:
            self.uretim_personel_2.set(
                aktif_personeller[1]
            )
        else:
            self.uretim_personel_2.set(
                aktif_personeller[0]
            )

        self.uretim_aciklama = self.form_entry(
            form,
            "Açıklama"
        )

        ctk.CTkLabel(
            form,
            text="HAMMADDE LOT / PARTİ PLANI",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 4)
        )

        ctk.CTkLabel(
            form,
            text=(
                "Parti sayısını girin. Sistem FIFO lot "
                "planını önerir. Üretim ortasında lot "
                "değişiyorsa aralıkları düzenleyin."
            ),
            justify="left",
            wraplength=350
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 8)
        )

        ctk.CTkButton(
            form,
            text="FIFO LOT PLANINI HAZIRLA",
            command=self.uretim_lot_plani_hazirla,
            height=38,
            width=350
        ).pack(
            padx=25,
            pady=(0, 8)
        )

        self.uretim_lot_plan_frame = (
            ctk.CTkScrollableFrame(
                form,
                width=350,
                height=300
            )
        )
        self.uretim_lot_plan_frame.pack(
            fill="x",
            padx=25,
            pady=(0, 10)
        )

        self.uretim_lot_plan_satirlari = []

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
            text="ÜRETİM KAYITLARI",
            font=("Arial", 18, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 8),
        )

        summary = ctk.CTkFrame(
            liste,
            fg_color="transparent",
        )
        summary.pack(
            fill="x",
            padx=12,
            pady=(0, 8),
        )

        self.uretim_ozet_labels = {}

        cards = (
            ("kayit", "TOPLAM KAYIT", "0"),
            ("net", "TOPLAM NET", "0.000 kg"),
            ("fire", "TOPLAM FİRE", "0.000 kg"),
            ("son", "SON LOT", "-"),
        )

        for key, title, value in cards:
            card = ctk.CTkFrame(
                summary,
                height=78,
                corner_radius=10,
            )
            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=4,
            )
            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 10, "bold"),
                text_color="#9CA3AF",
            ).pack(
                anchor="w",
                padx=12,
                pady=(12, 2),
            )

            label = ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 16, "bold"),
            )
            label.pack(
                anchor="w",
                padx=12,
            )
            self.uretim_ozet_labels[key] = label

        toolbar = ctk.CTkFrame(
            liste,
            corner_radius=8,
        )
        toolbar.pack(
            fill="x",
            padx=15,
            pady=(0, 8),
        )

        self.uretim_arama = ctk.CTkEntry(
            toolbar,
            width=235,
            height=36,
            placeholder_text="Tarih, ürün lotu veya personel ara...",
        )
        self.uretim_arama.pack(
            side="left",
            padx=(10, 5),
            pady=10,
        )
        self.uretim_arama.bind(
            "<KeyRelease>",
            lambda _event: self.uretim_listele(),
        )

        ctk.CTkButton(
            toolbar,
            text="TEMİZLE",
            width=85,
            height=36,
            fg_color="#4B5563",
            command=self.uretim_filtre_temizle,
        ).pack(
            side="left",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            toolbar,
            text="+ YENİ ÜRETİM",
            width=135,
            height=36,
            font=("Arial", 11, "bold"),
            command=self.uretim_form_goster,
        ).pack(
            side="right",
            padx=(5, 10),
            pady=10,
        )

        ctk.CTkButton(
            toolbar,
            text="SEÇİLİ PDF",
            width=105,
            height=36,
            command=self.uretim_secili_pdf,
        ).pack(
            side="right",
            padx=(5, 10),
            pady=10,
        )

        ctk.CTkButton(
            toolbar,
            text="SEÇİLİ KAYDI SİL",
            width=125,
            height=36,
            fg_color="#4B5563",
            command=self.uretim_secili_sil,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        self.uretim_liste_frame = ctk.CTkFrame(
            liste,
            corner_radius=8,
        )
        self.uretim_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

        self.uretim_ozet_guncelle()
        self.uretim_listele()
        self.uretim_form_panel.pack_forget()

    def uretim_form_goster(self):
        self.uretim_liste_panel.pack_forget()
        self.uretim_form_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

    def uretim_liste_goster(self):
        self.uretim_form_panel.pack_forget()
        self.uretim_liste_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.uretim_ozet_guncelle()
        self.uretim_listele()

    def uretim_lot_plani_hazirla(self):
        try:
            parti_text = (
                self.parti_sayisi
                .get()
                .strip()
            )

            if not parti_text:
                raise ValueError(
                    "Önce parti sayısını girin."
                )

            parti = int(parti_text)

            if parti <= 0:
                raise ValueError(
                    "Parti sayısı 0'dan büyük olmalıdır."
                )

            conn = get_connection()

            try:
                plan = lot_parti_plani_oner(
                    conn,
                    parti
                )

                lot_rows = conn.execute("""
                    SELECT
                        dk.id,
                        dk.hammadde_id,
                        h.ad AS hammadde,
                        dk.tedarikci_lot_no,
                        dk.kabul_tarihi
                    FROM depo_kabul dk
                    JOIN hammaddeler h
                      ON h.id = dk.hammadde_id
                    WHERE dk.kabul_durumu = 'KABUL'
                    ORDER BY
                        dk.hammadde_id,
                        substr(dk.kabul_tarihi, 7, 4),
                        substr(dk.kabul_tarihi, 4, 2),
                        substr(dk.kabul_tarihi, 1, 2),
                        dk.id
                """).fetchall()
            finally:
                conn.close()

            for widget in (
                self.uretim_lot_plan_frame
                .winfo_children()
            ):
                widget.destroy()

            self.uretim_lot_plan_satirlari = []

            lotlar_by_hammadde = {}

            for row in lot_rows:
                lotlar_by_hammadde.setdefault(
                    row["hammadde_id"],
                    []
                ).append(row)

            for index, row in enumerate(plan):
                hammadde_id = row["hammadde_id"]

                lot_map = {}

                for lot in lotlar_by_hammadde.get(
                    hammadde_id,
                    []
                ):
                    anahtar = (
                        f'LOT {lot["tedarikci_lot_no"]} | '
                        f'{lot["kabul_tarihi"]}'
                    )

                    lot_map[anahtar] = lot["id"]

                secili_anahtar = None

                for anahtar, depo_id in lot_map.items():
                    if depo_id == row["depo_kabul_id"]:
                        secili_anahtar = anahtar
                        break

                satir = ctk.CTkFrame(
                    self.uretim_lot_plan_frame
                )
                satir.pack(
                    fill="x",
                    padx=4,
                    pady=4
                )

                ctk.CTkLabel(
                    satir,
                    text=row["hammadde"],
                    font=("Arial", 12, "bold")
                ).pack(
                    anchor="w",
                    padx=8,
                    pady=(6, 2)
                )

                lot_secim = ctk.CTkComboBox(
                    satir,
                    values=list(lot_map.keys()),
                    width=310
                )
                lot_secim.pack(
                    padx=8,
                    pady=2
                )

                if secili_anahtar:
                    lot_secim.set(secili_anahtar)

                aralik_frame = ctk.CTkFrame(satir)
                aralik_frame.pack(
                    fill="x",
                    padx=8,
                    pady=(2, 6)
                )

                ctk.CTkLabel(
                    aralik_frame,
                    text="Başlangıç"
                ).pack(
                    side="left",
                    padx=(4, 2)
                )

                baslangic = ctk.CTkEntry(
                    aralik_frame,
                    width=55
                )
                baslangic.pack(
                    side="left",
                    padx=2
                )
                baslangic.insert(
                    0,
                    str(row["parti_baslangic"])
                )

                ctk.CTkLabel(
                    aralik_frame,
                    text="Bitiş"
                ).pack(
                    side="left",
                    padx=(8, 2)
                )

                bitis = ctk.CTkEntry(
                    aralik_frame,
                    width=55
                )
                bitis.pack(
                    side="left",
                    padx=2
                )
                bitis.insert(
                    0,
                    str(row["parti_bitis"])
                )

                self.uretim_lot_plan_satirlari.append({
                    "hammadde_id": hammadde_id,
                    "hammadde": row["hammadde"],
                    "lot_secim": lot_secim,
                    "lot_map": lot_map,
                    "parti_baslangic": baslangic,
                    "parti_bitis": bitis,
                })

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "FIFO lot-parti planı hazırlandı.\n\n"
                    "Üretimde gerçek lot geçişi farklıysa "
                    "aralıkları ve lotları kontrol ederek "
                    "düzenleyin."
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Lot Planı Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Lot planı hazırlanamadı:\n{hata}"
            )

    def uretim_lot_plani_getir(self):
        if not self.uretim_lot_plan_satirlari:
            raise ValueError(
                "Hammadde lot-parti planı hazırlanmalıdır."
            )

        plan = []

        for row in self.uretim_lot_plan_satirlari:
            secim = (
                row["lot_secim"]
                .get()
                .strip()
            )

            if secim not in row["lot_map"]:
                raise ValueError(
                    f'{row["hammadde"]}: '
                    f'geçerli lot seçilmelidir.'
                )

            baslangic_text = (
                row["parti_baslangic"]
                .get()
                .strip()
            )

            bitis_text = (
                row["parti_bitis"]
                .get()
                .strip()
            )

            if not baslangic_text or not bitis_text:
                raise ValueError(
                    f'{row["hammadde"]}: '
                    f'parti aralığı boş bırakılamaz.'
                )

            plan.append({
                "hammadde_id": row["hammadde_id"],
                "depo_kabul_id": row["lot_map"][secim],
                "parti_baslangic": int(baslangic_text),
                "parti_bitis": int(bitis_text),
            })

        return plan

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

            analiz = denge.get("analiz", {})

            for ad, lbl in self.analiz_labels.items():
                miktar = analiz.get(ad, 0.0)
                lbl.configure(
                    text=f"{ad}: {miktar:.3f} kg"
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
            baslama_saati = (
                self.uretim_baslama_saati.get().strip()
            )
            bitis_saati = (
                self.uretim_bitis_saati.get().strip()
            )
            lot_no = self.urun_lot_no.get().strip()
            parti_text = self.parti_sayisi.get().strip()
            fire_text = self.uretim_firesi.get().strip().replace(",", ".")
            aciklama = self.uretim_aciklama.get().strip()

            personel_1 = (
                self.uretim_personel_1
                .get()
                .strip()
            )

            personel_2 = (
                self.uretim_personel_2
                .get()
                .strip()
            )

            if not tarih:
                raise ValueError("Üretim tarihi boş bırakılamaz.")

            uretim_suresi_dakika = (
                self.calisma_suresi_hesapla(
                    baslama_saati,
                    bitis_saati,
                    "Üretim",
                )
            )

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

            aktif_personeller = (
                self.yetkili_personelleri_getir(
                "URETIM"
            )
            )

            if personel_1 not in aktif_personeller:
                raise ValueError(
                    "Personel 1 aktif personel "
                    "listesinde bulunmuyor."
                )

            if personel_2 not in aktif_personeller:
                raise ValueError(
                    "Personel 2 aktif personel "
                    "listesinde bulunmuyor."
                )

            if personel_1 == personel_2:
                raise ValueError(
                    "Personel 1 ve Personel 2 "
                    "aynı kişi olamaz."
                )

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
                        baslama_saati,
                        bitis_saati,
                        uretim_suresi_dakika,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    baslama_saati,
                    bitis_saati,
                    uretim_suresi_dakika,
                    lot_no,
                    parti,
                    teorik,
                    fire,
                    net,
                    personel_1,
                    personel_2,
                    aciklama,
                    datetime.now().isoformat(timespec="seconds")
                ))

                uretim_id = cursor.lastrowid

                lot_parti_plani = (
                    self.uretim_lot_plani_getir()
                )

                uretim_stok_isle(
                    conn,
                    uretim_id,
                    parti,
                    lot_parti_plani=lot_parti_plani
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

    def uretim_ozet_guncelle(self):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS kayit_sayisi,
                    COALESCE(SUM(net_uretim_kg), 0) AS net_kg,
                    COALESCE(SUM(uretim_firesi_kg), 0) AS fire_kg
                FROM uretim
            """).fetchone()

            son = conn.execute("""
                SELECT urun_lot_no
                FROM uretim
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()
        finally:
            conn.close()

        self.uretim_ozet_labels["kayit"].configure(
            text=str(int(row["kayit_sayisi"])),
        )
        self.uretim_ozet_labels["net"].configure(
            text=f'{float(row["net_kg"]):.3f} kg',
        )
        self.uretim_ozet_labels["fire"].configure(
            text=f'{float(row["fire_kg"]):.3f} kg',
        )
        self.uretim_ozet_labels["son"].configure(
            text=son["urun_lot_no"] if son else "-",
        )

    def uretim_filtre_temizle(self):
        self.uretim_arama.delete(0, "end")
        self.uretim_listele()

    def uretim_secili_pdf(self):
        secim = self.uretim_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "PDF için tablodan bir üretim kaydı seçin.",
            )
            return

        self.uretim_pdf_raporu(int(secim[0]))

    def uretim_secili_sil(self):
        secim = self.uretim_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "Silmek için tablodan bir üretim kaydı seçin.",
            )
            return

        self.uretim_sil(int(secim[0]))

    def uretim_listele(self):
        for widget in self.uretim_liste_frame.winfo_children():
            widget.destroy()

        arama = ""
        if hasattr(self, "uretim_arama"):
            arama = self.uretim_arama.get().strip()

        like = f"%{arama}%"

        conn = get_connection()
        try:
            kayitlar = conn.execute("""
                SELECT
                    id,
                    uretim_tarihi,
                    baslama_saati,
                    bitis_saati,
                    uretim_suresi_dakika,
                    urun_lot_no,
                    parti_sayisi,
                    teorik_uretim_kg,
                    uretim_firesi_kg,
                    net_uretim_kg,
                    personel_1,
                    personel_2
                FROM uretim
                WHERE (
                    ? = ''
                    OR uretim_tarihi LIKE ?
                    OR urun_lot_no LIKE ?
                    OR COALESCE(personel_1, '') LIKE ?
                    OR COALESCE(personel_2, '') LIKE ?
                )
                ORDER BY id DESC
                LIMIT 200
            """, (
                arama,
                like,
                like,
                like,
                like,
            )).fetchall()
        finally:
            conn.close()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Production.Treeview",
            background="#2b2b2b",
            fieldbackground="#2b2b2b",
            foreground="#e5e7eb",
            rowheight=38,
            borderwidth=0,
            font=("Arial", 11),
        )
        style.configure(
            "Production.Treeview.Heading",
            background="#343434",
            foreground="#e5e7eb",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Production.Treeview",
            background=[("selected", "#1f6aa5")],
            foreground=[("selected", "#ffffff")],
        )

        info = ctk.CTkLabel(
            self.uretim_liste_frame,
            text=f"GÖSTERİLEN KAYIT: {len(kayitlar)}",
            font=("Arial", 11, "bold"),
            text_color="#9CA3AF",
        )
        info.pack(
            anchor="w",
            padx=12,
            pady=(10, 5),
        )

        tree_area = ctk.CTkFrame(
            self.uretim_liste_frame,
            fg_color="transparent",
        )
        tree_area.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )
        tree_area.grid_rowconfigure(0, weight=1)
        tree_area.grid_columnconfigure(0, weight=1)

        columns = (
            "tarih",
            "saat",
            "sure",
            "lot",
            "parti",
            "teorik",
            "fire",
            "net",
        )

        self.uretim_tree = ttk.Treeview(
            tree_area,
            columns=columns,
            show="headings",
            style="Production.Treeview",
            selectmode="browse",
        )

        headings = (
            ("tarih", "TARİH", 85, "w"),
            ("saat", "BAŞLANGIÇ–BİTİŞ", 125, "center"),
            ("sure", "SÜRE", 85, "center"),
            ("lot", "ÜRÜN LOTU", 110, "w"),
            ("parti", "PARTİ", 55, "center"),
            ("teorik", "TEORİK KG", 82, "e"),
            ("fire", "FİRE KG", 68, "e"),
            ("net", "NET KG", 82, "e"),
        )

        for column, title, width, anchor in headings:
            self.uretim_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.uretim_tree.column(
                column,
                width=width,
                minwidth=55,
                anchor=anchor,
                stretch=True,
            )

        self.uretim_tree.tag_configure(
            "even",
            background="#292929",
        )
        self.uretim_tree.tag_configure(
            "odd",
            background="#303030",
        )

        for index, kayit in enumerate(kayitlar):
            self.uretim_tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["uretim_tarihi"],
                    (
                        f'{kayit["baslama_saati"]}–'
                        f'{kayit["bitis_saati"]}'
                        if kayit["baslama_saati"]
                        and kayit["bitis_saati"]
                        else "-"
                    ),
                    (
                        f'{int(kayit["uretim_suresi_dakika"]) // 60} sa '
                        f'{int(kayit["uretim_suresi_dakika"]) % 60} dk'
                        if kayit["uretim_suresi_dakika"] is not None
                        else "-"
                    ),
                    kayit["urun_lot_no"],
                    int(kayit["parti_sayisi"]),
                    f'{float(kayit["teorik_uretim_kg"]):.3f}',
                    f'{float(kayit["uretim_firesi_kg"]):.3f}',
                    f'{float(kayit["net_uretim_kg"]):.3f}',
                ),
                tags=(
                    "even"
                    if index % 2 == 0
                    else "odd",
                ),
            )

        scrollbar = ttk.Scrollbar(
            tree_area,
            orient="vertical",
            command=self.uretim_tree.yview,
        )
        self.uretim_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.uretim_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.uretim_tree.bind(
            "<Double-1>",
            lambda _event: self.uretim_secili_pdf(),
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

            self.uretim_ozet_guncelle()
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
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.paketleme_form_panel = form

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.paketleme_liste_panel = liste

        ctk.CTkButton(
            form,
            text="← KAYITLARA DÖN",
            width=160,
            height=36,
            fg_color="#4B5563",
            command=self.paketleme_liste_goster,
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 0),
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

        self.paketleme_baslama_saati = self.form_entry(
            form,
            "Paketleme Başlama Saati (SS:DD)",
            datetime.now().strftime("%H:%M"),
        )

        self.paketleme_bitis_saati = self.form_entry(
            form,
            "Paketleme Bitiş Saati (SS:DD)",
        )

        ctk.CTkLabel(
            form,
            text="Üretim Lotu",
            width=350,
            anchor="w",
        ).pack(
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
        self.paketleme_stok_label.configure(
            width=350,
            anchor="w",
        )
        self.paketleme_stok_label.pack(
            pady=(5, 15)
        )

        ctk.CTkLabel(
            form,
            text="Ambalaj",
            width=350,
            anchor="w",
        ).pack(
            pady=(5, 2)
        )

        self.ambalaj_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=["500 g", "2.5 kg"],
            command=self.paketleme_hesapla
        )
        self.ambalaj_secim.pack(
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
            text="PAKETLEME KAYITLARI",
            font=("Arial", 18, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 8),
        )

        summary = ctk.CTkFrame(
            liste,
            fg_color="transparent",
        )
        summary.pack(
            fill="x",
            padx=12,
            pady=(0, 8),
        )

        self.paketleme_ozet_labels = {}

        cards = (
            ("kayit", "TOPLAM KAYIT", "0"),
            ("paket", "TOPLAM PAKET", "0"),
            ("kg", "PAKETLENEN", "0.000 kg"),
            ("fire", "TOPLAM FİRE", "0.000 kg"),
        )

        for key, title, value in cards:
            card = ctk.CTkFrame(
                summary,
                height=78,
                corner_radius=10,
            )
            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=4,
            )
            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 10, "bold"),
                text_color="#9CA3AF",
            ).pack(
                anchor="w",
                padx=12,
                pady=(12, 2),
            )

            label = ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 16, "bold"),
            )
            label.pack(
                anchor="w",
                padx=12,
            )
            self.paketleme_ozet_labels[key] = label

        toolbar = ctk.CTkFrame(
            liste,
            corner_radius=8,
        )
        toolbar.pack(
            fill="x",
            padx=15,
            pady=(0, 8),
        )

        self.paketleme_arama = ctk.CTkEntry(
            toolbar,
            width=300,
            height=36,
            placeholder_text=(
                "Tarih, üretim lotu veya ambalaj ara..."
            ),
        )
        self.paketleme_arama.pack(
            side="left",
            padx=(10, 5),
            pady=10,
        )
        self.paketleme_arama.bind(
            "<KeyRelease>",
            lambda _event: self.paketleme_listele(),
        )

        ctk.CTkButton(
            toolbar,
            text="TEMİZLE",
            width=85,
            height=36,
            fg_color="#4B5563",
            command=self.paketleme_filtre_temizle,
        ).pack(
            side="left",
            padx=5,
            pady=10,
        )

        ctk.CTkButton(
            toolbar,
            text="+ YENİ PAKETLEME",
            width=160,
            height=36,
            font=("Arial", 11, "bold"),
            command=self.paketleme_form_goster,
        ).pack(
            side="right",
            padx=(5, 10),
            pady=10,
        )

        ctk.CTkButton(
            toolbar,
            text="SEÇİLİ PDF",
            width=110,
            height=36,
            command=self.paketleme_secili_pdf,
        ).pack(
            side="right",
            padx=5,
            pady=10,
        )

        self.paketleme_liste_frame = ctk.CTkFrame(
            liste,
            corner_radius=8,
        )
        self.paketleme_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

        self.paketleme_ozet_guncelle()
        self.paketleme_listele()
        self.paketleme_form_panel.pack_forget()

    def paketleme_form_goster(self):
        self.paketleme_liste_panel.pack_forget()
        self.paketleme_form_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

    def paketleme_liste_goster(self):
        self.paketleme_form_panel.pack_forget()
        self.paketleme_liste_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.paketleme_ozet_guncelle()
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
            baslama_saati = (
                self.paketleme_baslama_saati.get().strip()
            )
            bitis_saati = (
                self.paketleme_bitis_saati.get().strip()
            )
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

            paketleme_suresi_dakika = (
                self.calisma_suresi_hesapla(
                    baslama_saati,
                    bitis_saati,
                    "Paketleme",
                )
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
                        baslama_saati,
                        bitis_saati,
                        paketleme_suresi_dakika,
                        uretim_id,
                        ambalaj_gram,
                        paket_adedi,
                        koli_ici_adet,
                        paketlenen_kg,
                        paketleme_firesi_kg,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    baslama_saati,
                    bitis_saati,
                    paketleme_suresi_dakika,
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

                paketleme_id = conn.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]

                mamul_stok_hareketi_ekle(
                    conn=conn,
                    paketleme_id=paketleme_id,
                    hareket_tarihi=tarih,
                    hareket_tipi="PAKETLEME",
                    yon="GIRIS",
                    paket_adedi=adet,
                )

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


    def paketleme_ozet_guncelle(self):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS kayit_sayisi,
                    COALESCE(SUM(paket_adedi), 0) AS paket_adedi,
                    COALESCE(SUM(paketlenen_kg), 0) AS paketlenen_kg,
                    COALESCE(
                        SUM(paketleme_firesi_kg),
                        0
                    ) AS fire_kg
                FROM paketleme
            """).fetchone()
        finally:
            conn.close()

        self.paketleme_ozet_labels["kayit"].configure(
            text=str(int(row["kayit_sayisi"])),
        )
        self.paketleme_ozet_labels["paket"].configure(
            text=str(int(row["paket_adedi"])),
        )
        self.paketleme_ozet_labels["kg"].configure(
            text=f'{float(row["paketlenen_kg"]):.3f} kg',
        )
        self.paketleme_ozet_labels["fire"].configure(
            text=f'{float(row["fire_kg"]):.3f} kg',
        )

    def paketleme_filtre_temizle(self):
        self.paketleme_arama.delete(0, "end")
        self.paketleme_listele()

    def paketleme_secili_pdf(self):
        secim = self.paketleme_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "PDF için tablodan bir paketleme kaydı seçin.",
            )
            return

        self.paketleme_pdf_raporu(int(secim[0]))

    def paketleme_listele(self):
        for widget in (
            self.paketleme_liste_frame.winfo_children()
        ):
            widget.destroy()

        arama = ""
        if hasattr(self, "paketleme_arama"):
            arama = self.paketleme_arama.get().strip()

        like = f"%{arama}%"

        conn = get_connection()
        try:
            kayitlar = conn.execute("""
                SELECT
                    p.id,
                    p.paketleme_tarihi,
                    p.baslama_saati,
                    p.bitis_saati,
                    p.paketleme_suresi_dakika,
                    u.urun_lot_no,
                    p.ambalaj_gram,
                    p.paket_adedi,
                    p.koli_ici_adet,
                    p.paketlenen_kg,
                    p.paketleme_firesi_kg
                FROM paketleme p
                JOIN uretim u
                  ON u.id = p.uretim_id
                WHERE (
                    ? = ''
                    OR p.paketleme_tarihi LIKE ?
                    OR u.urun_lot_no LIKE ?
                    OR CAST(p.ambalaj_gram AS TEXT) LIKE ?
                )
                ORDER BY p.id DESC
                LIMIT 200
            """, (
                arama,
                like,
                like,
                like,
            )).fetchall()
        finally:
            conn.close()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Packaging.Treeview",
            background="#2b2b2b",
            fieldbackground="#2b2b2b",
            foreground="#e5e7eb",
            rowheight=38,
            borderwidth=0,
            font=("Arial", 11),
        )
        style.configure(
            "Packaging.Treeview.Heading",
            background="#343434",
            foreground="#e5e7eb",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Packaging.Treeview",
            background=[("selected", "#1f6aa5")],
            foreground=[("selected", "#ffffff")],
        )

        ctk.CTkLabel(
            self.paketleme_liste_frame,
            text=f"GÖSTERİLEN KAYIT: {len(kayitlar)}",
            font=("Arial", 11, "bold"),
            text_color="#9CA3AF",
        ).pack(
            anchor="w",
            padx=12,
            pady=(10, 5),
        )

        tree_area = ctk.CTkFrame(
            self.paketleme_liste_frame,
            fg_color="transparent",
        )
        tree_area.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )
        tree_area.grid_rowconfigure(0, weight=1)
        tree_area.grid_columnconfigure(0, weight=1)

        columns = (
            "tarih",
            "saat",
            "sure",
            "lot",
            "ambalaj",
            "paket",
            "koli_ici",
            "kg",
            "fire",
        )

        self.paketleme_tree = ttk.Treeview(
            tree_area,
            columns=columns,
            show="headings",
            style="Packaging.Treeview",
            selectmode="browse",
        )

        headings = (
            ("tarih", "TARİH", 82, "w"),
            ("saat", "BAŞLANGIÇ–BİTİŞ", 120, "center"),
            ("sure", "SÜRE", 82, "center"),
            ("lot", "ÜRETİM LOTU", 105, "w"),
            ("ambalaj", "AMBALAJ", 75, "center"),
            ("paket", "PAKET", 65, "e"),
            ("koli_ici", "KOLİ İÇİ", 65, "e"),
            ("kg", "PAKETLENEN KG", 100, "e"),
            ("fire", "FİRE KG", 70, "e"),
        )

        for column, title, width, anchor in headings:
            self.paketleme_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.paketleme_tree.column(
                column,
                width=width,
                minwidth=60,
                anchor=anchor,
                stretch=True,
            )

        self.paketleme_tree.tag_configure(
            "even",
            background="#292929",
        )
        self.paketleme_tree.tag_configure(
            "odd",
            background="#303030",
        )

        for index, kayit in enumerate(kayitlar):
            gram = int(kayit["ambalaj_gram"])
            ambalaj = (
                "500 g"
                if gram == 500
                else "2.5 kg"
                if gram == 2500
                else f"{gram} g"
            )

            self.paketleme_tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["paketleme_tarihi"],
                    (
                        f'{kayit["baslama_saati"]}–'
                        f'{kayit["bitis_saati"]}'
                        if kayit["baslama_saati"]
                        and kayit["bitis_saati"]
                        else "-"
                    ),
                    (
                        f'{int(kayit["paketleme_suresi_dakika"]) // 60} sa '
                        f'{int(kayit["paketleme_suresi_dakika"]) % 60} dk'
                        if kayit["paketleme_suresi_dakika"] is not None
                        else "-"
                    ),
                    kayit["urun_lot_no"],
                    ambalaj,
                    int(kayit["paket_adedi"]),
                    int(kayit["koli_ici_adet"] or 0),
                    f'{float(kayit["paketlenen_kg"]):.3f}',
                    f'{float(kayit["paketleme_firesi_kg"]):.3f}',
                ),
                tags=(
                    "even"
                    if index % 2 == 0
                    else "odd",
                ),
            )

        scrollbar = ttk.Scrollbar(
            tree_area,
            orient="vertical",
            command=self.paketleme_tree.yview,
        )
        self.paketleme_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.paketleme_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.paketleme_tree.bind(
            "<Double-1>",
            lambda _event: self.paketleme_secili_pdf(),
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
            label_text="",
        )

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        self.sevkiyat_form_panel = form
        self.sevkiyat_liste_panel = liste

        ctk.CTkButton(
            form,
            text="← KAYITLARA DÖN",
            width=160,
            height=36,
            fg_color="#4B5563",
            command=self.sevkiyat_liste_goster,
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 0),
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
            text="Müşteri / Sevk Noktası",
            width=350,
            anchor="w",
        ).pack(
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
            text="Mamul Stok / Ürün Lotu",
            width=350,
            anchor="w",
        ).pack(
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
            text="Soğuk Zincir",
            width=350,
            anchor="w",
        ).pack(
            pady=(5, 2)
        )

        self.soguk_zincir_secim = ctk.CTkComboBox(
            form,
            width=350,
            values=["EVET", "HAYIR"],
            state="readonly"
        )
        self.soguk_zincir_secim.pack(
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

        ust = ctk.CTkFrame(
            liste,
            fg_color="transparent",
        )
        ust.pack(
            fill="x",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            ust,
            text="SEVKİYAT KAYITLARI",
            font=("Arial", 22, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            ust,
            text="+ YENİ SEVKİYAT",
            width=170,
            height=40,
            font=("Arial", 13, "bold"),
            command=self.sevkiyat_form_goster,
        ).pack(side="right")

        kpi_alani = ctk.CTkFrame(
            liste,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        self.sevkiyat_kpi_labels = []

        for baslik in (
            "TOPLAM KAYIT",
            "TOPLAM PAKET",
            "SEVK EDİLEN KG",
            "MÜŞTERİ SAYISI",
        ):
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.pack(
                side="left",
                fill="x",
                expand=True,
                padx=5,
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=baslik,
                font=("Arial", 11, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            deger = ctk.CTkLabel(
                kart,
                text="0",
                font=("Arial", 21, "bold"),
            )
            deger.pack()
            self.sevkiyat_kpi_labels.append(deger)

        araclar = ctk.CTkFrame(
            liste,
            fg_color="transparent",
        )
        araclar.pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        self.sevkiyat_arama = ctk.CTkEntry(
            araclar,
            placeholder_text=(
                "Tarih, müşteri, plaka, belge veya lot ara..."
            ),
            height=38,
        )
        self.sevkiyat_arama.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8),
        )
        self.sevkiyat_arama.bind(
            "<KeyRelease>",
            lambda event: self.sevkiyat_listele(),
        )

        ctk.CTkButton(
            araclar,
            text="TEMİZLE",
            width=95,
            height=38,
            fg_color="#4B5563",
            command=self.sevkiyat_filtre_temizle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            araclar,
            text="SEÇİLİ PDF",
            width=125,
            height=38,
            command=self.sevkiyat_secili_pdf,
        ).pack(side="left")

        self.sevkiyat_liste_frame = ctk.CTkFrame(
            liste
        )
        self.sevkiyat_liste_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20),
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

                dagitim = sevkiyat_stok_dus(
                    conn=conn,
                    sevkiyat_id=sevkiyat_id,
                    uretim_id=stok["uretim_id"],
                    ambalaj_gram=stok["ambalaj_gram"],
                    paket_adedi=toplam_paket
                )

                for satir in dagitim:
                    sevkiyat_hareketi_ekle(
                        conn=conn,
                        paketleme_id=satir["paketleme_id"],
                        hareket_tarihi=tarih,
                        paket_adedi=satir["paket_adedi"],
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


    def sevkiyat_form_goster(self):
        self.sevkiyat_liste_panel.pack_forget()
        self.sevkiyat_form_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

    def sevkiyat_liste_goster(self):
        self.sevkiyat_form_panel.pack_forget()
        self.sevkiyat_liste_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.sevkiyat_listele()

    def sevkiyat_filtre_temizle(self):
        self.sevkiyat_arama.delete(0, "end")
        self.sevkiyat_listele()

    def sevkiyat_secili_pdf(self):
        secim = self.sevkiyat_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                "PDF için tablodan bir sevkiyat kaydı seçin.",
            )
            return

        self.sevkiyat_pdf_raporu(int(secim[0]))

    def sevkiyat_ozet_guncelle(self, arama=""):
        like = f"%{arama.casefold()}%"
        conn = get_connection()
        conn.create_function(
            "TR_CASEFOLD",
            1,
            lambda value: (
                str(value).casefold()
                if value is not None
                else ""
            ),
        )

        try:
            ozet = conn.execute("""
                SELECT
                    COUNT(DISTINCT s.id) AS toplam_kayit,
                    COALESCE(
                        SUM(sk.paket_adedi),
                        0
                    ) AS toplam_paket,
                    COALESCE(
                        SUM(sk.sevk_kg),
                        0
                    ) AS toplam_kg,
                    COUNT(
                        DISTINCT COALESCE(
                            s.musteri_id,
                            s.musteri
                        )
                    ) AS musteri_sayisi
                FROM sevkiyat s
                LEFT JOIN sevkiyat_kalemleri sk
                  ON sk.sevkiyat_id = s.id
                LEFT JOIN paketleme p
                  ON p.id = sk.paketleme_id
                LEFT JOIN uretim u
                  ON u.id = p.uretim_id
                WHERE (
                    ? = ''
                    OR TR_CASEFOLD(
                        s.sevkiyat_tarihi
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.musteri, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.arac_plaka, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.belge_no, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(u.urun_lot_no, '')
                    ) LIKE ?
                )
            """, (
                arama,
                like,
                like,
                like,
                like,
                like,
            )).fetchone()
        finally:
            conn.close()

        degerler = (
            str(int(ozet["toplam_kayit"] or 0)),
            f'{int(ozet["toplam_paket"] or 0):,}'.replace(
                ",",
                ".",
            ),
            f'{float(ozet["toplam_kg"] or 0):.3f}',
            str(int(ozet["musteri_sayisi"] or 0)),
        )

        for label, deger in zip(
            self.sevkiyat_kpi_labels,
            degerler,
        ):
            label.configure(text=deger)

    def sevkiyat_listele(self):
        for widget in (
            self.sevkiyat_liste_frame.winfo_children()
        ):
            widget.destroy()

        arama = ""
        if hasattr(self, "sevkiyat_arama"):
            arama = self.sevkiyat_arama.get().strip()

        like = f"%{arama.casefold()}%"
        conn = get_connection()
        conn.create_function(
            "TR_CASEFOLD",
            1,
            lambda value: (
                str(value).casefold()
                if value is not None
                else ""
            ),
        )

        try:
            kayitlar = conn.execute("""
                SELECT
                    s.id,
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.arac_plaka,
                    s.belge_no,
                    s.soguk_zincir,
                    COALESCE(
                        SUM(sk.paket_adedi),
                        0
                    ) AS toplam_paket,
                    COALESCE(
                        SUM(sk.sevk_kg),
                        0
                    ) AS toplam_kg,
                    COUNT(
                        DISTINCT u.urun_lot_no
                    ) AS lot_sayisi
                FROM sevkiyat s
                LEFT JOIN sevkiyat_kalemleri sk
                  ON sk.sevkiyat_id = s.id
                LEFT JOIN paketleme p
                  ON p.id = sk.paketleme_id
                LEFT JOIN uretim u
                  ON u.id = p.uretim_id
                WHERE (
                    ? = ''
                    OR TR_CASEFOLD(
                        s.sevkiyat_tarihi
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.musteri, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.arac_plaka, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(s.belge_no, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(u.urun_lot_no, '')
                    ) LIKE ?
                )
                GROUP BY
                    s.id,
                    s.sevkiyat_tarihi,
                    s.musteri,
                    s.arac_plaka,
                    s.belge_no,
                    s.soguk_zincir
                ORDER BY s.id DESC
                LIMIT 200
            """, (
                arama,
                like,
                like,
                like,
                like,
                like,
            )).fetchall()
        finally:
            conn.close()

        self.sevkiyat_ozet_guncelle(arama)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Shipment.Treeview",
            background="#292929",
            foreground="#F3F4F6",
            fieldbackground="#292929",
            borderwidth=0,
            rowheight=36,
            font=("Arial", 12),
        )
        style.configure(
            "Shipment.Treeview.Heading",
            background="#1F2937",
            foreground="#F9FAFB",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Shipment.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        tree_area = ctk.CTkFrame(
            self.sevkiyat_liste_frame
        )
        tree_area.pack(
            fill="both",
            expand=True,
        )
        tree_area.grid_rowconfigure(0, weight=1)
        tree_area.grid_columnconfigure(0, weight=1)

        columns = (
            "tarih",
            "musteri",
            "paket",
            "kg",
            "lot",
            "plaka",
            "belge",
            "soguk",
        )

        self.sevkiyat_tree = ttk.Treeview(
            tree_area,
            columns=columns,
            show="headings",
            style="Shipment.Treeview",
            selectmode="browse",
        )

        headings = (
            ("tarih", "TARİH", 95, "w"),
            ("musteri", "MÜŞTERİ / SEVK NOKTASI", 210, "w"),
            ("paket", "TOPLAM PAKET", 105, "e"),
            ("kg", "SEVK KG", 95, "e"),
            ("lot", "LOT SAYISI", 85, "center"),
            ("plaka", "ARAÇ PLAKA", 105, "center"),
            ("belge", "BELGE NO", 115, "w"),
            ("soguk", "SOĞUK ZİNCİR", 105, "center"),
        )

        for column, title, width, anchor in headings:
            self.sevkiyat_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.sevkiyat_tree.column(
                column,
                width=width,
                minwidth=70,
                anchor=anchor,
                stretch=True,
            )

        self.sevkiyat_tree.tag_configure(
            "even",
            background="#292929",
        )
        self.sevkiyat_tree.tag_configure(
            "odd",
            background="#303030",
        )

        for index, kayit in enumerate(kayitlar):
            self.sevkiyat_tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["sevkiyat_tarihi"],
                    kayit["musteri"] or "-",
                    int(kayit["toplam_paket"] or 0),
                    f'{float(kayit["toplam_kg"] or 0):.3f}',
                    int(kayit["lot_sayisi"] or 0),
                    kayit["arac_plaka"] or "-",
                    kayit["belge_no"] or "-",
                    (
                        "EVET"
                        if kayit["soguk_zincir"]
                        else "HAYIR"
                    ),
                ),
                tags=(
                    "even"
                    if index % 2 == 0
                    else "odd",
                ),
            )

        vertical = ttk.Scrollbar(
            tree_area,
            orient="vertical",
            command=self.sevkiyat_tree.yview,
        )
        horizontal = ttk.Scrollbar(
            tree_area,
            orient="horizontal",
            command=self.sevkiyat_tree.xview,
        )

        self.sevkiyat_tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.sevkiyat_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.sevkiyat_tree.bind(
            "<Double-1>",
            lambda event: self.sevkiyat_secili_pdf(),
        )

    def sevkiyat_raporu(self):
        self.show_page(
            "SEVKİYAT RAPORU",
            "Tarih aralığı ve müşteri bazlı sevkiyat analizi"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30),
        )

        filtre = ctk.CTkFrame(ana_frame)
        filtre.pack(
            fill="x",
            padx=10,
            pady=(10, 12),
        )

        ctk.CTkLabel(
            filtre,
            text="RAPOR FİLTRELERİ",
            font=("Arial", 17, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(16, 10),
        )

        alanlar = ctk.CTkFrame(
            filtre,
            fg_color="transparent",
        )
        alanlar.pack(
            fill="x",
            padx=15,
            pady=(0, 16),
        )

        for index in range(4):
            alanlar.grid_columnconfigure(
                index,
                weight=1,
                uniform="shipment_report_filter",
            )

        ctk.CTkLabel(
            alanlar,
            text="Başlangıç Tarihi",
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=5,
            pady=(0, 4),
        )

        ctk.CTkLabel(
            alanlar,
            text="Bitiş Tarihi",
            anchor="w",
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=5,
            pady=(0, 4),
        )

        ctk.CTkLabel(
            alanlar,
            text="Müşteri / Sevk Noktası",
            anchor="w",
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=5,
            pady=(0, 4),
        )

        ctk.CTkLabel(
            alanlar,
            text="İşlem",
            anchor="w",
        ).grid(
            row=0,
            column=3,
            sticky="ew",
            padx=5,
            pady=(0, 4),
        )

        self.rapor_baslangic = ctk.CTkEntry(
            alanlar,
            height=40,
        )
        self.rapor_baslangic.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=5,
        )
        self.rapor_baslangic.insert(0, "01.01.2026")

        self.rapor_bitis = ctk.CTkEntry(
            alanlar,
            height=40,
        )
        self.rapor_bitis.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=5,
        )
        self.rapor_bitis.insert(
            0,
            datetime.now().strftime("%d.%m.%Y"),
        )

        conn = get_connection()
        try:
            musteriler = conn.execute("""
                SELECT
                    id,
                    musteri_adi
                FROM musteriler
                WHERE aktif = 1
                ORDER BY musteri_adi
            """).fetchall()
        finally:
            conn.close()

        self.rapor_musteri_map = {
            row["musteri_adi"]: row["id"]
            for row in musteriler
        }

        musteri_degerleri = [
            "TÜMÜ",
            *self.rapor_musteri_map.keys(),
        ]

        self.rapor_musteri_secim = ctk.CTkComboBox(
            alanlar,
            values=musteri_degerleri,
            state="readonly",
            height=40,
        )
        self.rapor_musteri_secim.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=5,
        )
        self.rapor_musteri_secim.set("TÜMÜ")

        ctk.CTkButton(
            alanlar,
            text="RAPORU GETİR",
            command=self.sevkiyat_raporu_getir,
            height=40,
            font=("Arial", 13, "bold"),
        ).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=5,
        )

        self.sevkiyat_rapor_sonuc = ctk.CTkScrollableFrame(
            ana_frame
        )
        self.sevkiyat_rapor_sonuc.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        ctk.CTkLabel(
            self.sevkiyat_rapor_sonuc,
            text=(
                "Rapor oluşturmak için tarih aralığını "
                "ve müşteri filtresini seçin."
            ),
            font=("Arial", 15),
            text_color="#A3A3A3",
        ).pack(pady=35)

    def sevkiyat_rapor_tablo(
        self,
        baslik,
        sutunlar,
        satirlar,
    ):
        ctk.CTkLabel(
            self.sevkiyat_rapor_sonuc,
            text=baslik,
            font=("Arial", 18, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(18, 8),
        )

        tablo = ctk.CTkFrame(
            self.sevkiyat_rapor_sonuc,
            fg_color="transparent",
        )
        tablo.pack(
            fill="x",
            padx=10,
            pady=(0, 10),
        )

        for index in range(len(sutunlar)):
            tablo.grid_columnconfigure(
                index,
                weight=1,
                uniform="shipment_report_table",
            )

        for column, baslik_metni in enumerate(sutunlar):
            ctk.CTkLabel(
                tablo,
                text=baslik_metni,
                height=38,
                fg_color="#1F2937",
                font=("Arial", 10, "bold"),
                wraplength=135,
            ).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=1,
                pady=1,
            )

        for row_index, satir in enumerate(satirlar, 1):
            renk = (
                "#292929"
                if row_index % 2
                else "#303030"
            )

            for column, deger in enumerate(satir):
                ctk.CTkLabel(
                    tablo,
                    text=str(deger),
                    height=38,
                    fg_color=renk,
                    font=("Arial", 10),
                    justify="center",
                    wraplength=135,
                ).grid(
                    row=row_index,
                    column=column,
                    sticky="nsew",
                    padx=1,
                    pady=1,
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

            kpi_alani = ctk.CTkFrame(
                self.sevkiyat_rapor_sonuc,
                fg_color="transparent",
            )
            kpi_alani.pack(
                fill="x",
                padx=5,
                pady=(10, 12),
            )

            kpi_verileri = (
                ("SEVKİYAT", toplam_sevkiyat),
                ("MÜŞTERİ", len(musteri_adlari)),
                ("TOPLAM KOLİ", toplam_koli),
                ("AÇIK PAKET", toplam_acik),
                ("TOPLAM PAKET", toplam_paket),
                ("SEVK EDİLEN KG", f"{toplam_kg:.3f}"),
            )

            for index in range(len(kpi_verileri)):
                kpi_alani.grid_columnconfigure(
                    index,
                    weight=1,
                    uniform="shipment_report_kpi",
                )

            for index, (baslik, deger) in enumerate(
                kpi_verileri
            ):
                kart = ctk.CTkFrame(
                    kpi_alani,
                    height=80,
                )
                kart.grid(
                    row=0,
                    column=index,
                    sticky="nsew",
                    padx=4,
                )
                kart.grid_propagate(False)

                ctk.CTkLabel(
                    kart,
                    text=baslik,
                    font=("Arial", 10, "bold"),
                    text_color="#A3A3A3",
                ).pack(pady=(12, 3))

                ctk.CTkLabel(
                    kart,
                    text=str(deger),
                    font=("Arial", 18, "bold"),
                ).pack()

            musteri_gruplari = {}

            for row in filtreli:
                musteri_gruplari.setdefault(
                    row["musteri"],
                    []
                ).append(row)

            musteri_satirlari = []

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
                    int(row["sevk_koli_adedi"] or 0)
                    for row in kayitlar
                )
                musteri_acik = sum(
                    int(
                        row["sevk_acik_paket_adedi"] or 0
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
                    for detay in detay_map.get(row["id"], []):
                        gram = int(detay["ambalaj_gram"])
                        ambalaj_toplam[gram] = (
                            ambalaj_toplam.get(gram, 0)
                            + int(detay["paket_adedi"])
                        )
                        lotlar.add(detay["urun_lot_no"])

                musteri_satirlari.append((
                    musteri,
                    min(tarihler).strftime("%d.%m.%Y"),
                    max(tarihler).strftime("%d.%m.%Y"),
                    len(kayitlar),
                    musteri_koli,
                    musteri_acik,
                    musteri_paket,
                    ambalaj_toplam.get(500, 0),
                    ambalaj_toplam.get(2500, 0),
                    f"{musteri_kg:.3f}",
                    ", ".join(sorted(lotlar)) or "-",
                ))

            self.sevkiyat_rapor_tablo(
                "MÜŞTERİ / SEVK NOKTASI ÖZETİ",
                (
                    "MÜŞTERİ",
                    "İLK SEVK",
                    "SON SEVK",
                    "SEVKİYAT",
                    "KOLİ",
                    "AÇIK",
                    "PAKET",
                    "500 G",
                    "2.5 KG",
                    "TOPLAM KG",
                    "ÜRÜN LOTLARI",
                ),
                musteri_satirlari,
            )

            detay_satirlari = [
                (
                    row["sevkiyat_tarihi"],
                    row["musteri"],
                    int(row["sevk_koli_adedi"] or 0),
                    int(
                        row["sevk_acik_paket_adedi"] or 0
                    ),
                    int(row["toplam_paket"] or 0),
                    f'{float(row["toplam_kg"] or 0):.3f}',
                    row["arac_plaka"] or "-",
                    row["belge_no"] or "-",
                    (
                        "EVET"
                        if row["soguk_zincir"]
                        else "HAYIR"
                    ),
                )
                for row in filtreli
            ]

            self.sevkiyat_rapor_tablo(
                "SEVKİYAT KAYIT DETAYLARI",
                (
                    "TARİH",
                    "MÜŞTERİ",
                    "KOLİ",
                    "AÇIK",
                    "PAKET",
                    "SEVK KG",
                    "ARAÇ PLAKA",
                    "BELGE NO",
                    "SOĞUK ZİNCİR",
                ),
                detay_satirlari,
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
            pady=(0, 30),
        )

        conn = get_connection()

        try:
            lotlar = conn.execute("""
                SELECT
                    id,
                    urun_lot_no,
                    uretim_tarihi,
                    net_uretim_kg
                FROM uretim
                ORDER BY id DESC
            """).fetchall()

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

            ozet = conn.execute("""
                SELECT
                    (SELECT COUNT(*) FROM uretim)
                        AS urun_lotu,
                    (SELECT COUNT(*) FROM depo_kabul)
                        AS hammadde_lotu,
                    (SELECT COUNT(*) FROM sevkiyat)
                        AS sevkiyat,
                    (
                        SELECT COUNT(
                            DISTINCT COALESCE(
                                musteri_id,
                                musteri
                            )
                        )
                        FROM sevkiyat
                    ) AS musteri
            """).fetchone()
        finally:
            conn.close()

        baslik = ctk.CTkFrame(
            ana_frame,
            fg_color="transparent",
        )
        baslik.pack(
            fill="x",
            padx=20,
            pady=(20, 12),
        )

        ctk.CTkLabel(
            baslik,
            text="LOT İZLENEBİLİRLİK MERKEZİ",
            font=("Arial", 22, "bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            baslik,
            text="İleri izleme ve geri çağırma analizi",
            font=("Arial", 13),
            text_color="#A3A3A3",
        ).pack(side="right")

        kpi_alani = ctk.CTkFrame(
            ana_frame,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 15),
        )

        kpi_verileri = (
            ("ÜRÜN LOTU", ozet["urun_lotu"]),
            ("HAMMADDE LOTU", ozet["hammadde_lotu"]),
            ("SEVKİYAT KAYDI", ozet["sevkiyat"]),
            ("MÜŞTERİ SAYISI", ozet["musteri"]),
        )

        for kart_basligi, kart_degeri in kpi_verileri:
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.pack(
                side="left",
                fill="x",
                expand=True,
                padx=5,
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=kart_basligi,
                font=("Arial", 11, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            ctk.CTkLabel(
                kart,
                text=str(int(kart_degeri or 0)),
                font=("Arial", 21, "bold"),
            ).pack()

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

        sorgu_alani = ctk.CTkFrame(
            ana_frame,
            fg_color="transparent",
        )
        sorgu_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 15),
        )

        ileri_panel = ctk.CTkFrame(sorgu_alani)
        ileri_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5,
        )

        geri_panel = ctk.CTkFrame(sorgu_alani)
        geri_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5,
        )

        ctk.CTkLabel(
            ileri_panel,
            text="ÜRÜN LOTUNDAN İLERİ İZLEME",
            font=("Arial", 15, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 4),
        )

        ctk.CTkLabel(
            ileri_panel,
            text=(
                "Üretim → hammadde → paketleme → "
                "sevkiyat → müşteri"
            ),
            font=("Arial", 12),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 12),
        )

        lot_degerleri = list(
            self.izlenebilirlik_lot_map.keys()
        )

        self.izlenebilirlik_lot_secim = ctk.CTkComboBox(
            ileri_panel,
            values=(
                lot_degerleri
                if lot_degerleri
                else [""]
            ),
            state="readonly",
            height=38,
        )
        self.izlenebilirlik_lot_secim.pack(
            fill="x",
            padx=20,
            pady=(0, 10),
        )
        self.izlenebilirlik_lot_secim.set("")

        ileri_butonlar = ctk.CTkFrame(
            ileri_panel,
            fg_color="transparent",
        )
        ileri_butonlar.pack(
            fill="x",
            padx=20,
            pady=(0, 18),
        )

        ctk.CTkButton(
            ileri_butonlar,
            text="İLERİ İZLE",
            height=40,
            font=("Arial", 13, "bold"),
            command=self.izlenebilirlik_getir,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5),
        )

        ctk.CTkButton(
            ileri_butonlar,
            text="PDF RAPORU",
            height=40,
            width=120,
            fg_color="#4B5563",
            command=self.izlenebilirlik_pdf_raporu,
        ).pack(side="left", padx=(5, 0))

        ctk.CTkLabel(
            geri_panel,
            text="HAMMADDE LOTUNDAN GERİ ÇAĞIRMA",
            font=("Arial", 15, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 4),
        )

        ctk.CTkLabel(
            geri_panel,
            text=(
                "Hammadde → üretim lotları → paketler → "
                "sevkiyatlar → müşteriler"
            ),
            font=("Arial", 12),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 12),
        )

        geri_lot_degerleri = list(
            self.geri_cagirma_lot_map.keys()
        )

        self.geri_cagirma_lot_secim = ctk.CTkComboBox(
            geri_panel,
            values=(
                geri_lot_degerleri
                if geri_lot_degerleri
                else [""]
            ),
            state="readonly",
            height=38,
        )
        self.geri_cagirma_lot_secim.pack(
            fill="x",
            padx=20,
            pady=(0, 10),
        )
        self.geri_cagirma_lot_secim.set("")

        geri_butonlar = ctk.CTkFrame(
            geri_panel,
            fg_color="transparent",
        )
        geri_butonlar.pack(
            fill="x",
            padx=20,
            pady=(0, 18),
        )

        ctk.CTkButton(
            geri_butonlar,
            text="GERİ ÇAĞIRMA İZİNİ GETİR",
            height=40,
            font=("Arial", 13, "bold"),
            command=self.geri_cagirma_izi_getir,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5),
        )

        ctk.CTkButton(
            geri_butonlar,
            text="PDF RAPORU",
            height=40,
            width=120,
            fg_color="#4B5563",
            command=self.geri_cagirma_pdf_raporu,
        ).pack(side="left", padx=(5, 0))

        sonuc_baslik = ctk.CTkFrame(
            ana_frame,
            fg_color="transparent",
        )
        sonuc_baslik.pack(
            fill="x",
            padx=20,
            pady=(0, 6),
        )

        ctk.CTkLabel(
            sonuc_baslik,
            text="İZLENEBİLİRLİK SONUCU",
            font=("Arial", 16, "bold"),
        ).pack(side="left")

        self.izlenebilirlik_sonuc_frame = (
            ctk.CTkScrollableFrame(
                ana_frame
            )
        )
        self.izlenebilirlik_sonuc_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20),
        )

        ctk.CTkLabel(
            self.izlenebilirlik_sonuc_frame,
            text=(
                "Analiz için ürün lotu veya hammadde "
                "lotu seçin."
            ),
            font=("Arial", 15),
            text_color="#A3A3A3",
        ).pack(pady=35)

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

            self.izlenebilirlik_tablo(
                "1. ÜRÜN LOTU VE ÜRETİM",
                (
                    "ÜRÜN LOTU",
                    "ÜRETİM TARİHİ",
                    "REÇETE",
                    "PARTİ",
                    "TEORİK KG",
                    "FİRE KG",
                    "NET KG",
                    "PERSONEL",
                ),
                [(
                    uretim["urun_lot_no"],
                    uretim["uretim_tarihi"],
                    uretim["recete_adi"] or "-",
                    uretim["parti_sayisi"],
                    f'{uretim["teorik_uretim_kg"]:.3f}',
                    f'{uretim["uretim_firesi_kg"]:.3f}',
                    f'{uretim["net_uretim_kg"]:.3f}',
                    (
                        f'{uretim["personel_1"] or "-"} / '
                        f'{uretim["personel_2"] or "-"}'
                    ),
                )],
            )

            self.izlenebilirlik_tablo(
                "2. HAMMADDE LOT ZİNCİRİ",
                (
                    "HAMMADDE",
                    "TEDARİKÇİ",
                    "LOT NO",
                    "ÜRT",
                    "SKT / TETT",
                    "KULLANILAN KG",
                ),
                [
                    (
                        row["hammadde_adi"],
                        row["tedarikci"] or "-",
                        row["tedarikci_lot_no"],
                        row["uretim_tarihi"] or "-",
                        row["skt_tett"] or "-",
                        f'{row["kullanilan_miktar_kg"]:.3f}',
                    )
                    for row in hammaddeler
                ],
            )

            paketleme_satirlari = []

            for row in paketlemeler:
                ambalaj = (
                    "500 g"
                    if row["ambalaj_gram"] == 500
                    else "2.5 kg"
                    if row["ambalaj_gram"] == 2500
                    else f'{row["ambalaj_gram"]} g'
                )

                koli_ici = row["koli_ici_adet"] or 0
                tam_koli = (
                    row["paket_adedi"] // koli_ici
                    if koli_ici > 0
                    else 0
                )
                acik_paket = (
                    row["paket_adedi"] % koli_ici
                    if koli_ici > 0
                    else row["paket_adedi"]
                )

                paketleme_satirlari.append((
                    row["paketleme_tarihi"],
                    ambalaj,
                    row["paket_adedi"],
                    tam_koli,
                    acik_paket,
                    f'{row["paketlenen_kg"]:.3f}',
                    f'{row["paketleme_firesi_kg"]:.3f}',
                ))

            self.izlenebilirlik_tablo(
                "3. PAKETLEME",
                (
                    "TARİH",
                    "AMBALAJ",
                    "PAKET",
                    "TAM KOLİ",
                    "AÇIK PAKET",
                    "PAKETLENEN KG",
                    "FİRE KG",
                ),
                paketleme_satirlari,
            )

            self.izlenebilirlik_tablo(
                "4. SEVKİYAT VE MÜŞTERİ ZİNCİRİ",
                (
                    "TARİH",
                    "MÜŞTERİ",
                    "PAKET",
                    "SEVK KG",
                    "ARAÇ PLAKA",
                    "BELGE NO",
                    "SOĞUK ZİNCİR",
                ),
                [
                    (
                        row["sevkiyat_tarihi"],
                        row["musteri"],
                        row["toplam_paket"],
                        f'{row["toplam_kg"]:.3f}',
                        row["arac_plaka"] or "-",
                        row["belge_no"] or "-",
                        (
                            "EVET"
                            if row["soguk_zincir"]
                            else "HAYIR"
                        ),
                    )
                    for row in sevkiyatlar
                ],
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

            if not hammadde_lotu:
                self.izlenebilirlik_kart(
                    "HAMMADDE LOT KAYDI BULUNAMADI"
                )
                return

            self.izlenebilirlik_tablo(
                "GERİ ÇAĞIRMA / TERS İZLENEBİLİRLİK",
                (
                    "HAMMADDE",
                    "TEDARİKÇİ",
                    "LOT NO",
                    "KABUL TARİHİ",
                    "ÜRT",
                    "SKT / TETT",
                    "MİKTAR KG",
                    "DURUM",
                ),
                [(
                    hammadde_lotu["hammadde"],
                    hammadde_lotu["tedarikci"] or "-",
                    hammadde_lotu["tedarikci_lot_no"],
                    hammadde_lotu["kabul_tarihi"],
                    hammadde_lotu["uretim_tarihi"] or "-",
                    hammadde_lotu["skt_tett"] or "-",
                    f'{hammadde_lotu["miktar_kg"]:.3f}',
                    hammadde_lotu["kabul_durumu"],
                )],
            )

            self.izlenebilirlik_tablo(
                "1. ETKİLENEN ÜRETİM LOTLARI",
                (
                    "ÜRÜN LOTU",
                    "ÜRETİM TARİHİ",
                    "PARTİ",
                    "NET ÜRETİM KG",
                    "KULLANILAN KG",
                ),
                [
                    (
                        row["urun_lot_no"],
                        row["uretim_tarihi"],
                        row["parti_sayisi"],
                        f'{row["net_uretim_kg"]:.3f}',
                        f'{row["kullanilan_miktar_kg"]:.3f}',
                    )
                    for row in uretimler
                ],
            )

            paketleme_satirlari = []

            for row in paketlemeler:
                ambalaj = (
                    "500 g"
                    if row["ambalaj_gram"] == 500
                    else "2.5 kg"
                    if row["ambalaj_gram"] == 2500
                    else f'{row["ambalaj_gram"]} g'
                )

                koli_ici = row["koli_ici_adet"] or 0
                tam_koli = (
                    row["paket_adedi"] // koli_ici
                    if koli_ici > 0
                    else 0
                )
                acik_paket = (
                    row["paket_adedi"] % koli_ici
                    if koli_ici > 0
                    else row["paket_adedi"]
                )

                paketleme_satirlari.append((
                    row["urun_lot_no"],
                    row["paketleme_tarihi"],
                    ambalaj,
                    row["paket_adedi"],
                    tam_koli,
                    acik_paket,
                    f'{row["paketlenen_kg"]:.3f}',
                ))

            self.izlenebilirlik_tablo(
                "2. ETKİLENEN PAKETLEMELER",
                (
                    "ÜRÜN LOTU",
                    "TARİH",
                    "AMBALAJ",
                    "PAKET",
                    "TAM KOLİ",
                    "AÇIK PAKET",
                    "PAKETLENEN KG",
                ),
                paketleme_satirlari,
            )

            self.izlenebilirlik_tablo(
                "3. ETKİLENEN SEVKİYAT VE MÜŞTERİLER",
                (
                    "ÜRÜN LOTU",
                    "TARİH",
                    "MÜŞTERİ",
                    "AMBALAJ",
                    "PAKET",
                    "SEVK KG",
                    "ARAÇ PLAKA",
                    "BELGE NO",
                    "SOĞUK ZİNCİR",
                ),
                [
                    (
                        row["urun_lot_no"],
                        row["sevkiyat_tarihi"],
                        row["musteri"],
                        (
                            "500 g"
                            if row["ambalaj_gram"] == 500
                            else "2.5 kg"
                            if row["ambalaj_gram"] == 2500
                            else f'{row["ambalaj_gram"]} g'
                        ),
                        row["paket_adedi"],
                        f'{row["sevk_kg"]:.3f}',
                        row["arac_plaka"] or "-",
                        row["belge_no"] or "-",
                        (
                            "EVET"
                            if row["soguk_zincir"]
                            else "HAYIR"
                        ),
                    )
                    for row in sevkiyatlar
                ],
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


    def hammadde_kabul_pdf_raporu(self, depo_kabul_id):
        conn = None

        try:
            conn = get_connection()

            pdf = hammadde_kabul_pdf_olustur(
                conn,
                depo_kabul_id
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Hammadde kabul PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Hammadde Kabul PDF Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Hammadde kabul PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

    def uretim_pdf_raporu(self, uretim_id):
        conn = None

        try:
            conn = get_connection()

            pdf = uretim_pdf_olustur(
                conn,
                uretim_id
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Üretim PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Üretim PDF Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Üretim PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

    def paketleme_pdf_raporu(self, paketleme_id):
        conn = None

        try:
            conn = get_connection()

            pdf = paketleme_pdf_olustur(
                conn,
                paketleme_id
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Paketleme PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Paketleme PDF Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Paketleme PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

    def sevkiyat_pdf_raporu(self, sevkiyat_id):
        conn = None

        try:
            conn = get_connection()

            pdf = sevkiyat_pdf_olustur(
                conn,
                sevkiyat_id
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Sevkiyat PDF raporu "
                    "başarıyla oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                )
            )

        except ValueError as hata:
            messagebox.showerror(
                "Sevkiyat PDF Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Sevkiyat PDF raporu "
                    f"oluşturulamadı:\n{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

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


    def izlenebilirlik_tablo(
        self,
        baslik,
        sutunlar,
        satirlar,
    ):
        self.izlenebilirlik_baslik(baslik)

        if not satirlar:
            self.izlenebilirlik_kart(
                "Bu bölüme ait kayıt bulunamadı."
            )
            return

        tablo = ctk.CTkFrame(
            self.izlenebilirlik_sonuc_frame,
            fg_color="transparent",
        )
        tablo.pack(
            fill="x",
            padx=12,
            pady=(0, 14),
        )

        for index in range(len(sutunlar)):
            tablo.grid_columnconfigure(
                index,
                weight=1,
                uniform="traceability",
            )

        for column, baslik_metni in enumerate(sutunlar):
            ctk.CTkLabel(
                tablo,
                text=baslik_metni,
                height=38,
                fg_color="#1F2937",
                font=("Arial", 11, "bold"),
                anchor="center",
                wraplength=150,
            ).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=1,
                pady=1,
            )

        for row_index, satir in enumerate(satirlar, 1):
            renk = (
                "#292929"
                if row_index % 2
                else "#303030"
            )

            for column, deger in enumerate(satir):
                ctk.CTkLabel(
                    tablo,
                    text=str(deger),
                    height=38,
                    fg_color=renk,
                    font=("Arial", 11),
                    anchor="center",
                    justify="center",
                    wraplength=150,
                ).grid(
                    row=row_index,
                    column=column,
                    sticky="nsew",
                    padx=1,
                    pady=1,
                )

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
            "Planlı temizlik görevleri ve gerçekleşme takibi"
        )

        ana = ctk.CTkFrame(self.content)
        ana.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30),
        )

        filtre = ctk.CTkFrame(ana)
        filtre.pack(
            fill="x",
            padx=10,
            pady=(10, 12),
        )

        ctk.CTkLabel(
            filtre,
            text="PLANLI TEMİZLİK GÖREVLERİ",
            font=("Arial", 19, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 10),
        )

        filtre_alanlari = ctk.CTkFrame(
            filtre,
            fg_color="transparent",
        )
        filtre_alanlari.pack(
            fill="x",
            padx=15,
            pady=(0, 15),
        )

        for column in range(5):
            filtre_alanlari.grid_columnconfigure(
                column,
                weight=1,
                uniform="cleaning_filter",
            )

        filtre_basliklari = (
            "Görev Tarihi",
            "Periyot",
            "Durum",
            "Liste",
            "Rapor",
        )

        for column, baslik in enumerate(
            filtre_basliklari
        ):
            ctk.CTkLabel(
                filtre_alanlari,
                text=baslik,
                anchor="w",
            ).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=5,
                pady=(0, 4),
            )

        self.temizlik_plan_tarih = ctk.CTkEntry(
            filtre_alanlari,
            height=40,
        )
        self.temizlik_plan_tarih.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=5,
        )
        self.temizlik_plan_tarih.insert(
            0,
            datetime.now().strftime("%d.%m.%Y"),
        )

        self.temizlik_periyot_filtre = ctk.CTkOptionMenu(
            filtre_alanlari,
            values=[
                "TÜMÜ",
                "GÜNLÜK",
                "ÜRETİM SONRASI",
                "HAFTALIK",
                "AYLIK",
                "YILLIK",
            ],
            command=lambda _value: (
                self.temizlik_planli_gorevleri_listele()
            ),
            height=40,
        )
        self.temizlik_periyot_filtre.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=5,
        )
        self.temizlik_periyot_filtre.set("TÜMÜ")

        self.temizlik_durum_filtre = ctk.CTkOptionMenu(
            filtre_alanlari,
            values=[
                "TÜMÜ",
                "GECİKEN",
                "BEKLEYEN",
                "GELECEK",
            ],
            command=lambda _value: (
                self.temizlik_planli_gorevleri_listele()
            ),
            height=40,
        )
        self.temizlik_durum_filtre.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=5,
        )
        self.temizlik_durum_filtre.set("TÜMÜ")

        ctk.CTkButton(
            filtre_alanlari,
            text="GÖREVLERİ GETİR",
            command=self.temizlik_planli_gorevleri_listele,
            height=40,
            font=("Arial", 12, "bold"),
        ).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=5,
        )

        ctk.CTkButton(
            filtre_alanlari,
            text="PDF OLUŞTUR",
            command=self.temizlik_pdf_raporu,
            height=40,
            fg_color="#4B5563",
            font=("Arial", 12, "bold"),
        ).grid(
            row=1,
            column=4,
            sticky="ew",
            padx=5,
        )

        kpi_alani = ctk.CTkFrame(
            ana,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=5,
            pady=(0, 12),
        )

        self.temizlik_kpi_labels = []

        for baslik in (
            "TOPLAM GÖREV",
            "GECİKEN",
            "BEKLEYEN",
            "GELECEK",
        ):
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.pack(
                side="left",
                fill="x",
                expand=True,
                padx=5,
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=baslik,
                font=("Arial", 11, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            deger = ctk.CTkLabel(
                kart,
                text="0",
                font=("Arial", 21, "bold"),
            )
            deger.pack()
            self.temizlik_kpi_labels.append(deger)

        islem = ctk.CTkFrame(ana)
        islem.pack(
            fill="x",
            padx=10,
            pady=(0, 12),
        )

        aktif_personeller = (
            self.yetkili_personelleri_getir("TEMIZLIK")
        )

        if not aktif_personeller:
            raise RuntimeError(
                "Aktif temizlik yetkili personeli bulunmuyor."
            )

        for column in range(4):
            islem.grid_columnconfigure(
                column,
                weight=1,
                uniform="cleaning_action",
            )

        for column, baslik in enumerate((
            "Uygulayan",
            "Kontrol Eden",
            "Açıklama",
            "İşlem",
        )):
            ctk.CTkLabel(
                islem,
                text=baslik,
                anchor="w",
            ).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=10,
                pady=(10, 4),
            )

        self.temizlik_uygulayan = ctk.CTkOptionMenu(
            islem,
            values=aktif_personeller,
            height=38,
        )
        self.temizlik_uygulayan.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 12),
        )
        self.temizlik_uygulayan.set(
            aktif_personeller[0]
        )

        self.temizlik_kontrol = ctk.CTkOptionMenu(
            islem,
            values=aktif_personeller,
            height=38,
        )
        self.temizlik_kontrol.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=10,
            pady=(0, 12),
        )
        self.temizlik_kontrol.set(
            aktif_personeller[1]
            if len(aktif_personeller) > 1
            else aktif_personeller[0]
        )

        self.temizlik_aciklama = ctk.CTkEntry(
            islem,
            height=38,
        )
        self.temizlik_aciklama.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=10,
            pady=(0, 12),
        )

        ctk.CTkButton(
            islem,
            text="SEÇİLİ GÖREVİ TAMAMLA",
            command=self.temizlik_secili_gorev_tamamla,
            height=38,
            font=("Arial", 12, "bold"),
        ).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=10,
            pady=(0, 12),
        )

        self.temizlik_plan_liste_frame = ctk.CTkFrame(
            ana
        )
        self.temizlik_plan_liste_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        self.temizlik_planli_gorevleri_listele()

    def temizlik_secili_gorev_tamamla(self):
        secim = self.temizlik_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Görev Seçilmedi",
                (
                    "Tamamlamak için tablodan "
                    "bir temizlik görevi seçin."
                ),
            )
            return

        gorev = self.temizlik_gorev_map.get(secim[0])

        if gorev is None:
            messagebox.showerror(
                "Görev Hatası",
                "Seçilen görev bilgisi bulunamadı.",
            )
            return

        self.temizlik_planli_gorev_tamamla(gorev)

    def temizlik_planli_gorevleri_listele(self):
        for widget in (
            self.temizlik_plan_liste_frame.winfo_children()
        ):
            widget.destroy()

        conn = None

        try:
            tarih = self.temizlik_plan_tarih.get().strip()
            datetime.strptime(tarih, "%d.%m.%Y")

            conn = get_connection()
            gorevler = get_due_cleaning_tasks(conn, tarih)
            ozet = get_due_cleaning_summary(conn, tarih)

            periyot_filtre = (
                self.temizlik_periyot_filtre.get().strip()
            )
            durum_filtre = (
                self.temizlik_durum_filtre.get().strip()
            )

            periyot_map = {
                "TÜMÜ": None,
                "GÜNLÜK": "GUNLUK",
                "ÜRETİM SONRASI": "URETIM_SONRASI",
                "HAFTALIK": "HAFTALIK",
                "AYLIK": "AYLIK",
                "YILLIK": "YILLIK",
            }
            durum_map = {
                "TÜMÜ": None,
                "GECİKEN": "GECIKEN",
                "BEKLEYEN": "BEKLEYEN",
                "GELECEK": "GELECEK",
            }

            if periyot_filtre not in periyot_map:
                raise ValueError(
                    "Geçerli periyot seçilmelidir."
                )
            if durum_filtre not in durum_map:
                raise ValueError(
                    "Geçerli durum seçilmelidir."
                )

            secili_periyot = periyot_map[periyot_filtre]
            secili_durum = durum_map[durum_filtre]

            filtreli = [
                gorev
                for gorev in gorevler
                if (
                    (
                        secili_periyot is None
                        or gorev["periyot"] == secili_periyot
                    )
                    and (
                        secili_durum is None
                        or gorev["durum"] == secili_durum
                    )
                )
            ]

            durum_sayilari = {
                "GECIKEN": 0,
                "BEKLEYEN": 0,
                "GELECEK": 0,
            }

            for gorev in gorevler:
                durum_sayilari[gorev["durum"]] += 1

            kpi_degerleri = (
                int(ozet["TOPLAM"]),
                durum_sayilari["GECIKEN"],
                durum_sayilari["BEKLEYEN"],
                durum_sayilari["GELECEK"],
            )

            for label, deger in zip(
                self.temizlik_kpi_labels,
                kpi_degerleri,
            ):
                label.configure(text=str(deger))

            style = ttk.Style()
            style.theme_use("default")
            style.configure(
                "Cleaning.Treeview",
                background="#292929",
                foreground="#F3F4F6",
                fieldbackground="#292929",
                borderwidth=0,
                rowheight=40,
                font=("Arial", 11),
            )
            style.configure(
                "Cleaning.Treeview.Heading",
                background="#1F2937",
                foreground="#F9FAFB",
                relief="flat",
                font=("Arial", 10, "bold"),
            )
            style.map(
                "Cleaning.Treeview",
                background=[("selected", "#1F6AA5")],
                foreground=[("selected", "#FFFFFF")],
            )

            tree_area = ctk.CTkFrame(
                self.temizlik_plan_liste_frame
            )
            tree_area.pack(
                fill="both",
                expand=True,
            )
            tree_area.grid_rowconfigure(0, weight=1)
            tree_area.grid_columnconfigure(0, weight=1)

            columns = (
                "durum",
                "periyot",
                "tarih",
                "kat",
                "alan",
                "ekipman",
                "lot",
                "gorev",
                "talimat",
            )

            self.temizlik_tree = ttk.Treeview(
                tree_area,
                columns=columns,
                show="headings",
                style="Cleaning.Treeview",
                selectmode="browse",
            )

            headings = (
                ("durum", "DURUM", 90, "center"),
                ("periyot", "PERİYOT", 115, "center"),
                ("tarih", "PLAN TARİHİ", 95, "center"),
                ("kat", "KAT", 110, "w"),
                ("alan", "ALAN", 150, "w"),
                ("ekipman", "EKİPMAN", 145, "w"),
                ("lot", "ÜRETİM LOTU", 105, "center"),
                ("gorev", "GÖREV", 220, "w"),
                ("talimat", "TALİMAT", 300, "w"),
            )

            for column, title, width, anchor in headings:
                self.temizlik_tree.heading(
                    column,
                    text=title,
                    anchor=anchor,
                )
                self.temizlik_tree.column(
                    column,
                    width=width,
                    minwidth=75,
                    anchor=anchor,
                    stretch=True,
                )

            self.temizlik_tree.tag_configure(
                "delayed",
                foreground="#FCA5A5",
            )
            self.temizlik_tree.tag_configure(
                "pending",
                foreground="#FDE68A",
            )
            self.temizlik_tree.tag_configure(
                "future",
                foreground="#93C5FD",
            )

            self.temizlik_gorev_map = {}

            durum_gosterim = {
                "GECIKEN": "GECİKEN",
                "BEKLEYEN": "BEKLEYEN",
                "GELECEK": "GELECEK",
            }
            tag_map = {
                "GECIKEN": "delayed",
                "BEKLEYEN": "pending",
                "GELECEK": "future",
            }

            for index, gorev in enumerate(filtreli):
                iid = (
                    f'{gorev["plan_id"]}:'
                    f'{gorev["planlanan_tarih"]}:'
                    f'{index}'
                )
                self.temizlik_gorev_map[iid] = gorev

                self.temizlik_tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        durum_gosterim[gorev["durum"]],
                        gorev["periyot"],
                        gorev["planlanan_tarih"],
                        gorev["kat_adi"],
                        gorev["alan_adi"],
                        gorev["ekipman_adi"] or "-",
                        gorev["urun_lot_no"] or "-",
                        gorev["gorev_adi"],
                        gorev["talimat"],
                    ),
                    tags=(tag_map[gorev["durum"]],),
                )

            vertical = ttk.Scrollbar(
                tree_area,
                orient="vertical",
                command=self.temizlik_tree.yview,
            )
            horizontal = ttk.Scrollbar(
                tree_area,
                orient="horizontal",
                command=self.temizlik_tree.xview,
            )

            self.temizlik_tree.configure(
                yscrollcommand=vertical.set,
                xscrollcommand=horizontal.set,
            )
            self.temizlik_tree.grid(
                row=0,
                column=0,
                sticky="nsew",
            )
            vertical.grid(
                row=0,
                column=1,
                sticky="ns",
            )
            horizontal.grid(
                row=1,
                column=0,
                sticky="ew",
            )

        except ValueError:
            messagebox.showerror(
                "Planlı Temizlik Hatası",
                "Tarih veya filtre seçimi geçerli değildir.",
            )

        except Exception as hata:
            messagebox.showerror(
                "Planlı Temizlik Hatası",
                (
                    "Planlı temizlik görevleri yüklenemedi:\n"
                    f"{hata}"
                ),
            )

        finally:
            if conn is not None:
                conn.close()

    def temizlik_pdf_raporu(self):
        conn = None

        try:
            target_date = self.temizlik_plan_tarih.get().strip()

            conn = get_connection()

            pdf_path = temizlik_pdf_olustur(
                conn,
                target_date,
            )

            messagebox.showinfo(
                "Temizlik PDF",
                "Temizlik PDF başarıyla oluşturuldu."
            )

            subprocess.Popen(
                ["open", pdf_path]
            )

        except Exception as exc:

            messagebox.showerror(
                "Temizlik PDF",
                str(exc)
            )

        finally:

            if conn is not None:
                conn.close()


    def temizlik_planli_gorev_tamamla(
        self,
        gorev,
    ):
        conn = None

        try:
            aktif_personeller = (
                self.yetkili_personelleri_getir("TEMIZLIK")
            )

            if not aktif_personeller:
                raise ValueError(
                    "Aktif temizlik yetkili personeli bulunmuyor."
                )

            uygulayan = (
                self.temizlik_uygulayan.get().strip()
            )

            kontrol_eden = (
                self.temizlik_kontrol.get().strip()
            )

            if uygulayan not in aktif_personeller:
                raise ValueError(
                    "Geçerli ve aktif uygulayan personel seçilmelidir."
                )

            if kontrol_eden not in aktif_personeller:
                raise ValueError(
                    "Geçerli ve aktif kontrol eden personel seçilmelidir."
                )

            if uygulayan == kontrol_eden:
                raise ValueError(
                    "Uygulayan ve kontrol eden aynı personel olamaz."
                )

            onay = messagebox.askyesno(
                "Planlı Temizlik Tamamlama",
                (
                    f'{gorev["gorev_adi"]}\n\n'
                    f'Planlanan Tarih: {gorev["planlanan_tarih"]}\n'
                    f'Uygulayan: {uygulayan}\n'
                    f'Kontrol Eden: {kontrol_eden}\n\n'
                    "Bu görev TAMAMLANDI olarak kaydedilsin mi?"
                )
            )

            if not onay:
                return

            conn = get_connection()

            complete_cleaning_task(
                conn,
                gorev["plan_id"],
                gorev["planlanan_tarih"],
                uygulayan,
                kontrol_eden,
                aciklama=(
                    self.temizlik_aciklama.get().strip()
                    or None
                ),
                uretim_id=gorev["uretim_id"],
            )

            conn.commit()

            messagebox.showinfo(
                "Planlı Temizlik",
                "Planlı temizlik görevi tamamlandı."
            )

            self.temizlik_planli_gorevleri_listele()

        except ValueError as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Planlı Temizlik Hatası",
                str(hata)
            )

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Sistem Hatası",
                (
                    "Planlı temizlik görevi tamamlanamadı:\n"
                    f"{hata}"
                )
            )

        finally:
            if conn is not None:
                conn.close()

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

            aktif_personeller = (
                self.yetkili_personelleri_getir(
                "TEMIZLIK"
            )
            )

            if uygulayan not in aktif_personeller:
                raise ValueError(
                    "Geçerli ve aktif uygulayan "
                    "personel seçilmelidir."
                )

            if kontrol_eden not in aktif_personeller:
                raise ValueError(
                    "Geçerli ve aktif kontrol eden "
                    "personel seçilmelidir."
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

        aktif_personeller = (
            self.aktif_personelleri_getir()
        )

        if aktif_personeller:
            self.temizlik_uygulayan.configure(
                values=aktif_personeller
            )

            self.temizlik_kontrol.configure(
                values=aktif_personeller
            )

            self.temizlik_uygulayan.set(
                aktif_personeller[0]
            )

            self.temizlik_kontrol.set(
                (
                    aktif_personeller[1]
                    if len(aktif_personeller) > 1
                    else aktif_personeller[0]
                )
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



    def recete_verilerini_getir(self):
        if not self.formul_yetkili:
            raise PermissionError(
                "1 parti üretim formülüne erişim yetkiniz yok."
            )

        conn = get_connection()

        try:
            recete = conn.execute(
                """
                SELECT
                    id,
                    ad,
                    parti_teorik_kg,
                    aktif,
                    revizyon_no,
                    gecerlilik_tarihi,
                    revizyon_aciklamasi
                FROM receteler
                WHERE aktif = 1
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

            if recete is None:
                return None, [], 0.0

            kalemler = conn.execute(
                """
                SELECT
                    h.ad,
                    rk.miktar_kg
                FROM recete_kalemleri rk
                JOIN hammaddeler h
                  ON h.id = rk.hammadde_id
                WHERE rk.recete_id = ?
                ORDER BY rk.id
                """,
                (
                    recete["id"],
                ),
            ).fetchall()

            ayar = conn.execute(
                """
                SELECT deger
                FROM sistem_ayarlari
                WHERE anahtar = ?
                LIMIT 1
                """,
                (
                    "PARTI_PROSES_SUYU_KG",
                ),
            ).fetchone()

            proses_suyu_kg = (
                float(ayar["deger"])
                if ayar is not None
                else 0.0
            )

            return (
                recete,
                kalemler,
                proses_suyu_kg,
            )

        finally:
            conn.close()


    def recete(self):
        if not self.formul_erisim_kontrolu():
            return

        self.show_page(
            "REÇETE MERKEZİ",
            (
                "Aktif üretim reçetesi ve "
                "1 parti kütle dengesi"
            ),
        )

        try:
            (
                recete,
                kalemler,
                proses_suyu_kg,
            ) = self.recete_verilerini_getir()

        except Exception as hata:
            messagebox.showerror(
                "Reçete Hatası",
                str(hata),
            )
            return

        conn = get_connection()
        try:
            revizyonlar = conn.execute("""
                SELECT
                    r.id,
                    r.ad,
                    r.revizyon_no,
                    r.gecerlilik_tarihi,
                    r.aktif,
                    r.revizyon_aciklamasi,
                    p.ad_soyad AS olusturan
                FROM receteler r
                LEFT JOIN personeller p
                  ON p.id = r.olusturan_personel_id
                ORDER BY r.id DESC
            """).fetchall()
        finally:
            conn.close()

        if recete is None:
            messagebox.showwarning(
                "Aktif Reçete Yok",
                (
                    "Sistemde aktif üretim "
                    "reçetesi bulunamadı."
                ),
            )
            return

        ana_kart = ctk.CTkScrollableFrame(
            self.content,
            corner_radius=14,
        )

        ana_kart.pack(
            fill="both",
            expand=True,
            padx=45,
            pady=(0, 35),
        )

        ust = ctk.CTkFrame(
            ana_kart,
            corner_radius=12,
        )

        ust.pack(
            fill="x",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            ust,
            text=str(recete["ad"]),
            font=("Arial", 23, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 4),
        )

        durum = (
            "AKTİF"
            if int(recete["aktif"]) == 1
            else "PASİF"
        )

        ctk.CTkLabel(
            ust,
            text=(
                f"Reçete ID: {recete['id']}  •  "
                f"Revizyon: {recete['revizyon_no'] or '-'}  •  "
                f"Durum: {durum}  •  "
                f"Geçerlilik: "
                f"{recete['gecerlilik_tarihi'] or '-'}  •  "
                f"1 PARTİ: "
                f"{float(recete['parti_teorik_kg']):.3f} kg"
            ),
            font=("Arial", 14),
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18),
        )

        kuru_toplam_kpi = sum(
            float(kalem["miktar_kg"])
            for kalem in kalemler
        )
        toplam_kpi = kuru_toplam_kpi + proses_suyu_kg
        su_orani = (
            proses_suyu_kg / toplam_kpi * 100
            if toplam_kpi > 0
            else 0.0
        )

        kpi_alani = ctk.CTkFrame(
            ana_kart,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        kpi_verileri = (
            (
                "1 PARTİ",
                f"{float(recete['parti_teorik_kg']):.3f} kg",
            ),
            ("HAMMADDE KALEMİ", len(kalemler)),
            (
                "HAMMADDE TOPLAMI",
                f"{kuru_toplam_kpi:.3f} kg",
            ),
            (
                "PROSES SUYU ORANI",
                f"%{su_orani:.2f}",
            ),
        )

        for index in range(len(kpi_verileri)):
            kpi_alani.grid_columnconfigure(
                index,
                weight=1,
                uniform="recipe_kpi",
            )

        for index, (kart_basligi, deger) in enumerate(
            kpi_verileri
        ):
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5,
            )
            kart.grid_propagate(False)

            ctk.CTkLabel(
                kart,
                text=kart_basligi,
                font=("Arial", 10, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            ctk.CTkLabel(
                kart,
                text=str(deger),
                font=("Arial", 19, "bold"),
            ).pack()

        tablo = ctk.CTkFrame(
            ana_kart,
            corner_radius=12,
        )

        tablo.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10,
        )

        baslik = ctk.CTkFrame(
            tablo,
            corner_radius=8,
        )

        baslik.pack(
            fill="x",
            padx=12,
            pady=(12, 4),
        )

        baslik.grid_columnconfigure(
            0,
            weight=1,
        )

        baslik.grid_columnconfigure(
            1,
            weight=0,
        )

        ctk.CTkLabel(
            baslik,
            text="HAMMADDE / BİLEŞEN",
            font=("Arial", 13, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=10,
        )

        ctk.CTkLabel(
            baslik,
            text="1 PARTİ MİKTAR",
            font=("Arial", 13, "bold"),
        ).grid(
            row=0,
            column=1,
            sticky="e",
            padx=15,
            pady=10,
        )

        kuru_toplam = 0.0

        for kalem in kalemler:
            miktar = float(
                kalem["miktar_kg"]
            )

            kuru_toplam += miktar

            satir = ctk.CTkFrame(
                tablo,
                corner_radius=6,
            )

            satir.pack(
                fill="x",
                padx=12,
                pady=2,
            )

            satir.grid_columnconfigure(
                0,
                weight=1,
            )

            satir.grid_columnconfigure(
                1,
                weight=0,
            )

            ctk.CTkLabel(
                satir,
                text=str(kalem["ad"]),
                font=("Arial", 14),
            ).grid(
                row=0,
                column=0,
                sticky="w",
                padx=15,
                pady=8,
            )

            ctk.CTkLabel(
                satir,
                text=f"{miktar:.3f} kg",
                font=("Arial", 14, "bold"),
            ).grid(
                row=0,
                column=1,
                sticky="e",
                padx=15,
                pady=8,
            )

        su_satir = ctk.CTkFrame(
            tablo,
            corner_radius=6,
        )

        su_satir.pack(
            fill="x",
            padx=12,
            pady=2,
        )

        su_satir.grid_columnconfigure(
            0,
            weight=1,
        )

        su_satir.grid_columnconfigure(
            1,
            weight=0,
        )

        ctk.CTkLabel(
            su_satir,
            text="Proses Suyu",
            font=("Arial", 14),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=8,
        )

        ctk.CTkLabel(
            su_satir,
            text=f"{proses_suyu_kg:.3f} kg",
            font=("Arial", 14, "bold"),
        ).grid(
            row=0,
            column=1,
            sticky="e",
            padx=15,
            pady=8,
        )

        hesaplanan_toplam = (
            kuru_toplam
            + proses_suyu_kg
        )

        beklenen_toplam = float(
            recete["parti_teorik_kg"]
        )

        fark = (
            hesaplanan_toplam
            - beklenen_toplam
        )

        denge_durumu = (
            "KÜTLE DENGESİ UYUMLU"
            if abs(fark) < 0.000001
            else "KÜTLE DENGESİ UYUMSUZ"
        )

        ozet = ctk.CTkFrame(
            ana_kart,
            corner_radius=12,
        )

        ozet.pack(
            fill="x",
            padx=20,
            pady=(10, 20),
        )

        ctk.CTkLabel(
            ozet,
            text=(
                f"Hammadde Toplamı: "
                f"{kuru_toplam:.3f} kg"
            ),
            font=("Arial", 14),
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 3),
        )

        ctk.CTkLabel(
            ozet,
            text=(
                f"Proses Suyu: "
                f"{proses_suyu_kg:.3f} kg"
            ),
            font=("Arial", 14),
        ).pack(
            anchor="w",
            padx=20,
            pady=3,
        )

        ctk.CTkLabel(
            ozet,
            text=(
                f"Hesaplanan 1 Parti: "
                f"{hesaplanan_toplam:.3f} kg"
            ),
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=3,
        )

        ctk.CTkLabel(
            ozet,
            text=(
                f"Tanımlı 1 Parti: "
                f"{beklenen_toplam:.3f} kg"
            ),
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=3,
        )

        ctk.CTkLabel(
            ozet,
            text=(
                f"{denge_durumu}  •  "
                f"Fark: {fark:.6f} kg"
            ),
            font=("Arial", 15, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(3, 15),
        )

        islemler = ctk.CTkFrame(
            ozet,
            fg_color="transparent",
        )
        islemler.pack(
            fill="x",
            padx=20,
            pady=(5, 18),
        )

        ctk.CTkButton(
            islemler,
            text="+ YENİ HAMMADDE TANIMLA",
            command=self.recete_hammadde_tanimla,
            height=42,
            fg_color="#4B5563",
            font=("Arial", 13, "bold"),
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5),
        )

        ctk.CTkButton(
            islemler,
            text="YENİ REVİZYON OLUŞTUR",
            command=self.recete_revizyon_formu_ac,
            height=42,
            font=("Arial", 13, "bold"),
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0),
        )

        ctk.CTkLabel(
            ana_kart,
            text="REVİZYON GEÇMİŞİ",
            font=("Arial", 18, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(5, 8),
        )

        gecmis = ctk.CTkFrame(
            ana_kart,
            fg_color="transparent",
        )
        gecmis.pack(
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        gecmis_basliklari = (
            "REV",
            "REÇETE ADI",
            "GEÇERLİLİK",
            "DURUM",
            "OLUŞTURAN",
            "AÇIKLAMA",
        )

        for index in range(len(gecmis_basliklari)):
            gecmis.grid_columnconfigure(
                index,
                weight=1,
                uniform="recipe_history",
            )

        for column, baslik_metni in enumerate(
            gecmis_basliklari
        ):
            ctk.CTkLabel(
                gecmis,
                text=baslik_metni,
                height=38,
                fg_color="#1F2937",
                font=("Arial", 10, "bold"),
                wraplength=170,
            ).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=1,
                pady=1,
            )

        for row_index, row in enumerate(
            revizyonlar,
            1,
        ):
            renk = (
                "#292929"
                if row_index % 2
                else "#303030"
            )

            degerler = (
                row["revizyon_no"] or "-",
                row["ad"],
                row["gecerlilik_tarihi"] or "-",
                (
                    "AKTİF"
                    if int(row["aktif"]) == 1
                    else "PASİF"
                ),
                row["olusturan"] or "-",
                row["revizyon_aciklamasi"] or "-",
            )

            for column, deger in enumerate(degerler):
                ctk.CTkLabel(
                    gecmis,
                    text=str(deger),
                    height=40,
                    fg_color=renk,
                    font=("Arial", 10),
                    wraplength=170,
                ).grid(
                    row=row_index,
                    column=column,
                    sticky="nsew",
                    padx=1,
                    pady=1,
                )


    def recete_hammadde_tanimla(self):
        if not self.formul_erisim_kontrolu():
            return

        pencere = ctk.CTkToplevel(self)
        pencere.title("Yeni Hammadde Tanımla")
        pencere.geometry("520x360")
        pencere.resizable(False, False)
        pencere.transient(self)
        pencere.grab_set()

        govde = ctk.CTkFrame(pencere)
        govde.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        ctk.CTkLabel(
            govde,
            text="YENİ HAMMADDE TANIMLA",
            font=("Arial", 21, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5),
        )

        ctk.CTkLabel(
            govde,
            text=(
                "Tanımlanan hammadde, yeni reçete "
                "revizyonunda seçilebilir."
            ),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 15),
        )

        ctk.CTkLabel(
            govde,
            text="Hammadde Adı",
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(5, 3),
        )

        ad_entry = ctk.CTkEntry(
            govde,
            height=38,
        )
        ad_entry.pack(
            fill="x",
            padx=20,
            pady=(0, 10),
        )

        ctk.CTkLabel(
            govde,
            text="Birim",
            anchor="w",
        ).pack(
            fill="x",
            padx=20,
            pady=(5, 3),
        )

        birim_secim = ctk.CTkComboBox(
            govde,
            values=["kg", "g"],
            state="readonly",
            height=38,
        )
        birim_secim.pack(
            fill="x",
            padx=20,
            pady=(0, 15),
        )
        birim_secim.set("kg")

        ctk.CTkButton(
            govde,
            text="HAMMADDEYİ TANIMLA",
            height=42,
            font=("Arial", 13, "bold"),
            command=lambda: self.recete_hammadde_kaydet(
                pencere,
                ad_entry,
                birim_secim,
            ),
        ).pack(
            fill="x",
            padx=20,
            pady=(5, 20),
        )

        ad_entry.focus_set()

    def recete_hammadde_kaydet(
        self,
        pencere,
        ad_entry,
        birim_secim,
    ):
        ad = ad_entry.get().strip()
        birim = birim_secim.get().strip()

        if not ad:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Hammadde adı boş bırakılamaz.",
            )
            return

        if birim not in ("kg", "g"):
            messagebox.showwarning(
                "Birim Hatası",
                "Geçerli birim seçilmelidir.",
            )
            return

        conn = None

        try:
            conn = get_connection()
            conn.execute("BEGIN IMMEDIATE")

            mevcutlar = conn.execute("""
                SELECT
                    id,
                    ad,
                    aktif
                FROM hammaddeler
            """).fetchall()

            ayni = next(
                (
                    row
                    for row in mevcutlar
                    if str(row["ad"]).casefold()
                    == ad.casefold()
                ),
                None,
            )

            if ayni is not None:
                if int(ayni["aktif"]) == 1:
                    raise ValueError(
                        "Bu hammadde zaten aktif olarak tanımlı."
                    )

                conn.execute("""
                    UPDATE hammaddeler
                    SET
                        aktif = 1,
                        birim = ?
                    WHERE id = ?
                """, (
                    birim,
                    ayni["id"],
                ))
            else:
                conn.execute("""
                    INSERT INTO hammaddeler (
                        ad,
                        birim,
                        aktif
                    )
                    VALUES (?, ?, 1)
                """, (
                    ad,
                    birim,
                ))

            conn.commit()

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Hammadde Tanımlanamadı",
                str(hata),
            )
            return

        finally:
            if conn is not None:
                conn.close()

        if pencere.winfo_exists():
            pencere.destroy()

        messagebox.showinfo(
            "Reçete Merkezi",
            (
                f"{ad} başarıyla tanımlandı. "
                "Yeni revizyonda miktar verebilirsiniz."
            ),
        )

        self.recete()

    def recete_revizyon_no_uret(self, conn):
        rows = conn.execute(
            "SELECT revizyon_no FROM receteler"
        ).fetchall()

        sayilar = []

        for row in rows:
            try:
                sayilar.append(int(row["revizyon_no"]))
            except (TypeError, ValueError):
                continue

        sonraki = max(sayilar) + 1 if sayilar else 1

        return f"{sonraki:02d}"


    def recete_revizyon_formu_ac(self):
        if not self.formul_erisim_kontrolu():
            return

        conn = None

        try:
            conn = get_connection()

            recete = conn.execute(
                """
                SELECT
                    id,
                    ad,
                    parti_teorik_kg,
                    revizyon_no
                FROM receteler
                WHERE aktif = 1
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

            if recete is None:
                messagebox.showwarning(
                    "Aktif Reçete Yok",
                    "Revize edilecek aktif reçete bulunamadı.",
                )
                return

            kalemler = conn.execute(
                """
                SELECT
                    h.id AS hammadde_id,
                    h.ad,
                    COALESCE(
                        rk.miktar_kg,
                        0
                    ) AS miktar_kg,
                    CASE
                        WHEN rk.id IS NULL THEN 1
                        ELSE 0
                    END AS yeni_kalem
                FROM hammaddeler h
                LEFT JOIN recete_kalemleri rk
                  ON rk.hammadde_id = h.id
                 AND rk.recete_id = ?
                WHERE h.aktif = 1
                ORDER BY
                    yeni_kalem,
                    COALESCE(rk.id, h.id)
                """,
                (recete["id"],),
            ).fetchall()

            yeni_revizyon_no = (
                self.recete_revizyon_no_uret(conn)
            )

        finally:
            if conn is not None:
                conn.close()

        personeller = self.aktif_personelleri_getir()

        if not personeller:
            messagebox.showwarning(
                "Aktif Personel Yok",
                (
                    "Reçete revizyonunu oluşturacak "
                    "aktif personel bulunamadı."
                ),
            )
            return

        pencere = ctk.CTkToplevel(self)
        pencere.title("Yeni Reçete Revizyonu")
        pencere.geometry("760x820")
        pencere.minsize(700, 700)
        pencere.transient(self)
        pencere.grab_set()

        govde = ctk.CTkScrollableFrame(
            pencere,
            corner_radius=12,
        )
        govde.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        ctk.CTkLabel(
            govde,
            text="YENİ REÇETE REVİZYONU",
            font=("Arial", 24, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 5),
        )

        ctk.CTkLabel(
            govde,
            text=(
                f"Mevcut Revizyon: {recete["revizyon_no"]}  •  "
                f"Yeni Revizyon: {yeni_revizyon_no}"
            ),
            font=("Arial", 14),
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 15),
        )

        ctk.CTkLabel(
            govde,
            text="Reçete Adı",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(5, 3))

        ad_entry = ctk.CTkEntry(
            govde,
            height=38,
        )
        ad_entry.pack(fill="x", padx=15, pady=(0, 10))
        ad_entry.insert(
            0,
            (
                f"{recete["ad"]} "
                f"REV {yeni_revizyon_no}"
            ),
        )

        ctk.CTkLabel(
            govde,
            text="Geçerlilik Tarihi (GG.AA.YYYY)",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(5, 3))

        tarih_entry = ctk.CTkEntry(
            govde,
            height=38,
        )
        tarih_entry.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            govde,
            text="Revizyon Açıklaması",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(5, 3))

        aciklama_entry = ctk.CTkEntry(
            govde,
            height=38,
        )
        aciklama_entry.pack(
            fill="x",
            padx=15,
            pady=(0, 10),
        )

        ctk.CTkLabel(
            govde,
            text="Oluşturan Personel",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w", padx=15, pady=(5, 3))

        personel_secim = ctk.CTkComboBox(
            govde,
            values=personeller,
            height=38,
            state="readonly",
        )
        personel_secim.pack(
            fill="x",
            padx=15,
            pady=(0, 15),
        )
        personel_secim.set(personeller[0])

        ctk.CTkLabel(
            govde,
            text="1 PARTİ REÇETE KALEMLERİ",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(10, 8),
        )

        miktar_entryleri = {}

        for kalem in kalemler:
            satir = ctk.CTkFrame(
                govde,
                corner_radius=8,
            )
            satir.pack(
                fill="x",
                padx=15,
                pady=3,
            )
            satir.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                satir,
                text=str(kalem["ad"]),
                font=("Arial", 13),
            ).grid(
                row=0,
                column=0,
                sticky="w",
                padx=12,
                pady=8,
            )

            entry = ctk.CTkEntry(
                satir,
                width=130,
                height=34,
            )
            entry.grid(
                row=0,
                column=1,
                padx=12,
                pady=8,
            )
            entry.insert(
                0,
                f"{float(kalem["miktar_kg"]):.3f}",
            )

            miktar_entryleri[
                int(kalem["hammadde_id"])
            ] = entry

        ctk.CTkLabel(
            govde,
            text=(
                "Miktarı 0 olan yeni hammaddeler revizyona "
                "alınmaz. Toplam hammadde ve proses suyu "
                "tanımlı 1 parti miktarına eşit olmalıdır."
            ),
            font=("Arial", 12),
            wraplength=650,
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 8),
        )

        kaydet_buton = ctk.CTkButton(
            govde,
            text="REVİZYONU KAYDET",
            command=self.recete_revizyon_kaydet,
            height=44,
            font=("Arial", 14, "bold"),
        )
        kaydet_buton.pack(
            fill="x",
            padx=15,
            pady=(5, 20),
        )

        self.recete_revizyon_form_state = {
            "pencere": pencere,
            "kaynak_recete_id": int(recete["id"]),
            "yeni_revizyon_no": yeni_revizyon_no,
            "ad_entry": ad_entry,
            "tarih_entry": tarih_entry,
            "aciklama_entry": aciklama_entry,
            "personel_secim": personel_secim,
            "miktar_entryleri": miktar_entryleri,
            "kaydet_buton": kaydet_buton,
        }


    def recete_revizyon_kaydet(self):
        if not self.formul_erisim_kontrolu():
            return

        state = getattr(
            self,
            "recete_revizyon_form_state",
            None,
        )

        if not state:
            messagebox.showerror(
                "Revizyon Hatası",
                "Revizyon form durumu bulunamadı.",
            )
            return

        ad = state["ad_entry"].get().strip()
        tarih = state["tarih_entry"].get().strip()
        aciklama = (
            state["aciklama_entry"].get().strip()
        )
        personel_adi = (
            state["personel_secim"].get().strip()
        )

        if not ad:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Reçete adı boş bırakılamaz.",
            )
            return

        if not tarih:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Geçerlilik tarihi zorunludur.",
            )
            return

        try:
            datetime.strptime(
                tarih,
                "%d.%m.%Y",
            )

        except ValueError:
            messagebox.showwarning(
                "Tarih Hatası",
                "Geçerlilik tarihi GG.AA.YYYY olmalıdır.",
            )
            return

        if not aciklama:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Revizyon açıklaması zorunludur.",
            )
            return

        miktarlar = {}

        try:
            for (
                hammadde_id,
                entry,
            ) in state["miktar_entryleri"].items():
                metin = (
                    entry.get()
                    .strip()
                    .replace(",", ".")
                )

                miktar = float(metin) if metin else 0.0

                if miktar < 0:
                    raise ValueError(
                        "Reçete miktarı negatif olamaz."
                    )

                if miktar > 0:
                    miktarlar[int(hammadde_id)] = miktar

        except ValueError as hata:
            messagebox.showwarning(
                "Miktar Hatası",
                str(hata),
            )
            return

        if not miktarlar:
            messagebox.showerror(
                "Reçete Hatası",
                "Revizyonda en az bir hammadde bulunmalıdır.",
            )
            return

        conn = None

        try:
            conn = get_connection()
            conn.execute("BEGIN IMMEDIATE")

            kaynak = conn.execute(
                """
                SELECT
                    id,
                    parti_teorik_kg
                FROM receteler
                WHERE id = ?
                  AND aktif = 1
                LIMIT 1
                """,
                (
                    state["kaynak_recete_id"],
                ),
            ).fetchone()

            if kaynak is None:
                raise RuntimeError(
                    "Kaynak reçete artık aktif değil. Ekranı yenileyin."
                )

            kaynak_kalemler = conn.execute(
                """
                SELECT hammadde_id
                FROM recete_kalemleri
                WHERE recete_id = ?
                ORDER BY hammadde_id
                """,
                (
                    kaynak["id"],
                ),
            ).fetchall()

            kaynak_ids = {
                int(row["hammadde_id"])
                for row in kaynak_kalemler
            }

            if not kaynak_ids.issubset(
                set(miktarlar)
            ):
                raise RuntimeError(
                    "Mevcut reçete hammaddeleri yeni revizyonda "
                    "sıfır veya boş bırakılamaz."
                )

            ayar = conn.execute(
                """
                SELECT deger
                FROM sistem_ayarlari
                WHERE anahtar = ?
                LIMIT 1
                """,
                (
                    "PARTI_PROSES_SUYU_KG",
                ),
            ).fetchone()

            if ayar is None:
                raise RuntimeError(
                    "PARTI_PROSES_SUYU_KG sistem ayarı bulunamadı."
                )

            proses_suyu_kg = float(
                ayar["deger"]
            )

            hesaplanan_toplam = (
                sum(miktarlar.values())
                + proses_suyu_kg
            )

            parti_teorik_kg = float(
                kaynak["parti_teorik_kg"]
            )

            if abs(
                hesaplanan_toplam
                - parti_teorik_kg
            ) >= 0.000001:
                raise RuntimeError(
                    "Kütle dengesi uyumsuz. "
                    f"Hesaplanan: {hesaplanan_toplam:.3f} kg / "
                    f"Tanımlı: {parti_teorik_kg:.3f} kg"
                )

            personel = conn.execute(
                """
                SELECT id
                FROM personeller
                WHERE ad_soyad = ?
                  AND aktif = 1
                LIMIT 1
                """,
                (
                    personel_adi,
                ),
            ).fetchone()

            if personel is None:
                raise RuntimeError(
                    "Seçilen personel aktif değil veya bulunamadı."
                )

            yeni_revizyon_no = (
                self.recete_revizyon_no_uret(conn)
            )

            if (
                yeni_revizyon_no
                != state["yeni_revizyon_no"]
            ):
                raise RuntimeError(
                    "Revizyon numarası değişti. Ekranı yenileyin."
                )

            conn.execute(
                """
                UPDATE receteler
                SET aktif = 0
                WHERE id = ?
                  AND aktif = 1
                """,
                (
                    kaynak["id"],
                ),
            )

            if conn.total_changes < 1:
                raise RuntimeError(
                    "Kaynak reçete pasife alınamadı."
                )

            cursor = conn.execute(
                """
                INSERT INTO receteler (
                    ad,
                    parti_teorik_kg,
                    aktif,
                    revizyon_no,
                    gecerlilik_tarihi,
                    revizyon_aciklamasi,
                    olusturan_personel_id
                )
                VALUES (?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    ad,
                    parti_teorik_kg,
                    yeni_revizyon_no,
                    tarih,
                    aciklama,
                    personel["id"],
                ),
            )

            yeni_recete_id = cursor.lastrowid

            for (
                hammadde_id,
                miktar_kg,
            ) in miktarlar.items():
                conn.execute(
                    """
                    INSERT INTO recete_kalemleri (
                        recete_id,
                        hammadde_id,
                        miktar_kg
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        yeni_recete_id,
                        hammadde_id,
                        miktar_kg,
                    ),
                )

            aktif_sayisi = conn.execute(
                """
                SELECT COUNT(*)
                FROM receteler
                WHERE aktif = 1
                """
            ).fetchone()[0]

            yeni_kalem_sayisi = conn.execute(
                """
                SELECT COUNT(*)
                FROM recete_kalemleri
                WHERE recete_id = ?
                """,
                (
                    yeni_recete_id,
                ),
            ).fetchone()[0]

            if aktif_sayisi != 1:
                raise RuntimeError(
                    "Tek aktif reçete doğrulaması başarısız."
                )

            if yeni_kalem_sayisi != len(miktarlar):
                raise RuntimeError(
                    "Yeni reçete kalem sayısı doğrulaması başarısız."
                )

            conn.commit()

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Revizyon Kaydedilemedi",
                str(hata),
            )
            return

        finally:
            if conn is not None:
                conn.close()

        pencere = state.get("pencere")

        if (
            pencere is not None
            and pencere.winfo_exists()
        ):
            pencere.destroy()

        self.recete_revizyon_form_state = None

        messagebox.showinfo(
            "Reçete Revizyonu",
            (
                f"Revizyon {yeni_revizyon_no} başarıyla oluşturuldu. "
                "Yeni reçete aktif edildi."
            ),
        )

        self.recete()


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
            "Personel ve görev / yetki yönetimi"
        )

        ana = ctk.CTkFrame(self.content)
        ana.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30),
        )

        form_panel = ctk.CTkScrollableFrame(ana)
        liste_panel = ctk.CTkFrame(ana)
        liste_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        self.personel_form_panel = form_panel
        self.personel_liste_panel = liste_panel

        ctk.CTkButton(
            form_panel,
            text="← KAYITLARA DÖN",
            width=160,
            height=36,
            fg_color="#4B5563",
            command=self.personel_liste_goster,
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5),
        )

        form = ctk.CTkFrame(form_panel)
        form.pack(
            fill="x",
            padx=20,
            pady=(10, 10),
        )

        ctk.CTkLabel(
            form,
            text="YENİ PERSONEL KAYDI",
            font=("Arial", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            padx=15,
            pady=(15, 10),
        )

        alanlar = (
            ("Ad Soyad", "personel_ad"),
            ("Ana Görev / Ünvan", "personel_gorev"),
            ("Açıklama", "personel_aciklama"),
        )

        for column, (etiket, degisken) in enumerate(
            alanlar
        ):
            ctk.CTkLabel(
                form,
                text=etiket,
                anchor="w",
            ).grid(
                row=1,
                column=column,
                sticky="ew",
                padx=15,
                pady=(5, 3),
            )

            entry = ctk.CTkEntry(
                form,
                height=40,
            )
            entry.grid(
                row=2,
                column=column,
                sticky="ew",
                padx=15,
                pady=(0, 15),
            )
            setattr(self, degisken, entry)

        ctk.CTkButton(
            form,
            text="PERSONEL KAYDET",
            command=self.personel_kaydet,
            height=40,
            font=("Arial", 13, "bold"),
        ).grid(
            row=2,
            column=3,
            sticky="ew",
            padx=15,
            pady=(0, 15),
        )

        for column in range(4):
            form.grid_columnconfigure(
                column,
                weight=1,
                uniform="personnel_form",
            )

        yetki_frame = ctk.CTkFrame(form_panel)
        yetki_frame.pack(
            fill="x",
            padx=20,
            pady=(10, 20),
        )

        ctk.CTkLabel(
            yetki_frame,
            text="PERSONEL GÖREV / YETKİ ATAMA",
            font=("Arial", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=6,
            sticky="w",
            padx=15,
            pady=(15, 10),
        )

        aktif_personeller = self.aktif_personelleri_getir()

        if not aktif_personeller:
            aktif_personeller = ["AKTİF PERSONEL YOK"]

        ctk.CTkLabel(
            yetki_frame,
            text="Personel",
            anchor="w",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(5, 3),
        )

        self.personel_yetki_secim = ctk.CTkOptionMenu(
            yetki_frame,
            values=aktif_personeller,
            command=self.personel_yetki_secildi,
            height=38,
        )
        self.personel_yetki_secim.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 15),
        )

        self.personel_yetki_vars = {}

        yetkiler = [
            ("URETIM", "Üretim"),
            ("TEMIZLIK", "Temizlik"),
            ("DEPO_KABUL", "Depo Kabul"),
            ("PAKETLEME", "Paketleme"),
            ("SEVKIYAT", "Sevkiyat"),
        ]

        for index, (
            yetki_kodu,
            yetki_adi,
        ) in enumerate(yetkiler, 1):
            var = ctk.BooleanVar(value=False)
            self.personel_yetki_vars[yetki_kodu] = var

            ctk.CTkCheckBox(
                yetki_frame,
                text=yetki_adi,
                variable=var,
            ).grid(
                row=2,
                column=index,
                sticky="w",
                padx=10,
                pady=(0, 15),
            )

        ctk.CTkButton(
            yetki_frame,
            text="YETKİLERİ KAYDET",
            command=self.personel_yetkileri_kaydet,
            height=40,
            font=("Arial", 13, "bold"),
        ).grid(
            row=3,
            column=0,
            columnspan=6,
            sticky="ew",
            padx=15,
            pady=(0, 15),
        )

        for column in range(6):
            yetki_frame.grid_columnconfigure(
                column,
                weight=1,
            )

        ust = ctk.CTkFrame(
            liste_panel,
            fg_color="transparent",
        )
        ust.pack(
            fill="x",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            ust,
            text="PERSONEL KAYITLARI",
            font=("Arial", 22, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            ust,
            text="+ YENİ PERSONEL / YETKİ",
            width=210,
            height=40,
            font=("Arial", 13, "bold"),
            command=self.personel_form_goster,
        ).pack(side="right")

        kpi_alani = ctk.CTkFrame(
            liste_panel,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        self.personel_kpi_labels = []

        for baslik in (
            "TOPLAM PERSONEL",
            "AKTİF PERSONEL",
            "PASİF PERSONEL",
            "YETKİLİ PERSONEL",
        ):
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.pack(
                side="left",
                fill="x",
                expand=True,
                padx=5,
            )
            kart.pack_propagate(False)

            ctk.CTkLabel(
                kart,
                text=baslik,
                font=("Arial", 11, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            deger = ctk.CTkLabel(
                kart,
                text="0",
                font=("Arial", 21, "bold"),
            )
            deger.pack()
            self.personel_kpi_labels.append(deger)

        araclar = ctk.CTkFrame(
            liste_panel,
            fg_color="transparent",
        )
        araclar.pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        self.personel_arama = ctk.CTkEntry(
            araclar,
            placeholder_text=(
                "Ad soyad, görev, yetki veya açıklama ara..."
            ),
            height=38,
        )
        self.personel_arama.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8),
        )
        self.personel_arama.bind(
            "<KeyRelease>",
            lambda event: self.personel_listele(),
        )

        ctk.CTkButton(
            araclar,
            text="TEMİZLE",
            width=95,
            height=38,
            fg_color="#4B5563",
            command=self.personel_filtre_temizle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            araclar,
            text="AKTİF / PASİF DEĞİŞTİR",
            width=180,
            height=38,
            command=self.personel_secili_aktiflik_degistir,
        ).pack(side="left")

        self.personel_liste_frame = ctk.CTkFrame(
            liste_panel
        )
        self.personel_liste_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20),
        )

        self.personel_listele()

        if (
            aktif_personeller
            and aktif_personeller[0]
            != "AKTİF PERSONEL YOK"
        ):
            self.personel_yetki_secildi(
                aktif_personeller[0]
            )

    def personel_form_goster(self):
        self.personel_liste_panel.pack_forget()
        self.personel_form_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

    def personel_liste_goster(self):
        self.personel_form_panel.pack_forget()
        self.personel_liste_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        self.personel_listele()

    def personel_filtre_temizle(self):
        self.personel_arama.delete(0, "end")
        self.personel_listele()

    def personel_secili_aktiflik_degistir(self):
        secim = self.personel_tree.selection()

        if not secim:
            messagebox.showwarning(
                "Kayıt Seçilmedi",
                (
                    "Durumunu değiştirmek için "
                    "tablodan personel seçin."
                ),
            )
            return

        degerler = self.personel_tree.item(
            secim[0],
            "values",
        )
        mevcut_aktif = (
            1
            if degerler[2] == "AKTİF"
            else 0
        )

        self.personel_aktiflik_degistir(
            int(secim[0]),
            mevcut_aktif,
        )

    def personel_ozet_guncelle(self, arama=""):
        like = f"%{arama.casefold()}%"
        conn = get_connection()
        conn.create_function(
            "TR_CASEFOLD",
            1,
            lambda value: (
                str(value).casefold()
                if value is not None
                else ""
            ),
        )

        try:
            ozet = conn.execute("""
                SELECT
                    COUNT(DISTINCT p.id) AS toplam,
                    COUNT(
                        DISTINCT CASE
                            WHEN p.aktif = 1 THEN p.id
                        END
                    ) AS aktif,
                    COUNT(
                        DISTINCT CASE
                            WHEN p.aktif = 0 THEN p.id
                        END
                    ) AS pasif,
                    COUNT(
                        DISTINCT CASE
                            WHEN py.aktif = 1 THEN p.id
                        END
                    ) AS yetkili
                FROM personeller p
                LEFT JOIN personel_yetkileri py
                  ON py.personel_id = p.id
                WHERE (
                    ? = ''
                    OR TR_CASEFOLD(p.ad_soyad) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(p.gorev, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(p.aciklama, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(py.yetki_kodu, '')
                    ) LIKE ?
                )
            """, (
                arama,
                like,
                like,
                like,
                like,
            )).fetchone()
        finally:
            conn.close()

        degerler = (
            ozet["toplam"],
            ozet["aktif"],
            ozet["pasif"],
            ozet["yetkili"],
        )

        for label, deger in zip(
            self.personel_kpi_labels,
            degerler,
        ):
            label.configure(text=str(int(deger or 0)))

    def personel_yetki_secildi(
        self,
        secim=None
    ):
        try:
            ad_soyad = (
                self.personel_yetki_secim
                .get()
                .strip()
            )

            for var in (
                self.personel_yetki_vars
                .values()
            ):
                var.set(False)

            if (
                not ad_soyad
                or ad_soyad
                == "AKTİF PERSONEL YOK"
            ):
                return

            conn = get_connection()

            try:
                rows = conn.execute("""
                    SELECT
                        py.yetki_kodu
                    FROM personel_yetkileri py
                    JOIN personeller p
                        ON p.id = py.personel_id
                    WHERE
                        p.ad_soyad = ?
                        AND p.aktif = 1
                        AND py.aktif = 1
                    ORDER BY py.yetki_kodu
                """, (
                    ad_soyad,
                )).fetchall()

            finally:
                conn.close()

            for row in rows:
                yetki_kodu = row[
                    "yetki_kodu"
                ]

                if (
                    yetki_kodu
                    in self.personel_yetki_vars
                ):
                    self.personel_yetki_vars[
                        yetki_kodu
                    ].set(True)

        except Exception as hata:
            messagebox.showerror(
                "Personel Yetki Hatası",
                str(hata)
            )


    def personel_yetkileri_kaydet(self):
        conn = None

        try:
            ad_soyad = (
                self.personel_yetki_secim
                .get()
                .strip()
            )

            if (
                not ad_soyad
                or ad_soyad
                == "AKTİF PERSONEL YOK"
            ):
                raise ValueError(
                    "Geçerli personel seçilmelidir."
                )

            conn = get_connection()

            personel = conn.execute("""
                SELECT
                    id
                FROM personeller
                WHERE
                    ad_soyad = ?
                    AND aktif = 1
            """, (
                ad_soyad,
            )).fetchone()

            if personel is None:
                raise ValueError(
                    "Aktif personel bulunamadı."
                )

            personel_id = personel["id"]

            now = datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            )

            conn.execute("BEGIN")

            for (
                yetki_kodu,
                var
            ) in self.personel_yetki_vars.items():
                aktif = (
                    1
                    if var.get()
                    else 0
                )

                conn.execute("""
                    INSERT INTO personel_yetkileri (
                        personel_id,
                        yetki_kodu,
                        aktif,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (
                        personel_id,
                        yetki_kodu
                    )
                    DO UPDATE SET
                        aktif = excluded.aktif
                """, (
                    personel_id,
                    yetki_kodu,
                    aktif,
                    now,
                ))

            conn.commit()

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Personel görev / yetkileri "
                    "kaydedildi."
                )
            )

            self.personel_yetki_secildi(
                ad_soyad
            )

        except Exception as hata:
            if conn is not None:
                conn.rollback()

            messagebox.showerror(
                "Personel Yetki Hatası",
                str(hata)
            )

        finally:
            if conn is not None:
                conn.close()


    def yetkili_personelleri_getir(
        self,
        yetki_kodu
    ):
        conn = get_connection()

        try:
            rows = conn.execute("""
                SELECT
                    p.ad_soyad
                FROM personeller p
                JOIN personel_yetkileri py
                    ON py.personel_id = p.id
                WHERE
                    p.aktif = 1
                    AND py.aktif = 1
                    AND py.yetki_kodu = ?
                ORDER BY p.ad_soyad
            """, (
                yetki_kodu,
            )).fetchall()

            return [
                row["ad_soyad"]
                for row in rows
            ]

        finally:
            conn.close()


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

            self.personel()
            self.personel_form_goster()
            self.personel_yetki_secim.set(ad_soyad)
            self.personel_yetki_secildi(ad_soyad)

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

            self.personel()

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
        for widget in (
            self.personel_liste_frame.winfo_children()
        ):
            widget.destroy()

        arama = ""
        if hasattr(self, "personel_arama"):
            arama = self.personel_arama.get().strip()

        like = f"%{arama.casefold()}%"
        conn = get_connection()
        conn.create_function(
            "TR_CASEFOLD",
            1,
            lambda value: (
                str(value).casefold()
                if value is not None
                else ""
            ),
        )

        try:
            rows = conn.execute("""
                SELECT
                    p.id,
                    p.ad_soyad,
                    p.gorev,
                    p.aktif,
                    p.aciklama,
                    GROUP_CONCAT(
                        CASE
                            WHEN py.aktif = 1
                            THEN py.yetki_kodu
                        END,
                        ', '
                    ) AS yetkiler
                FROM personeller p
                LEFT JOIN personel_yetkileri py
                  ON py.personel_id = p.id
                WHERE (
                    ? = ''
                    OR TR_CASEFOLD(p.ad_soyad) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(p.gorev, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(p.aciklama, '')
                    ) LIKE ?
                    OR TR_CASEFOLD(
                        COALESCE(py.yetki_kodu, '')
                    ) LIKE ?
                )
                GROUP BY
                    p.id,
                    p.ad_soyad,
                    p.gorev,
                    p.aktif,
                    p.aciklama
                ORDER BY
                    p.aktif DESC,
                    p.ad_soyad COLLATE NOCASE
            """, (
                arama,
                like,
                like,
                like,
                like,
            )).fetchall()
        finally:
            conn.close()

        self.personel_ozet_guncelle(arama)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Personnel.Treeview",
            background="#292929",
            foreground="#F3F4F6",
            fieldbackground="#292929",
            borderwidth=0,
            rowheight=40,
            font=("Arial", 12),
        )
        style.configure(
            "Personnel.Treeview.Heading",
            background="#1F2937",
            foreground="#F9FAFB",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Personnel.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        tree_area = ctk.CTkFrame(
            self.personel_liste_frame
        )
        tree_area.pack(
            fill="both",
            expand=True,
        )
        tree_area.grid_rowconfigure(0, weight=1)
        tree_area.grid_columnconfigure(0, weight=1)

        columns = (
            "ad",
            "gorev",
            "durum",
            "yetkiler",
            "aciklama",
        )

        self.personel_tree = ttk.Treeview(
            tree_area,
            columns=columns,
            show="headings",
            style="Personnel.Treeview",
            selectmode="browse",
        )

        headings = (
            ("ad", "AD SOYAD", 190, "w"),
            ("gorev", "ANA GÖREV / ÜNVAN", 180, "w"),
            ("durum", "DURUM", 90, "center"),
            ("yetkiler", "GÖREV / YETKİLER", 310, "w"),
            ("aciklama", "AÇIKLAMA", 250, "w"),
        )

        for column, title, width, anchor in headings:
            self.personel_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.personel_tree.column(
                column,
                width=width,
                minwidth=80,
                anchor=anchor,
                stretch=True,
            )

        self.personel_tree.tag_configure(
            "even",
            background="#292929",
        )
        self.personel_tree.tag_configure(
            "odd",
            background="#303030",
        )
        self.personel_tree.tag_configure(
            "passive",
            foreground="#9CA3AF",
        )

        yetki_adlari = {
            "URETIM": "Üretim",
            "TEMIZLIK": "Temizlik",
            "DEPO_KABUL": "Depo Kabul",
            "PAKETLEME": "Paketleme",
            "SEVKIYAT": "Sevkiyat",
        }

        for index, row in enumerate(rows):
            kodlar = [
                kod.strip()
                for kod in (row["yetkiler"] or "").split(",")
                if kod.strip()
            ]
            yetkiler = ", ".join(
                yetki_adlari.get(kod, kod)
                for kod in kodlar
            ) or "-"

            tags = [
                "even" if index % 2 == 0 else "odd"
            ]

            if int(row["aktif"]) == 0:
                tags.append("passive")

            self.personel_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["ad_soyad"],
                    row["gorev"] or "-",
                    (
                        "AKTİF"
                        if int(row["aktif"]) == 1
                        else "PASİF"
                    ),
                    yetkiler,
                    row["aciklama"] or "-",
                ),
                tags=tuple(tags),
            )

        vertical = ttk.Scrollbar(
            tree_area,
            orient="vertical",
            command=self.personel_tree.yview,
        )
        horizontal = ttk.Scrollbar(
            tree_area,
            orient="horizontal",
            command=self.personel_tree.xview,
        )

        self.personel_tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.personel_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
        )

    def sistem(self):
        SystemPage(self).create()


if __name__ == "__main__":
    init_database()

    current_user = authenticate_user()

    if current_user is not None:
        app = RedboxOS(current_user)
        app.mainloop()
