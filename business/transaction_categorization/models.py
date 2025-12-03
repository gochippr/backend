from pydantic import BaseModel


class TransactionCategorizationRequestItem(BaseModel):
    transaction_id: str
    transaction_description: str
    amount: float


class TransactionCategorizationRequest(BaseModel):
    items: list[TransactionCategorizationRequestItem]
    categories: list[str]


class TransactionCategorizationResponseItem(BaseModel):
    transaction_id: str
    category: str


class TransactionCategorizationResponse(BaseModel):
    transactions: list[TransactionCategorizationResponseItem]


TRANSACTION_CATEGORIZATION_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "required": ["transactions"],
    "properties": {
        "transactions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["transaction_id", "category"],
                "properties": {
                    "transaction_id": {"type": "STRING"},
                    "category": {"type": "STRING"},
                },
            },
        },
    },
}
