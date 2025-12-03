from business.transaction_categorization.models import (
    TransactionCategorizationRequest,
)

CATEGORIES = [
    "Groceries",
    "Dining",
    "Utilities",
    "Entertainment",
    "Transportation",
    "Healthcare",
    "Education",
    "Shopping",
    "Travel",
    "Personal Care",
    "Subscriptions",
    "Gifts & Donations",
    "Miscellaneous",
]


def get_system_prompt() -> str:
    categories_str = "\n".join(
        f"{idx + 1}. {cat}" for idx, cat in enumerate(CATEGORIES)
    )
    system_prompt = (
        "You are a financial assistant that categorizes bank transactions into predefined categories. "
        "Given a transaction description and amount, assign the most appropriate category from the list below.\n\n"
        "Categories:\n"
        f"{categories_str}\n\n"
        "Instructions:\n"
        "1. Analyze the transaction description and amount.\n"
        "2. Choose the most relevant category from the list.\n"
        "3. If the transaction does not fit any category, assign it to 'Miscellaneous'.\n"
        "4. Respond in JSON format as specified.\n\n"
        "Response Format:\n"
        "{\n"
        '  "transaction_id_to_category": {\n'
        '    "<transaction_id>": "<category>",\n'
        "    ...\n"
        "  }\n"
        "}\n\n"
        "Example:\n"
        'Input: {"transaction_id": "tx123", "transaction_description": "Starbucks Coffee", "amount": 5.75}\n'
        'Output: {"transaction_id_to_category": {"tx123": "Dining"}}\n\n'
        "Now, categorize the following transactions:"
    )
    return system_prompt


def get_user_prompt(request: TransactionCategorizationRequest) -> str:
    items_str = "\n".join(
        f'- Input: {{"transaction_id": "{item.transaction_id}", "transaction_description": "{item.transaction_description}", "amount": {item.amount}}}'
        for item in request.items
    )
    user_prompt = f"{items_str}\n\nRespond with the categories for each transaction."
    return user_prompt
