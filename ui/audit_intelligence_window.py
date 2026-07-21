from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from database.audit_intelligence_engine import (
    denetim_zekasi_ozeti,
    ic_denetim_olustur,
)
from database.db import get_connection


SECTIONS = (
    ("İÇ DENETİM", "#2563EB"),
    ("MÜŞTERİ ŞİKÂYETİ", "#F59E0B"),
    ("NUMUNE VE LABORATUVAR", "#7C3AED"),
    ("KARANTİNA / BLOKE / SERBEST", "#DC2626"),
    ("YÖNETİMİN GÖZDEN GEÇİRMESİ", "#059669"),
    ("TEDARİKÇİ RİSK PUANLAMA", "#0F766E"),
    ("MOCK RECALL", "#9333EA"),
)


class AuditIntelligenceWindow(ctk.CTkToplevel):

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("REDBOX OS — Denetim Zekâsı")
        self.geometry("1260x760")
        self.minsize(1050, 650)
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
            text="DENETİM ZEKÂSI MERKEZİ",
            font=("Arial", 24, "bold"),
        ).pack(anchor="w", padx=26, pady=(20, 4))
        ctk.CTkLabel(
            header,
            text=(
                "Gıda güvenliği performansı, risk, doğrulama "
                "ve geri çağırma ölçüm merkezi"
            ),
            text_color="#A3A3A3",
            font=("Arial", 12),
        ).pack(anchor="w", padx=26, pady=(0, 18))

        body = ctk.CTkScrollableFrame(
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
        self._build_sections(body)

    def _build_summary(self, parent):
        area = ctk.CTkFrame(
            parent,
            fg_color="transparent",
        )
        area.pack(fill="x", pady=(0, 15))
        self.summary_labels = {}
        cards = (
            ("acik_denetim", "AÇIK DENETİM", "#2563EB"),
            ("acik_sikayet", "AÇIK ŞİKÂYET", "#F59E0B"),
            ("bekleyen_numune", "BEKLEYEN NUMUNE", "#7C3AED"),
            ("bloke_lot", "BLOKE / KARANTİNA", "#DC2626"),
            ("riskli_tedarikci", "RİSKLİ TEDARİKÇİ", "#0F766E"),
            ("basarisiz_recall", "BAŞARISIZ RECALL", "#9333EA"),
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
                padx=4,
            )
            ctk.CTkLabel(
                card,
                text=title,
                text_color="#A3A3A3",
                font=("Arial", 10, "bold"),
            ).pack(anchor="w", padx=12, pady=(12, 3))
            label = ctk.CTkLabel(
                card,
                text="0",
                text_color=color,
                font=("Arial", 21, "bold"),
            )
            label.pack(anchor="w", padx=12, pady=(0, 12))
            self.summary_labels[key] = label

    def _build_sections(self, parent):
        grid = ctk.CTkFrame(
            parent,
            fg_color="transparent",
        )
        grid.pack(fill="both", expand=True)

        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)

        descriptions = {
            "İÇ DENETİM":
                "Plan, bulgu, kritik bulgu ve kapanış takibi.",
            "MÜŞTERİ ŞİKÂYETİ":
                "Lot bağlantılı şikâyet, kök neden ve yanıt.",
            "NUMUNE VE LABORATUVAR":
                "Numune zinciri, analiz ve uygunluk sonucu.",
            "KARANTİNA / BLOKE / SERBEST":
                "Lot bazında kontrollü ürün durum kararları.",
            "YÖNETİMİN GÖZDEN GEÇİRMESİ":
                "Girdi, karar, aksiyon ve takip toplantıları.",
            "TEDARİKÇİ RİSK PUANLAMA":
                "Kalite, teslimat ve gıda güvenliği skoru.",
            "MOCK RECALL":
                "Süre, izlenen miktar ve başarı oranı ölçümü.",
        }

        for index, (title, color) in enumerate(SECTIONS):
            card = ctk.CTkFrame(
                grid,
                corner_radius=13,
                border_width=1,
                border_color=color,
            )
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=7,
                pady=7,
            )
            ctk.CTkLabel(
                card,
                text=title,
                text_color=color,
                font=("Arial", 15, "bold"),
            ).pack(anchor="w", padx=18, pady=(16, 5))
            ctk.CTkLabel(
                card,
                text=descriptions[title],
                text_color="#C4C4C4",
                justify="left",
                wraplength=470,
            ).pack(anchor="w", padx=18, pady=(0, 12))

            command = (
                self.open_new_internal_audit
                if title == "İÇ DENETİM"
                else lambda name=title: self._show_module(name)
            )
            ctk.CTkButton(
                card,
                text="MODÜLÜ AÇ",
                height=36,
                fg_color=color,
                command=command,
            ).pack(
                anchor="e",
                padx=18,
                pady=(0, 16),
            )

    def refresh(self):
        conn = get_connection()
        try:
            summary = denetim_zekasi_ozeti(conn)
        except Exception as exc:
            messagebox.showerror(
                "Denetim Zekâsı",
                str(exc),
                parent=self,
            )
            return
        finally:
            conn.close()

        for key, label in self.summary_labels.items():
            label.configure(text=str(summary[key]))

    def _show_module(self, title):
        messagebox.showinfo(
            title,
            (
                f"{title} altyapısı hazırdır. "
                "Kayıtlar kontrollü GFS motoru üzerinden yönetilir."
            ),
            parent=self,
        )

    def open_new_internal_audit(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Yeni İç Denetim")
        dialog.geometry("640x470")
        dialog.transient(self)
        dialog.grab_set()

        form = ctk.CTkFrame(dialog)
        form.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=22,
        )
        form.grid_columnconfigure(1, weight=1)

        code = ctk.CTkEntry(form)
        date = ctk.CTkEntry(form)
        date.insert(0, datetime.now().strftime("%d.%m.%Y"))
        scope = ctk.CTkTextbox(form, height=150)

        fields = (
            ("Denetim Kodu", code),
            ("Denetim Tarihi", date),
            ("Kapsam", scope),
        )
        for row, (title, widget) in enumerate(fields):
            ctk.CTkLabel(
                form,
                text=title,
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
                ic_denetim_olustur(
                    conn,
                    {
                        "denetim_kodu": code.get(),
                        "denetim_tarihi": date.get(),
                        "kapsam": scope.get("1.0", "end"),
                        "bas_denetci_personel_id": (
                            self.app.current_user.get("personel_id")
                        ),
                    },
                    kullanici=self.app.current_user,
                )
            except Exception as exc:
                conn.rollback()
                messagebox.showerror(
                    "İç Denetim",
                    str(exc),
                    parent=dialog,
                )
                return
            else:
                conn.commit()
            finally:
                conn.close()

            dialog.destroy()
            self.refresh()

        ctk.CTkButton(
            form,
            text="DENETİMİ OLUŞTUR",
            height=44,
            command=save,
        ).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )
