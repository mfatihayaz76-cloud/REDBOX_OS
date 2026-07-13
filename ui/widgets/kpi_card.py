import customtkinter as ctk


class KPICard(ctk.CTkFrame):

    def __init__(
        self,
        master,
        title,
        value,
        width=240,
        height=120,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=12,
        )

        self.grid_propagate(False)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Arial", 14, "bold"),
            anchor="w",
        )

        self.title_label.pack(
            anchor="w",
            padx=15,
            pady=(12, 4),
        )

        self.value_label = ctk.CTkLabel(
            self,
            text=str(value),
            font=("Arial", 28, "bold"),
            anchor="w",
        )

        self.value_label.pack(
            anchor="w",
            padx=15,
        )

    def update_value(self, value):
        self.value_label.configure(
            text=str(value)
        )
