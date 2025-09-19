from ollama import chat


def chat_with_ollama_stream(messages):
    response = chat(
        model='deepseek-r1:7b',
        messages=messages,
        stream=True
    )

    for chunk in response:
        yield chunk['message']['content']
