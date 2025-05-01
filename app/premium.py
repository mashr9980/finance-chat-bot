from fastapi import HTTPException, Depends
from app.auth import decode_access_token
from app.database import get_db_connection
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_premium_access(token: str):
    """
    Middleware to verify if a user has premium access.
    Returns the user if they have premium access, otherwise raises an exception.
    """
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")
    
    user_id = user["user_id"]
    
    # Check if user is admin - admins always have premium access
    if user.get("role") == "admin":
        return user
    
    # Check if user has premium access
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT status, expiry_date
            FROM payment_status
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        # If no payment status record or status is free
        if not result or result[0] != "premium":
            raise HTTPException(
                status_code=403, 
                detail="Premium access required. Please upgrade your account to access this feature."
            )
        
        # Check if premium has expired
        if result[1] and result[1] < datetime.now():
            # Update status to free since it's expired
            cursor.execute("""
                UPDATE payment_status
                SET status = 'free'
                WHERE user_id = %s
            """, (user_id,))
            conn.commit()
            
            raise HTTPException(
                status_code=403, 
                detail="Your premium subscription has expired. Please renew to access this feature."
            )
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Error verifying premium access: {str(e)}")
        raise HTTPException(status_code=500, detail="Error verifying premium status")
        
    finally:
        cursor.close()
        conn.close()

def verify_premium_or_pass(token: str):
    """
    Middleware that checks premium status but doesn't block access.
    Returns a tuple with (user, is_premium) where is_premium is a boolean.
    """
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")
    
    user_id = user["user_id"]
    
    # Admin always has premium access
    if user.get("role") == "admin":
        return (user, True)
    
    # Check premium status
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT status, expiry_date
            FROM payment_status
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        # If no payment status record or status is free
        if not result or result[0] != "premium":
            return (user, False)
        
        # Check if premium has expired
        if result[1] and result[1] < datetime.now():
            # Update status to free since it's expired
            cursor.execute("""
                UPDATE payment_status
                SET status = 'free'
                WHERE user_id = %s
            """, (user_id,))
            conn.commit()
            return (user, False)
        
        # User has valid premium status
        return (user, True)
        
    except Exception as e:
        logger.error(f"Error checking premium status: {str(e)}")
        return (user, False)
        
    finally:
        cursor.close()
        conn.close()