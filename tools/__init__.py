from tools.weather import get_weather
from tools.stories import get_story, list_stories
from tools.browser_control import play_youtube, open_website, google_search
from tools.pc_control import open_app, set_volume, mute_volume, unmute_volume, take_screenshot, get_now_playing

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
            "ONLY use this tool when the user EXPLICITLY asks for a story, కథ చెప్పు, కథ వినాలి, "
            "or uses the word 'story'/'కథ'. Do NOT use for questions, facts, how-to, visa, weather, or any other topic."
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
    {
        "name": "play_youtube",
        "description": (
            "Search YouTube and play a song, video, or music. "
            "Use when user says 'play', 'put on', 'start', followed by a song or artist name, "
            "or explicitly mentions YouTube."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song name, artist, or video to search and play on YouTube."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_website",
        "description": (
            "Open any website or URL in the browser. "
            "Use when user says 'open', 'go to', 'visit', followed by a website name or URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL or domain to open, e.g. 'netflix.com' or 'https://github.com'."}
            },
            "required": ["url"],
        },
    },
    {
        "name": "google_search",
        "description": (
            "Search Google for any topic. "
            "Use when user says 'search for', 'look up', 'google', followed by a topic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for on Google."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_app",
        "description": (
            "Open an application on the Mac. "
            "Use when user says 'open', 'launch', 'start' followed by an app name like Spotify, Chrome, VS Code, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app to open, e.g. 'Spotify', 'Chrome', 'Terminal'."}
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "set_volume",
        "description": "Set the Mac system volume to a specific level (0–100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Volume level from 0 (silent) to 100 (max)."}
            },
            "required": ["level"],
        },
    },
    {
        "name": "mute_volume",
        "description": "Mute the Mac system audio.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "unmute_volume",
        "description": "Unmute the Mac system audio.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot of the screen and save it to the Desktop.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_now_playing",
        "description": "Get the currently playing song from Spotify or Apple Music.",
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
    if tool_name == "play_youtube":
        return await play_youtube(**tool_input)
    if tool_name == "open_website":
        return await open_website(**tool_input)
    if tool_name == "google_search":
        return await google_search(**tool_input)
    if tool_name == "open_app":
        return await open_app(**tool_input)
    if tool_name == "set_volume":
        return await set_volume(**tool_input)
    if tool_name == "mute_volume":
        return await mute_volume()
    if tool_name == "unmute_volume":
        return await unmute_volume()
    if tool_name == "take_screenshot":
        return await take_screenshot()
    if tool_name == "get_now_playing":
        return await get_now_playing()
    return f"Unknown tool: {tool_name}"
