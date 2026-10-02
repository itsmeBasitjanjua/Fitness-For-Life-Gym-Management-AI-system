"""
Calorie and macro targets (pure maths - no database, no AI).

Doing the numbers in code, not in the language model, means they are always
correct and repeatable. The AI then turns them into a friendly meal plan.
Formula: Mifflin-St Jeor. This is general guidance, not medical advice.
"""
from gym_ai.utils import GymError

ACTIVITY_FACTORS = {
    "sedentary": 1.2,      # desk job, little exercise
    "light": 1.375,        # 1-3 workouts a week
    "moderate": 1.55,      # 3-5 workouts a week
    "active": 1.725,       # 6-7 workouts a week
    "very_active": 1.9,    # hard training / physical job
}
GOAL_ADJUSTMENT = {"fat_loss": -500, "maintain": 0, "muscle_gain": 300}  # kcal per day


def calculate_targets(weight_kg: float, height_cm: float, age: int, gender: str,
                      activity_level: str = "moderate", goal: str = "maintain") -> dict:
    if activity_level not in ACTIVITY_FACTORS:
        raise GymError(f"activity_level must be one of {list(ACTIVITY_FACTORS)}.")
    if goal not in GOAL_ADJUSTMENT:
        raise GymError(f"goal must be one of {list(GOAL_ADJUSTMENT)}.")
    if gender.lower() not in ("male", "female"):
        raise GymError("gender must be 'male' or 'female' for the calorie formula.")
    if not (30 <= weight_kg <= 300 and 120 <= height_cm <= 230 and 14 <= age <= 90):
        raise GymError("Weight, height or age looks unrealistic - please double-check.")

    sex_constant = 5 if gender.lower() == "male" else -161
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_constant
    maintenance = bmr * ACTIVITY_FACTORS[activity_level]
    calories = maintenance + GOAL_ADJUSTMENT[goal]

    protein_g = weight_kg * (1.6 if goal == "maintain" else 2.0)
    fat_g = calories * 0.25 / 9
    carbs_g = (calories - protein_g * 4 - fat_g * 9) / 4
    bmi = weight_kg / ((height_cm / 100) ** 2)

    return {
        "bmi": round(bmi, 1),
        "bmr_kcal": round(bmr),
        "maintenance_kcal": round(maintenance),
        "target_kcal": round(calories),
        "protein_g": round(protein_g),
        "carbs_g": round(max(carbs_g, 0)),
        "fat_g": round(fat_g),
        "goal": goal,
        "note": "General guidance only - not medical advice.",
    }
