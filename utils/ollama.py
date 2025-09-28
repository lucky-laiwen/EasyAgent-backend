from ollama import chat


def chat_with_ollama_stream(messages):
    with open(r"utils\optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    full_messages = [{
        "role":"system",
        "content": system_prompt
    }] + messages
    response = chat(
        model='qwen3:8b',
        messages=full_messages,
        stream=True,
    )

    for chunk in response:
        yield chunk['message']['content']
