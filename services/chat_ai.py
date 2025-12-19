# services/chat_ai.py
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutTimeout
from typing import Any

logger = logging.getLogger(__name__)

# optional import — your original code used a gigachat client
try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole

    GIGACHAT_AVAILABLE = True
except ImportError:
    GigaChat = None  # type: ignore
    Chat = None  # type: ignore
    Messages = None  # type: ignore
    MessagesRole = None  # type: ignore
    GIGACHAT_AVAILABLE = False


class CardioChatService:
    def __init__(self, auth_key: str | None = None, timeout_seconds: int = 8):
        self.auth_key = auth_key
        self.timeout_seconds = timeout_seconds
        self.mock_mode = not bool(auth_key) or not GIGACHAT_AVAILABLE

        if self.mock_mode:
            logger.warning(
                "CardioChatService running in MOCK mode (no auth_key or gigachat client missing)."
            )
        else:
            logger.info("CardioChatService initialized with real GigaChat client.")

    def _build_prompt(
        self,
        user_profile: dict[str, Any],
        scores: dict[str, float],
        supplements_data: dict[str, Any],
    ) -> str:
        main_focus = max(scores, key=lambda k: scores[k]) if scores else "Неизвестно"
        if not supplements_data:
            supp_text = (
                "В БАЗЕ ЗНАНИЙ НЕТ ПОДХОДЯЩИХ СРЕДСТВ. В ответе напиши строго: "
                "'К сожалению, на основе текущих данных я не могу подобрать "
                "специфические нутриенты.'"
            )
            instruction_tone = "Будь краток, так как данных о нутриентах нет."
        else:
            instruction_tone = (
                "Используй ТОЛЬКО данные из списка ниже. "
                "Не выдумывай несуществующие препараты."
            )
            supp_text = "--- РАЗРЕШЕННЫЙ СПИСОК НУТРИЕНТОВ (Knowledge Base) ---\n"
            for name, data in supplements_data.items():
                mechanism = data.get("mechanism", "")
                warnings = data.get("warnings", "-")
                supp_text += (
                    f"- {data.get('name')}: {mechanism}. "
                    f"(Меры предосторожности: {warnings})\n"
                )
            supp_text += "--- КОНЕЦ СПИСКА ---"

        prompt = (
            f"Роль: Ты профессиональный, но эмпатичный AI-коуч 'CardioVoice'.\n"
            f"Задача: Интерпретировать риск-профиль и дать рекомендации.\n\n"
            f"ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:\n"
            f"- Возраст: {user_profile.get('age')} лет\n"
            f"- Пол: {user_profile.get('gender')}\n"
            f"- Курение: {user_profile.get('smoking_status')}\n"
            f"- Активность: {user_profile.get('activity_level')}\n"
            f"- ВЫЯВЛЕННЫЙ РИСК: {main_focus}\n\n"
            f"ИНСТРУКЦИИ:\n"
            f"1. Дай ОДНУ конкретную, выполнимую рекомендацию по образу жизни "
            f"(персонализированную под возраст и активность).\n"
            f"2. {instruction_tone} Если список ниже не пуст, выбери 2-3 "
            f"наиболее подходящих пунктов и кратко опиши их пользу.\n\n"
            f"{supp_text}\n\n"
            f"ВАЖНО: Закончи ответ фразой: 'Данная информация носит "
            f"ознакомительный характер и не заменяет консультацию врача.'"
        )
        return prompt

    def _call_gigachat(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Calls the gigachat client. This function is executed inside a ThreadPoolExecutor
        so the outer code can enforce a timeout.
        """
        if not GIGACHAT_AVAILABLE:
            raise RuntimeError("GigaChat client not available in environment.")

        # Import settings here to avoid circular imports
        from config import settings

        # Use SSL verification from config (default: True for production safety)
        giga = GigaChat(
            credentials=self.auth_key,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=settings.verify_ssl,
        )
        payload = Chat(
            messages=[Messages(role=MessagesRole.USER, content=prompt)],
            temperature=temperature,
        )
        response = giga.chat(payload)
        # Original code used response.choices[0].message.content
        return getattr(response.choices[0].message, "content", str(response))

    def generate_explanation(
        self,
        user_profile: dict[str, Any],
        scores: dict[str, float],
        supplements_data: dict[str, Any],
    ) -> str:
        """
        Public method to produce the chat explanation with timeouts and fallbacks.
        """
        if self.mock_mode:
            # deterministic fallback that looks plausible
            main_focus = (
                max(scores, key=lambda k: scores[k]) if scores else "общий риск"
            )
            return (
                f"Краткий вывод: обнаружен повышенный риск — {main_focus}. "
                "Рекомендация: увеличить физическую активность, сократить "
                "курение и обсудить с врачом подходящие нутриенты. "
                "Данная информация носит ознакомительный характер "
                "и не заменяет консультацию врача."
            )

        prompt = self._build_prompt(user_profile, scores, supplements_data)

        # Run gigachat call in thread with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(self._call_gigachat, prompt)
                resp = fut.result(timeout=self.timeout_seconds)
                logger.info("GigaChat call succeeded.")
                return resp
        except FutTimeout:
            logger.error("GigaChat call timed out.")
            return "Извините, сервис анализа временно недоступен (таймаут). Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"GigaChat call failed: {e}")
            return "Извините, сервис анализа временно недоступен. Мы уже работаем над устранением неполадок."
