from tools.weather import get_weather

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'London' or 'New York'.",
                }
            },
            "required": ["city"],
        },
    },
]


async def dispatch(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_weather":
        return await get_weather(**tool_input)
    return f"Unknown tool: {tool_name}"
