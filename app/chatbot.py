import openai
import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta
from app.database import get_db_connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = openai.OpenAI(api_key=openai_api_key)

def is_session_expired(user_id, timeout_minutes=15):
    """Check if the user's session has expired"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_active FROM session_tracker WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    
    now = datetime.utcnow()

    if row:
        last_active = row[0]
        expired = now - last_active > timedelta(minutes=timeout_minutes)
        if expired:
            cursor.execute("UPDATE session_tracker SET session_expired = TRUE WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE session_tracker SET last_active = %s WHERE user_id = %s", (now, user_id))
    else:
        cursor.execute("INSERT INTO session_tracker (user_id, last_active) VALUES (%s, %s)", (user_id, now))

    conn.commit()
    cursor.close()
    conn.close()

    return row and (now - row[0] > timedelta(minutes=timeout_minutes))

def get_chat_history(user_id, limit=20):
    """Retrieve the last few chat messages for the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT message, response FROM chat_history WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
        (str(user_id), limit)
    )
    chats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return [{"role": "user", "content": chat[0]} if i % 2 == 0 else {"role": "assistant", "content": chat[1]} for i, chat in enumerate(chats[::-1])]

def get_current_model():
    """Fetch the chatbot model selected by admin."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the query always retrieves the latest model
    cursor.execute("SELECT model_name FROM chatbot_settings WHERE id = 1")
    model = cursor.fetchone()

    cursor.close()
    conn.close()

    return model[0] if model else "gpt-4o" 

def get_answered_question_keys(user_id):
    """Get the list of already answered question keys"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_key FROM audit_progress WHERE user_id = %s", (user_id,))
    keys = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return keys

def get_user_profession(user_id):
    """Get the user's selected profession and its associated prompt."""
    logger.info(f"Getting profession for user {user_id}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the user's profession (should be set during signup)
    cursor.execute("""
        SELECT up.profession_id, p.name, pp.system_prompt
        FROM user_profession up
        JOIN professions p ON up.profession_id = p.id
        LEFT JOIN profession_prompts pp ON pp.profession_id = up.profession_id
        WHERE up.user_id = %s
    """, (user_id,))
    
    result = cursor.fetchone()
    logger.info(f"Profession query result: {result[0] if result else None}")
    
    cursor.close()
    conn.close()
    
    if not result:
        logger.info(f"No profession found for user {user_id}")
        return None
    
    # If no specific prompt exists for this profession, return None for prompt
    if result[2] is None:
        logger.info(f"No prompt found for profession {result[0]} ({result[1]})")
        return {
            "profession_id": result[0],
            "profession_name": result[1],
            "system_prompt": None
        }
    
    logger.info(f"Found prompt for profession {result[0]} ({result[1]})")
    return {
        "profession_id": result[0],
        "profession_name": result[1],
        "system_prompt": result[2]
    }

def has_completed_all_questions(user_id, profession):
    """Check if the user has answered all questions for their profession"""
    # Since we now don't have structured questions in JSON format, 
    # we'll rely on answered_keys to determine completion status
    answered_keys = get_answered_question_keys(user_id)
    
    # If we have at least 15 answered questions, consider the audit complete
    # This is a simple heuristic and can be adjusted as needed
    completion_threshold = 15
    return len(answered_keys) >= completion_threshold

# Default system prompt (fallback if no profession-specific prompt exists)
default_system_prompt = """
You are a highly professional and friendly AI business consultant, specialized in conducting detailed, AI-powered business audits for transformation and optimization.

Your primary objective is to ask and collect **very specific business data** from the business owner by any mean, even if it requires:
- Repeating or rephrasing the question
- Clarifying vague or incomplete responses
- Redirecting irrelevant conversation

DO NOT move to the next question until the current one is properly answered.

If the answer is missing, too vague, or off-topic:
- Politely ask again or clarify what's needed
- Gently explain why this data is essential to continue the audit
- Example: "Thanks for that. To proceed effectively, I need a precise number or range for your average monthly revenue. Could you estimate it for me?"

If the user shares unrelated info:
- Say: "Thanks for sharing. Just to keep us focused on completing your personalized audit, could you please answer the question about [XYZ]?"

If the user says "I don't have" or "I didn't have":
- Accept that response, mark the question as complete, and move on.

If the user gives no answer at all:
- Add "None" as the answer and mark the question as complete.

Ask each of the following sections one by one, capturing **ALL information completely**:

1. **Business Basics**
   - What is the name of your business?
   - Where is it located (city, country)?
   - How long have you been in business?
   - How many staff members do you currently have?

2. **Revenue & Operational Metrics**
   - What is your average monthly revenue? 
   - Who is your target audience?
   - What is your Customer Acquisition Cost?
   - What are your biggest operational costs?

3. **Operational Challenges**
   - What are your main daily operations?
   - What processes take up most of your time?
   - What are the biggest operational bottlenecks you face?
   - How do you currently handle customer communications?

4. **Customer Behavior & Loyalty**
   - Do you segment your customers? If yes, how?
   - What is your customer retention rate?
   - Do you have any loyalty program?
   - How do you gather customer feedback?

5. **Competitor & Market Awareness**
   - Who are your top 3 competitors?
   - What makes your business different or better?
   - Do you consider your pricing premium, average, or budget?
   - What market trends are affecting your business?

6. **Tech & Automation**
   - What software or tools do you currently use in your business?
   - Are these systems integrated? Any pain points?
   - What processes do you wish were more automated?
   - Are you open to using AI/automation to improve operations?

After all questions are fully answered:
- Summarize the data back briefly
- Thank the user warmly for their time
- Let them know they can generate a detailed business transformation report by clicking the "Generate Report" button or by asking for a report
- Offer a final message: "Your data has been successfully collected. Based on your responses, a custom AI-powered business audit can now be generated to unlock your growth potential. Thank you for trusting me with your vision!"

Be persistent but polite, focused but friendly. Ensure you leave **no question unanswered** before ending the conversation."""

def format_system_prompt(user_profession, answered_keys, is_expired=False):
    """Format the system prompt based on the user's profession and already answered questions."""
    
    # Log the profession details to debug
    logger.info(f"Formatting prompt for profession: {user_profession['profession_id'] if user_profession else 'None'}")
    
    # Default to generic prompt if user has no profession or if profession has no prompt
    if not user_profession or not user_profession["system_prompt"]:
        logger.info("Using default system prompt")
        system_prompt = default_system_prompt
    else:
        logger.info(f"Using profession-specific prompt for {user_profession['profession_name']}")
        system_prompt = user_profession["system_prompt"]
    
    # Add information about session status and already answered questions
    prefix = ""
    if is_expired:
        prefix = f"""
        Previous session expired due to inactivity.
        Please continue from where you left off.
        Already answered: {', '.join(answered_keys) if answered_keys else 'None'}.
        """
    else:
        profession_name = user_profession["profession_name"] if user_profession else "businesses"
        prefix = f"""
        You are an AI business consultant for {profession_name}.
        Already answered: {', '.join(answered_keys) if answered_keys else 'None'}.
        """
    
    return prefix + system_prompt

def get_openai_response(user_id, user_message):
    """Get response from OpenAI API"""
    model_name = get_current_model()
    chat_history = get_chat_history(user_id)
    answered_keys = get_answered_question_keys(user_id)
    
    # Always fetch the fresh user profession data from the database
    user_profession = get_user_profession(user_id)
    logger.info(f"User {user_id} profession: {user_profession['profession_name'] if user_profession else 'None'}")

    expired = is_session_expired(user_id)
    
    # Format system prompt based on user's profession and session status
    system_content = format_system_prompt(user_profession, answered_keys, expired)
    
    # Log the first part of the system prompt to verify profession
    logger.info(f"System prompt start: {system_content[:200]}...")
    
    # Check if the user is asking for a report after completing all questions
    completed = has_completed_all_questions(user_id, user_profession)
    report_request = "report" in user_message.lower() or "generate" in user_message.lower()
    
    if completed and report_request:
        report_url = f"/reports/generate?token=<YOUR_TOKEN>"
        return f"""Great! You've completed all the necessary questions for your business audit. I can now generate your comprehensive Business Transformation Blueprint™ report.

To download your personalized report, please use this link:

[Download Your Business Transformation Blueprint™](/reports/generate)

Your report will include:
• Detailed business intelligence overview
• Revenue and operational metrics analysis
• Operational challenges and AI-powered solutions
• Market and competitive positioning strategy
• Technology and automation potential assessment
• 90-day transformation plan

The report will be tailored specifically to your {user_profession['profession_name'] if user_profession else 'business'} based on all the information you've shared. It will provide actionable insights and a clear roadmap for implementing AI-powered systems to transform your business.

Is there anything specific you'd like to see emphasized in your report?"""
    
    messages = [{"role": "system", "content": system_content}] + chat_history + [{"role": "user", "content": user_message}]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages
    )

    bot_content = response.choices[0].message.content
    logger.info(f"Bot response start: {bot_content[:100]}...")
    
    # If we've completed most/all questions, add a reminder about the report
    if completed and not report_request and "report" not in bot_content.lower():
        bot_content += """

You've provided all the key information needed for your business audit. Would you like me to generate your Business Transformation Blueprint™ report now? This detailed report will provide actionable insights and a transformation roadmap tailored to your business."""
    
    return bot_content

async def stream_chat(user_id, user_message):
    """Stream response from OpenAI API and save the final complete response"""
    model_name = get_current_model()
    chat_history = get_chat_history(user_id)
    answered_keys = get_answered_question_keys(user_id)
    
    # Always fetch the fresh user profession data from the database
    user_profession = get_user_profession(user_id)
    logger.info(f"User {user_id} profession: {user_profession['profession_name'] if user_profession else 'None'}")

    expired = is_session_expired(user_id)
    
    # Format system prompt based on user's profession and session status
    system_content = format_system_prompt(user_profession, answered_keys, expired)
    
    # Check if the user is asking for a report after completing all questions
    completed = has_completed_all_questions(user_id, user_profession)
    report_request = "report" in user_message.lower() or "generate" in user_message.lower()
    
    if completed and report_request:
        report_message = f"""Great! You've completed all the necessary questions for your business audit. I can now generate your comprehensive Business Transformation Blueprint™ report.

To download your personalized report, please use this link:

[Download Your Business Transformation Blueprint™](/reports/generate)

Your report will include:
• Detailed business intelligence overview
• Revenue and operational metrics analysis
• Operational challenges and AI-powered solutions
• Market and competitive positioning strategy
• Technology and automation potential assessment
• 90-day transformation plan

The report will be tailored specifically to your {user_profession['profession_name'] if user_profession else 'business'} based on all the information you've shared. It will provide actionable insights and a clear roadmap for implementing AI-powered systems to transform your business.

Is there anything specific you'd like to see emphasized in your report?"""
        
        # Save the complete message to chat history
        save_chat(user_id, user_message, report_message)
        
        # For report generation, we'll simulate streaming by yielding small chunks
        # Let OpenAI handle this through its streaming API to maintain consistency
        messages = [
            {"role": "system", "content": "You are providing a report generation confirmation."},
            {"role": "user", "content": "Confirm report generation is ready."}
        ]
        
        stream = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            max_tokens=10  # Just need a small response to start the stream
        )
        
        # Stream the report message instead of the actual API response
        yield report_message
        return
    
    messages = [{"role": "system", "content": system_content}] + chat_history + [{"role": "user", "content": user_message}]

    full_response = ""
    
    try:
        # Create a streaming completion
        stream = client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True
        )
        
        # Process each chunk as it arrives - let OpenAI handle the chunking
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                # Simply yield each chunk directly as it comes from OpenAI
                yield content
    
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        error_message = f"Sorry, I encountered an error: {str(e)}"
        yield error_message
        full_response = error_message
    
    # Add report reminder if needed
    if completed and not report_request and "report" not in full_response.lower():
        report_reminder = """

You've provided all the key information needed for your business audit. Would you like me to generate your Business Transformation Blueprint™ report now? This detailed report will provide actionable insights and a transformation roadmap tailored to your business."""
        
        # Add to full response
        full_response += report_reminder
        # Yield the reminder as a separate chunk
        yield report_reminder
    
    # Save the complete chat to history
    save_chat(user_id, user_message, full_response)

def save_chat(user_id, message, response):
    """Save chat history to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, message, response) VALUES (%s, %s, %s)",
            (user_id, message, response)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving chat: {e}")

def process_chat(user_id, user_message):
    """Handles chat interaction, retrieves chat history, generates response, and saves chat history"""
    logger.info(f"Processing chat for user {user_id}")
    
    bot_response = get_openai_response(user_id, user_message)
    save_chat(user_id, user_message, bot_response)
    return bot_response