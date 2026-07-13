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

        self.box.delete("1.0", "end")

        if not rows:
            self.box.insert(
                "end",
                "Kayıt bulunamadı."
            )
            return

        for row in rows:
            self.box.insert(
                "end",
                row + "\n"
            )

        self.box.configure(
            state="disabled"
        )
