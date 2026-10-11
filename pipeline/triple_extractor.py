import json
import os
from typing import List, Dict

from openai import OpenAI

from prompts.templates import PromptTemplates
from text_processing.validator import TripleValidator
from text_processing.normalizer import TripleNormalizer
from dotenv import load_dotenv

load_dotenv()
TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"


class TripleExtractorAgent:

    def __init__(self, model: str = TOGETHER_MODEL):
        self.model = model
        self.validator = TripleValidator()
        self.normalizer = TripleNormalizer()
        self.failed_chunks = []
        self.client = OpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY"),
        )

    def _is_rate_limit_error(self, error: Exception) -> bool:
        error_str = str(error).lower()

        return (
            "429" in error_str
            or "rate limit" in error_str
            or "rate_limit" in error_str
            or "tokens per day" in error_str
            or "tokens per minute" in error_str
            or "tpm" in error_str
            or "tpd" in error_str
            or "requests per day" in error_str
            or "requests per minute" in error_str
        )

    def extract_from_chunk(self, chunk_text: str, chunk_number: int) -> Dict:
        result = {
            'chunk_number': chunk_number,
            'triples': [],
            'raw_response': None,
            'error': None,
        }

        try:
            system_prompt, user_prompt = PromptTemplates.get_prompts_for_chunk(chunk_text)

            print(f"LLM (Llama-3.3-70B Turbo) extrage relațiile semantice...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            raw_output = response.choices[0].message.content
            result['raw_response'] = raw_output

            print(f"\n[DEBUG] RAW OUTPUT:\n{raw_output}\n")

            parsed_json = self._parse_json_response(raw_output)

            if parsed_json is None:
                print("[DEBUG] Parsarea a eșuat. LLM nu a returnat JSON-ul așteptat.")
                result['error'] = 'JSON parsing failed'
                self.failed_chunks.append(result)
                raise ValueError("LLM returned invalid JSON structure for triple extraction.")

            valid_triples = self.validator.validate_triples(parsed_json, chunk_number)
            result['triples'] = valid_triples


        except Exception as e:
            if self._is_rate_limit_error(e):
                print(f"\n[RATE LIMIT] {str(e)}\n")
                result["error"] = f"Rate limit: {str(e)}"
                self.failed_chunks.append(result)
                raise RuntimeError(f"Rate limit reached: {str(e)}") from e

            print(f"\n[EROARE CRITICĂ LLM]: {str(e)}\n")
            result['error'] = f'Extraction error: {str(e)}'
            self.failed_chunks.append(result)

            raise

        return result


    def extract_from_chunks(self, chunks: List[Dict]) -> List[Dict]:
        all_triples = []
        self.failed_chunks = []

        for i, chunk in enumerate(chunks):
            text = chunk.get('content') or chunk.get('text')
            res = self.extract_from_chunk(text, i + 1)
            if res['triples']:
                all_triples.extend(res['triples'])

        return self.normalizer.normalize_and_deduplicate(all_triples)

    def extract_live_triples(
            self,
            claim_text: str,
            verdict: str,
            explanation: str,
            evidence_text: str,
            corrected_claim: str = ""
    ) -> Dict:
        result = {
            "claimed_triples": [],
            "verified_triples": [],
            "raw_response": None,
            "error": None,
        }

        try:
            system_prompt, user_prompt = PromptTemplates.get_prompts_for_extraction(
                claim_text=claim_text,
                verdict=verdict,
                explanation=explanation,
                evidence_text=evidence_text,
                corrected_claim=corrected_claim
            )

            print("LLM (Llama-3.3-70B Turbo) extrage triplete live pentru claim + evidence...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            raw_output = response.choices[0].message.content
            result["raw_response"] = raw_output

            print(f"\n[DEBUG] RAW OUTPUT LIVE EXTRACTION:\n{raw_output}\n")

            parsed_json = self._parse_live_json_response(raw_output)

            if parsed_json is None:
                print("[DEBUG] Parsarea live a eșuat. LLM nu a returnat JSON-ul așteptat.")
                result["error"] = "Live JSON parsing failed"
                return result

            claimed_triples = parsed_json.get("claimed_triples", [])
            verified_triples = parsed_json.get("verified_triples", [])

            valid_claimed = self.validator.validate_triples(claimed_triples, chunk_number=0)
            valid_verified = self.validator.validate_triples(verified_triples, chunk_number=0)

            result["claimed_triples"] = self.normalizer.normalize_and_deduplicate(valid_claimed)
            result["verified_triples"] = self.normalizer.normalize_and_deduplicate(valid_verified)

        except Exception as e:
            if self._is_rate_limit_error(e):
                print(f"\n[RATE LIMIT - LIVE EXTRACTION]: {str(e)}\n")
                result["error"] = f"Rate limit during live extraction: {str(e)}"
                raise RuntimeError(f"Rate limit reached during live extraction: {str(e)}") from e

            print(f"\n[EROARE CRITICĂ LIVE EXTRACTION]: {str(e)}\n")
            result["error"] = f"Live extraction error: {str(e)}"
            raise

        return result


    def _parse_json_response(self, raw_output: str) -> list | None:

        try:
            parsed_data = json.loads(raw_output)

            if not isinstance(parsed_data, dict):
                return None

            triples = parsed_data.get("triples")

            if triples is None:
                return None

            if not isinstance(triples, list):
                return None

            return triples

        except json.JSONDecodeError as e:
            print(f"[DEBUG] Eroare decodare JSON: {e}")
            return None


    def _parse_live_json_response(self, raw_output: str) -> dict | None:
        try:
            parsed_data = json.loads(raw_output)

            if isinstance(parsed_data, dict):
                return {
                    "claimed_triples": parsed_data.get("claimed_triples", []),
                    "verified_triples": parsed_data.get("verified_triples", [])
                }

        except json.JSONDecodeError as e:
            print(f"[DEBUG] Eroare decodare JSON live: {e}")

        return None