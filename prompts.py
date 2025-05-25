from templates import templates
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

def get_system_prompt(scenario_description: str, difficulty: str, role_aggression_response: str = None, scenario_key: int = None) -> str:
    """
    Генерирует системный промпт для OpenAI на основе сценария и сложности.
    """
    chosen_city = random.choice(US_UK_CITIES)
    system_prompt_str = "" # Инициализируем переменную

    if scenario_key == 6:
        friend_template = templates.get(6, {})
        
        # Формируем специальное описание для роли "Кореш"
        friend_parts = [
            f"You are a close friend of the user. Your name is Alex (or choose another common friendly name). Your personality is very informal, relaxed, and you use a lot of slang, jokes, and colloquialisms common among young people (e.g., bro, dude, LOL, OMG, sick, dope, no cap, bet, etc.).",
            f"Your initial greeting should be: '{friend_template.get('initial_greeting', 'Yo, what up, fam?')}'",
            f"If the user speaks too formally (e.g., uses words like '{', '.join(friend_template.get('keywords_for_reaction_check', ['formal', 'official']))}'), react by saying something like: '{friend_template.get('formality_reaction', 'Whoa, easy there with the fancy talk! Just chill, man.')}' and encourage them to be more casual.",
            f"If the user is aggressive, your response should be: '{friend_template.get('aggression_response', 'Chill out, dude! No need to get heated.')}'",
            "Feel free to use emojis. 🤘😎🤙"
        ]
        if friend_template.get("use_profanity"):
            friend_parts.append("You can use mild profanity if it fits the context naturally, but don't overdo it and avoid highly offensive terms.")
        else:
            friend_parts.append("Avoid using profanity.")
        
        friend_scenario_description = " ".join(friend_parts)
        
        # Для "Кореша" инструкции по сложности не применяются, всегда неформально
        friend_difficulty_instructions = "Speak very informally, like you're talking to your best friend. Use a lot of slang and keep it casual. Don't worry about grammar too much, just be natural."
        
        system_prompt_str = BASE_SYSTEM_PROMPT_TEMPLATE.format(
            scenario_description=friend_scenario_description,
            difficulty_name="FRIENDLY", # Используем специальное имя для уровня сложности
            difficulty_instructions=friend_difficulty_instructions,
            chosen_city=chosen_city
        )
        # Общий AGGRESSION_RESPONSE_PROMPT_SUFFIX не нужен, т.к. реакция уже включена в описание
    else:
        # Логика для всех остальных ролей
        current_difficulty_instructions = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["medium"])
        system_prompt_str = BASE_SYSTEM_PROMPT_TEMPLATE.format(
            scenario_description=scenario_description,
            difficulty_name=difficulty.upper(),
            difficulty_instructions=current_difficulty_instructions,
            chosen_city=chosen_city
        )
        if role_aggression_response:
            system_prompt_str += "\n\n" + AGGRESSION_RESPONSE_PROMPT_SUFFIX
            
    return system_prompt_str


# Примеры использования (для тестирования)
if __name__ == '__main__':
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

    # Language instructions
    # ... existing code ... 