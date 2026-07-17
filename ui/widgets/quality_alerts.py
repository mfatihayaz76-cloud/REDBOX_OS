import customtkinter as ctk


class QualityAlerts(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            corner_radius=12,
            border_width=1,
            border_color="#7C3AED",
        )

        ctk.CTkLabel(
            self,
            text="KALİTE / CAPA UYARILARI",
            font=("Arial", 17, "bold"),
            text_color="#C4B5FD",
        ).pack(
            anchor="w",
            padx=18,
            pady=(14, 7),
        )

        self.summary_label = ctk.CTkLabel(
            self,
            text="Açık: 0  |  Kritik: 0  |  Geciken: 0",
            font=("Arial", 12, "bold"),
            text_color="#A3A3A3",
        )
        self.summary_label.pack(
            anchor="w",
            padx=18,
            pady=(0, 8),
        )

        self.rows_frame = ctk.CTkScrollableFrame(
            self,
            label_text="",
            corner_radius=6,
        )
        self.rows_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

    def load(
        self,
        *,
        acik=0,
        kritik=0,
        geciken=0,
        rows=None,
    ):
        self.summary_label.configure(
            text=(
                f"Açık: {int(acik)}  |  "
                f"Kritik: {int(kritik)}  |  "
                f"Geciken: {int(geciken)}"
            )
        )

        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        rows = rows or []

        if not rows:
            ctk.CTkLabel(
                self.rows_frame,
                text="Kritik veya geciken kalite kaydı bulunmuyor.",
                font=("Arial", 12),
                text_color="#22C55E",
                anchor="w",
            ).pack(
                fill="x",
                padx=10,
                pady=10,
            )
            return

        for item in rows:
            gecikmis = bool(item.get("gecikmis"))
            color = "#DC2626" if gecikmis else "#F59E0B"
            durum = "GECİKMİŞ" if gecikmis else item["durum"]

            row = ctk.CTkFrame(
                self.rows_frame,
                corner_radius=6,
                border_width=1,
                border_color=color,
            )
            row.pack(
                fill="x",
                padx=2,
                pady=3,
            )
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=(
                    f'{item["kayit_no"]}  |  '
                    f'{item["onem"]}  |  {durum}'
                ),
                font=("Arial", 11, "bold"),
                text_color=color,
                anchor="w",
            ).grid(
                row=0,
                column=0,
                sticky="ew",
                padx=10,
                pady=(8, 2),
            )

            ctk.CTkLabel(
                row,
                text=(
                    f'{item["baslik"]}  |  '
                    f'Hedef: {item["hedef_tarih"]}'
                ),
                font=("Arial", 11),
                anchor="w",
                wraplength=320,
            ).grid(
                row=1,
                column=0,
                sticky="ew",
                padx=10,
                pady=(2, 8),
            )
