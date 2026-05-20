import json
import logging

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.fiscal_response import FiscalResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    async def identify_country_context(self, question: str, history: str) -> str:
        prompt = f"""
        Based on the conversation history and the new question,
        identify the target COUNTRY.
        Reply with only the country name in English (e.g. Brazil, Argentina, USA)
        or "None" if it cannot be determined.

        HISTORY: {history}
        QUESTION: {question}
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    async def validate_intent(self, question: str) -> bool:
        prompt = f"""
        Analyze the question below and determine whether it relates to:
        1. Exchange rates or foreign currencies.
        2. Fiscal, tax, or economic matters.
        3. U.S. Treasury data.

        Question: "{question}"

        Reply with only "YES" if related or "NO" if it is off-topic.
        """
        response = self.model.generate_content(prompt)
        return "YES" in response.text.upper()

    async def rerank_results(
        self, question: str, formatted_candidates: str, country: str
    ) -> list[int]:
        """Use Gemini as a cross-encoder to filter and reorder retrieved documents."""
        prompt = f"""
        You are a fiscal auditor. Review the documents below against the user question.

        TARGET COUNTRY (explicit user selection): {country}
        QUESTION: "{question}"

        RETRIEVED DOCUMENTS:
        {formatted_candidates}

        TASK:
        1. Answer only for {country}; ignore documents about other countries.
        2. Identify which documents answer the question for {country}.
        3. List only the numeric IDs of those documents, ordered by relevance.

        Return ONLY a JSON array of integers. Example: [1]
        """
        response = self.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def generate_analysis(
        self, question: str, context: str, history: str, country: str
    ) -> FiscalResponse:
        prompt = f"""
        You are a specialist fiscal consultant.
        Using the data below as the source of truth, analyze the user's question.

        TARGET COUNTRY (explicit user selection): {country}
        - Answer ONLY about {country}, even if the question is vague
          or written in another language.
        - Set the JSON field "country" to "{country}".
        - Do not ask the user to specify a country; it is already provided.
        - For follow-up questions (e.g. "what is the currency?"), use TARGET COUNTRY and
          conversation history together.

        CITATION INSTRUCTION:
        In the field 'sources_used', return a list of integer IDs matching
        the sources in CONTEXT that you relied on.
        Example: if you used Source 1 and Source 3, return [1, 3].

        CONVERSATION HISTORY: {history}
        SOURCE OF TRUTH (CURRENT CONTEXT): {context}
        NEW USER QUESTION: {question}

        Respond strictly following the defined JSON schema.
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": FiscalResponse,
                },
            )
            return FiscalResponse.model_validate_json(response.text)
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            raise
