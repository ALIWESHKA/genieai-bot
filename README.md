# GenieAI Bot

Telegram bot for AI text and image generation with subscription payment.

## Features

- Text generation (articles, summaries, translations)
- Image generation from descriptions
- Professional style responses
- Inline keyboard navigation
- Subscription plans with YooKassa payment

## Setup

### 1. Get Telegram Token

1. Open Telegram, find @BotFather
2. Send `/newbot`
3. Choose a name: `GenieAI Bot`
4. Choose a username: `GenieAI_bot` (must end with `bot`)
5. Copy the token

### 2. Get Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up / Sign in
3. Go to API Keys
4. Create new key
5. Copy the key

### 3. Get YooKassa Token

1. Go to https://yookassa.ru
2. Register an account
3. Create a shop
4. Go to Settings → API keys
5. Copy Shop ID and Secret Key

### 4. Configure

```bash
cp .env.example .env
```

Edit `.env` and add your tokens:

```
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

### 5. Install & Run

```bash
pip install -r requirements.txt
python bot.py
```

## Deploy to Railway (Free)

1. Create account at https://railway.app
2. Connect your GitHub repository
3. Add environment variables:
   - `TELEGRAM_TOKEN`
   - `GROQ_API_KEY`
4. Deploy

## Commands

- `/start` - Main menu
- `/help` - Show help
- `/image [description]` - Generate image
- `/subscription` - View subscription status

## Subscription Plans

- **Basic**: 500 RUB/month - 50 text, 10 image generations/day
- **Pro**: 1500 RUB/month - Unlimited text, 50 image generations/day
- **Premium**: 3000 RUB/month - Unlimited everything

## Payment Flow

1. User selects a plan
2. Bot creates a YooKassa payment
3. User clicks "Pay Now" and completes payment
4. Bot verifies payment and activates subscription

## Tech Stack

- Python 3.10+
- python-telegram-bot
- Groq API (Llama 3)
- Pollinations.ai (image generation)
- YooKassa (payment processing)
