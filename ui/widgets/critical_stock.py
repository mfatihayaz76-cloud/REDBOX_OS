import customtkinter as ctk


class CriticalStock(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            corner_radius=12
        )

        ctk.CTkLabel(
            self,
            text="KRİTİK HAMMADDE STOKLARI",
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

        header.grid_columnconfigure(0, weight=3)
        header.grid_columnconfigure(1, weight=2)

        ctk.CTkLabel(
            header,
            text="HAMMADDE",
            font=("Arial", 12, "bold"),
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=10
        )

        ctk.CTkLabel(
            header,
            text="KALAN STOK",
            font=("Arial", 12, "bold"),
            anchor="e"
        ).grid(
            row=0,
            column=1,
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

    def load(self, rows):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not rows:
            ctk.CTkLabel(
                self.rows_frame,
                text="Kritik stok bulunmuyor.",
                font=("Arial", 13)
            ).pack(
                anchor="w",
                padx=12,
                pady=12
            )
            return

        for text in rows:
            value = str(text)

            if ":" in value:
                name, amount = value.split(":", 1)
            else:
                name, amount = value, ""

            row = ctk.CTkFrame(
                self.rows_frame,
                corner_radius=4
            )
            row.pack(
                fill="x",
                padx=2,
                pady=2
            )

            row.grid_columnconfigure(0, weight=3)
            row.grid_columnconfigure(1, weight=2)

            ctk.CTkLabel(
                row,
                text=name.strip(),
                font=("Arial", 12),
                anchor="w"
            ).grid(
                row=0,
                column=0,
                sticky="ew",
                padx=10,
                pady=9
            )

            ctk.CTkLabel(
                row,
                text=amount.strip(),
                font=("Arial", 12, "bold"),
                anchor="e"
            ).grid(
                row=0,
                column=1,
                sticky="ew",
                padx=10,
                pady=9
            )
