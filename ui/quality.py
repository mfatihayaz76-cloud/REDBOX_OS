from datetime import datetime
import subprocess
from tkinter import messagebox, ttk

import customtkinter as ctk

from database.db import get_connection
from database.report_engine import kalite_capa_pdf_olustur
from database.quality_engine import (
    capa_durum_guncelle,
    capa_etkinlik_dogrula,
    capa_faaliyeti_ekle,
    capa_faaliyetlerini_getir,
    kalite_ozeti,
    uygunsuzluk_durum_guncelle,
    uygunsuzluk_olustur,
    uygunsuzluklari_getir,
)


class QualityPage:

    def __init__(self, app):
        self.app = app
        self.selected_quality_id = None
        self.selected_capa_id = None
        self.personnel_map = {}

    def create(self):
        self.app.show_page(
            "KALİTE / CAPA",
            (
                "Uygunsuzluk, kök neden ve düzeltici "
                "faaliyet yönetim merkezi"
            ),
        )

        workspace = ctk.CTkFrame(
            self.app.content,
            fg_color="transparent",
        )
        workspace.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 25),
        )

        self._load_personnel()
        self._build_kpis(workspace)
        self._build_toolbar(workspace)
        self._build_quality_table(workspace)
        self._build_capa_table(workspace)
        self.refresh()

    def _load_personnel(self):
        conn = get_connection()

        try:
            rows = conn.execute("""
                SELECT id, ad_soyad
                FROM personeller
                WHERE aktif = 1
                ORDER BY ad_soyad
            """).fetchall()
        finally:
            conn.close()

        self.personnel_map = {
            row["ad_soyad"]: row["id"]
            for row in rows
        }

    def _build_kpis(self, parent):
        area = ctk.CTkFrame(
            parent,
            fg_color="transparent",
        )
        area.pack(
            fill="x",
            pady=(0, 12),
        )

        self.kpi_labels = {}

        cards = (
            ("toplam", "TOPLAM UYGUNSUZLUK", "#2563EB"),
            ("acik", "AÇIK KAYIT", "#F59E0B"),
            ("kritik", "KRİTİK AÇIK", "#DC2626"),
            ("geciken", "GECİKEN", "#7C3AED"),
        )

        for index in range(len(cards)):
            area.grid_columnconfigure(
                index,
                weight=1,
                uniform="quality_kpi",
            )

        for index, (key, title, color) in enumerate(cards):
            card = ctk.CTkFrame(
                area,
                corner_radius=12,
                border_width=1,
                border_color=color,
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5,
            )

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 11, "bold"),
                text_color="#A3A3A3",
            ).pack(
                anchor="w",
                padx=16,
                pady=(13, 3),
            )

            label = ctk.CTkLabel(
                card,
                text="0",
                font=("Arial", 24, "bold"),
                text_color=color,
            )
            label.pack(
                anchor="w",
                padx=16,
                pady=(0, 13),
            )

            self.kpi_labels[key] = label

    def _build_toolbar(self, parent):
        toolbar = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        toolbar.pack(
            fill="x",
            pady=(0, 12),
        )
        toolbar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text=(
                "Kalitede ara: kayıt no, başlık, "
                "kategori, kaynak, sorumlu..."
            ),
            height=40,
        )
        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(14, 7),
            pady=12,
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda _event: self.refresh(),
        )

        self.status_filter = ctk.CTkComboBox(
            toolbar,
            values=[
                "TÜM DURUMLAR",
                "ACIK",
                "INCELEMEDE",
                "AKSIYONDA",
                "DOGRULAMADA",
                "KAPALI",
                "IPTAL",
            ],
            state="readonly",
            width=150,
            height=40,
            command=lambda _value: self.refresh(),
        )
        self.status_filter.grid(
            row=0,
            column=1,
            padx=7,
            pady=12,
        )
        self.status_filter.set("TÜM DURUMLAR")

        self.severity_filter = ctk.CTkComboBox(
            toolbar,
            values=[
                "TÜM ÖNEMLER",
                "DUSUK",
                "ORTA",
                "YUKSEK",
                "KRITIK",
            ],
            state="readonly",
            width=135,
            height=40,
            command=lambda _value: self.refresh(),
        )
        self.severity_filter.grid(
            row=0,
            column=2,
            padx=7,
            pady=12,
        )
        self.severity_filter.set("TÜM ÖNEMLER")

        ctk.CTkButton(
            toolbar,
            text="YENİ UYGUNSUZLUK",
            width=165,
            height=40,
            command=self.open_new_quality,
        ).grid(
            row=0,
            column=3,
            padx=7,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="CAPA EKLE",
            width=115,
            height=40,
            fg_color="#7C3AED",
            command=self.open_new_capa,
        ).grid(
            row=0,
            column=4,
            padx=7,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="PDF RAPORU",
            width=115,
            height=40,
            fg_color="#DC2626",
            command=self.create_pdf,
        ).grid(
            row=0,
            column=5,
            padx=(7, 14),
            pady=12,
        )


    def create_pdf(self):
        arama = self.search_entry.get().strip() or None
        durum = self.status_filter.get()

        if durum == "TÜM DURUMLAR":
            durum = None

        onem_derecesi = self.severity_filter.get()

        if onem_derecesi == "TÜM ÖNEMLER":
            onem_derecesi = None

        conn = get_connection()

        try:
            pdf = kalite_capa_pdf_olustur(
                conn,
                arama=arama,
                durum=durum,
                onem_derecesi=onem_derecesi,
            )

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False,
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Kalite/CAPA PDF raporu oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                ),
            )
        except Exception as error:
            messagebox.showerror(
                "Kalite/CAPA PDF Hatası",
                str(error),
            )
        finally:
            conn.close()


    def _tree_style(self):
        style = ttk.Style()
        style.configure(
            "Quality.Treeview",
            background="#252525",
            fieldbackground="#252525",
            foreground="#E5E7EB",
            rowheight=34,
            borderwidth=0,
            font=("Arial", 11),
        )
        style.configure(
            "Quality.Treeview.Heading",
            background="#343434",
            foreground="#F3F4F6",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "Quality.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

    def _build_quality_table(self, parent):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        card.pack(
            fill="both",
            expand=True,
            pady=(0, 12),
        )

        header = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        header.pack(
            fill="x",
            padx=15,
            pady=(12, 6),
        )

        ctk.CTkLabel(
            header,
            text="UYGUNSUZLUK KAYITLARI",
            font=("Arial", 16, "bold"),
        ).pack(side="left")

        self.quality_count_label = ctk.CTkLabel(
            header,
            text="0 kayıt",
            font=("Arial", 11, "bold"),
            text_color="#A3A3A3",
        )
        self.quality_count_label.pack(side="right")

        frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self._tree_style()

        columns = (
            "record",
            "date",
            "source",
            "title",
            "severity",
            "status",
            "responsible",
            "target",
            "open_capa",
        )

        self.quality_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            style="Quality.Treeview",
            height=9,
            selectmode="browse",
        )

        headings = (
            ("record", "KAYIT NO", 125, "w"),
            ("date", "TESPİT", 90, "center"),
            ("source", "KAYNAK", 115, "w"),
            ("title", "BAŞLIK", 230, "w"),
            ("severity", "ÖNEM", 80, "center"),
            ("status", "DURUM", 105, "center"),
            ("responsible", "SORUMLU", 125, "w"),
            ("target", "HEDEF", 90, "center"),
            ("open_capa", "AÇIK CAPA", 80, "center"),
        )

        for column, title, width, anchor in headings:
            self.quality_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.quality_tree.column(
                column,
                width=width,
                minwidth=65,
                anchor=anchor,
                stretch=(column == "title"),
            )

        self.quality_tree.tag_configure(
            "even",
            background="#252525",
        )
        self.quality_tree.tag_configure(
            "odd",
            background="#2D2D2D",
        )
        self.quality_tree.tag_configure(
            "critical",
            foreground="#F87171",
        )
        self.quality_tree.tag_configure(
            "closed",
            foreground="#86EFAC",
        )

        vertical = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.quality_tree.yview,
        )
        horizontal = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=self.quality_tree.xview,
        )

        self.quality_tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )
        self.quality_tree.grid(
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

        self.quality_tree.bind(
            "<<TreeviewSelect>>",
            self._quality_selected,
        )

    def _build_capa_table(self, parent):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        card.pack(
            fill="both",
            expand=True,
        )

        header = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        header.pack(
            fill="x",
            padx=15,
            pady=(12, 6),
        )

        self.capa_title_label = ctk.CTkLabel(
            header,
            text="SEÇİLİ KAYDIN CAPA FAALİYETLERİ",
            font=("Arial", 16, "bold"),
        )
        self.capa_title_label.pack(side="left")

        ctk.CTkButton(
            header,
            text="ETKİNLİK DOĞRULA",
            width=145,
            height=34,
            fg_color="#7C3AED",
            command=self.open_effectiveness,
        ).pack(
            side="right",
            padx=(6, 0),
        )

        ctk.CTkButton(
            header,
            text="CAPA TAMAMLA",
            width=125,
            height=34,
            fg_color="#059669",
            command=self.open_complete_capa,
        ).pack(
            side="right",
            padx=6,
        )

        ctk.CTkButton(
            header,
            text="DURUM İLERLET",
            width=125,
            height=34,
            fg_color="#B45309",
            command=self.advance_quality_status,
        ).pack(
            side="right",
            padx=6,
        )

        frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        columns = (
            "type",
            "description",
            "responsible",
            "target",
            "status",
            "effectiveness",
        )

        self.capa_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            style="Quality.Treeview",
            height=5,
            selectmode="browse",
        )

        headings = (
            ("type", "FAALİYET", 110, "w"),
            ("description", "AÇIKLAMA", 350, "w"),
            ("responsible", "SORUMLU", 135, "w"),
            ("target", "HEDEF", 90, "center"),
            ("status", "DURUM", 120, "center"),
            ("effectiveness", "ETKİNLİK", 100, "center"),
        )

        for column, title, width, anchor in headings:
            self.capa_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.capa_tree.column(
                column,
                width=width,
                minwidth=75,
                anchor=anchor,
                stretch=(column == "description"),
            )

        vertical = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.capa_tree.yview,
        )

        self.capa_tree.configure(
            yscrollcommand=vertical.set,
        )
        self.capa_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.capa_tree.bind(
            "<<TreeviewSelect>>",
            self._capa_selected,
        )

    def refresh(self):
        conn = get_connection()

        try:
            summary = kalite_ozeti(conn)

            status_value = (
                self.status_filter.get().strip()
            )
            severity_value = (
                self.severity_filter.get().strip()
            )

            rows = uygunsuzluklari_getir(
                conn,
                arama=(
                    self.search_entry.get().strip()
                    or None
                ),
                durum=(
                    None
                    if status_value == "TÜM DURUMLAR"
                    else status_value
                ),
                onem_derecesi=(
                    None
                    if severity_value == "TÜM ÖNEMLER"
                    else severity_value
                ),
            )
        finally:
            conn.close()

        for key in (
            "toplam",
            "acik",
            "kritik",
            "geciken",
        ):
            self.kpi_labels[key].configure(
                text=str(int(summary[key] or 0))
            )

        for item in self.quality_tree.get_children():
            self.quality_tree.delete(item)

        for index, row in enumerate(rows):
            tags = [
                "even" if index % 2 == 0 else "odd"
            ]

            if row["onem_derecesi"] == "KRITIK":
                tags.append("critical")

            if row["durum"] == "KAPALI":
                tags.append("closed")

            self.quality_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["kayit_no"],
                    row["tespit_tarihi"],
                    row["kaynak_turu"],
                    row["baslik"],
                    row["onem_derecesi"],
                    row["durum"],
                    row["sorumlu_personel"] or "-",
                    row["hedef_tarih"] or "-",
                    row["acik_capa"],
                ),
                tags=tuple(tags),
            )

        self.quality_count_label.configure(
            text=f"{len(rows)} kayıt"
        )

        visible_ids = {
            str(row["id"])
            for row in rows
        }

        if (
            self.selected_quality_id is not None
            and str(self.selected_quality_id)
            not in visible_ids
        ):
            self.selected_quality_id = None
            self._refresh_capa()

    def _quality_selected(self, _event=None):
        selection = self.quality_tree.selection()

        if not selection:
            self.selected_quality_id = None
        else:
            self.selected_quality_id = int(
                selection[0]
            )

        self._refresh_capa()

    def _refresh_capa(self):
        self.selected_capa_id = None

        for item in self.capa_tree.get_children():
            self.capa_tree.delete(item)

        if self.selected_quality_id is None:
            self.capa_title_label.configure(
                text="SEÇİLİ KAYDIN CAPA FAALİYETLERİ"
            )
            return

        conn = get_connection()

        try:
            quality = conn.execute("""
                SELECT kayit_no
                FROM kalite_uygunsuzluklari
                WHERE id = ?
            """, (
                self.selected_quality_id,
            )).fetchone()

            rows = capa_faaliyetlerini_getir(
                conn,
                self.selected_quality_id,
            )
        finally:
            conn.close()

        self.capa_title_label.configure(
            text=(
                f'{quality["kayit_no"]} — '
                "CAPA FAALİYETLERİ"
            )
        )

        for row in rows:
            self.capa_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["faaliyet_turu"],
                    row["aciklama"],
                    row["sorumlu_personel"],
                    row["hedef_tarih"],
                    row["durum"],
                    row["etkinlik_durumu"] or "BEKLIYOR",
                ),
            )

    def _capa_selected(self, _event=None):
        selection = self.capa_tree.selection()

        self.selected_capa_id = (
            int(selection[0])
            if selection
            else None
        )

    def advance_quality_status(self):
        if self.selected_quality_id is None:
            messagebox.showwarning(
                "Kalite",
                "Önce bir uygunsuzluk kaydı seçin.",
            )
            return

        conn = get_connection()

        try:
            row = conn.execute("""
                SELECT
                    kayit_no,
                    durum
                FROM kalite_uygunsuzluklari
                WHERE id = ?
            """, (
                self.selected_quality_id,
            )).fetchone()
        finally:
            conn.close()

        if row is None:
            messagebox.showerror(
                "Kalite",
                "Seçilen uygunsuzluk bulunamadı.",
            )
            return

        transitions = {
            "ACIK": "INCELEMEDE",
            "INCELEMEDE": "AKSIYONDA",
            "AKSIYONDA": "DOGRULAMADA",
        }

        if row["durum"] == "DOGRULAMADA":
            self.open_close_quality()
            return

        new_status = transitions.get(
            row["durum"]
        )

        if new_status is None:
            messagebox.showwarning(
                "Kalite",
                (
                    f'{row["kayit_no"]} kaydı '
                    f'{row["durum"]} durumunda ilerletilemez.'
                ),
            )
            return

        confirmed = messagebox.askyesno(
            "Kalite Durumu",
            (
                f'{row["kayit_no"]}\n\n'
                f'{row["durum"]} → {new_status}\n\n'
                "Durum ilerletilsin mi?"
            ),
        )

        if not confirmed:
            return

        conn = get_connection()

        try:
            conn.execute("BEGIN IMMEDIATE")

            uygunsuzluk_durum_guncelle(
                conn,
                uygunsuzluk_id=self.selected_quality_id,
                yeni_durum=new_status,
                kullanici=self.app.current_user,
            )

            conn.commit()

        except Exception as exc:
            conn.rollback()
            messagebox.showerror(
                "Kalite Durumu",
                str(exc),
            )
            return

        finally:
            conn.close()

        self.refresh()
        self._reselect_quality()

    def _reselect_quality(self):
        if self.selected_quality_id is None:
            return

        item = str(self.selected_quality_id)

        if self.quality_tree.exists(item):
            self.quality_tree.selection_set(item)
            self.quality_tree.focus(item)
            self.quality_tree.see(item)
            self._refresh_capa()

    def open_complete_capa(self):
        if self.selected_capa_id is None:
            messagebox.showwarning(
                "CAPA",
                "Önce tamamlanacak CAPA faaliyetini seçin.",
            )
            return

        window = ctk.CTkToplevel(self.app)
        window.title("CAPA Faaliyetini Tamamla")
        window.geometry("620x430")
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkFrame(window)
        body.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        body.grid_columnconfigure(1, weight=1)

        completion_date = ctk.CTkEntry(body)
        completion_date.insert(
            0,
            datetime.now().strftime("%d.%m.%Y"),
        )
        completion_note = ctk.CTkTextbox(
            body,
            height=160,
        )

        self._form_row(
            body,
            0,
            "Tamamlanma Tarihi",
            completion_date,
        )
        self._form_row(
            body,
            1,
            "Tamamlanma Açıklaması",
            completion_note,
        )

        def save():
            conn = get_connection()

            try:
                conn.execute("BEGIN IMMEDIATE")

                capa_durum_guncelle(
                    conn,
                    capa_id=self.selected_capa_id,
                    yeni_durum="TAMAMLANDI",
                    tamamlanma_tarihi=(
                        completion_date.get()
                    ),
                    tamamlanma_aciklamasi=(
                        completion_note.get(
                            "1.0",
                            "end",
                        )
                    ),
                    kullanici=self.app.current_user,
                )

                conn.commit()

            except Exception as exc:
                conn.rollback()
                messagebox.showerror(
                    "CAPA Tamamlama",
                    str(exc),
                    parent=window,
                )
                return

            finally:
                conn.close()

            window.destroy()
            self.refresh()
            self._reselect_quality()

        ctk.CTkButton(
            body,
            text="CAPA FAALİYETİNİ TAMAMLA",
            height=44,
            fg_color="#059669",
            command=save,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )

    def open_effectiveness(self):
        if self.selected_capa_id is None:
            messagebox.showwarning(
                "CAPA",
                "Önce doğrulanacak CAPA faaliyetini seçin.",
            )
            return

        window = ctk.CTkToplevel(self.app)
        window.title("CAPA Etkinlik Doğrulaması")
        window.geometry("650x540")
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkFrame(window)
        body.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        body.grid_columnconfigure(1, weight=1)

        result = ctk.CTkComboBox(
            body,
            values=[
                "ETKILI",
                "ETKISIZ",
            ],
            state="readonly",
        )
        result.set("ETKILI")

        explanation = ctk.CTkTextbox(
            body,
            height=160,
        )

        personnel = list(self.personnel_map)
        verifier = ctk.CTkComboBox(
            body,
            values=personnel,
            state="readonly",
        )

        current_name = self.app.current_user.get(
            "ad_soyad",
            "",
        )
        verifier.set(
            current_name
            if current_name in self.personnel_map
            else personnel[0]
        )

        verification_date = ctk.CTkEntry(body)
        verification_date.insert(
            0,
            datetime.now().strftime("%d.%m.%Y"),
        )

        fields = (
            ("Etkinlik Sonucu", result),
            ("Etkinlik Açıklaması", explanation),
            ("Doğrulayan", verifier),
            ("Doğrulama Tarihi", verification_date),
        )

        for row, (label, widget) in enumerate(fields):
            self._form_row(
                body,
                row,
                label,
                widget,
            )

        def save():
            conn = get_connection()

            try:
                conn.execute("BEGIN IMMEDIATE")

                capa_etkinlik_dogrula(
                    conn,
                    capa_id=self.selected_capa_id,
                    etkinlik_durumu=result.get(),
                    etkinlik_aciklamasi=(
                        explanation.get(
                            "1.0",
                            "end",
                        )
                    ),
                    dogrulayan_personel_id=(
                        self.personnel_map[
                            verifier.get()
                        ]
                    ),
                    dogrulama_tarihi=(
                        verification_date.get()
                    ),
                    kullanici=self.app.current_user,
                )

                conn.commit()

            except Exception as exc:
                conn.rollback()
                messagebox.showerror(
                    "Etkinlik Doğrulaması",
                    str(exc),
                    parent=window,
                )
                return

            finally:
                conn.close()

            window.destroy()
            self.refresh()
            self._reselect_quality()

        ctk.CTkButton(
            body,
            text="ETKİNLİK SONUCUNU KAYDET",
            height=44,
            fg_color="#7C3AED",
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )

    def open_close_quality(self):
        window = ctk.CTkToplevel(self.app)
        window.title("Uygunsuzluğu Kapat")
        window.geometry("680x620")
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkFrame(window)
        body.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        body.grid_columnconfigure(1, weight=1)

        root_cause = ctk.CTkTextbox(
            body,
            height=150,
        )
        closing_note = ctk.CTkTextbox(
            body,
            height=150,
        )
        closing_date = ctk.CTkEntry(body)
        closing_date.insert(
            0,
            datetime.now().strftime("%d.%m.%Y"),
        )

        self._form_row(
            body,
            0,
            "Kök Neden",
            root_cause,
        )
        self._form_row(
            body,
            1,
            "Kapanış Açıklaması",
            closing_note,
        )
        self._form_row(
            body,
            2,
            "Kapatma Tarihi",
            closing_date,
        )

        def save():
            conn = get_connection()

            try:
                conn.execute("BEGIN IMMEDIATE")

                uygunsuzluk_durum_guncelle(
                    conn,
                    uygunsuzluk_id=(
                        self.selected_quality_id
                    ),
                    yeni_durum="KAPALI",
                    kok_neden=root_cause.get(
                        "1.0",
                        "end",
                    ),
                    kapanis_aciklamasi=(
                        closing_note.get(
                            "1.0",
                            "end",
                        )
                    ),
                    kapatma_tarihi=(
                        closing_date.get()
                    ),
                    kullanici=self.app.current_user,
                )

                conn.commit()

            except Exception as exc:
                conn.rollback()
                messagebox.showerror(
                    "Uygunsuzluk Kapatma",
                    str(exc),
                    parent=window,
                )
                return

            finally:
                conn.close()

            window.destroy()
            self.refresh()
            self._reselect_quality()

        ctk.CTkButton(
            body,
            text="UYGUNSUZLUĞU KAPAT",
            height=44,
            fg_color="#DC2626",
            command=save,
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )

    def _form_row(
        self,
        parent,
        row,
        label,
        widget,
    ):
        ctk.CTkLabel(
            parent,
            text=label,
            font=("Arial", 12, "bold"),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )
        widget.grid(
            row=row,
            column=1,
            sticky="ew",
            pady=6,
        )

    def open_new_quality(self):
        window = ctk.CTkToplevel(self.app)
        window.title("Yeni Uygunsuzluk Kaydı")
        window.geometry("720x760")
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkScrollableFrame(window)
        body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )
        body.grid_columnconfigure(1, weight=1)

        today = datetime.now().strftime("%d.%m.%Y")

        record_date = ctk.CTkEntry(body)
        record_date.insert(0, today)
        detection_date = ctk.CTkEntry(body)
        detection_date.insert(0, today)

        source = ctk.CTkComboBox(
            body,
            values=[
                "DEPO_KABUL",
                "URETIM",
                "PAKETLEME",
                "SEVKIYAT",
                "TEMIZLIK",
                "MUSTERI_SIKAYETI",
                "TEDARIKCI",
                "DIGER",
            ],
            state="readonly",
        )
        source.set("URETIM")

        source_id = ctk.CTkEntry(
            body,
            placeholder_text=(
                "Varsa ilgili kayıt ID"
            ),
        )
        category = ctk.CTkEntry(body)
        title = ctk.CTkEntry(body)
        description = ctk.CTkTextbox(
            body,
            height=90,
        )
        severity = ctk.CTkComboBox(
            body,
            values=[
                "DUSUK",
                "ORTA",
                "YUKSEK",
                "KRITIK",
            ],
            state="readonly",
        )
        severity.set("ORTA")

        personnel = list(self.personnel_map)
        reporter = ctk.CTkComboBox(
            body,
            values=personnel,
            state="readonly",
        )
        responsible = ctk.CTkComboBox(
            body,
            values=["ATANMADI"] + personnel,
            state="readonly",
        )

        current_name = self.app.current_user.get(
            "ad_soyad",
            "",
        )

        reporter.set(
            current_name
            if current_name in self.personnel_map
            else personnel[0]
        )
        responsible.set("ATANMADI")

        target_date = ctk.CTkEntry(
            body,
            placeholder_text="GG.AA.YYYY",
        )
        immediate_action = ctk.CTkTextbox(
            body,
            height=80,
        )

        fields = (
            ("Kayıt Tarihi", record_date),
            ("Tespit Tarihi", detection_date),
            ("Kaynak Türü", source),
            ("Bağlı Kayıt ID", source_id),
            ("Kategori", category),
            ("Başlık", title),
            ("Açıklama", description),
            ("Önem Derecesi", severity),
            ("Bildiren", reporter),
            ("Sorumlu", responsible),
            ("Hedef Tarih", target_date),
            ("Anlık Aksiyon", immediate_action),
        )

        for row, (label, widget) in enumerate(fields):
            self._form_row(
                body,
                row,
                label,
                widget,
            )

        def save():
            conn = None

            try:
                source_value = source.get().strip()
                source_id_text = source_id.get().strip()
                relation = {}

                relation_map = {
                    "DEPO_KABUL": "depo_kabul_id",
                    "URETIM": "uretim_id",
                    "PAKETLEME": "paketleme_id",
                    "SEVKIYAT": "sevkiyat_id",
                    "TEDARIKCI": "tedarikci_id",
                    "MUSTERI_SIKAYETI": "musteri_id",
                }

                if source_id_text:
                    key = relation_map.get(source_value)

                    if key:
                        relation[key] = int(source_id_text)

                reporter_id = self.personnel_map[
                    reporter.get()
                ]

                responsible_value = responsible.get()
                responsible_id = (
                    None
                    if responsible_value == "ATANMADI"
                    else self.personnel_map[
                        responsible_value
                    ]
                )

                conn = get_connection()
                conn.execute("BEGIN IMMEDIATE")

                _quality_id, record_no = (
                    uygunsuzluk_olustur(
                        conn,
                        kayit_tarihi=record_date.get(),
                        tespit_tarihi=detection_date.get(),
                        kaynak_turu=source_value,
                        kategori=category.get(),
                        baslik=title.get(),
                        aciklama=description.get(
                            "1.0",
                            "end",
                        ),
                        onem_derecesi=severity.get(),
                        bildiren_personel_id=reporter_id,
                        sorumlu_personel_id=responsible_id,
                        hedef_tarih=(
                            target_date.get().strip()
                            or None
                        ),
                        anlik_aksiyon=(
                            immediate_action.get(
                                "1.0",
                                "end",
                            )
                        ),
                        kullanici=self.app.current_user,
                        **relation,
                    )
                )

                conn.commit()

            except Exception as exc:
                if conn is not None:
                    conn.rollback()

                messagebox.showerror(
                    "Uygunsuzluk Kaydı",
                    str(exc),
                    parent=window,
                )
                return

            finally:
                if conn is not None:
                    conn.close()

            messagebox.showinfo(
                "Uygunsuzluk Kaydı",
                f"{record_no} başarıyla oluşturuldu.",
                parent=window,
            )
            window.destroy()
            self.refresh()

        ctk.CTkButton(
            body,
            text="UYGUNSUZLUĞU KAYDET",
            height=44,
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 8),
        )

    def open_new_capa(self):
        if self.selected_quality_id is None:
            messagebox.showwarning(
                "CAPA",
                "Önce bir uygunsuzluk kaydı seçin.",
            )
            return

        window = ctk.CTkToplevel(self.app)
        window.title("Yeni CAPA Faaliyeti")
        window.geometry("650x500")
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkFrame(window)
        body.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        body.grid_columnconfigure(1, weight=1)

        activity_type = ctk.CTkComboBox(
            body,
            values=[
                "DUZELTME",
                "DUZELTICI",
                "ONLEYICI",
            ],
            state="readonly",
        )
        activity_type.set("DUZELTICI")

        description = ctk.CTkTextbox(
            body,
            height=130,
        )

        personnel = list(self.personnel_map)
        responsible = ctk.CTkComboBox(
            body,
            values=personnel,
            state="readonly",
        )
        responsible.set(personnel[0])

        target_date = ctk.CTkEntry(
            body,
            placeholder_text="GG.AA.YYYY",
        )

        fields = (
            ("Faaliyet Türü", activity_type),
            ("Faaliyet Açıklaması", description),
            ("Sorumlu", responsible),
            ("Hedef Tarih", target_date),
        )

        for row, (label, widget) in enumerate(fields):
            self._form_row(
                body,
                row,
                label,
                widget,
            )

        def save():
            conn = None

            try:
                conn = get_connection()
                conn.execute("BEGIN IMMEDIATE")

                capa_faaliyeti_ekle(
                    conn,
                    uygunsuzluk_id=(
                        self.selected_quality_id
                    ),
                    faaliyet_turu=activity_type.get(),
                    aciklama=description.get(
                        "1.0",
                        "end",
                    ),
                    sorumlu_personel_id=(
                        self.personnel_map[
                            responsible.get()
                        ]
                    ),
                    hedef_tarih=target_date.get(),
                    kullanici=self.app.current_user,
                )

                conn.commit()

            except Exception as exc:
                if conn is not None:
                    conn.rollback()

                messagebox.showerror(
                    "CAPA",
                    str(exc),
                    parent=window,
                )
                return

            finally:
                if conn is not None:
                    conn.close()

            messagebox.showinfo(
                "CAPA",
                "CAPA faaliyeti başarıyla oluşturuldu.",
                parent=window,
            )
            window.destroy()
            self.refresh()
            self._refresh_capa()

        ctk.CTkButton(
            body,
            text="CAPA FAALİYETİNİ KAYDET",
            height=44,
            fg_color="#7C3AED",
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 0),
        )
