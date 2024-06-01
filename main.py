import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, CallbackQueryHandler, filters
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
DATABASE_URL = "postgresql://ldiueqzskvrgow:be012ee6b6cee9dc6f30ca0a8a37ae17b90fb5c5e142a6efe4cb15494e10bf48@ec2-52-31-2-97.eu-west-1.compute.amazonaws.com:5432/d4a91jiqud73el"
engine = create_engine(DATABASE_URL)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    wallet_address = Column(String)
    referral_id = Column(BigInteger)
    dmt_balance = Column(Float, default=2.0)
    subscription_rewarded = Column(Boolean, default=False)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

DEX_SCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens/EQDqZlrARv4jPJpwzbYPNiOtD_CouWxeAGbp7awAzoezQImY,EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c"  # Замените на ваш реальный API-эндпоинт
CHANNEL_ID = "@test312361935"  # Замените на ваш реальный ID канала


async def fetch_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get(DEX_SCREENER_API_URL)
        response.raise_for_status()
        return response.json()


async def start(update: Update, context: CallbackContext) -> None:
    if context.args:
        referral_id = int(context.args[0])
        context.user_data["referral_id"] = referral_id

    keyboard = [
        [InlineKeyboardButton("Регистрация кошелька", callback_data='register')],
        [InlineKeyboardButton("Изменить кошелек", callback_data='change_wallet')],
        [InlineKeyboardButton("Получить реферальную ссылку", callback_data='referral')],
        [InlineKeyboardButton("Проверить баланс", callback_data='balance')],
        [InlineKeyboardButton("Метрики DMT", callback_data='metrics')],
        [InlineKeyboardButton("Показать кошелек", callback_data='show_wallet')],
        [InlineKeyboardButton("Проверить подписку", callback_data='check_subscription')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Выберите команду:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Выберите команду:", reply_markup=reply_markup)


async def show_metrics(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    try:
        data = await fetch_metrics()
        if data and 'pairs' in data and data['pairs']:
            pair = data['pairs'][0]
            metrics_text = f"""
            Price: {pair['priceNative']} TON | {pair['priceUsd']} USD

            Liquidity:
            {pair['liquidity']['base']} DMT
            {pair['liquidity']['quote']} TON
            {pair['liquidity']['usd']} USD

            Volume:
            5m ${pair['volume']['m5']}
            1h ${pair['volume']['h1']}
            6h ${pair['volume']['h6']}
            24h ${pair['volume']['h24']}
            """
        else:
            metrics_text = "Не удалось получить данные метрик: данные отсутствуют или некорректны."
    except Exception as e:
        metrics_text = f"Не удалось получить данные метрик: {e}"

    keyboard = [[InlineKeyboardButton("Back", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(metrics_text, reply_markup=reply_markup)


async def register_wallet(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Отправьте ваш кошелек в сети TON для регистрации.")
    context.user_data['awaiting_wallet'] = True


async def change_wallet(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Отправьте новый адрес вашего кошелька.")
    context.user_data['awaiting_change_wallet'] = True


async def referral(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        referral_link = f"https://t.me/your_bot_username?start={telegram_id}"
        await query.message.reply_text(f"Ваша реферальная ссылка: {referral_link}")
    else:
        await query.message.reply_text("Сначала зарегистрируйтесь, отправив ваш кошелек.")


async def balance(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        await query.message.reply_text(f"Ваш баланс: {user.dmt_balance} DMT коина.")
    else:
        await query.message.reply_text("Сначала зарегистрируйтесь, отправив ваш кошелек.")


async def show_wallet(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        await query.message.reply_text(f"Ваш сохраненный кошелек: {user.wallet_address}")
    else:
        await query.message.reply_text("Сначала зарегистрируйтесь, отправив ваш кошелек.")


async def check_subscription(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    try:
        member_status = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
        if member_status.status in ["member", "administrator", "creator"]:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                if not user.subscription_rewarded:
                    user.dmt_balance += 1
                    user.subscription_rewarded = True
                    session.commit()
                    await query.message.reply_text("Вы подписаны на канал. Вам начислено 1 DMT коина.")
                else:
                    await query.message.reply_text("Вы уже получили награду за подписку.")
            else:
                await query.message.reply_text("Сначала зарегистрируйтесь, отправив ваш кошелек.")
        else:
            await query.message.reply_text(
                "Вы не подписаны на канал. Пожалуйста, подпишитесь на канал и попробуйте снова.")
    except Exception as e:
        await query.message.reply_text(f"Произошла ошибка при проверке подписки: {e}")


async def handle_message(update: Update, context: CallbackContext) -> None:
    wallet_address = update.message.text
    telegram_id = update.message.from_user.id

    if context.user_data.get('awaiting_wallet'):
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            await update.message.reply_text("Вы уже зарегистрированы.")
            context.user_data['awaiting_wallet'] = False
            return

        referral_id = context.user_data.get("referral_id")
        user = User(telegram_id=telegram_id, wallet_address=wallet_address, referral_id=referral_id)
        session.add(user)
        session.commit()

        if referral_id:
            referrer = session.query(User).filter_by(telegram_id=referral_id).first()
            if referrer:
                referrer.dmt_balance += 3
                session.commit()
                await context.bot.send_message(chat_id=referrer.telegram_id,
                                               text=f"По вашей реферальной ссылке зарегистрировался новый пользователь. Вам начислено 3 DMT коина.")

        await update.message.reply_text("Регистрация успешна. Вам начислено 2 DMT коина.")
        context.user_data['awaiting_wallet'] = False

    elif context.user_data.get('awaiting_change_wallet'):
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.wallet_address = wallet_address
            session.commit()
        user.wallet_address = wallet_address
        session.commit()
        await update.message.reply_text("Адрес кошелька успешно изменен.")
    else:
        await update.message.reply_text("Сначала зарегистрируйтесь, отправив ваш кошелек.")
    context.user_data['awaiting_change_wallet'] = False

async def back_to_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await start(update, context)

def main() -> None:
    application = Application.builder().token("7369129455:AAEu-3TQk3DHfimKAH6efBMUia1QoxG8pEc").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(register_wallet, pattern='register'))
    application.add_handler(CallbackQueryHandler(change_wallet, pattern='change_wallet'))
    application.add_handler(CallbackQueryHandler(referral, pattern='referral'))
    application.add_handler(CallbackQueryHandler(balance, pattern='balance'))
    application.add_handler(CallbackQueryHandler(show_metrics, pattern='metrics'))
    application.add_handler(CallbackQueryHandler(show_wallet, pattern='show_wallet'))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern='check_subscription'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='back_to_menu'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
