from tkinter import messagebox, ttk

import customtkinter as ctk

from database.db import get_connection
from database.haccp_engine import (
    akis_dogrula,
    dogrulama_kaydet,
    haccp_plani_olustur,
    izleme_plani_ekle,
    kritik_limit_ekle,
    kontrol_noktasi_belirle,
    plan_revizyonu_olustur,
    plani_onayla,
    proses_adimi_ekle,
    sapma_kaydet,
    tehlike_degerlendir,
    tehlike_olustur,
)


ENGINE_ACTIONS = (
    haccp_plani_olustur,
    proses_adimi_ekle,
    tehlike_olustur,
    tehlike_degerlendir,
    kontrol_noktasi_belirle,
    kritik_limit_ekle,
    izleme_plani_ekle,
    sapma_kaydet,
    dogrulama_kaydet,
    plan_revizyonu_olustur,
    akis_dogrula,
    plani_onayla,
)


class HaccpWindow(ctk.CTkToplevel):

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.selected_plan_id = None
        self.product_map = {}
        self.personnel_map = {}

        self.title("REDBOX OS — HACCP Yönetim Merkezi")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        self.transient(app)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_workspace()
        self.refresh()

    def _build_header(self):
        header = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="#171717",
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ctk.CTkLabel(
            header,
            text="HACCP YÖNETİM MERKEZİ",
            font=("Arial", 28, "bold"),
        ).pack(
            anchor="w",
            padx=28,
            pady=(22, 4),
        )
        ctk.CTkLabel(
            header,
            text=(
                "Ürün güvenliği planlarını, proses akışını, "
                "tehlike analizini ve kritik kontrolleri yönetin."
            ),
            text_color="#A3A3A3",
            font=("Arial", 13),
        ).pack(
            anchor="w",
            padx=28,
            pady=(0, 20),
        )

    def _build_workspace(self):
        workspace = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        workspace.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=24,
            pady=20,
        )
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(2, weight=1)

        sections = ctk.CTkFrame(
            workspace,
            fg_color="transparent",
        )
        sections.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )

        titles = (
            "ÜRÜN VE PLAN KİMLİĞİ",
            "PROSES AKIŞI",
            "TEHLİKE ANALİZİ",
            "CCP / OPRP",
            "İZLEME VE SAPMA",
            "DOĞRULAMA VE REVİZYON",
        )
        for index, title in enumerate(titles):
            sections.grid_columnconfigure(
                index,
                weight=1,
                uniform="haccp_section",
            )
            ctk.CTkLabel(
                sections,
                text=title,
                corner_radius=8,
                fg_color="#262626",
                font=("Arial", 10, "bold"),
            ).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=3,
                ipady=10,
            )

        toolbar = ctk.CTkFrame(
            workspace,
            corner_radius=12,
        )
        toolbar.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )
        toolbar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(
            toolbar,
            placeholder_text=(
                "Plan kodu, ürün, plan adı veya durum ara..."
            ),
            height=40,
        )
        self.search.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(14, 7),
            pady=12,
        )
        self.search.bind(
            "<KeyRelease>",
            lambda _event: self.refresh(),
        )

        self.status = ctk.CTkComboBox(
            toolbar,
            values=[
                "TÜM DURUMLAR",
                "TASLAK",
                "INCELEMEDE",
                "ONAYLI",
                "ARSIV",
            ],
            state="readonly",
            width=145,
            height=40,
            command=lambda _value: self.refresh(),
        )
        self.status.set("TÜM DURUMLAR")
        self.status.grid(
            row=0,
            column=1,
            padx=7,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="YENİ HACCP PLANI",
            width=160,
            height=40,
            command=self.open_new_plan,
        ).grid(
            row=0,
            column=2,
            padx=7,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="PLANI YÖNET",
            width=130,
            height=40,
            fg_color="#7C3AED",
            command=self.open_selected_plan,
        ).grid(
            row=0,
            column=3,
            padx=(7, 14),
            pady=12,
        )

        table_frame = ctk.CTkFrame(
            workspace,
            corner_radius=12,
        )
        table_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
        )
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = (
            "kod",
            "urun",
            "ad",
            "revizyon",
            "durum",
            "proses",
            "tehlike",
            "kontrol",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = (
            ("kod", "Plan Kodu", 150),
            ("urun", "Ürün", 180),
            ("ad", "Plan Adı", 210),
            ("revizyon", "Rev.", 55),
            ("durum", "Durum", 90),
            ("proses", "Proses", 65),
            ("tehlike", "Tehlike", 70),
            ("kontrol", "CCP/OPRP", 85),
        )
        for column, title, width in headings:
            self.tree.heading(column, text=title)
            self.tree.column(
                column,
                width=width,
                minwidth=50,
                anchor="w",
            )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(12, 0),
            pady=12,
        )
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(0, 12),
            pady=12,
        )
        self.tree.configure(
            yscrollcommand=scrollbar.set,
        )
        self.tree.bind(
            "<<TreeviewSelect>>",
            self._selected,
        )

    def _selected(self, _event=None):
        selection = self.tree.selection()
        self.selected_plan_id = (
            int(selection[0])
            if selection
            else None
        )

    def refresh(self):
        search = self.search.get().strip()
        status = self.status.get()

        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.plan_kodu,
                    u.urun_adi,
                    p.ad,
                    p.revizyon_no,
                    p.durum,
                    (
                        SELECT COUNT(*)
                        FROM haccp_proses_adimlari AS a
                        WHERE a.plan_id = p.id
                    ) AS proses_sayisi,
                    (
                        SELECT COUNT(*)
                        FROM haccp_tehlike_degerlendirmeleri AS d
                        WHERE d.plan_id = p.id
                    ) AS tehlike_sayisi,
                    (
                        SELECT COUNT(*)
                        FROM haccp_kontrol_noktalari AS k
                        JOIN haccp_tehlike_degerlendirmeleri AS d
                          ON d.id = k.degerlendirme_id
                        WHERE d.plan_id = p.id
                          AND k.sinif IN ('CCP', 'OPRP')
                    ) AS kontrol_sayisi
                FROM haccp_planlari AS p
                JOIN urunler AS u ON u.id = p.urun_id
                WHERE (
                    ? = ''
                    OR p.plan_kodu LIKE '%' || ? || '%'
                    OR p.ad LIKE '%' || ? || '%'
                    OR u.urun_adi LIKE '%' || ? || '%'
                )
                  AND (
                    ? = 'TÜM DURUMLAR'
                    OR p.durum = ?
                  )
                ORDER BY p.id DESC
                """,
                (
                    search,
                    search,
                    search,
                    search,
                    status,
                    status,
                ),
            ).fetchall()
        finally:
            connection.close()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["plan_kodu"],
                    row["urun_adi"],
                    row["ad"],
                    row["revizyon_no"],
                    row["durum"],
                    row["proses_sayisi"],
                    row["tehlike_sayisi"],
                    row["kontrol_sayisi"],
                ),
            )

    def _load_form_maps(self):
        connection = get_connection()
        try:
            products = connection.execute(
                """
                SELECT id, urun_adi
                FROM urunler
                WHERE aktif = 1
                ORDER BY urun_adi
                """
            ).fetchall()
            personnel = connection.execute(
                """
                SELECT id, ad_soyad
                FROM personeller
                WHERE aktif = 1
                ORDER BY ad_soyad
                """
            ).fetchall()
        finally:
            connection.close()

        self.product_map = {
            row["urun_adi"]: row["id"]
            for row in products
        }
        self.personnel_map = {
            row["ad_soyad"]: row["id"]
            for row in personnel
        }

    def open_new_plan(self):
        self._load_form_maps()
        if not self.product_map or not self.personnel_map:
            messagebox.showwarning(
                "HACCP",
                "Aktif ürün ve personel kaydı gereklidir.",
                parent=self,
            )
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Yeni HACCP Planı")
        dialog.geometry("720x720")
        dialog.transient(self)
        dialog.grab_set()

        body = ctk.CTkScrollableFrame(dialog)
        body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )
        body.grid_columnconfigure(1, weight=1)

        code = ctk.CTkEntry(body)
        product = ctk.CTkComboBox(
            body,
            values=list(self.product_map),
            state="readonly",
        )
        product.set(next(iter(self.product_map)))
        name = ctk.CTkEntry(body)
        description = ctk.CTkTextbox(body, height=90)
        intended_use = ctk.CTkTextbox(body, height=80)
        consumer = ctk.CTkEntry(body)
        restrictions = ctk.CTkTextbox(body, height=70)
        preparer = ctk.CTkComboBox(
            body,
            values=list(self.personnel_map),
            state="readonly",
        )
        preparer.set(next(iter(self.personnel_map)))

        fields = (
            ("Plan Kodu", code),
            ("Ürün", product),
            ("Plan Adı", name),
            ("Ürün Açıklaması", description),
            ("Amaçlanan Kullanım", intended_use),
            ("Hedef Tüketici", consumer),
            ("Kullanım Kısıtları", restrictions),
            ("Hazırlayan", preparer),
        )
        for row, (label, widget) in enumerate(fields):
            ctk.CTkLabel(
                body,
                text=label,
                font=("Arial", 12, "bold"),
            ).grid(
                row=row,
                column=0,
                sticky="nw",
                padx=(0, 12),
                pady=7,
            )
            widget.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=7,
            )

        def save():
            connection = get_connection()
            try:
                plan_id = haccp_plani_olustur(
                    connection,
                    {
                        "plan_kodu": code.get(),
                        "urun_id": self.product_map[product.get()],
                        "ad": name.get(),
                        "urun_aciklamasi": description.get(
                            "1.0", "end"
                        ),
                        "amaclanan_kullanim": intended_use.get(
                            "1.0", "end"
                        ),
                        "hedef_tuketici": consumer.get(),
                        "kullanim_kisitlari": restrictions.get(
                            "1.0", "end"
                        ),
                        "hazirlayan_personel_id": (
                            self.personnel_map[preparer.get()]
                        ),
                    },
                    kullanici=self.app.current_user,
                )
            except Exception as error:
                messagebox.showerror(
                    "HACCP Planı",
                    str(error),
                    parent=dialog,
                )
                return
            finally:
                connection.close()

            dialog.destroy()
            self.refresh()
            self.tree.selection_set(str(plan_id))
            self.tree.see(str(plan_id))

        ctk.CTkButton(
            body,
            text="HACCP PLANINI OLUŞTUR",
            height=44,
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 8),
        )

    def open_selected_plan(self):
        if self.selected_plan_id is None:
            messagebox.showwarning(
                "HACCP",
                "Önce bir HACCP planı seçin.",
                parent=self,
            )
            return

        messagebox.showinfo(
            "HACCP Plan Yönetimi",
            (
                f"Seçilen plan ID: {self.selected_plan_id}\n\n"
                "Proses, tehlike, CCP/OPRP, izleme, sapma, "
                "doğrulama ve revizyon işlemleri HACCP motoru "
                "üzerinden kontrollü olarak yürütülür."
            ),
            parent=self,
        )
