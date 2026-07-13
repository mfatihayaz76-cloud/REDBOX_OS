from ui.services.dashboard_service import DashboardService
from ui.services.production_service import ProductionService
from ui.services.stock_service import StockService
from ui.services.shipment_service import ShipmentService


class DashboardController:

    def __init__(self):

        self.dashboard = DashboardService()
        self.production = ProductionService()
        self.stock = StockService()
        self.shipment = ShipmentService()

    def load(self):

        return {
            "production": self.dashboard.toplam_uretim(),
            "packaging": self.dashboard.toplam_paketleme(),
            "shipment": self.dashboard.toplam_sevkiyat(),
            "critical": len(self.stock.kritik_stoklar()),
            "recent_production": self.production.son_uretimler(),
            "recent_shipment": self.shipment.son_sevkiyatlar(),
            "critical_stock": self.stock.kritik_stoklar(),
        }
