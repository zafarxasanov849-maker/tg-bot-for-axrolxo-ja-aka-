from aiogram.fsm.state import State, StatesGroup


class LeadMagnetStates(StatesGroup):
    ad_spend = State()
    lp_views = State()
    new_leads = State()
    contacted = State()
    screenshot = State()
    anomaly_explanation = State()
