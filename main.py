import asyncio
import logging
from AGENT.aiagent import PumpAgent  # Импортируем PumpAgent из файла pump_agent.py

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    websocket_uri = "wss://pumpportal.fun/api/data"
    agent = PumpAgent(websocket_uri)

    try:
        asyncio.run(agent.run())  # Запуск основного метода run()
    except KeyboardInterrupt:
        logging.info("Agent stopped manually.")