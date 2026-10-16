import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Form, Depends, Request
from app.utils.auth import get_current_user
from app.database import db
from app.models.user import create_user_document
from app.schemas.user import (
    UserCreate,
    UserResponse,
    TokenResponse,
    ProfileUpdateRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SendVerificationRequest,
    VerifyEmailRequest,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    validate_password_strength,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.email_service import send_email, send_verification_email, is_email_configured
from app.services.audit import log_audit_event

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/")
def auth_status():
    return {
        "message": "Authentication module is ready"
    }


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def signup(user: UserCreate, request: Request):
    existing_user = db.users.find_one({
        "email": str(user.email).lower()
    })

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Authoritative password strength validation
    is_strong, reason = validate_password_strength(user.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason or "Password does not meet complexity requirements."
        )

    password_hash = hash_password(user.password)

    user_document = create_user_document(
        name=user.name,
        email=str(user.email).lower(),
        password_hash=password_hash
    )

    result = db.users.insert_one(user_document)
    user_id = str(result.inserted_id)

    log_audit_event(
        user_id=user_id,
        email=str(user.email).lower(),
        action="USER_SIGNUP",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "id": user_id,
        "name": user.name,
        "email": str(user.email).lower(),
        "is_verified": False,
        "is_active": True,
        "role": "user"
    }


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    email = username.strip().lower()

    existing_user = db.users.find_one({
        "email": email
    })

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if user account is deactivated
    if existing_user.get("is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator."
        )

    stored_hash = existing_user.get("password_hash", "")

    try:
        password_valid = (
            bool(stored_hash)
            and verify_password(password, stored_hash)
        )
    except (ValueError, TypeError):
        password_valid = False

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = str(existing_user["_id"])
    access_token = create_access_token(
        user_id=user_id,
        email=existing_user["email"],
        role=existing_user.get("role", "user")
    )

    log_audit_event(
        user_id=user_id,
        email=existing_user["email"],
        action="USER_LOGIN",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post(
    "/admin-login",
    response_model=TokenResponse
)
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Dedicated Administrator Sign-In endpoint.
    
    Verifies credentials and strictly enforces that the user has the 'admin' role
    in the database. If a regular user attempts login here, access is denied with
    HTTP 403 Forbidden and no token is issued.
    """
    email = username.strip().lower()

    existing_user = db.users.find_one({
        "email": email
    })

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if account is deactivated
    if existing_user.get("is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact a system administrator."
        )

    stored_hash = existing_user.get("password_hash", "")

    try:
        password_valid = (
            bool(stored_hash)
            and verify_password(password, stored_hash)
        )
    except (ValueError, TypeError):
        password_valid = False

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # STRICT ROLE AUTHORIZATION CHECK: Must be admin
    if existing_user.get("role") != "admin":
        log_audit_event(
            user_id=str(existing_user["_id"]),
            email=existing_user["email"],
            action="ADMIN_LOGIN_DENIED_NON_ADMIN",
            resource_type="auth",
            resource_id=str(existing_user["_id"]),
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrator privileges required."
        )

    user_id = str(existing_user["_id"])
    access_token = create_access_token(
        user_id=user_id,
        email=existing_user["email"],
        role="admin"
    )

    log_audit_event(
        user_id=user_id,
        email=existing_user["email"],
        action="ADMIN_LOGIN_SUCCESS",
        resource_type="auth",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "is_verified": current_user.get("is_verified", False),
        "is_active": current_user.get("is_active", True),
        "role": current_user.get("role", "user"),
        "created_at": current_user.get("created_at"),
    }


@router.put("/profile")
def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"name": body.name, "updated_at": datetime.now(timezone.utc)}}
    )
    return {
        "message": "Profile updated successfully",
        "name": body.name
    }


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    stored_hash = current_user.get("password_hash", "")
    try:
        valid = bool(stored_hash) and verify_password(body.old_password, stored_hash)
    except Exception:
        valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Authoritative password strength validation
    is_strong, reason = validate_password_strength(body.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason or "New password does not meet security requirements."
        )

    new_hash = hash_password(body.new_password)
    db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "password_hash": new_hash,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    log_audit_event(
        user_id=str(current_user["_id"]),
        email=current_user["email"],
        action="PASSWORD_CHANGED",
        resource_type="user",
        resource_id=str(current_user["_id"]),
    )

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    email = str(body.email).strip().lower()
    user = db.users.find_one({"email": email})

    # Always return a neutral success message to prevent user enumeration
    if not user:
        return {
            "message": "If an account exists with this email, password reset instructions have been sent."
        }

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_token": token,
                "reset_token_expires": expires,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    # Attempt to send email via SMTP if configured
    email_sent, email_err = send_email(
        to_email=email,
        subject="Password Reset - AI Codebase Assistant",
        html_content=f"<p>Use token <code>{token}</code> to reset your password. Valid for 15 minutes.</p>",
        text_content=f"Password reset token: {token} (valid for 15 minutes)"
    )

    log_audit_event(
        user_id=str(user["_id"]),
        email=email,
        action="FORGOT_PASSWORD_REQUESTED",
        resource_type="user",
        resource_id=str(user["_id"]),
        details={"email_sent": email_sent}
    )

    resp = {
        "message": "If an account exists with this email, password reset instructions have been sent."
    }
    # For local/testing environments without external SMTP, return the token for automation
    if not email_sent:
        resp["dev_token"] = token

    return resp


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    user = db.users.find_one({"reset_token": body.token})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    expires = user.get("reset_token_expires")
    if not expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Convert naive to timezone-aware if stored naive
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Authoritative password strength validation
    is_strong, reason = validate_password_strength(body.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason or "New password does not meet security requirements."
        )

    new_hash = hash_password(body.new_password)
    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": new_hash,
                "updated_at": datetime.now(timezone.utc),
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expires": ""
            }
        }
    )

    log_audit_event(
        user_id=str(user["_id"]),
        email=user["email"],
        action="PASSWORD_RESET_SUCCESS",
        resource_type="user",
        resource_id=str(user["_id"])
    )

    return {"message": "Password has been successfully reset. You may now log in."}


def _hash_otp(otp: str, user_id: str) -> str:
    """Generate SHA-256 hash of OTP salted with user_id to prevent plaintext exposure."""
    return hashlib.sha256(f"{otp.strip()}:{user_id}".encode()).hexdigest()


@router.post("/send-verification")
def send_verification(
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("is_verified", False):
        return {"message": "Email is already verified."}

    now = datetime.now(timezone.utc)
    cooldown = current_user.get("resend_cooldown_expires")
    if cooldown:
        if cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if now < cooldown:
            remaining = int((cooldown - now).total_seconds())
            if remaining > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining} seconds before requesting another verification code."
                )

    # Check honest email provider configuration
    if not is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email delivery service is not configured. Please configure SMTP_HOST, "
                "SMTP_PORT, SMTP_USER, and SMTP_PASS in backend/.env to receive verification emails."
            )
        )

    otp = f"{secrets.randbelow(900000) + 100000}"
    user_id = str(current_user["_id"])
    otp_hash = _hash_otp(otp, user_id)
    expires = now + timedelta(minutes=10)
    next_cooldown = now + timedelta(seconds=60)

    sent, err_msg = send_verification_email(current_user["email"], otp)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email delivery failed: {err_msg}. Please check your SMTP provider configuration."
        )

    db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "verification_otp_hash": otp_hash,
                "verification_expires": expires,
                "resend_cooldown_expires": next_cooldown,
                "verification_attempts": 0,
                "updated_at": now
            },
            "$unset": {
                "verification_otp": ""
            }
        }
    )

    log_audit_event(
        user_id=user_id,
        email=current_user["email"],
        action="VERIFICATION_EMAIL_SENT",
        resource_type="user",
        resource_id=user_id
    )

    return {
        "message": f"Verification code sent to {current_user['email']}.",
        "cooldown_seconds": 60
    }


@router.post("/verify-email")
def verify_email(
    body: VerifyEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    stored_hash = current_user.get("verification_otp_hash")
    expires = current_user.get("verification_expires")
    attempts = current_user.get("verification_attempts", 0)

    if not stored_hash and not current_user.get("verification_otp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification request found. Please request a new verification code."
        )

    if expires:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired (valid for 10 minutes). Please request a new code."
            )

    if attempts >= 5:
        db.users.update_one(
            {"_id": current_user["_id"]},
            {
                "$unset": {
                    "verification_otp_hash": "",
                    "verification_expires": "",
                    "verification_otp": ""
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed verification attempts. This code has been invalidated. Please request a new one."
        )

    user_id = str(current_user["_id"])
    input_hash = _hash_otp(body.otp, user_id)

    is_match = False
    if stored_hash and input_hash == stored_hash:
        is_match = True
    elif current_user.get("verification_otp") == body.otp.strip():
        is_match = True

    if not is_match:
        new_attempts = attempts + 1
        remaining = 5 - new_attempts
        db.users.update_one(
            {"_id": current_user["_id"]},
            {"$set": {"verification_attempts": new_attempts}}
        )
        if remaining <= 0:
            db.users.update_one(
                {"_id": current_user["_id"]},
                {
                    "$unset": {
                        "verification_otp_hash": "",
                        "verification_expires": "",
                        "verification_otp": ""
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed verification attempts. This code has been invalidated. Please request a new one."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "is_verified": True,
                "updated_at": datetime.now(timezone.utc)
            },
            "$unset": {
                "verification_otp_hash": "",
                "verification_otp": "",
                "verification_expires": "",
                "resend_cooldown_expires": "",
                "verification_attempts": ""
            }
        }
    )

    log_audit_event(
        user_id=user_id,
        email=current_user["email"],
        action="EMAIL_VERIFIED",
        resource_type="user",
        resource_id=user_id
    )

    return {
        "message": "Email verified successfully.",
        "is_verified": True
    }