from tools.weather import get_weather
from tools.stories import get_story, list_stories

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Irving' or 'Hyderabad'."}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_story",
        "description": (
            "Tell a Telugu story from the local library. "
            "Use when the user asks for a story, కథ చెప్పు, కథ వినాలి, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Story category: 'పంచతంత్ర' or 'తెనాలి రామకృష్ణుడు'. Leave empty for random.",
                },
                "title": {
                    "type": "string",
                    "description": "Partial title to search for a specific story. Leave empty for random.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_stories",
        "description": "List all available Telugu stories in the local library.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


async def dispatch(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_weather":
        return await get_weather(**tool_input)
    if tool_name == "get_story":
        return get_story(**tool_input)
    if tool_name == "list_stories":
        return list_stories()
    return f"Unknown tool: {tool_name}"
