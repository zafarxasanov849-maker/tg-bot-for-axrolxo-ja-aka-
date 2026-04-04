from aiogram.fsm.state import State, StatesGroup


class SalesStates(StatesGroup):
    customer_id = State()
    funnel_source = State()
    tariff_type = State()
    price = State()
    customer_type = State()   # new / upsell / recurring
    lead_status = State()     # hot / warm / cold (kvalifikatsiya natijasi)
    screenshot = State()
    anomaly_explanation = State()
