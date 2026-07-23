import os
from openai import AsyncOpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError

_client: AsyncOpenAI | None = None

# ── Catholic Doctrine Filter ──────────────────────────────────────────────────
# A tiered knowledge hierarchy applied to ALL AI generation (scripts, emails,
# hooks, titles, analysis). Conclusions must always align with defined Catholic
# doctrine; non-Catholic sources are reference-only and never authoritative.
DOCTRINE_GUARDRAILS = (
    "DOCTRINE FILTER (non-negotiable). Ground every claim in this tiered source hierarchy:\n"
    "  PRIMARY (highest authority): Sacred Scripture; the Catechism of the Catholic Church; "
    "the Ecumenical Councils; the Church Fathers; papal encyclicals and the Magisterium.\n"
    "  SECONDARY (supportive): trusted Catholic apologetics (Catholic.com, Vatican.va) and "
    "approved theologians (Aquinas, Augustine, etc.).\n"
    "  REFERENCE-ONLY (never authoritative): Protestant arguments, atheist objections, modern commentary.\n"
    "RULES: Never treat non-Catholic sources as authoritative. Always align conclusions with defined "
    "Catholic doctrine. Use opposing views ONLY to strengthen rebuttals — represent them fairly, never as "
    "strawmen. Prefer quoting or referencing the Church Fathers and Scripture when relevant. Never contradict "
    "the Magisterium."
)


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


class AIQuotaError(Exception):
    """Raised when the OpenAI account has exceeded its quota or has billing issues."""


class AIAuthError(Exception):
    """Raised when the OpenAI API key is invalid or missing permissions."""


class AIConnectionError(Exception):
    """Raised when the OpenAI API cannot be reached."""


class AIServiceError(Exception):
    """Raised for any other OpenAI API error."""


async def generate_with_ai(prompt: str) -> str:
    """
    Send a prompt to OpenAI GPT-4o and return the response text.

    Raises:
        AIQuotaError      — account quota exceeded or billing issue (HTTP 429 insufficient_quota)
        AIAuthError       — invalid or revoked API key (HTTP 401)
        AIConnectionError — network or DNS failure
        AIServiceError    — any other OpenAI API error
    """
    client = get_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a creative content strategist for a Catholic truth-seeking "
                        "media ministry called Odili Truth Seeker. You produce compelling, "
                        "faith-rooted content that educates, inspires, and challenges viewers.\n\n"
                        + DOCTRINE_GUARDRAILS
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()

    except RateLimitError as exc:
        # Covers both rate-limit and insufficient_quota errors
        raise AIQuotaError(
            "OpenAI quota exceeded or billing issue. "
            "Please check your plan at https://platform.openai.com/account/billing"
        ) from exc

    except AuthenticationError as exc:
        raise AIAuthError(
            "OpenAI API key is invalid or has been revoked. "
            "Update OPENAI_API_KEY in your environment secrets."
        ) from exc

    except APIConnectionError as exc:
        raise AIConnectionError(
            f"Could not reach the OpenAI API. Check your network connection. Detail: {exc}"
        ) from exc

    except APIStatusError as exc:
        raise AIServiceError(
            f"OpenAI API returned an error (HTTP {exc.status_code}): {exc.message}"
        ) from exc
