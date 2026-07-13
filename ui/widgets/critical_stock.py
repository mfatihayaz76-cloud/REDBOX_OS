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
            padx=15,
            pady=(15, 10)
        )

        self.box = ctk.CTkTextbox(
            self,
            height=260
        )

        self.box.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

    def load(self, rows):

        self.box.configure(state="normal")
        self.box.delete("1.0", "end")

        if not rows:
            self.box.insert(
                "end",
                "Kritik stok bulunmuyor."
            )
        else:
            for row in rows:
                self.box.insert(
                    "end",
                    row + "\n"
                )

        self.box.configure(state="disabled")
