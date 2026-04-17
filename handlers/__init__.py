from .common import router as common_router
from .vsl import router as vsl_router
from .lead_magnet import router as lead_magnet_router
from .seminar import router as seminar_router
from .sales import router as sales_router
from .stats import router as stats_router
from .customer_journey import router as journey_router

__all__ = [
    "common_router",
    "vsl_router",
    "lead_magnet_router",
    "seminar_router",
    "sales_router",
    "stats_router",
    "journey_router",
]
