from app.collectors.base import Collector
from app.collectors.manual import ManualCollector

__all__ = ["Collector", "ManualCollector"]
from app.collectors.restaurant_for_sales import RestaurantForSalesCollector
from app.collectors.restaurant_realty import RestaurantRealtyCollector

__all__ = ["RestaurantForSalesCollector", "RestaurantRealtyCollector"]
