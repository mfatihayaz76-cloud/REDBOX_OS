import customtkinter as ctk


class KPICard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: str = "",
        width: int = 220,
        height: int = 110,
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=12,
            **kwargs,
        )

        self.grid_propagate(False)
        self.pack_propagate(False)

        self.columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Arial", 14, "bold"),
            anchor="w",
        )
        self.title_label.grid(
            row=0,
            column=0,
            padx=16,
            pady=(14, 2),
            sticky="ew",
        )

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=("Arial", 28, "bold"),
            anchor="w",
        )
        self.value_label.grid(
            row=1,
            column=0,
            padx=16,
            pady=(0, 2),
            sticky="ew",
        )

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=("Arial", 12),
            anchor="w",
            text_color="gray70",
        )
        self.subtitle_label.grid(
            row=2,
            column=0,
            padx=16,
            pady=(0, 14),
            sticky="ew",
        )

    def update_values(
        self,
        value: str,
        subtitle: str | None = None,
    ):
        self.value_label.configure(text=value)

        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)
