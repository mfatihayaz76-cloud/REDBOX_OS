import customtkinter as ctk


class PersonnelPage(ctk.CTkFrame):

    def __init__(
        self,
        master,
        db=None,
    ):
        super().__init__(
            master,
            fg_color="transparent"
        )

        self.db = db

        ctk.CTkLabel(
            self,
            text="PERSONEL",
            font=("Arial", 28, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        ctk.CTkLabel(
            self,
            text="Sprint 23 refaktör aşaması",
            font=("Arial", 15)
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

        self.body = ctk.CTkFrame(
            self,
            corner_radius=12
        )

        self.body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )
