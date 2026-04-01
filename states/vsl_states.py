from aiogram.fsm.state import State, StatesGroup


class VSLStates(StatesGroup):
    ad_spend = State()
    page_views = State()
    video_start = State()
    watch_50 = State()
    watch_100 = State()
    cta_clicks = State()
    screenshot = State()
    anomaly_explanation = State()
