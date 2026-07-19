import subprocess
from tkinter import messagebox, ttk

import customtkinter as ctk

from database.audit_engine import denetim_kaydi_ekle
from database.db import get_connection
from database.report_engine import recete_pdf_olustur
from database.recipe_approval_engine import (
    recete_onayini_reddet,
    receteyi_dijital_onayla,
    receteyi_incelemeye_gonder,
)
from database.recipe_center_engine import (
    RECIPE_STATUSES,
    recete_katalog_ozeti,
    recete_katalogunu_getir,
)


class RecipeDecisionDialog(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        title,
        prompt,
        confirm_text,
        confirm_color,
        on_confirm,
    ):
        super().__init__(master)

        self.on_confirm = on_confirm

        self.title(title)
        self.geometry("620x390")
        self.minsize(560, 350)
        self.transient(master)
        self.grab_set()

        header = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        header.pack(
            fill="x",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            header,
            text=title.upper(),
            font=("Arial", 20, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 4),
        )

        ctk.CTkLabel(
            header,
            text=prompt,
            text_color="#D4D4D4",
            wraplength=540,
            justify="left",
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 16),
        )

        ctk.CTkLabel(
            self,
            text="İşlem Açıklaması / Gerekçe",
            font=("Arial", 12, "bold"),
        ).pack(
            anchor="w",
            padx=24,
            pady=(8, 5),
        )

        self.reason_text = ctk.CTkTextbox(
            self,
            height=135,
            wrap="word",
        )
        self.reason_text.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 10),
        )

        footer = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        footer.pack(
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        ctk.CTkButton(
            footer,
            text="VAZGEÇ",
            width=130,
            height=40,
            fg_color="#525252",
            hover_color="#404040",
            command=self.destroy,
        ).pack(
            side="left",
            padx=12,
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text=confirm_text,
            width=190,
            height=40,
            fg_color=confirm_color,
            command=self._confirm,
        ).pack(
            side="right",
            padx=12,
            pady=12,
        )

        self.after(
            100,
            lambda: (
                self.lift(),
                self.reason_text.focus_set(),
            ),
        )

    def _confirm(self):
        reason = self.reason_text.get(
            "1.0",
            "end",
        ).strip()

        if not reason:
            messagebox.showwarning(
                "Kontrollü Reçete İşlemi",
                "İşlem açıklaması boş bırakılamaz.",
                parent=self,
            )
            return

        self.on_confirm(reason)
        self.destroy()


class RecipeCenterWindow(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        current_user,
        on_select=None,
    ):
        super().__init__(master)

        self.current_user = current_user
        self.on_select = on_select
        self.rows_by_id = {}

        self.title("Profesyonel Reçete Kataloğu")
        self.geometry("1280x780")
        self.minsize(1050, 680)
        self.transient(master)
        self.grab_set()

        self._build()
        self.refresh()

        self.after(
            100,
            lambda: (
                self.lift(),
                self.focus_force(),
            ),
        )

    def _build(self):
        header = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        header.pack(
            fill="x",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            header,
            text="PROFESYONEL REÇETE KATALOĞU",
            font=("Arial", 23, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 4),
        )

        ctk.CTkLabel(
            header,
            text=(
                "Ürün ve reçete kimliği, revizyon durumu, "
                "kütle dengesi ve dijital onay bütünlüğü "
                "tek merkezden izlenir."
            ),
            text_color="#A3A3A3",
            wraplength=1100,
            justify="left",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18),
        )

        filters = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        filters.pack(
            fill="x",
            padx=20,
            pady=10,
        )

        ctk.CTkLabel(
            filters,
            text="Katalog Arama",
            font=("Arial", 12, "bold"),
        ).pack(
            side="left",
            padx=(15, 8),
            pady=14,
        )

        self.search_entry = ctk.CTkEntry(
            filters,
            width=360,
            placeholder_text=(
                "Ürün kodu, ürün adı, barkod veya reçete..."
            ),
        )
        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 12),
            pady=12,
        )
        self.search_entry.bind(
            "<Return>",
            lambda _event: self.refresh(),
        )

        ctk.CTkLabel(
            filters,
            text="Durum",
            font=("Arial", 12, "bold"),
        ).pack(
            side="left",
            padx=(0, 8),
            pady=14,
        )

        self.status_combo = ctk.CTkComboBox(
            filters,
            values=[
                "TÜM DURUMLAR",
                *RECIPE_STATUSES,
            ],
            width=170,
            state="readonly",
            command=lambda _value: self.refresh(),
        )
        self.status_combo.pack(
            side="left",
            padx=(0, 10),
            pady=12,
        )
        self.status_combo.set("TÜM DURUMLAR")

        ctk.CTkButton(
            filters,
            text="ARA / YENİLE",
            width=140,
            height=38,
            command=self.refresh,
        ).pack(
            side="right",
            padx=(5, 15),
            pady=12,
        )

        summary = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        summary.pack(
            fill="x",
            padx=15,
            pady=(2, 8),
        )

        self.summary_labels = {}

        summary_items = (
            ("kayit_sayisi", "REÇETE"),
            ("urun_sayisi", "ÜRÜN"),
            ("aktif_recete_sayisi", "AKTİF"),
            ("onayli_recete_sayisi", "DİJİTAL ONAYLI"),
            ("kutle_dengesi_hatasi", "DENGE HATASI"),
        )

        for index, (key, title) in enumerate(
            summary_items
        ):
            summary.grid_columnconfigure(
                index,
                weight=1,
                uniform="recipe_center_summary",
            )

            card = ctk.CTkFrame(
                summary,
                corner_radius=10,
                height=78,
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5,
            )
            card.grid_propagate(False)

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 10, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(11, 2))

            label = ctk.CTkLabel(
                card,
                text="0",
                font=("Arial", 19, "bold"),
            )
            label.pack()
            self.summary_labels[key] = label

        table_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(5, 10),
        )
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            table_frame,
            text="Katalog yükleniyor...",
            anchor="w",
            font=("Arial", 13, "bold"),
        )
        self.status_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=(13, 7),
        )

        tree_container = ctk.CTkFrame(
            table_frame,
            fg_color="transparent",
        )
        tree_container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(0, 15),
        )
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "RecipeCenter.Treeview",
            background="#202020",
            fieldbackground="#202020",
            foreground="#F3F4F6",
            rowheight=38,
            borderwidth=0,
            font=("Arial", 10),
        )
        style.configure(
            "RecipeCenter.Treeview.Heading",
            background="#1F2937",
            foreground="#FFFFFF",
            relief="flat",
            font=("Arial", 10, "bold"),
        )
        style.map(
            "RecipeCenter.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        columns = (
            "urun_kodu",
            "urun_adi",
            "recete_kodu",
            "revizyon",
            "durum",
            "parti",
            "kalem",
            "denge",
            "onay",
        )

        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="RecipeCenter.Treeview",
        )

        headings = (
            ("urun_kodu", "ÜRÜN KODU", 105, "center"),
            ("urun_adi", "ÜRÜN ADI", 190, "w"),
            ("recete_kodu", "REÇETE KODU", 125, "center"),
            ("revizyon", "REV", 60, "center"),
            ("durum", "DURUM", 95, "center"),
            ("parti", "1 PARTİ KG", 95, "e"),
            ("kalem", "KALEM", 65, "center"),
            ("denge", "KÜTLE DENGESİ", 120, "center"),
            ("onay", "DİJİTAL ONAY", 120, "center"),
        )

        for column, title, width, anchor in headings:
            self.tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.tree.column(
                column,
                width=width,
                minwidth=55,
                anchor=anchor,
                stretch=True,
            )

        self.tree.tag_configure(
            "even",
            background="#202020",
        )
        self.tree.tag_configure(
            "odd",
            background="#292929",
        )
        self.tree.tag_configure(
            "active",
            foreground="#86EFAC",
        )
        self.tree.tag_configure(
            "error",
            foreground="#FCA5A5",
        )
        self.tree.tag_configure(
            "approved",
            foreground="#93C5FD",
        )

        vertical = ttk.Scrollbar(
            tree_container,
            orient="vertical",
            command=self.tree.yview,
        )
        horizontal = ttk.Scrollbar(
            tree_container,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.tree.grid(
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

        self.tree.bind(
            "<Double-1>",
            lambda _event: self.open_selected_product(),
        )

        footer = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        footer.pack(
            side="bottom",
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        ctk.CTkButton(
            footer,
            text="KAPAT",
            width=140,
            height=40,
            fg_color="#525252",
            hover_color="#404040",
            command=self.destroy,
        ).pack(
            side="left",
            padx=15,
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text="REDDET",
            width=125,
            height=40,
            fg_color="#B91C1C",
            hover_color="#991B1B",
            command=lambda: self.request_decision(
                "REJECT"
            ),
        ).pack(
            side="right",
            padx=(5, 15),
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text="DİJİTAL ONAYLA",
            width=155,
            height=40,
            fg_color="#15803D",
            hover_color="#166534",
            command=lambda: self.request_decision(
                "APPROVE"
            ),
        ).pack(
            side="right",
            padx=5,
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text="İNCELEMEYE GÖNDER",
            width=185,
            height=40,
            fg_color="#B7791F",
            hover_color="#975A16",
            command=lambda: self.request_decision(
                "REVIEW"
            ),
        ).pack(
            side="right",
            padx=5,
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text="PDF REÇETE FÖYÜ",
            width=175,
            height=40,
            fg_color="#1F6AA5",
            hover_color="#144E75",
            command=self.create_selected_recipe_pdf,
        ).pack(
            side="right",
            padx=5,
            pady=12,
        )

        ctk.CTkButton(
            footer,
            text="SEÇİLİ ÜRÜNE GİT",
            width=190,
            height=40,
            command=self.open_selected_product,
        ).pack(
            side="right",
            padx=15,
            pady=12,
        )

        table_frame.pack_forget()
        table_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(5, 10),
        )

    def _selected_status(self):
        value = self.status_combo.get().strip()

        if value == "TÜM DURUMLAR":
            return None

        return value

    def refresh(self):
        conn = get_connection()

        try:
            rows = recete_katalogunu_getir(
                conn,
                arama=self.search_entry.get(),
                durum=self._selected_status(),
                limit=5000,
            )
        except Exception as error:
            messagebox.showerror(
                "Reçete Kataloğu",
                str(error),
                parent=self,
            )
            return
        finally:
            conn.close()

        summary = recete_katalog_ozeti(rows)

        for key, label in self.summary_labels.items():
            label.configure(
                text=str(summary[key]),
            )

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        self.rows_by_id = {}

        for index, row in enumerate(rows):
            recipe_id = str(row["recete_id"])
            self.rows_by_id[recipe_id] = row

            tags = [
                "even" if index % 2 == 0 else "odd",
            ]

            if row["recete_aktif"]:
                tags.append("active")

            if not row["kutle_dengesi_uyumlu"]:
                tags.append("error")

            if row["gecerli_dijital_onay"]:
                tags.append("approved")

            self.tree.insert(
                "",
                "end",
                iid=recipe_id,
                values=(
                    row["urun_kodu"],
                    row["urun_adi"],
                    row["recete_kodu"] or "-",
                    row["revizyon_no"] or "-",
                    row["durum"],
                    f'{row["parti_teorik_kg"]:.3f}',
                    row["hammadde_sayisi"],
                    (
                        "UYUMLU"
                        if row["kutle_dengesi_uyumlu"]
                        else (
                            f'HATA '
                            f'{row["kutle_dengesi_farki_kg"]:+.3f}'
                        )
                    ),
                    (
                        "GEÇERLİ"
                        if row["gecerli_dijital_onay"]
                        else "YOK / GEÇERSİZ"
                    ),
                ),
                tags=tuple(tags),
            )

        if rows:
            first_id = str(rows[0]["recete_id"])
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)

        self.status_label.configure(
            text=(
                f"{summary['kayit_sayisi']} reçete, "
                f"{summary['urun_sayisi']} ürün gösteriliyor."
            ),
            text_color=(
                "#FCA5A5"
                if summary["kutle_dengesi_hatasi"]
                else "#86EFAC"
            ),
        )

    def _selected_recipe(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "Reçete Kataloğu",
                "Önce bir reçete seçin.",
                parent=self,
            )
            return None

        row = self.rows_by_id.get(selection[0])

        if row is None:
            messagebox.showerror(
                "Reçete Kataloğu",
                "Seçilen katalog kaydı bulunamadı.",
                parent=self,
            )
            return None

        return row

    def request_decision(self, action):
        row = self._selected_recipe()

        if row is None:
            return

        contracts = {
            "REVIEW": {
                "allowed": {"TASLAK"},
                "title": "Reçeteyi İncelemeye Gönder",
                "prompt": (
                    f'{row["urun_kodu"]} / '
                    f'{row["recete_kodu"]} '
                    f'Rev.{row["revizyon_no"]} '
                    "teknik inceleme sürecine alınacaktır."
                ),
                "confirm": "İNCELEMEYE GÖNDER",
                "color": "#B7791F",
            },
            "APPROVE": {
                "allowed": {
                    "INCELEMEDE",
                    "AKTIF",
                },
                "title": "Dijital Reçete Onayı",
                "prompt": (
                    f'{row["urun_kodu"]} / '
                    f'{row["recete_kodu"]} '
                    f'Rev.{row["revizyon_no"]} '
                    "mevcut içerik SHA-256 parmak iziyle "
                    "dijital olarak onaylanacaktır."
                ),
                "confirm": "DİJİTAL ONAYLA",
                "color": "#15803D",
            },
            "REJECT": {
                "allowed": {"INCELEMEDE"},
                "title": "Reçete Onayını Reddet",
                "prompt": (
                    f'{row["urun_kodu"]} / '
                    f'{row["recete_kodu"]} '
                    f'Rev.{row["revizyon_no"]} '
                    "TASLAK durumuna döndürülecektir."
                ),
                "confirm": "REDDET",
                "color": "#B91C1C",
            },
        }

        contract = contracts.get(action)

        if contract is None:
            messagebox.showerror(
                "Kontrollü Reçete İşlemi",
                "Geçersiz reçete işlemi.",
                parent=self,
            )
            return

        if row["durum"] not in contract["allowed"]:
            allowed_text = ", ".join(
                sorted(contract["allowed"])
            )
            messagebox.showwarning(
                "Kontrollü Reçete İşlemi",
                (
                    f'Bu işlem {row["durum"]} durumundaki '
                    "reçeteye uygulanamaz. "
                    f"İzin verilen durum: {allowed_text}"
                ),
                parent=self,
            )
            return

        RecipeDecisionDialog(
            self,
            title=contract["title"],
            prompt=contract["prompt"],
            confirm_text=contract["confirm"],
            confirm_color=contract["color"],
            on_confirm=lambda reason: (
                self._execute_decision(
                    action,
                    row["recete_id"],
                    reason,
                )
            ),
        )

    def _execute_decision(
        self,
        action,
        recipe_id,
        reason,
    ):
        conn = get_connection()

        try:
            if action == "REVIEW":
                result = receteyi_incelemeye_gonder(
                    conn,
                    recipe_id,
                    self.current_user,
                    reason,
                )
                result_message = (
                    "Reçete inceleme sürecine gönderildi."
                )

            elif action == "APPROVE":
                result = receteyi_dijital_onayla(
                    conn,
                    recipe_id,
                    self.current_user,
                    reason,
                )
                result_message = (
                    "Reçete içeriği dijital olarak onaylandı."
                )

            elif action == "REJECT":
                result = recete_onayini_reddet(
                    conn,
                    recipe_id,
                    self.current_user,
                    reason,
                )
                result_message = (
                    "Reçete reddedilerek TASLAK "
                    "durumuna döndürüldü."
                )

            else:
                raise ValueError(
                    "Geçersiz kontrollü reçete işlemi."
                )

        except Exception as error:
            messagebox.showerror(
                "Kontrollü Reçete İşlemi",
                str(error),
                parent=self,
            )
            return

        finally:
            conn.close()

        self.refresh()

        messagebox.showinfo(
            "Kontrollü Reçete İşlemi",
            (
                result_message
                + "\n\n"
                + f'Reçete ID: {result["recete_id"]}'
                + "\n"
                + f'Yeni durum: {result["durum"]}'
                + "\n"
                + "İçerik SHA-256: "
                + result["icerik_sha256"]
            ),
            parent=self,
        )

    def create_selected_recipe_pdf(self):
        row = self._selected_recipe()

        if row is None:
            return

        conn = get_connection()

        try:
            with conn:
                pdf_path = recete_pdf_olustur(
                    conn,
                    row["recete_id"],
                )

                denetim_kaydi_ekle(
                    conn,
                    modul="RECETE",
                    islem="PDF_OLUSTURMA",
                    kullanici=self.current_user,
                    kayit_turu="receteler",
                    kayit_id=int(row["recete_id"]),
                    aciklama=(
                        "Kontrollü reçete föyü oluşturuldu: "
                        f'{row["urun_kodu"]} / '
                        f'{row["recete_kodu"]} '
                        f'Rev.{row["revizyon_no"]}'
                    ),
                    yeni_deger={
                        "pdf_dosyasi": str(pdf_path),
                        "recete_kodu": row["recete_kodu"],
                        "revizyon_no": row["revizyon_no"],
                    },
                    oturum_id=self.current_user.get(
                        "oturum_id"
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Reçete PDF Hatası",
                (
                    "Kontrollü reçete föyü "
                    f"oluşturulamadı:\n{error}"
                ),
                parent=self,
            )
            return

        finally:
            conn.close()

        subprocess.run(
            ["open", str(pdf_path.resolve())],
            check=False,
        )

        messagebox.showinfo(
            "Kontrollü Reçete Föyü",
            (
                "PDF reçete föyü başarıyla oluşturuldu "
                "ve açıldı.\n\n"
                f"Reçete ID: {row['recete_id']}\n"
                f"Dosya: {pdf_path.name}"
            ),
            parent=self,
        )

    def open_selected_product(self):
        row = self._selected_recipe()

        if row is None:
            return

        if self.on_select is not None:
            self.on_select(
                row["urun_id"],
                row["urun_adi"],
            )

        self.destroy()
