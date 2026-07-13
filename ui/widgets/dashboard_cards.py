import customtkinter as ctk

from .kpi_card import KPICard


class DashboardCards(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color="transparent"
        )

        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_uretim = KPICard(
            self,
            "NET ÜRETİM",
            "0 kg"
        )

        self.kpi_paketleme = KPICard(
            self,
            "PAKETLEME",
            "0 kg"
        )

        self.kpi_sevkiyat = KPICard(
            self,
            "SEVKİYAT",
            "0 kg"
        )

        self.kpi_hammadde = KPICard(
            self,
            "KRİTİK STOK",
            "0"
        )

        self.kpi_uretim.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="nsew"
        )

        self.kpi_paketleme.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
            sticky="nsew"
        )

        self.kpi_sevkiyat.grid(
            row=0,
            column=2,
            padx=10,
            pady=10,
            sticky="nsew"
        )

        self.kpi_hammadde.grid(
            row=0,
            column=3,
            padx=10,
            pady=10,
            sticky="nsew"
        )

    def update_cards(
        self,
        uretim,
        paketleme,
        sevkiyat,
        kritik
    ):
        self.kpi_uretim.update_value(
            f"{uretim:.3f} kg"
        )

        self.kpi_paketleme.update_value(
            f"{paketleme:.3f} kg"
        )

        self.kpi_sevkiyat.update_value(
            f"{sevkiyat:.3f} kg"
        )

        self.kpi_hammadde.update_value(
            kritik
        )
