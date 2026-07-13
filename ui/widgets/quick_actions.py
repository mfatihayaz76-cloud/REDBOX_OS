import customtkinter as ctk


class QuickActions(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            corner_radius=12
        )

        ctk.CTkLabel(
            self,
            text="HIZLI İŞLEMLER",
            font=("Arial", 18, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )

        self.container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.container.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

    def add_button(self, text, command):

        ctk.CTkButton(
            self.container,
            text=text,
            command=command,
            height=42
        ).pack(
            fill="x",
            pady=5
        )
