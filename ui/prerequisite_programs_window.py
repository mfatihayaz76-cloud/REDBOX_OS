from tkinter import messagebox, ttk

import customtkinter as ctk

from database.db import get_connection
from database.prerequisite_programs_engine import (
    prp_ozeti,
    prp_programi_olustur,
    prp_programlarini_getir,
)


PROGRAM_LABELS = {
    "ALERJEN": "ALERJEN YÖNETİMİ",
    "KALIBRASYON": "KALİBRASYON",
    "BAKIM_ARIZA": "BAKIM VE ARIZA",
    "ZARARLI_MUCADELESI": "ZARARLI MÜCADELESİ",
    "EGITIM_YETKINLIK": "EĞİTİM VE YETKİNLİK",
    "TACCP": "GIDA SAVUNMASI / TACCP",
    "VACCP": "GIDA SAHTECİLİĞİ / VACCP",
}
LABEL_TO_CODE = {
    label: code
    for code, label in PROGRAM_LABELS.items()
}


class PrerequisiteProgramsWindow(ctk.CTkToplevel):

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("REDBOX OS — Ön Gereksinim Programları")
        self.geometry("1280x780")
        self.minsize(1050, 680)
        self.transient(app)
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="#171717",
        )
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="ÖN GEREKSİNİM PROGRAMLARI MERKEZİ",
            font=("Arial", 23, "bold"),
        ).pack(
            anchor="w",
            padx=26,
            pady=(20, 4),
        )
        ctk.CTkLabel(
            header,
            text=(
                "Alerjen, kalibrasyon, bakım, zararlı, eğitim, "
                "TACCP ve VACCP kontrolleri"
            ),
            text_color="#A3A3A3",
            font=("Arial", 12),
        ).pack(
            anchor="w",
            padx=26,
            pady=(0, 18),
        )

        body = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        body.pack(
            fill="both",
            expand=True,
            padx=24,
            pady=20,
        )

        self._build_summary(body)
        self._build_program_navigation(body)
        self._build_toolbar(body)
        self._build_table(body)

    def _build_summary(self, parent):
        area = ctk.CTkFrame(
            parent,
            fg_color="transparent",
        )
        area.pack(fill="x", pady=(0, 12))
        self.summary_labels = {}

        cards = (
            ("toplam_program", "TOPLAM PROGRAM", "#2563EB"),
            ("aktif_program", "AKTİF PROGRAM", "#059669"),
            ("acik_aksiyon", "AÇIK AKSİYON", "#F59E0B"),
            ("yuksek_risk", "YÜKSEK RİSK", "#DC2626"),
        )
        for index, (key, title, color) in enumerate(cards):
            area.grid_columnconfigure(index, weight=1)
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
                text_color="#A3A3A3",
                font=("Arial", 11, "bold"),
            ).pack(anchor="w", padx=15, pady=(12, 3))
            label = ctk.CTkLabel(
                card,
                text="0",
                text_color=color,
                font=("Arial", 22, "bold"),
            )
            label.pack(anchor="w", padx=15, pady=(0, 12))
            self.summary_labels[key] = label

    def _build_program_navigation(self, parent):
        area = ctk.CTkScrollableFrame(
            parent,
            height=72,
            orientation="horizontal",
        )
        area.pack(fill="x", pady=(0, 12))

        for index, (code, title) in enumerate(
            PROGRAM_LABELS.items()
        ):
            ctk.CTkButton(
                area,
                text=title,
                width=185,
                height=42,
                fg_color="#374151",
                hover_color="#4B5563",
                command=lambda value=code: self._select_type(value),
            ).grid(
                row=0,
                column=index,
                padx=5,
                pady=4,
            )

    def _build_toolbar(self, parent):
        toolbar = ctk.CTkFrame(parent, corner_radius=12)
        toolbar.pack(fill="x", pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(
            toolbar,
            placeholder_text="Program kodu, başlık veya kapsam ara...",
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

        self.type_filter = ctk.CTkComboBox(
            toolbar,
            values=["TÜM PROGRAMLAR"] + list(
                PROGRAM_LABELS.values()
            ),
            state="readonly",
            width=220,
            height=40,
            command=lambda _value: self.refresh(),
        )
        self.type_filter.set("TÜM PROGRAMLAR")
        self.type_filter.grid(
            row=0,
            column=1,
            padx=7,
            pady=12,
        )

        ctk.CTkButton(
            toolbar,
            text="YENİ PRP PROGRAMI",
            width=170,
            height=40,
            fg_color="#059669",
            command=self.open_new_program,
        ).grid(
            row=0,
            column=2,
            padx=(7, 14),
            pady=12,
        )

    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        columns = (
            "code",
            "type",
            "title",
            "status",
            "version",
            "responsible",
            "records",
            "review",
        )
        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=16,
        )
        headings = (
            ("code", "PROGRAM KODU", 130),
            ("type", "PROGRAM TÜRÜ", 190),
            ("title", "BAŞLIK", 230),
            ("status", "DURUM", 90),
            ("version", "REV.", 55),
            ("responsible", "SORUMLU", 150),
            ("records", "KAYIT", 65),
            ("review", "GÖZDEN GEÇİRME", 120),
        )
        for column, title, width in headings:
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=50)

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(14, 0),
            pady=14,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(0, 14),
            pady=14,
        )

    def _select_type(self, code):
        self.type_filter.set(PROGRAM_LABELS[code])
        self.refresh()

    def refresh(self):
        program_type = self.type_filter.get()
        if program_type == "TÜM PROGRAMLAR":
            program_type = None
        else:
            program_type = LABEL_TO_CODE[program_type]

        conn = get_connection()
        try:
            rows = prp_programlarini_getir(
                conn,
                program_turu=program_type,
                arama=self.search.get().strip() or None,
            )
            summary = prp_ozeti(conn)
        except Exception as exc:
            messagebox.showerror(
                "PRP Merkezi",
                str(exc),
                parent=self,
            )
            return
        finally:
            conn.close()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["program_kodu"],
                    PROGRAM_LABELS[row["program_turu"]],
                    row["baslik"],
                    row["durum"],
                    row["versiyon"],
                    row["sorumlu_adi"] or "-",
                    row["kayit_sayisi"],
                    row["gozden_gecirme_tarihi"] or "-",
                ),
            )

        for key, label in self.summary_labels.items():
            label.configure(text=str(summary[key]))

    def open_new_program(self):
        window = ctk.CTkToplevel(self)
        window.title("Yeni Ön Gereksinim Programı")
        window.geometry("650x520")
        window.transient(self)
        window.grab_set()

        form = ctk.CTkFrame(window)
        form.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        form.grid_columnconfigure(1, weight=1)

        program_type = ctk.CTkComboBox(
            form,
            values=list(PROGRAM_LABELS.values()),
            state="readonly",
        )
        program_type.set(PROGRAM_LABELS["ALERJEN"])
        code = ctk.CTkEntry(form)
        title = ctk.CTkEntry(form)
        scope = ctk.CTkTextbox(form, height=120)
        start_date = ctk.CTkEntry(form)

        fields = (
            ("Program Türü", program_type),
            ("Program Kodu", code),
            ("Başlık", title),
            ("Kapsam", scope),
            ("Başlangıç Tarihi", start_date),
        )
        for row, (label, widget) in enumerate(fields):
            ctk.CTkLabel(
                form,
                text=label,
                font=("Arial", 12, "bold"),
            ).grid(
                row=row,
                column=0,
                sticky="w",
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
            conn = get_connection()
            try:
                prp_programi_olustur(
                    conn,
                    {
                        "program_kodu": code.get(),
                        "program_turu": LABEL_TO_CODE[
                            program_type.get()
                        ],
                        "baslik": title.get(),
                        "kapsam": scope.get("1.0", "end"),
                        "baslangic_tarihi": start_date.get(),
                    },
                    kullanici=self.app.current_user,
                )
            except Exception as exc:
                conn.rollback()
                messagebox.showerror(
                    "Yeni PRP Programı",
                    str(exc),
                    parent=window,
                )
                return
            else:
                conn.commit()
            finally:
                conn.close()

            window.destroy()
            self.refresh()

        ctk.CTkButton(
            form,
            text="PROGRAMI OLUŞTUR",
            height=44,
            fg_color="#059669",
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )
