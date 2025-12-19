# services/ml.py
import logging
import random

logger = logging.getLogger(__name__)


class MockMLService:
    """
    Mock ML service that produces risk scores and a search query.
    Interface preserved from previous implementation.
    """

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)

    def get_mock_risk_scores(
        self, age: int, gender: str, smoking_status: str, activity_level: str
    ) -> tuple[dict[str, float], str]:
        # Base logic (keeps your prior heuristics)
        base_ihd_risk = 0.05 + ((age - 20) * 0.007) if age > 20 else 0.05
        gender_mult = 1.2 if gender == "male" else 1.0
        smoke_mult = 1.5 if smoking_status == "smoker" else 1.0
        sedentary_mult = 1.3 if activity_level == "sedentary" else 1.0

        base_ihd_risk = base_ihd_risk * gender_mult * smoke_mult * sedentary_mult

        scores = {
            "АГ (Гипертензия)": round(max(0.0, min(1.0, random.uniform(0.1, 0.75))), 2),
            "СД2 (Диабет)": round(max(0.0, min(1.0, random.uniform(0.05, 0.45))), 2),
            "ИБС (Сердце)": round(
                max(0.0, min(1.0, base_ihd_risk + random.uniform(-0.05, 0.05))), 2
            ),
        }

        highest_risk = max(scores, key=lambda k: scores[k])
        query_map = {
            "АГ (Гипертензия)": "давление сосуды",
            "СД2 (Диабет)": "сахар инсулин",
            "ИБС (Сердце)": "сердце миокард",
        }
        search_query = query_map.get(highest_risk, "сердце сосуды")

        if smoking_status == "smoker":
            search_query += " курение"
        if activity_level == "sedentary":
            search_query += " активность"
        if activity_level == "active":
            search_query += " энергия"
        if age > 50:
            search_query += " усталость"

        logger.info(f"MockML: scores={scores}, query='{search_query}'")
        return scores, search_query
