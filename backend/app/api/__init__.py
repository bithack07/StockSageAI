from .stocks import router as stocks_router
from .portfolio import router as portfolio_router
from .watchlist import router as watchlist_router
from .alerts import router as alerts_router
from .market import router as market_router
from .screener import router as screener_router
from .analysis_history import router as analysis_router
from .ws import router as ws_router
from .investor import router as investor_router

__all__ = [
    "stocks_router",
    "portfolio_router",
    "watchlist_router",
    "alerts_router",
    "market_router",
    "screener_router",
    "analysis_router",
    "ws_router",
    "investor_router",
]
