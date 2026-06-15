import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=api_key)


system_prompt = """You are a helpful assistant that always responds with valid JSON.
Your response must be ONLY the raw JSON object - no markdown code blocks, no ```json``` tags, no additional text or formatting.
Start directly with { and end with }."""


def get_structured_response(
    prompt,
    schema_description=None,
    model="claude-sonnet-4-6",
    system_prompt=system_prompt,
):
    """
    Agent that returns structured JSON output using Anthropic's API.

    Args:
        prompt: The user's question or request
        schema_description: Optional description of the expected JSON structure
        model: Model to use (default: claude-sonnet-4-6)

    Returns:
        dict: Parsed JSON response from the model
    """

    if schema_description:
        system_prompt += f"\n\nPlease format your response according to this structure:\n{schema_description}"

    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # print(f"Raw API response: {message}")
        response_text = message.content[0].text  # type: ignore

        # Strip markdown code blocks if present
        if response_text.strip().startswith("```"):
            # Remove ```json or ``` at start and ``` at end
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        # Parse the JSON response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw response: {response_text}")
            return {"error": "Failed to parse JSON", "raw_response": response_text}

    except Exception as e:
        print(f"API Error: {e}")
        return {"error": str(e)}


def analyze(prompt):
    return get_structured_response(prompt, model="claude-sonnet-4-6")
