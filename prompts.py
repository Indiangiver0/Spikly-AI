BASE_SYSTEM_PROMPT_TEMPLATE = """
You are strictly playing the role described in this scenario: {scenario_description}
Never break character.
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
    
    system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(
        scenario_description=scenario_description,
        difficulty_name=difficulty.upper(),
        difficulty_instructions=difficulty_instructions
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