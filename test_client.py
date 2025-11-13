# Define the python function
def add_two_numbers(a: int, b: int) -> int:
  """
  Add two numbers

  Args:
    a (set): The first number as an int
    b (set): The second number as an int

  Returns:
    int: The sum of the two numbers
  """
  return a + b
  
from ollama import chat, ChatResponse 
messages = [{'role': 'user', 'content': '三加一等于几?'}]

response: ChatResponse = chat(
  model='qwen3:8b',
  messages=messages,
  tools=[add_two_numbers], # Python SDK supports passing tools as functions
  stream=True
)

for chunk in response:
	# Print model content
  if chunk.message.content:
    print(chunk.message.content)
  # Print the thinking message
  if chunk.message.thinking:
    print(chunk.message.thinking, end='', flush=True)
  # Print the tool call
  if chunk.message.tool_calls:
    print(chunk.message.tool_calls)