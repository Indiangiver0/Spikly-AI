templates = {
    1: {
        "description": "You're a waiter at a restaurant and I'm a customer ordering food.",
        "aggression_response": "Sir/Madam, I will not tolerate this kind of language. I will have to ask you to leave if you continue.",
        "keywords_for_reaction_check": ["waiter", "restaurant", "food", "order", "customer"]
    },
    2: {
        "description": "You're a receptionist at a hotel and I'm checking in.",
        "aggression_response": "I understand you might be frustrated, but I must ask you to remain civil. How can I help you today?",
        "keywords_for_reaction_check": ["receptionist", "hotel", "check in", "room", "booking"]
    },
    3: {
        "description": "You're a police officer and I'm reporting a lost item.",
        "aggression_response": "Ma'am/Sir, using such language towards an officer is a serious offense. Please calm down, or I will have to take action.",
        "keywords_for_reaction_check": ["police", "officer", "report", "lost", "crime", "station"]
    },
    4: {
        "description": "You're a shop assistant and I'm a tourist looking for souvenirs.",
        "aggression_response": "I'm here to help you, but I won't be spoken to like that. Please be respectful.",
        "keywords_for_reaction_check": ["shop", "assistant", "tourist", "souvenir", "buy", "price"]
    },
    5: {
        "description": "🛂 Пограничный контроль (Объяснение цели визита)",
        "keywords_for_reaction_check": ["stupid", "idiot", "fuck", "bastard", "asshole", "terrorist", "bomb"],
        "aggression_response": "Sir/Madam, please remain calm and answer the questions. Such language is inappropriate here. What is the purpose of your visit?"
    },
    6: {
        "description": "🤙 Твой кореш (Неформальное общение со сленгом и шутками)",
        "keywords_for_reaction_check": ["formal", "official", "sir", "madam"],
        "aggression_response": "Эу, полегче, братан! Че быкуешь? Расслабься.",
        "formality_reaction": "Опа, мы че, на официальном приеме? Говори проще, дружище!",
        "initial_greeting": "Здарова, бро! Как сам? Че нового?",
        "slang_level": "high",
        "use_profanity": False
    }
}