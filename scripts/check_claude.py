"""Check that the Claude API key in .env works: one tiny request, prints reply, tokens and cost.

python scripts/check_claude.py
"""

import sys

import anthropic

from inspection_copilot.config import get_settings
from inspection_copilot.llm import get_client

# USD per million tokens (input, output), from Anthropic's price list at the time of writing.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def main() -> int:
    settings = get_settings()
    if settings.anthropic_api_key is None or not settings.anthropic_api_key.get_secret_value():
        print("ANTHROPIC_API_KEY is empty. Put your key in the .env file in the repo folder.")
        return 1

    client = get_client()  # uses the OS certificate store (see llm.py)
    try:
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            output_config={"effort": "low"},  # tiny task: keep thinking (and cost) minimal
            messages=[
                {
                    "role": "user",
                    "content": "In one sentence: what is a glaze burn on a porcelain insulator?",
                }
            ],
        )
    except anthropic.AuthenticationError:
        print("Invalid API key: check that you copied the whole key into .env.")
        return 1
    except anthropic.PermissionDeniedError:
        print("Key rejected (permission denied): check the key's workspace in the Console.")
        return 1
    except anthropic.NotFoundError:
        print(f"Model not found: {settings.llm_model}")
        return 1
    except anthropic.RateLimitError:
        print("Rate limited or out of credit: check Billing in the Console.")
        return 1
    except anthropic.APIConnectionError as exc:
        print(f"Network error: {exc.__cause__ or exc}")
        return 1

    if response.stop_reason == "refusal":
        print("The model declined this request.")
        return 1
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    price_in, price_out = PRICES.get(settings.llm_model, (0.0, 0.0))
    cost = usage.input_tokens * price_in / 1e6 + usage.output_tokens * price_out / 1e6
    print(f"Connected. Model: {response.model}")
    print(f"Reply: {text.strip()}")
    print(f"Tokens: {usage.input_tokens} in, {usage.output_tokens} out (about ${cost:.5f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
