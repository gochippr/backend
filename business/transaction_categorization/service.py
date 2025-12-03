from business.transaction_categorization.models import (
    TransactionCategorizationRequest,
)
from business.transaction_categorization.prompts import get_user_prompt
from integrations.gemini import llmCallType, textInference


def categorize_transactions(
    request: TransactionCategorizationRequest,
) -> dict[str, str]:
    response = textInference(
        prompt=get_user_prompt(request),
        call_type=llmCallType.transaction_categorization,
    )
    return {item.transaction_id: item.category for item in response.transactions}
