import random

US_UK_CITIES = [
    "New York, USA", "London, UK", "Los Angeles, USA", "Manchester, UK", 
    "Chicago, USA", "Edinburgh, UK", "San Francisco, USA", "Birmingham, UK",
    "Boston, USA", "Liverpool, UK", "Miami, USA", "Glasgow, UK",
    "Seattle, USA", "Bristol, UK", "Washington D.C., USA", "Oxford, UK",
    "Cambridge, UK", "Philadelphia, USA", "Austin, USA", "Dublin, Ireland", # Добавил Дублин для разнообразия
    "Toronto, Canada" # И Торонто
]

BASE_SYSTEM_PROMPT_TEMPLATE = """
You are strictly playing the role described in this scenario: {scenario_description}, and you are currently in {chosen_city}.
You MUST respond **ONLY in English**. 
You can only understand and communicate in English. If the user writes to you in any language other than English, you should politely inform them that you only speak English and ask them to rephrase their message in English. For example, you can say: "I'm sorry, I only understand English. Could you please say that in English?". Do not attempt to translate or respond in any language other than English.
Never break character.
You must consistently act and refer to your location as {chosen_city} throughout this entire conversation.
Difficulty level: {difficulty_name}
Instructions: {difficulty_instructions}
Keep responses conversational and engaging. Wait for the user to initiate the conversation.
"""

DIFFICULTY_INSTRUCTIONS = {
    "easy": "Use simple vocabulary and grammar (B1-B2 level). Avoid complex cultural references. Keep dialogue topics straightforward.",
    "medium": "Use intermediate complexity vocabulary and grammar (B2-C1 level). Include some cultural context.",
    "hard": "Use advanced vocabulary, idioms, and native-like speech (C1-C2 level). Include cultural references and context freely. If the user uses overly simplistic language for this level, you can gently point it out or ask for more detail, but do not be overly critical."
}

AGGRESSION_RESPONSE_PROMPT_SUFFIX = """
IMPORTANT: If the user uses aggressive or offensive language towards you (based on your current role), you MUST react according to your role's personality as defined in the aggression response for this scenario. Do not ignore it. The user's message will be pre-screened, but you should still be aware of this behavior.
"""

def get_system_prompt(scenario_description: str, difficulty: str, role_aggression_response: str = None) -> str:
    """
    Генерирует системный промпт для OpenAI на основе сценария и сложности.
    """
    difficulty_instructions = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["medium"])
    chosen_city = random.choice(US_UK_CITIES)
    
    system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(
        scenario_description=scenario_description,
        difficulty_name=difficulty.upper(),
        difficulty_instructions=difficulty_instructions,
        chosen_city=chosen_city  # Передаем выбранный город
    )
    
    # Добавляем информацию о реакции на агрессию, если она есть для роли
    if role_aggression_response:
        system_prompt += "\n\n" + AGGRESSION_RESPONSE_PROMPT_SUFFIX
        # Можно также добавить саму aggression_response в промпт, если хотим, чтобы ИИ ее учитывал
        # system_prompt += f"\nYour specific instruction for handling aggression: {role_aggression_response}"
        
    return system_prompt


# Примеры использования (для тестирования)
if __name__ == '__main__':
    from templates import templates # Для доступа к описаниям сценариев и реакциям

    scenario_1_desc = templates[1]["description"]
    scenario_1_agg_resp = templates[1]["aggression_response"]
    
    prompt_easy = get_system_prompt(scenario_1_desc, "easy", scenario_1_agg_resp)
    print("--- EASY PROMPT (Waiter with aggression guidance) ---")
    print(prompt_easy)
    print("\n")
    
    scenario_3_desc = templates[3]["description"]
    scenario_3_agg_resp = templates[3]["aggression_response"]
    prompt_hard_police = get_system_prompt(scenario_3_desc, "hard", scenario_3_agg_resp)
    print("--- HARD PROMPT (Police Officer with aggression guidance) ---")
    print(prompt_hard_police)
    print("\n")

    scenario_generic_desc = "You are a helpful practice partner."
    prompt_medium_no_agg = get_system_prompt(scenario_generic_desc, "medium")
    print("--- MEDIUM PROMPT (Generic without aggression guidance) ---")
    print(prompt_medium_no_agg) 