from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth import decode_access_token
from app.database import get_db_connection
from typing import Optional

router = APIRouter(tags=["User Profession"])

class UserProfessionResponse(BaseModel):
    user_id: int
    profession_id: int
    profession_name: str

@router.get("/current", response_model=Optional[UserProfessionResponse])
def get_current_profession(token: str):
    """Get the user's currently selected profession"""
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user["user_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT up.user_id, up.profession_id, p.name
            FROM user_profession up
            JOIN professions p ON up.profession_id = p.id
            WHERE up.user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            return None
        
        return {
            "user_id": result[0],
            "profession_id": result[1],
            "profession_name": result[2]
        }
    
    finally:
        cursor.close()
        conn.close()