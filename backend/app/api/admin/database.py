"""Database Explorer API Routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db

router = APIRouter(tags=["Admin - Database"])


@router.get("/tables")
async def list_tables(db: Session = Depends(get_db)):
    """List all tables with row counts."""
    inspector = inspect(db.get_bind())
    tables = []
    
    for table_name in inspector.get_table_names():
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
        except Exception:
            count = 0
            
        tables.append({
            "name": table_name,
            "row_count": count
        })
    
    return sorted(tables, key=lambda x: x["name"])


@router.get("/tables/{table_name}")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get table data with pagination."""
    inspector = inspect(db.get_bind())
    
    # Validate table exists
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Get columns info
    columns = []
    pk_columns = [pk.name for pk in inspector.get_pk_constraint(table_name).get('constrained_columns', [])]
    
    for col in inspector.get_columns(table_name):
        columns.append({
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
            "primary_key": col["name"] in pk_columns
        })
    
    # Get total count
    count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    total = count_result.scalar()
    
    # Get paginated data
    offset = (page - 1) * per_page
    result = db.execute(text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"), 
                        {"limit": per_page, "offset": offset})
    rows = [dict(row._mapping) for row in result]
    
    return {
        "table": table_name,
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.post("/query")
async def execute_query(
    data: dict,
    db: Session = Depends(get_db)
):
    """Execute a read-only SQL query."""
    query = data.get("query", "").strip()
    
    # Security: Only allow SELECT queries
    if not query.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    # Block dangerous keywords
    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "GRANT"]
    query_upper = query.upper()
    for keyword in dangerous:
        if keyword in query_upper:
            raise HTTPException(status_code=400, detail=f"Keyword {keyword} is not allowed")
    
    try:
        result = db.execute(text(query))
        rows = [dict(row._mapping) for row in result]
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
