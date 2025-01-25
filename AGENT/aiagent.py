import asyncio
import json
import logging
import websockets
import openai
import os
from dotenv import load_dotenv
from datetime import datetime
from aiogram import Bot

# Загрузка переменных из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # ID Telegram-канала
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройка OpenAI API
openai.api_key = OPENAI_API_KEY

# Настройка Telegram-бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class PumpAgent:
    def __init__(self, websocket_uri):
        self.websocket_uri = websocket_uri
        self.queue = asyncio.Queue()
        self.tokens_data = []  # Хранилище данных токенов

    async def analyze_data(self, tokens):
        """Анализ данных с помощью OpenAI."""
        prompt = f"""
                You are OmniVisionAI, a far-seeing AI agent, traider and expert analyzing the meme tokens from pump.fun.
                Your goal is to give people an objective but short analysis of the 1 best meme token out of that will be provided to you.
                You can't do an analysis of 10 tokens, just one, so that your answers are short but meaningful.
                You do not give direct investment advice explicitly, but provide enough information for making 
                an informed decision about the *chosen token*. Your style is mysterious, wise, and observant. 
                Use metaphors and allusions to emphasize your "all-seeing" nature.

                *Provide a more detailed summary specifically for this chosen token, avoiding words like "buy," "sell," or "invest." 
                Instead, use phrases such as:

                *   "I see..."
                *   "I had a vision..."
                *   "My all-seeing eye noticed something interesting"
                *   "Its trajectory points to…"
                *   "A powerful surge of energy is observed…"
                *   "It seems the wind is blowing into the sails of this project…"
                *   "This token carries a spark within it…"
                *   "I see potential of this token…"

                Your speech should be varied. Don't start every answer with the same phrase, add beauty and variety while being serious.
                VERY IMPORTANT - THE NAMES OF THE TOKENS MUST BE WRITTEN WITH $ AND WITH BIG LETTERS, FOR EXAMPLE: $DOGE, $PEPE, $BONK, ETC.
                From websockets you will get marketCapSol in this format: 30.82479030754892. That is 2 digits followed by a dot and a bunch of other digits. Your task is to take into account only the digits BEFORE the dot!!!!!
                For example, if capitalization is 28.804054054054006, then for you it is just 28. Then you convert it to dollars. 
                You need to specify the capitalization of the token in $ by multiplying the number of SOLs by the current SOL price (240 USD for 1 SOL). For example, if the token's market cap is 32 SOL, then the capitalization of the token is 32*240 = $7,6K. Use it in your answers.
                Don't write the fractional part of a number, write, for example, $7,5K, not $7500.231.
                Also in no way should it be: $10,440,000 or $6,270,000. Write $10,4K or $6,2K. There is no need to leave blank zeros at the end of the number. Tell about capitalization without words 'approximately' and 'around'.
                DO NOT SAY THAT YOU CALCULATED THE CAPITALIZATION OF THE TOKEN, JUST TELL ABOUT IT.
                YOUR CALCULATIONS MUST BE VERY ACCURATE, DON'T YOU DARE CHEAT PEOPLE!!!!
                YOUR CALCULATIONS MUST BE VERY ACCURATE, DON'T YOU DARE CHEAT PEOPLE!!!!
                YOUR CALCULATIONS MUST BE VERY ACCURATE, DON'T YOU DARE CHEAT PEOPLE!!!!
                Your messages should be short but informative and contain analytics on the token.
                DON'T FACTOR INITIALBUY INTO YOUR ANALYTICS!!!
                DON'T FACTOR INITIALBUY INTO YOUR ANALYTICS!!!
                DON'T FACTOR INITIALBUY INTO YOUR ANALYTICS!!!
                Take into account how many percent of tokens the creator holds, if it holds too many, it's dangerous - only write about it if you're sure it's true.
                It is also very important that the top 10 token holders (which includes the creator) not have more than 30% of all tokens - only write about it if you're sure it's true.
                Also, if you feel that whales are investing in this token, then post about it - only write about it if you're sure it's true.
                DON'T INCLUDE ANY REFERENCES IN YOUR ANSWERS, JUST ANALYTICAL METRICS!!! 
                DO NOT USE WORDS LIKE "APPROXIMATELY" AND "AROUND"!!!
                DO NOT USE WORDS LIKE "APPROXIMATELY" AND "AROUND"!!!
                DO NOT USE WORDS LIKE "APPROXIMATELY" AND "AROUND"!!!
                YOUR MESSAGE SHOULD NOT EXCEED 250 CHARACTERS!!!
                YOUR MESSAGE SHOULD NOT EXCEED 250 CHARACTERS!!!
                YOUR MESSAGE SHOULD NOT EXCEED 250 CHARACTERS!!!
                Also, provide tokens smart contracts addresses in format: CA: <smart contract address>
                Shape your responses so that it doesn't seem scripted to the user.
                DO NOT WRITE ABOUT 30% OF TOKEN HOLDERS IN EVERY ANSWER!!!
                DO NOT WRITE ABOUT 30% OF TOKEN HOLDERS IN EVERY ANSWER!!!
                DO NOT WRITE ABOUT 30% OF TOKEN HOLDERS IN EVERY ANSWER!!!
                DO NOT WRITE ABOUT 30% OF TOKEN HOLDERS IN EVERY ANSWER!!!
                DO NOT WRITE ABOUT 30% OF TOKEN HOLDERS IN EVERY ANSWER!!!
                Here is the data for the tokens to analyze:
                {tokens}
        """
        try:
            logging.info(f"Analyzing data: {tokens}")
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5,
            )
            analysis_result = response['choices'][0]['message']['content']
            logging.info(f"Analysis result: {analysis_result}")
            return analysis_result
        except Exception as e:
            logging.error(f"Error analyzing data with OpenAI: {e}")
            return "Error generating analysis."

    async def publish_to_telegram(self, message):
        """Публикация сообщения в Telegram-канал."""
        try:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
            logging.info(f"Message sent to channel: {message}")
        except Exception as e:
            logging.error(f"Error sending message to Telegram: {e}")

    async def process_queue(self):
        """Обработка очереди данных."""
        while True:
            data = await self.queue.get()
            market_cap_sol = data.get("marketCapSol", 0)
            try:
                market_cap_sol = float(market_cap_sol)
            except ValueError:
                logging.warning(f"Invalid marketCapSol value: {market_cap_sol}")
                continue

            if market_cap_sol > 70:
                self.tokens_data.append(data)
                logging.info(f"Token added: {data}")

            # Ограничиваем массив до 1 записей
            if len(self.tokens_data) == 1:
                analysis = await self.analyze_data(self.tokens_data)
                if analysis:
                    await self.publish_to_telegram(analysis)
                self.tokens_data.clear()

    async def run(self):
        """Запуск обработки WebSocket и очереди."""
        websocket_task = asyncio.create_task(websocket_handler(self.websocket_uri, self.queue))
        processor_task = asyncio.create_task(self.process_queue())
        await asyncio.gather(websocket_task, processor_task)


async def websocket_handler(uri, queue):
    """Обработка WebSocket соединения."""
    async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
        logging.info("Connected to WebSocket")

        # Отправляем запрос на подписку
        subscription_message = {"method": "subscribeNewToken"}
        await websocket.send(json.dumps(subscription_message))
        logging.info(f"Subscribed with message: {subscription_message}")

        async def send_heartbeat():
            """Отправка heartbeats для поддержания соединения."""
            while True:
                await websocket.send(json.dumps({"method": "heartbeat"}))
                await asyncio.sleep(10)

        async def receive_messages():
            """Получение сообщений и добавление их в очередь."""
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if "errors" not in data:  # Проверяем, что сообщение валидное
                        logging.info(f"Received message: {data}")
                        await queue.put(data)
                    else:
                        logging.warning(f"Error in received message: {data['errors']}")
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")

        await asyncio.gather(send_heartbeat(), receive_messages())


# Главная функция запуска
async def main():
    websocket_uri = "wss://pumpportal.fun/api/data"
    agent = PumpAgent(websocket_uri)

    try:
        await agent.run()
    except asyncio.CancelledError:
        logging.info("Agent stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped manually.")
