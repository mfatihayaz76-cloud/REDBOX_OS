import customtkinter as ctk


class QuickActions(ctk.CTkFrame):

    def __init__(self, master, actions=None):
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

        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=1)

        for index, action in enumerate(actions or []):
            text, command = action

            ctk.CTkButton(
                self.container,
                text=text,
                command=command,
                height=44,
                corner_radius=7,
                font=("Arial", 12, "bold")
            ).grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=5,
                pady=5
            )

    def add_button(self, text, command):
        index = len(self.container.winfo_children())

        ctk.CTkButton(
            self.container,
            text=text,
            command=command,
            height=44,
            corner_radius=7,
            font=("Arial", 12, "bold")
        ).grid(
            row=index // 2,
            column=index % 2,
            sticky="ew",
            padx=5,
            pady=5
        )
