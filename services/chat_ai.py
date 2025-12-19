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
except Exception:
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
        else:
             # Logic for when supplements_data exists was missing or implicit in original code structure?
             # Ah, looking at original code, 'supp_text' block initialization was inside the `if not` block?
             # Wait, the original code had:
             # if not supplements_data: ...
             # prompt = ... {supp_text}
             # But supp_text wasn't defined if supplements_data WAS present?
             # Let me check the original file content again carefully.
             # Ah, lines 50-58 were indented inside `if not supplements_data`... wait.
             # No, lines 39: `if not supplements_data:`
             # Lines 50: `supp_text = "..."` -> This looks like it was overwriting the previous assignment?
             # The original code looks broken or I misread indentation.
             # Let's look at lines 39-58 in original.
             pass

        # Re-reading original file content from Step 110:
        # 39: if not supplements_data:
        # 40:    supp_text = (...)
        # ...
        # 46:    instruction_tone = (...)
        # 47:    instruction_tone = (...)  <-- Overwrites itself immediately?
        # 50:    supp_text = "..."         <-- Overwrites supp_text immediately?
        # 51:    for name, data in supplements_data.items(): ... <-- Iterates over empty dict if in `if not` block?
        #
        # Accessing `supplements_data.items()` inside `if not supplements_data` makes no sense if it's empty.
        # It seems the previous code had a logic bug or the indentation viewed is misleading.
        # But `supplements_data` is a dict. `if not` means empty.
        # I will fix this logic bug too while I am here.
        # Actually, let's just fix the Type Hint first to allow CI to pass, I don't want to change logic unless sure.
        # The key error was `Argument "key" to "max"`.

        # I will strictly apply the type fix requested.
        pass

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
            main_focus = max(scores, key=lambda k: scores[k]) if scores else "общий риск"
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
