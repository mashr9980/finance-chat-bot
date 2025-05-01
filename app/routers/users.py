from fastapi import APIRouter, HTTPException, Body
from app.auth import hash_password, create_access_token, verify_password
from app.schemas import UserCreate, Token, UserLogin, GoogleAuthRequest
from app.database import get_db_connection
import psycopg2
import os
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter(tags=["Users"])

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@admin.com")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post("/signup", response_model=Token)
def signup(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if username or email already exists before inserting
    cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (user.username, user.email))
    existing_user = cursor.fetchone()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    # Check if the profession exists
    cursor.execute("SELECT id FROM professions WHERE id = %s", (user.profession_id,))
    profession = cursor.fetchone()
    
    if not profession:
        raise HTTPException(status_code=404, detail="Profession not found")

    hashed_password = hash_password(user.password)
    role = "business_owner"  # Default role is business_owner

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user.username, user.email, hashed_password, role, "active")
        )
        user_id = cursor.fetchone()[0]
        
        # Add the user's profession immediately
        cursor.execute("""
            INSERT INTO user_profession (user_id, profession_id)
            VALUES (%s, %s)
        """, (user_id, user.profession_id))
        
        conn.commit()
    
    except psycopg2.Error as e:
        conn.rollback()  
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

    token = create_access_token({"sub": user.email, "user_id": user_id, "role": role})
    return {"access_token": token, "token_type": "bearer", "role": role}

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    """User and Admin Login"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, email, password_hash, status, role FROM users WHERE email = %s", (user.email,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user_data or not verify_password(user.password, user_data[2]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Check if the user is suspended
    if user_data[3] == "suspended":
        raise HTTPException(status_code=403, detail="Your account is suspended. Contact admin.")

    # Get the user's role
    role = "admin" if user_data[1] == ADMIN_EMAIL else user_data[4]

    token = create_access_token({"sub": user_data[1], "user_id": user_data[0], "role": role})
    return {"access_token": token, "token_type": "bearer", "role": role}

@router.post("/login/google", response_model=Token)
async def login_with_google(google_data: GoogleAuthRequest = Body(...)):
    """Login or sign up with Google ID token"""
    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            google_data.id_token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        email = idinfo.get('email')
        name = idinfo.get('name', 'Google User')
        google_id = idinfo.get('sub')
        picture = idinfo.get('picture')
        
        if not email or not google_id:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if this Google account is already linked to a user
            cursor.execute(
                "SELECT u.id, u.email, u.role, u.status FROM google_auth ga JOIN users u ON ga.user_id = u.id WHERE ga.google_id = %s", 
                (google_id,)
            )
            google_user = cursor.fetchone()
            
            # Check if user exists with this email
            cursor.execute("SELECT id, email, role, status FROM users WHERE email = %s", (email,))
            email_user = cursor.fetchone()
            
            user_id = None
            is_new_user = False
            needs_profession = False
            
            if google_user:
                # User already exists with this Google ID
                if google_user[3] == "suspended":
                    raise HTTPException(status_code=403, detail="Your account is suspended")
                
                user_id = google_user[0]
                email = google_user[1]
                role = google_user[2]
                
            elif email_user:
                # User exists with this email but Google account not linked
                if email_user[3] == "suspended":
                    raise HTTPException(status_code=403, detail="Your account is suspended")
                
                user_id = email_user[0]
                email = email_user[1]
                role = email_user[2]
                
                # Link Google account to existing user
                cursor.execute(
                    "INSERT INTO google_auth (user_id, google_id, name, picture_url) VALUES (%s, %s, %s, %s)",
                    (user_id, google_id, name, picture)
                )
                conn.commit()
                
            else:
                # New user, create account
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (name, email, "GOOGLE_AUTH", "business_owner", "active")
                )
                user_id = cursor.fetchone()[0]
                role = "business_owner"
                
                # Create Google auth record
                cursor.execute(
                    "INSERT INTO google_auth (user_id, google_id, name, picture_url) VALUES (%s, %s, %s, %s)",
                    (user_id, google_id, name, picture)
                )
                conn.commit()
                is_new_user = True
                needs_profession = True
            
            # Check if user needs to select a profession
            if not is_new_user:
                cursor.execute("SELECT profession_id FROM user_profession WHERE user_id = %s", (user_id,))
                profession_data = cursor.fetchone()
                needs_profession = profession_data is None
            
            # Create access token
            token = create_access_token({"sub": email, "user_id": user_id, "role": role})
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": role,
                "is_new_user": is_new_user,
                "needs_profession": needs_profession
            }
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        finally:
            cursor.close()
            conn.close()
            
    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

@router.post("/set-profession/{user_id}")
async def set_user_profession(user_id: int, profession_id: int, token: str):
    """Set the profession for a user (used after Google login for new users)"""
    from app.auth import decode_access_token
    
    # Verify token belongs to this user or an admin
    user_data = decode_access_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if user_data["user_id"] != user_id and user_data["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to set profession for this user")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if profession exists
        cursor.execute("SELECT id FROM professions WHERE id = %s", (profession_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Profession not found")
        
        # Set profession
        cursor.execute("""
            INSERT INTO user_profession (user_id, profession_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET profession_id = EXCLUDED.profession_id, selected_at = CURRENT_TIMESTAMP
        """, (user_id, profession_id))
        
        conn.commit()
        return {"message": "Profession set successfully"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()