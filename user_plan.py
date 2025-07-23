import json
import os
import time
from enum import Enum

USER_PLAN_FILE = "user_plans.json"

class Plan(Enum):
    FREE = "free"
    BMC = "bmc"
    PREMIUM = "premium"

def init_user_plans():
    if not os.path.exists(USER_PLAN_FILE):
        with open(USER_PLAN_FILE, 'w') as f:
            json.dump({}, f)

def get_user_plan(user_id):
    init_user_plans()
    with open(USER_PLAN_FILE, 'r') as f:
        data = json.load(f)
    user_id_str = str(user_id)
    user_data = data.get(user_id_str, {})

    if isinstance(user_data, dict):
        plan = user_data.get("plan", Plan.FREE.value)
        expires = user_data.get("expires")
        if expires and time.time() > expires:
            return Plan.FREE.value
        return plan
    elif isinstance(user_data, str):
        return user_data  # legacy format
    else:
        return Plan.FREE.value

def set_user_plan(user_id, plan, duration_days=None):
    init_user_plans()
    with open(USER_PLAN_FILE, 'r') as f:
        data = json.load(f)
    user_id_str = str(user_id)
    user_data = {"plan": plan}
    if duration_days:
        user_data["expires"] = time.time() + duration_days * 86400
    data[user_id_str] = user_data
    with open(USER_PLAN_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def clear_user_plan(user_id):
    init_user_plans()
    with open(USER_PLAN_FILE, 'r') as f:
        data = json.load(f)
    if str(user_id) in data:
        del data[str(user_id)]
        with open(USER_PLAN_FILE, 'w') as f:
            json.dump(data, f, indent=2)

def is_premium(user_id):
    return get_user_plan(user_id) == Plan.PREMIUM.value

def is_bmc(user_id):
    return get_user_plan(user_id) == Plan.BMC.value

def is_free(user_id):
    return get_user_plan(user_id) == Plan.FREE.value
