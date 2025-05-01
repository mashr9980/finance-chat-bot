from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db_connection
from app.routers.admin import is_admin

router = APIRouter(tags=["Professions"])

# Schema for profession
class ProfessionCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProfessionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

# Admin - Add new profession
@router.post("/", response_model=ProfessionResponse)
def add_profession(profession: ProfessionCreate, token: str = Depends(is_admin)):
    """Admin adds a new profession category."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if profession already exists
        cursor.execute("SELECT id FROM professions WHERE name = %s", (profession.name,))
        existing = cursor.fetchone()
        
        if existing:
            raise HTTPException(status_code=400, detail="Profession with this name already exists")
        
        # Insert the new profession
        cursor.execute(
            "INSERT INTO professions (name, description) VALUES (%s, %s) RETURNING id, name, description",
            (profession.name, profession.description)
        )
        
        new_profession = cursor.fetchone()
        conn.commit()
        
        return {
            "id": new_profession[0],
            "name": new_profession[1],
            "description": new_profession[2]
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# Get all professions - Available to all users
@router.get("/", response_model=List[ProfessionResponse])
def get_all_professions():
    """Get list of all available professions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, description FROM professions ORDER BY name")
    professions = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return [{"id": p[0], "name": p[1], "description": p[2]} for p in professions]

# Admin - Update a profession
@router.put("/{profession_id}", response_model=ProfessionResponse)
def update_profession(profession_id: int, profession: ProfessionCreate, token: str = Depends(is_admin)):
    """Admin updates an existing profession."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if profession exists
        cursor.execute("SELECT id FROM professions WHERE id = %s", (profession_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Profession not found")
        
        # Update the profession
        cursor.execute(
            "UPDATE professions SET name = %s, description = %s WHERE id = %s RETURNING id, name, description",
            (profession.name, profession.description, profession_id)
        )
        
        updated = cursor.fetchone()
        conn.commit()
        
        return {
            "id": updated[0],
            "name": updated[1],
            "description": updated[2]
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# Admin - Delete a profession
@router.delete("/{profession_id}")
def delete_profession(profession_id: int, token: str = Depends(is_admin)):
    """Admin deletes a profession."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if profession exists
        cursor.execute("SELECT id FROM professions WHERE id = %s", (profession_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Profession not found")
        
        # Delete the profession
        cursor.execute("DELETE FROM professions WHERE id = %s", (profession_id,))
        conn.commit()
        
        return {"message": f"Profession with ID {profession_id} deleted successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()