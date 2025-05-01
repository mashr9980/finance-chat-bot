from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.auth import decode_access_token, ADMIN_EMAIL
from app.database import get_db_connection

from app.routers.admin import is_admin

router = APIRouter(tags=["Profession Prompts"])

# Schema for profession prompts - simplified with a single text prompt field
class ProfessionPromptResponse(BaseModel):
    id: int
    profession_id: int
    profession_name: str
    system_prompt: str  # This will be the full text prompt

class ProfessionWithPrompt(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str  # Single text field for the prompt

class ProfessionPromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: str  # Single text field for the prompt

# Admin - Create profession with prompt together
@router.post("/profession-with-prompt", response_model=ProfessionPromptResponse)
def create_profession_with_prompt(data: ProfessionWithPrompt, token: str = Depends(is_admin)):
    """Admin creates a new profession and its prompt in a single operation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        cursor.execute("BEGIN")
        
        # First, create the profession
        cursor.execute(
            "INSERT INTO professions (name, description) VALUES (%s, %s) RETURNING id, name",
            (data.name, data.description)
        )
        
        profession = cursor.fetchone()
        profession_id = profession[0]
        profession_name = profession[1]
        
        # Create the prompt for this profession - now just a text field
        cursor.execute("""
            INSERT INTO profession_prompts (profession_id, system_prompt)
            VALUES (%s, %s)
            RETURNING id
        """, (profession_id, data.system_prompt))
        
        prompt_id = cursor.fetchone()[0]
        
        # Commit the transaction
        cursor.execute("COMMIT")
        
        return {
            "id": prompt_id,
            "profession_id": profession_id,
            "profession_name": profession_name,
            "system_prompt": data.system_prompt
        }
    
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# Admin - Update profession with prompt together
@router.put("/{profession_id}", response_model=ProfessionPromptResponse)
def update_profession_with_prompt(profession_id: int, data: ProfessionPromptUpdate, token: str = Depends(is_admin)):
    """Admin updates a profession and its prompt in a single operation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        cursor.execute("BEGIN")
        
        # Check if profession exists
        cursor.execute("SELECT id FROM professions WHERE id = %s", (profession_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Profession not found")
        
        # Update profession if name or description is provided
        if data.name or data.description:
            update_fields = []
            update_values = []
            
            if data.name:
                update_fields.append("name = %s")
                update_values.append(data.name)
            
            if data.description:
                update_fields.append("description = %s")
                update_values.append(data.description)
            
            if update_fields:
                update_sql = f"UPDATE professions SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(update_sql, update_values + [profession_id])
        
        # Check if prompt exists for this profession
        cursor.execute("SELECT id FROM profession_prompts WHERE profession_id = %s", (profession_id,))
        prompt_exists = cursor.fetchone()
        
        if prompt_exists:
            # Update existing prompt
            cursor.execute("""
                UPDATE profession_prompts
                SET system_prompt = %s, updated_at = CURRENT_TIMESTAMP
                WHERE profession_id = %s
                RETURNING id
            """, (data.system_prompt, profession_id))
        else:
            # Create new prompt
            cursor.execute("""
                INSERT INTO profession_prompts (profession_id, system_prompt)
                VALUES (%s, %s)
                RETURNING id
            """, (profession_id, data.system_prompt))
        
        prompt_id = cursor.fetchone()[0]
        
        # Get updated profession name
        cursor.execute("SELECT name FROM professions WHERE id = %s", (profession_id,))
        profession_name = cursor.fetchone()[0]
        
        # Commit the transaction
        cursor.execute("COMMIT")
        
        return {
            "id": prompt_id,
            "profession_id": profession_id,
            "profession_name": profession_name,
            "system_prompt": data.system_prompt
        }
    
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# Get prompt for a specific profession
@router.get("/{profession_id}", response_model=ProfessionPromptResponse)
def get_profession_prompt(profession_id: int):
    """Get the prompt for a specific profession."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT pp.id, pp.profession_id, p.name, pp.system_prompt
            FROM profession_prompts pp
            JOIN professions p ON pp.profession_id = p.id
            WHERE pp.profession_id = %s
        """, (profession_id,))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Prompt not found for this profession")
        
        return {
            "id": result[0],
            "profession_id": result[1],
            "profession_name": result[2],
            "system_prompt": result[3]
        }
    
    finally:
        cursor.close()
        conn.close()

# Admin - Get all profession prompts
@router.get("/", response_model=List[ProfessionPromptResponse])
def get_all_profession_prompts(token: str = Depends(is_admin)):
    """Admin gets all profession prompts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT pp.id, pp.profession_id, p.name, pp.system_prompt
            FROM profession_prompts pp
            JOIN professions p ON pp.profession_id = p.id
            ORDER BY p.name
        """)
        
        results = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "profession_id": row[1],
                "profession_name": row[2],
                "system_prompt": row[3]
            }
            for row in results
        ]
    
    finally:
        cursor.close()
        conn.close()

# Admin - Delete a profession and its prompt
@router.delete("/profession/{profession_id}")
def delete_profession_with_prompt(profession_id: int, token: str = Depends(is_admin)):
    """Admin deletes a profession and its associated prompt."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        cursor.execute("BEGIN")
        
        # Check if profession exists
        cursor.execute("SELECT id FROM professions WHERE id = %s", (profession_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Profession not found")
        
        # Delete the prompt first (if exists)
        cursor.execute("DELETE FROM profession_prompts WHERE profession_id = %s", (profession_id,))
        
        # Then delete the profession
        cursor.execute("DELETE FROM professions WHERE id = %s", (profession_id,))
        
        # Commit the transaction
        cursor.execute("COMMIT")
        
        return {"message": f"Profession with ID {profession_id} and its associated prompt deleted successfully"}
    
    except Exception as e:
        cursor.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()