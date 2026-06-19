import os
import logging
from yookassa import Configuration, Payment
from uuid import uuid4

logger = logging.getLogger(__name__)

Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic Plan",
        "price": 500,
        "currency": "RUB",
        "duration_days": 30,
        "features": "50 text generations, 10 image generations per day"
    },
    "pro": {
        "name": "Pro Plan",
        "price": 1500,
        "currency": "RUB",
        "duration_days": 30,
        "features": "Unlimited text, 50 image generations per day"
    },
    "premium": {
        "name": "Premium Plan",
        "price": 3000,
        "currency": "RUB",
        "duration_days": 30,
        "features": "Unlimited text and image generations, priority support"
    }
}

async def create_payment(plan_id: str, user_id: int, username: str) -> dict:
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return None
    
    idempotence_key = str(uuid4())
    
    payment = Payment.create({
        "amount": {
            "value": str(plan["price"] / 100),
            "currency": plan["currency"]
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/{username}"
        },
        "capture": True,
        "description": f"GenieAI Bot - {plan['name']}",
        "metadata": {
            "user_id": user_id,
            "plan_id": plan_id
        }
    }, idempotence_key)
    
    return {
        "payment_id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
        "status": payment.status
    }

async def check_payment_status(payment_id: str) -> dict:
    payment = Payment.find_one(payment_id)
    return {
        "status": payment.status,
        "paid": payment.paid,
        "metadata": payment.metadata
    }

def get_plan_price(plan_id: str) -> str:
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if plan:
        return f"{plan['price'] // 100} {plan['currency']}"
    return "Unknown"
