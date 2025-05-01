import os
import stripe
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db_connection
from app.auth import decode_access_token

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") 

router = APIRouter(tags=["Payment"])

# Request Model for Payment
class PaymentRequest(BaseModel):
    amount: int  
    currency: str = "usd"
    description: str
    email: str

class PaymentStatusResponse(BaseModel):
    status: str
    expiry_date: str = None
    payment_date: str = None

# Create Stripe Checkout Session
@router.post("/create-checkout-session")
def create_checkout_session(payment: PaymentRequest, token: str):
    try:
        # Validate user token
        user = decode_access_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")
        
        user_id = user["user_id"]
        
        # Create metadata to track the user
        metadata = {
            "user_id": str(user_id),
            "subscription_type": "premium"
        }
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": payment.currency,
                    "product_data": {
                        "name": payment.description,
                    },
                    "unit_amount": payment.amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://127.0.0.1:8800/payment/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://127.0.0.1:8800/payment/cancel",
            customer_email=payment.email,
            metadata=metadata,
        )
        
        # Store pending payment in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already has a payment record
        cursor.execute("SELECT id FROM payment_status WHERE user_id = %s", (user_id,))
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            cursor.execute("""
                UPDATE payment_status 
                SET payment_id = %s, payment_amount = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = %s
            """, (checkout_session.id, payment.amount, user_id))
        else:
            # Create new record
            cursor.execute("""
                INSERT INTO payment_status (user_id, status, payment_id, payment_amount)
                VALUES (%s, 'free', %s, %s)
            """, (user_id, checkout_session.id, payment.amount))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Created checkout session {checkout_session.id} for user {user_id}")
        
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Update payment status on success
def update_payment_status(session_id: str):
    try:
        # Retrieve session details from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != "paid":
            logger.warning(f"Session {session_id} payment status is not 'paid': {session.payment_status}")
            return False
        
        # Get user_id from metadata
        user_id = session.metadata.get("user_id")
        if not user_id:
            logger.error(f"No user_id found in session {session_id} metadata")
            return False
        
        # Calculate expiry date (365 days from now)
        expiry_date = datetime.now() + timedelta(days=365)
        
        # Update payment status in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE payment_status 
            SET status = 'premium', 
                payment_date = CURRENT_TIMESTAMP,
                expiry_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND payment_id = %s
            RETURNING id
        """, (expiry_date, user_id, session_id))
        
        updated = cursor.fetchone()
        
        if not updated:
            # If no record was updated, create a new one
            cursor.execute("""
                INSERT INTO payment_status 
                (user_id, status, payment_id, payment_amount, payment_date, expiry_date)
                VALUES (%s, 'premium', %s, %s, CURRENT_TIMESTAMP, %s)
            """, (user_id, session_id, session.amount_total, expiry_date))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully updated payment status for user {user_id} to premium")
        return True
    
    except Exception as e:
        logger.error(f"Error updating payment status: {str(e)}")
        return False

# Success Page that updates payment status
@router.get("/success")
async def payment_success(session_id: str, background_tasks: BackgroundTasks):
    # Process payment update in background to avoid blocking
    background_tasks.add_task(update_payment_status, session_id)
    
    return {
        "message": "Payment Successful! Your account has been upgraded to premium.",
        "session_id": session_id
    }

# Cancel Page
@router.get("/cancel")
def payment_cancel():
    return {"message": "Payment Cancelled"}

# Get payment status for current user
@router.get("/status", response_model=PaymentStatusResponse)
def get_payment_status(token: str):
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user["user_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT status, payment_date, expiry_date 
        FROM payment_status 
        WHERE user_id = %s
    """, (user_id,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not result:
        return {"status": "free"}
    
    # Format dates
    payment_date = result[1].isoformat() if result[1] else None
    expiry_date = result[2].isoformat() if result[2] else None
    
    return {
        "status": result[0],
        "payment_date": payment_date,
        "expiry_date": expiry_date
    }

# Webhook to Handle Stripe Events (e.g., Payment Success)
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle payment success
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Get user ID from metadata
        user_id = session.metadata.get("user_id")
        if not user_id:
            logger.error("No user_id found in session metadata")
            return {"message": "Error: No user ID in metadata"}
        
        # Update payment status
        success = update_payment_status(session.id)
        
        if success:
            logger.info(f"Webhook: Payment successful for user {user_id}")
            return {"message": f"Payment successfully processed for user {user_id}"}
        else:
            logger.error(f"Webhook: Payment processing failed for user {user_id}")
            return {"message": f"Error processing payment for user {user_id}"}

    return {"message": "Webhook received"}