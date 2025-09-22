from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, Type, TypeVar, overload

from google import genai
from pydantic import BaseModel

from business.transaction_categorization.models import TransactionCategorizationResponse
from business.transaction_categorization.prompts import get_system_prompt

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

CLIENT = genai.Client(api_key=API_KEY)
T = TypeVar("T", bound=BaseModel)


class llmCallType(str, Enum):
    transaction_categorization = "transaction_categorization"
    financial_advice = "financial_advice"


@dataclass
class llmCallConfig(Generic[T]):
    system_prompt: str
    response_model: Type[T]


llmCallToConfigMap: dict[llmCallType, llmCallConfig] = {
    llmCallType.transaction_categorization: llmCallConfig(
        system_prompt=get_system_prompt(),
        response_model=TransactionCategorizationResponse,
    ),
    # TO DO
    llmCallType.financial_advice: llmCallConfig(
        system_prompt="TO DO",
        response_model=BaseModel,
    ),
}


@overload
def textInference(
    prompt: str, call_type: Literal[llmCallType.transaction_categorization]
) -> TransactionCategorizationResponse: ...


@overload
def textInference(
    prompt: str, call_type: Literal[llmCallType.financial_advice]
) -> BaseModel: ...


def textInference(prompt: str, call_type: llmCallType) -> BaseModel:
    config = llmCallToConfigMap[call_type]

    response = CLIENT.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_model=config.response_model,
            system_instruction=config.system_prompt,
        ),
    )

    if not response or not response.text:
        raise ValueError("No response from LLM")

    return json.loads(response.text)
