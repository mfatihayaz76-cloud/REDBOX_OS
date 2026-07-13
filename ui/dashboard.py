import customtkinter as ctk

from ui.widgets.dashboard_cards import DashboardCards
from ui.widgets.recent_activity import RecentActivity
from ui.widgets.critical_stock import CriticalStock
from ui.widgets.quick_actions import QuickActions


class DashboardPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color="transparent"
        )

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)

        self.grid_rowconfigure(1, weight=1)

        self.cards = DashboardCards(self)

        self.cards.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(20, 10)
        )

        self.recent = RecentActivity(self)

        self.recent.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(20, 10),
            pady=(10, 20)
        )

        self.right = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.right.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(10, 20),
            pady=(10, 20)
        )

        self.right.grid_rowconfigure(0, weight=1)
        self.right.grid_rowconfigure(1, weight=1)

        self.stock = CriticalStock(self.right)

        self.stock.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 10)
        )

        self.actions = QuickActions(self.right)

        self.actions.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(10, 0)
        )
