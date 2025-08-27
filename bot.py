from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

'''FSM, или конечный автомат состояний (Finite State Machine), 
— это простой способ управлять сложными взаимодействиями в вашем 
Telegram боте. Он помогает боту "запомнить", 
на каком шаге процесса находится пользователь и что делать дальше.'''
from aiogram import Router
from aiogram.types import Message
import asyncio
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from aiogram.filters import Command

API_TOKEN = '8229345637:AAF6UqwKq4dSwEXIopqbe5NDBgeBQExXIH8'  


bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

engine = create_engine('sqlite:///nicole_survey.db')
Base = declarative_base()

class Survey(Base):
    __tablename__ = 'survey'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    q1 = Column(String)
    q2 = Column(String)
    q3 = Column(String)
    q4 = Column(String)
    q5 = Column(String)

class SupportMessage(Base):
    __tablename__ = 'support_message'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    question = Column(String)
    answer = Column(String, nullable=True)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


class SurveyStates(StatesGroup):
    Q1 = State()
    Q2 = State()
    Q3 = State()
    Q4 = State()
    Q5 = State()


@router.message(lambda msg: msg.text and msg.text.startswith('/start'))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать в бот поддержки магазина Nicole!\n"
        "Вы можете задать вопрос или пройти короткий опрос о магазине.\n"
        "Для начала опроса отправьте /survey\n"
        "Для отмены любого действия используйте /cancel"
    )


@router.message(lambda msg: msg.text and msg.text.startswith('/cancel'))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено. Чем могу помочь?")


@router.message(lambda msg: msg.text and msg.text.startswith('/survey'))
async def cmd_survey(message: Message, state: FSMContext):
    await state.set_state(SurveyStates.Q1)
    await message.answer("Вопрос 1: Как вы узнали о магазине Nicole?")

@router.message(SurveyStates.Q1)
async def process_q1(message: Message, state: FSMContext):
    answer = message.text.strip()
    if len(answer) < 3:
        await message.answer("Пожалуйста, дайте более подробный ответ.")
        return
    await state.update_data(q1=answer)
    await state.set_state(SurveyStates.Q2)
    await message.answer("Вопрос 2: Покупали ли вы товары в нашем магазине? (да/нет)")


@router.message(SurveyStates.Q2)
async def process_q2(message: Message, state: FSMContext):
    answer = message.text.lower().strip()
    if answer not in ['да', 'нет']:
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
        return
    await state.update_data(q2=answer)
    await state.set_state(SurveyStates.Q3)
    await message.answer("Вопрос 3: Оцените качество обслуживания (1-5)")

@router.message(SurveyStates.Q3)
async def process_q3(message: Message, state: FSMContext):
    answer = message.text.strip()
    if answer not in ['1', '2', '3', '4', '5']:
        await message.answer("Пожалуйста, введите число от 1 до 5.")
        return
    await state.update_data(q3=answer)
    await state.set_state(SurveyStates.Q4)
    await message.answer("Вопрос 4: Что бы вы хотели улучшить в магазине?")

@router.message(SurveyStates.Q4)
async def process_q4(message: Message, state: FSMContext):
    answer = message.text.strip()
    if len(answer) < 3:
        await message.answer("Пожалуйста, дайте более подробный ответ.")
        return
    await state.update_data(q4=answer)
    await state.set_state(SurveyStates.Q5)
    await message.answer("Вопрос 5: Порекомендуете ли вы Nicole друзьям? (да/нет)")


@router.message(SurveyStates.Q5)
async def process_q5(message: Message, state: FSMContext):
    answer = message.text.lower().strip()
    if answer not in ['да', 'нет']:
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
        return
    data = await state.get_data()
    session = Session()
    survey = Survey(
        user_id=message.from_user.id,
        q1=data.get('q1'),
        q2=data.get('q2'),
        q3=data.get('q3'),  
        q4=data.get('q4'),
        q5=answer
    )
    session.add(survey)
    session.commit()
    session.close()
    await state.clear()
    await message.answer("Спасибо за прохождение опроса! Ваши ответы сохранены.")


admin_ids = [1552297693]  

@router.message(lambda msg: not msg.text.startswith('/') and not (msg.text and msg.text.startswith('/survey')))
async def handle_support_question(message: Message):
    
    session = Session()
    support_msg = SupportMessage(
        user_id=message.from_user.id,
        question=message.text.strip()
    )
    session.add(support_msg)
    session.commit()
    session.close()
    await message.answer("Ваш вопрос отправлен в поддержку. Ожидайте ответа администратора.")

@router.message(Command(commands=['reply']))
async def admin_reply(message: Message):
    
    if message.from_user.id not in admin_ids:
        await message.answer("У вас нет прав для этой команды.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Используйте: /reply <user_id> <текст ответа>")
        return
    user_id, reply_text = parts[1], parts[2]
    try:
        user_id = int(user_id)
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    
    session = Session()
    msg = session.query(SupportMessage).filter_by(user_id=user_id, answer=None).order_by(SupportMessage.id.desc()).first()
    if not msg:
        await message.answer("Нет открытых вопросов от этого пользователя.")
        session.close()
        return
    msg.answer = reply_text
    session.commit()
    session.close()
    
    try:
        await bot.send_message(user_id, f"Ответ поддержки: {reply_text}")
        await message.answer("Ответ отправлен пользователю.")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")

@router.message(Command(commands=['myid']))
async def cmd_myid(message: Message):
    await message.answer(f"Ваш user_id: {message.from_user.id}")

@router.message(Command(commands=['inbox']))
async def admin_inbox(message: Message):
    if message.from_user.id not in admin_ids:
        await message.answer("У вас нет прав для этой команды.")
        return
    session = Session()
    msgs = session.query(SupportMessage).filter_by(answer=None).order_by(SupportMessage.id.asc()).all()
    session.close()
    if not msgs:
        await message.answer("Нет новых сообщений от пользователей.")
        return
    text = "Входящие вопросы:\n"
    for m in msgs:
        text += f"ID: {m.user_id}\nВопрос: {m.question}\n---\n"
    await message.answer(text)

@router.message(Command(commands=['ad']))
async def send_advertisement(message: Message):
    if message.from_user.id not in admin_ids:
        await message.answer("У вас нет прав для этой команды.")
        return
    
    photo_path = 'https://i.pinimg.com/originals/84/07/85/840785b9d92b8465aa511f0f8edd7e02.jpg'  
    ad_text = "🔥 Не пропустите наши новинки! 🔥"

    session = Session()

    survey_users = [row[0] for row in session.query(Survey.user_id).distinct().all()]
    support_users = [row[0] for row in session.query(SupportMessage.user_id).distinct().all()]
    user_ids = set(survey_users + support_users)
    session.close()

    if not user_ids:
        await message.answer("Нет пользователей для рассылки.")
        return

    sent = 0
    for uid in user_ids:
        try:
            await bot.send_photo(uid, photo_path, caption=ad_text)
            sent += 1
        except Exception as e:
            print(f"Не удалось отправить пользователю {uid}: {e}")
            continue

    await message.answer(f"Реклама отправлена {sent} пользователям.")


@router.message(Command(commands=['clear_inbox']))
async def clear_inbox(message: Message):
    if message.from_user.id not in admin_ids:
        await message.answer("У вас нет прав для этой команды.")
        return
    session = Session()
    deleted = session.query(SupportMessage).filter_by(answer=None).delete()
    session.commit()
    session.close()
    await message.answer(f"Удалено {deleted} входящих сообщений без ответа.")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))