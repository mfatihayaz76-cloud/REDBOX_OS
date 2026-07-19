import csv
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from database.db import get_connection
from database.recipe_import_engine import (
    CatalogValidationError,
    katalog_dosyasi_ice_aktar,
    katalog_dosyasi_on_kontrol,
)
from tools.create_recipe_catalog_template import (
    create_csv_template,
    create_xlsx_template,
)


class RecipeImportWindow(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        current_user,
        on_success=None,
    ):
        super().__init__(master)

        self.current_user = current_user
        self.on_success = on_success
        self.selected_path = None
        self.report = None

        self.title("Toplu Ürün / Reçete İçe Aktarma")
        self.geometry("1100x760")
        self.minsize(900, 650)
        self.transient(master)
        self.grab_set()

        self._build()
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
            text="TOPLU ÜRÜN / REÇETE İÇE AKTARMA",
            font=("Arial", 23, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 4),
        )

        ctk.CTkLabel(
            header,
            text=(
                "CSV veya XLSX dosyası önce salt okunur "
                "kontrolden geçirilir. Hatasız katalog "
                "tek transaction ile içe aktarılır."
            ),
            text_color="#A3A3A3",
            wraplength=950,
            justify="left",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18),
        )

        controls = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        controls.pack(
            fill="x",
            padx=20,
            pady=10,
        )

        self.file_label = ctk.CTkLabel(
            controls,
            text="Dosya seçilmedi",
            anchor="w",
        )
        self.file_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=15,
            pady=15,
        )

        ctk.CTkButton(
            controls,
            text="CSV / XLSX SEÇ",
            width=160,
            height=38,
            command=self.select_file,
        ).pack(
            side="right",
            padx=(6, 15),
            pady=12,
        )

        ctk.CTkButton(
            controls,
            text="ŞABLONLARI KAYDET",
            width=185,
            height=38,
            fg_color="#475569",
            hover_color="#334155",
            command=self.save_templates,
        ).pack(
            side="right",
            padx=6,
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
            ("satir_sayisi", "SATIR"),
            ("urun_sayisi", "ÜRÜN"),
            ("recete_sayisi", "REÇETE"),
            ("kalem_sayisi", "KALEM"),
            ("hata_sayisi", "HATA"),
            ("uyari_sayisi", "UYARI"),
        )

        for index, (key, title) in enumerate(
            summary_items
        ):
            summary.grid_columnconfigure(
                index,
                weight=1,
                uniform="import_summary",
            )
            card = ctk.CTkFrame(
                summary,
                corner_radius=10,
                height=76,
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

            value_label = ctk.CTkLabel(
                card,
                text="0",
                font=("Arial", 19, "bold"),
            )
            value_label.pack()
            self.summary_labels[key] = value_label

        result_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        result_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(5, 10),
        )
        result_frame.grid_rowconfigure(1, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            result_frame,
            text=(
                "Ön kontrol için katalog dosyası seçin."
            ),
            anchor="w",
            font=("Arial", 14, "bold"),
        )
        self.status_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=(14, 8),
        )

        columns = (
            "satir",
            "alan",
            "kod",
            "mesaj",
        )
        self.error_tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.error_tree.heading(
            "satir",
            text="SATIR",
        )
        self.error_tree.heading(
            "alan",
            text="ALAN",
        )
        self.error_tree.heading(
            "kod",
            text="HATA KODU",
        )
        self.error_tree.heading(
            "mesaj",
            text="AÇIKLAMA",
        )
        self.error_tree.column(
            "satir",
            width=70,
            anchor="center",
            stretch=False,
        )
        self.error_tree.column(
            "alan",
            width=180,
            anchor="w",
        )
        self.error_tree.column(
            "kod",
            width=210,
            anchor="w",
        )
        self.error_tree.column(
            "mesaj",
            width=520,
            anchor="w",
        )
        self.error_tree.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(15, 0),
            pady=(0, 15),
        )

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.error_tree.yview,
        )
        scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 15),
            pady=(0, 15),
        )
        self.error_tree.configure(
            yscrollcommand=scrollbar.set,
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
            text="KAPAT",
            width=130,
            height=40,
            fg_color="#525252",
            hover_color="#404040",
            command=self.destroy,
        ).pack(
            side="left",
            padx=15,
            pady=12,
        )

        self.report_button = ctk.CTkButton(
            footer,
            text="HATA RAPORUNU KAYDET",
            width=210,
            height=40,
            state="disabled",
            fg_color="#475569",
            hover_color="#334155",
            command=self.save_issue_report,
        )
        self.report_button.pack(
            side="left",
            padx=5,
            pady=12,
        )

        self.import_button = ctk.CTkButton(
            footer,
            text="KATALOĞU İÇE AKTAR",
            width=220,
            height=40,
            state="disabled",
            command=self.execute_import,
        )
        self.import_button.pack(
            side="right",
            padx=15,
            pady=12,
        )

    def save_templates(self):
        selected_directory = filedialog.askdirectory(
            parent=self,
            title="Reçete Katalog Şablonlarını Kaydet",
        )

        if not selected_directory:
            return

        output_dir = Path(selected_directory)
        conn = get_connection()

        try:
            materials = [
                row["ad"]
                for row in conn.execute(
                    """
                    SELECT ad
                    FROM hammaddeler
                    WHERE aktif = 1
                    ORDER BY ad COLLATE NOCASE
                    """
                ).fetchall()
            ]
        finally:
            conn.close()

        xlsx_path = (
            output_dir
            / "REDBOX_OS_RECETE_KATALOGU_SABLONU.xlsx"
        )
        csv_path = (
            output_dir
            / "REDBOX_OS_RECETE_KATALOGU_SABLONU.csv"
        )

        try:
            create_xlsx_template(
                xlsx_path,
                materials,
            )
            create_csv_template(csv_path)
        except Exception as error:
            messagebox.showerror(
                "Şablonlar Kaydedilemedi",
                str(error),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Reçete Katalog Şablonları",
            (
                "CSV ve XLSX şablonları başarıyla "
                "kaydedildi.\n\n"
                f"Klasör: {output_dir}"
            ),
            parent=self,
        )

    def save_issue_report(self):
        if self.report is None:
            return

        issues = (
            self.report["hatalar"]
            + self.report["uyarilar"]
        )

        if not issues:
            return

        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Katalog Hata Raporunu Kaydet",
            defaultextension=".csv",
            initialfile=(
                "REDBOX_OS_KATALOG_HATA_RAPORU.csv"
            ),
            filetypes=[
                ("CSV", "*.csv"),
            ],
        )

        if not selected:
            return

        try:
            with Path(selected).open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=(
                        "satir",
                        "alan",
                        "kod",
                        "mesaj",
                    ),
                    delimiter=";",
                )
                writer.writeheader()
                writer.writerows(issues)
        except Exception as error:
            messagebox.showerror(
                "Hata Raporu Kaydedilemedi",
                str(error),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Katalog Hata Raporu",
            "Satır bazlı rapor başarıyla kaydedildi.",
            parent=self,
        )

    def select_file(self):
        selected = filedialog.askopenfilename(
            parent=self,
            title="Reçete Katalog Dosyası Seç",
            initialdir="templates",
            filetypes=[
                (
                    "Reçete Katalog Dosyaları",
                    "*.xlsx *.csv",
                ),
                ("Excel Workbook", "*.xlsx"),
                ("CSV", "*.csv"),
            ],
        )

        if not selected:
            return

        self.selected_path = Path(selected)
        self.file_label.configure(
            text=self.selected_path.name
        )
        self.run_preflight()

    def run_preflight(self):
        if self.selected_path is None:
            return

        conn = get_connection()

        try:
            self.report = katalog_dosyasi_on_kontrol(
                conn,
                self.selected_path,
            )
        except Exception as error:
            self.report = None
            self.import_button.configure(
                state="disabled"
            )
            messagebox.showerror(
                "Katalog Ön Kontrolü",
                str(error),
                parent=self,
            )
            return
        finally:
            conn.close()

        self._render_report()

    def _render_report(self):
        for item in self.error_tree.get_children():
            self.error_tree.delete(item)

        summary = self.report["ozet"]

        for key, label in self.summary_labels.items():
            label.configure(
                text=str(summary.get(key, 0))
            )

        issues = (
            self.report["hatalar"]
            + self.report["uyarilar"]
        )

        self.report_button.configure(
            state="normal" if issues else "disabled"
        )

        for issue in issues:
            self.error_tree.insert(
                "",
                "end",
                values=(
                    issue["satir"],
                    issue["alan"],
                    issue["kod"],
                    issue["mesaj"],
                ),
            )

        if self.report["gecerli"]:
            self.status_label.configure(
                text=(
                    "ÖN KONTROL BAŞARILI — "
                    "katalog atomik import için hazır."
                ),
                text_color="#86EFAC",
            )
            self.import_button.configure(
                state="normal"
            )
        else:
            self.status_label.configure(
                text=(
                    "ÖN KONTROL BAŞARISIZ — "
                    "hatalar düzeltilmeden import yapılamaz."
                ),
                text_color="#FCA5A5",
            )
            self.import_button.configure(
                state="disabled"
            )

    def execute_import(self):
        if (
            self.selected_path is None
            or self.report is None
            or not self.report["gecerli"]
        ):
            return

        summary = self.report["ozet"]
        confirmed = messagebox.askyesno(
            "Katalog İçe Aktarma Onayı",
            (
                f'{summary["urun_sayisi"]} ürün, '
                f'{summary["recete_sayisi"]} reçete ve '
                f'{summary["kalem_sayisi"]} kalem '
                "tek transaction ile içe aktarılacak.\n\n"
                "Devam edilsin mi?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        conn = get_connection()

        try:
            result = katalog_dosyasi_ice_aktar(
                conn,
                self.selected_path,
                kullanici=self.current_user,
            )
        except CatalogValidationError as error:
            self.report = error.report
            self._render_report()
            messagebox.showerror(
                "Katalog Değişti",
                (
                    "Dosya import öncesinde yeniden "
                    "doğrulandı ve hata bulundu."
                ),
                parent=self,
            )
            return
        except Exception as error:
            messagebox.showerror(
                "Katalog İçe Aktarılamadı",
                str(error),
                parent=self,
            )
            return
        finally:
            conn.close()

        imported = result["ozet"]

        messagebox.showinfo(
            "Katalog İçe Aktarma",
            (
                "Katalog başarıyla içe aktarıldı.\n\n"
                f'Yeni ürün: '
                f'{imported["yeni_urun_sayisi"]}\n'
                f'Reçete: {imported["recete_sayisi"]}\n'
                f'Kalem: {imported["kalem_sayisi"]}'
            ),
            parent=self,
        )

        self.destroy()

        if self.on_success is not None:
            self.on_success()
