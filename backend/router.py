from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
)

# Requested model mapping
MODELS = {
    # Free multimodal (vision)
    "image": "moonshotai/kimi-vl-a3b-thinking:free",
    # PDF/doc reasoning and general deep reasoning
    "pdf_docs": "qwen/qwen2.5-vl-32b-instruct:free",
    "complex_chat": "qwen/qwen2.5-vl-32b-instruct:free",
    # Web context
    "web": "deepseek/deepseek-r1-distill-qwen-14b:free",
}


def ask_llm(model: str, prompt: str, image_path: str | None = None) -> str:
    """Direct call to OpenRouter-compatible Chat Completions. If image_path is provided,
    send a multimodal message. Returns assistant text content.
    """
    if image_path:
        with open(image_path, "rb") as img:
            img_bytes = img.read()
        # Some OpenRouter providers accept base64 image bytes via 'input_image'
        # For compatibility, we use OpenAI-style content blocks.
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_image", "image_data": img_bytes},
                ]
            }]
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
    return response.choices[0].message.content or ""
