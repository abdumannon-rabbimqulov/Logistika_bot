from .order_actions import create_order_action, get_my_orders_action, cancel_order_action
from .driver_actions import set_driver_status_action, search_available_orders_action
from .user_actions import get_profile_action, get_help_action

# Tool definitions for Gemini
LOGISTIKA_TOOLS = [
    {
        "name": "create_order",
        "description": "Creates a new logistics order for shipping cargo. Required parameters: from_city, to_city, cargo_type, weight, price.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "from_city": {"type": "STRING", "description": "Departure city"},
                "to_city": {"type": "STRING", "description": "Arrival city"},
                "cargo_type": {"type": "STRING", "description": "Type of cargo (food, construction, etc.)"},
                "weight": {"type": "NUMBER", "description": "Weight in tons"},
                "price": {"type": "NUMBER", "description": "Offered price for delivery"}
            },
            "required": ["from_city", "to_city", "cargo_type", "weight", "price"]
        }
    },
    {
        "name": "get_my_orders",
        "description": "Retrieves the list of orders created by the current user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "cancel_order",
        "description": "Cancels a specific order by its ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "order_id": {"type": "INTEGER", "description": "The ID of the order to cancel"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "get_profile",
        "description": "Shows the user's profile information (name, role, balance).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "set_driver_status",
        "description": "Sets the driver availability status to online or offline.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "online": {"type": "BOOLEAN", "description": "True for online, False for offline"}
            },
            "required": ["online"]
        }
    },
    {
        "name": "search_orders",
        "description": "Searches for available orders that drivers can take.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_help",
        "description": "Provides information about what the bot can do.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    }
]

# Map tool names to actual python functions
ACTION_MAP = {
    "create_order": create_order_action,
    "get_my_orders": get_my_orders_action,
    "cancel_order": cancel_order_action,
    "get_profile": get_profile_action,
    "set_driver_status": set_driver_status_action,
    "search_orders": search_available_orders_action,
    "get_help": get_help_action,
}
