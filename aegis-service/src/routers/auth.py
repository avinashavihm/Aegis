from fastapi import APIRouter, HTTPException, status, Depends, Body
from src.auth import hash_password, verify_password, create_access_token
from src.database import get_db_connection
from src.dependencies import get_current_user
from datetime import timedelta
from src.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: dict = Body(...)):
    """Register a new user."""
    # Validate required fields
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    
    if not all([username, email, password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username, email, and password are required"
        )
    
    full_name = data.get("full_name")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if username or email already exists
                cur.execute(
                    "SELECT id FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username or email already registered"
                    )
                
                # Create user
                cur.execute(
                    """INSERT INTO users (username, email, password_hash, full_name) 
                       VALUES (%s, %s, %s, %s) 
                       RETURNING id, username, email, full_name, created_at""",
                    (username, email, hash_password(password), full_name)
                )
                user_data = cur.fetchone()
        
        return dict(user_data)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "connection" in error_msg.lower() or "operational" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection failed. Please check if the database service is running."
            )
        if "row-level security" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.post("/login")
async def login(credentials: dict = Body(...)):
    """Login and receive JWT token."""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not all([username, password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required"
        )
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, password_hash FROM users WHERE username = %s",
                    (username,)
                )
                result = cur.fetchone()
        
        if not result or not verify_password(password, result["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(result["id"])},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "connection" in error_msg.lower() or "operational" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection failed. Please check if the database service is running."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user
