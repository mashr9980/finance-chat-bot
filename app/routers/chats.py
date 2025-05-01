from fastapi import APIRouter, HTTPException
from app.auth import decode_access_token
from app.chatbot import get_chat_history, process_chat, get_user_profession
from app.database import get_db_connection
from pydantic import BaseModel
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chats"])

class ChatRequest(BaseModel):
    user_message: str
    profession_id: Optional[int] = None

@router.post("/chat")
def chat(chat_request: ChatRequest, token: str):
    """REST API endpoint for sending messages without profession selection"""
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user["user_id"]
    user_message = chat_request.user_message

    logger.info(f"Chat request - User ID: {user_id}, Message: {user_message}")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user status
    cursor.execute("SELECT status FROM users WHERE id = %s", (user_id,))
    status = cursor.fetchone()
    
    if not status or status[0] == "suspended":
        cursor.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Your account is suspended. Contact admin.")

    # Verify the current profession set for the user
    cursor.execute("""
        SELECT up.profession_id, p.name 
        FROM user_profession up
        JOIN professions p ON up.profession_id = p.id
        WHERE up.user_id = %s
    """, (user_id,))
    
    current_profession = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not current_profession:
        logger.info(f"No profession set for user {user_id}")
        return {"response": "No profession is set for your account. This is unusual and might be a system error since profession should be selected during signup."}
    
    logger.info(f"Current profession for user {user_id}: ID {current_profession[0]} - {current_profession[1]}")
    
    # Get profession details before processing chat for logging
    profession_before = get_user_profession(user_id)

    if user_message.lower() in ["hi", "hello", "hey", "start"]:
        # For initial greetings, add a welcome message with profession info
        prof_name = profession_before["profession_name"] if profession_before else "Unknown"
        return {"response": f"Welcome! I'll be asking you specific questions about your {prof_name} business to help provide a customized audit. What's the name of your business?"}

    # Process the chat with the existing profession
    bot_response = process_chat(user_id, user_message)
    
    # Log the response
    logger.info(f"Bot response: {bot_response[:100]}...")
    
    return {"response": bot_response}

@router.get("/history")
def get_chat_history_api(token: str):
    """Retrieve chat history"""
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    chat_history = get_chat_history(user["user_id"])
    return chat_history