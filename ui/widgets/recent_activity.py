import customtkinter as ctk


class RecentActivity(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            corner_radius=12
        )

        ctk.CTkLabel(
            self,
            text="SON İŞLEMLER",
            font=("Arial", 18, "bold")
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 10)
        )

        header = ctk.CTkFrame(
            self,
            height=38,
            corner_radius=6
        )
        header.pack(
            fill="x",
            padx=15,
            pady=(0, 5)
        )

        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=2)
        header.grid_columnconfigure(2, weight=3)
        header.grid_columnconfigure(3, weight=2)

        for column, text in enumerate(
            ("İŞLEM", "TARİH", "DETAY", "MİKTAR")
        ):
            ctk.CTkLabel(
                header,
                text=text,
                font=("Arial", 12, "bold"),
                anchor="w"
            ).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=10,
                pady=10
            )

        self.rows_frame = ctk.CTkScrollableFrame(
            self,
            label_text="",
            corner_radius=6
        )
        self.rows_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.rows_frame.grid_columnconfigure(0, weight=1)

    def load(self, rows):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not rows:
            ctk.CTkLabel(
                self.rows_frame,
                text="Kayıt bulunamadı.",
                font=("Arial", 13)
            ).pack(
                anchor="w",
                padx=12,
                pady=12
            )
            return

        for index, text in enumerate(rows):
            parts = [
                part.strip()
                for part in str(text).split("|")
            ]

            while len(parts) < 4:
                parts.append("")

            row = ctk.CTkFrame(
                self.rows_frame,
                corner_radius=4
            )
            row.pack(
                fill="x",
                padx=2,
                pady=2
            )

            row.grid_columnconfigure(0, weight=2)
            row.grid_columnconfigure(1, weight=2)
            row.grid_columnconfigure(2, weight=3)
            row.grid_columnconfigure(3, weight=2)

            for column, value in enumerate(parts[:4]):
                ctk.CTkLabel(
                    row,
                    text=value,
                    font=("Arial", 12),
                    anchor="w"
                ).grid(
                    row=0,
                    column=column,
                    sticky="ew",
                    padx=10,
                    pady=9
                )
