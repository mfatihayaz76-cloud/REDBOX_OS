import customtkinter as ctk

from ui.widgets.dashboard_cards import DashboardCards
from ui.widgets.recent_activity import RecentActivity
from ui.widgets.critical_stock import CriticalStock
from ui.widgets.quality_alerts import QualityAlerts
from ui.widgets.quick_actions import QuickActions


class DashboardPage(ctk.CTkFrame):

    def __init__(
        self,
        master,
        db=None,
        quick_actions=None,
    ):
        super().__init__(
            master,
            fg_color="transparent"
        )

        self.db = db

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

        self.right.grid_columnconfigure(0, weight=1)
        self.right.grid_rowconfigure(0, weight=3)
        self.right.grid_rowconfigure(1, weight=2)
        self.right.grid_rowconfigure(2, weight=1)

        self.stock = CriticalStock(self.right)

        self.stock.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 8)
        )

        self.quality = QualityAlerts(self.right)

        self.quality.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=8
        )

        self.actions = QuickActions(
            self.right,
            actions=quick_actions,
        )

        self.actions.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(8, 0)
        )

    def load_data(
        self,
        production=0,
        packaging=0,
        shipment=0,
        critical=0,
        recent=None,
        stock=None,
        quality=None,
    ):

        self.cards.update_cards(
            production,
            packaging,
            shipment,
            critical,
        )

        self.recent.load(
            recent or []
        )

        self.stock.load(
            stock or []
        )

        quality = quality or {}

        self.quality.load(
            acik=quality.get("acik", 0),
            kritik=quality.get("kritik", 0),
            geciken=quality.get("geciken", 0),
            rows=quality.get("alerts", []),
        )
