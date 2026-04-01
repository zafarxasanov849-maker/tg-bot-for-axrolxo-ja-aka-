from aiogram.fsm.state import State, StatesGroup


class SeminarStates(StatesGroup):
    ad_spend = State()
    registrations = State()
    show_up = State()
    deposits = State()
    sales = State()
    full_payments = State()
    screenshot = State()
    anomaly_explanation = State()
