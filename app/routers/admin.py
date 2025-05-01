import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from app.auth import ADMIN_EMAIL, decode_access_token
from app.database import get_db_connection

router = APIRouter(tags=["Admin"])

# Define response models
class UserChatHistoryResponse(BaseModel):
    id: int
    message: str
    response: str
    timestamp: str

class PaymentStatusResponse(BaseModel):
    user_id: int
    status: str
    payment_id: Optional[str] = None
    payment_amount: Optional[int] = None
    payment_date: Optional[str] = None
    expiry_date: Optional[str] = None

class UserWithPaymentStatus(BaseModel):
    id: int
    username: str
    email: str
    role: str
    status: str
    payment_status: str = "free"
    payment_date: Optional[str] = None
    expiry_date: Optional[str] = None

def is_admin(token: str):
    """Check if the logged-in user is an admin"""
    user = decode_access_token(token)
    
    if not user or "sub" not in user:
        raise HTTPException(status_code=403, detail="Access denied: Invalid token")

    if user["sub"] != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Access denied: Admin only")

    return user

# Admin - View All Users with Payment Status
@router.get("/users", response_model=List[UserWithPaymentStatus])
def get_all_users(token: str = Depends(is_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.username, u.email, u.role, u.status, 
               ps.status, ps.payment_date, ps.expiry_date
        FROM users u
        LEFT JOIN payment_status ps ON u.id = ps.user_id
        WHERE u.role != 'admin'
    """)
    
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Format the user data with payment status
    result = []
    for u in users:
        # Format dates if they exist
        payment_date = None
        expiry_date = None
        
        if u[6]:  # payment_date
            payment_date = u[6].isoformat() if hasattr(u[6], 'isoformat') else str(u[6])
            
        if u[7]:  # expiry_date
            expiry_date = u[7].isoformat() if hasattr(u[7], 'isoformat') else str(u[7])
        
        result.append({
            "id": u[0],
            "username": u[1],
            "email": u[2],
            "role": u[3],
            "status": u[4],
            "payment_status": u[5] if u[5] else "free",
            "payment_date": payment_date,
            "expiry_date": expiry_date
        })
    
    return result

# Admin - Get All Payment Statuses
@router.get("/payment-status", response_model=List[PaymentStatusResponse])
def get_all_payment_status(token: str = Depends(is_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, status, payment_id, payment_amount, payment_date, expiry_date
        FROM payment_status
        ORDER BY payment_date DESC
    """)
    
    payments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    result = []
    for p in payments:
        # Format dates if they exist
        payment_date = None
        expiry_date = None
        
        if p[4]:  # payment_date
            payment_date = p[4].isoformat() if hasattr(p[4], 'isoformat') else str(p[4])
            
        if p[5]:  # expiry_date
            expiry_date = p[5].isoformat() if hasattr(p[5], 'isoformat') else str(p[5])
        
        result.append({
            "user_id": p[0],
            "status": p[1],
            "payment_id": p[2],
            "payment_amount": p[3],
            "payment_date": payment_date,
            "expiry_date": expiry_date
        })
    
    return result

# Admin - Get Payment Status for a Specific User
@router.get("/payment-status/{user_id}", response_model=PaymentStatusResponse)
def get_user_payment_status(user_id: int, token: str = Depends(is_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, status, payment_id, payment_amount, payment_date, expiry_date
        FROM payment_status
        WHERE user_id = %s
    """, (user_id,))
    
    payment = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not payment:
        return {
            "user_id": user_id,
            "status": "free"
        }
    
    # Format dates if they exist
    payment_date = None
    expiry_date = None
    
    if payment[4]:  # payment_date
        payment_date = payment[4].isoformat() if hasattr(payment[4], 'isoformat') else str(payment[4])
        
    if payment[5]:  # expiry_date
        expiry_date = payment[5].isoformat() if hasattr(payment[5], 'isoformat') else str(payment[5])
    
    return {
        "user_id": payment[0],
        "status": payment[1],
        "payment_id": payment[2],
        "payment_amount": payment[3],
        "payment_date": payment_date,
        "expiry_date": expiry_date
    }

# Admin - Manually Update User's Payment Status
@router.put("/payment-status/{user_id}")
def update_user_payment_status(
    user_id: int, 
    status: str = "premium", 
    token: str = Depends(is_admin)
):
    """Admin manually updates a user's payment status"""
    
    if status not in ["free", "premium"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'free' or 'premium'")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate expiry date if status is premium
        expiry_date = None
        if status == "premium":
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=365)
        
        # Check if payment record exists
        cursor.execute("SELECT id FROM payment_status WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing record
            if status == "premium":
                cursor.execute("""
                    UPDATE payment_status 
                    SET status = %s, 
                        payment_date = CURRENT_TIMESTAMP,
                        expiry_date = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (status, expiry_date, user_id))
            else:
                cursor.execute("""
                    UPDATE payment_status 
                    SET status = %s, 
                        expiry_date = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (status, user_id))
        else:
            # Create new record
            if status == "premium":
                cursor.execute("""
                    INSERT INTO payment_status 
                    (user_id, status, payment_date, expiry_date)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                """, (user_id, status, expiry_date))
            else:
                cursor.execute("""
                    INSERT INTO payment_status 
                    (user_id, status)
                    VALUES (%s, %s)
                """, (user_id, status))
        
        conn.commit()
        
        return {
            "message": f"User {user_id} payment status updated to {status}",
            "status": status
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating payment status: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# Admin - Suspend or Activate a User
@router.put("/users/{user_id}/status")
def update_user_status(user_id: int, status: str, token: str = Depends(is_admin)):
    """Admin suspends or activates a user."""
    valid_statuses = ["active", "suspended"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value. Use 'active' or 'suspended'.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the user exists
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user status with string value
    cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
    conn.commit()
    
    cursor.close()
    conn.close()

    return {"message": f"User {user_id} updated to {status}"}

# Admin - Delete a User
@router.delete("/users/{user_id}")
def delete_user(user_id: int, token: str = Depends(is_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
    deleted_user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {user_id} deleted"}

# Admin - Change OpenAI Model
@router.put("/settings/model")
def update_model(model_name: str, token: str = Depends(is_admin)):
    """Admin updates the chatbot model."""
    valid_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
    if model_name not in valid_models:
        raise HTTPException(status_code=400, detail="Invalid model name")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure model exists before updating
    cursor.execute("""
        INSERT INTO chatbot_settings (id, model_name) 
        VALUES (1, %s)
        ON CONFLICT (id) 
        DO UPDATE SET model_name = EXCLUDED.model_name;
    """, (model_name,))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"Chatbot model updated to {model_name}"}

# Admin - Get Current Chatbot Model
@router.get("/settings/model")
def get_current_model(token: str = Depends(is_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT model_name FROM chatbot_settings WHERE id = 1")
    model = cursor.fetchone()
    cursor.close()
    conn.close()

    return {"model": model[0] if model else "gpt-4o"}

# Admin - Delete Chat History for a User
@router.delete("/chat-history/{user_id}")
def delete_user_chat_history(
    user_id: int,
    token: str = Depends(is_admin)
):
    """
    Admin endpoint to delete all chat history for a specific user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete chat history
        cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
        conn.commit()
        
        deleted_count = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        return {"message": f"Successfully deleted {deleted_count} chat messages for user {user_id}"}
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error deleting chat history: {str(e)}")
    

# Admin - View Chat History for a Specific User
@router.get("/chat-history/{user_id}", response_model=List[UserChatHistoryResponse])
def get_user_chat_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    token: str = Depends(is_admin)
):
    """
    Admin endpoint to view chat history for a specific user.
    
    Parameters:
    - user_id: The ID of the user whose chat history to retrieve
    - limit: Maximum number of records to return (default 50, max 500)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First check if the user exists
    cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get chat history for this user
    cursor.execute(
        """
        SELECT id, message, response, timestamp 
        FROM chat_history 
        WHERE user_id = %s 
        ORDER BY timestamp DESC 
        LIMIT %s
        """,
        (user_id, limit)
    )
    chat_history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Format results without using isinstance
    results = []
    for chat in chat_history:
        # Handle timestamp safely without isinstance
        timestamp_str = ""
        if chat[3]:
            try:
                if hasattr(chat[3], 'isoformat'):
                    timestamp_str = chat[3].isoformat()
                else:
                    timestamp_str = str(chat[3])
            except:
                timestamp_str = str(chat[3])
                
        results.append({
            "id": chat[0],
            "message": chat[1],
            "response": chat[2],
            "timestamp": timestamp_str
        })
    
    return results