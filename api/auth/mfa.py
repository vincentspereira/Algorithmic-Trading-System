"""
Multi-Factor Authentication (MFA) Service for Algorithmic Trading System

This module provides TOTP-based MFA functionality integrated with the OAuth2 authentication system.
"""

import logging
import secrets
import qrcode
import io
import base64
from typing import Dict, Optional, Tuple
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pyotp

from .oauth2 import auth_service, authenticate_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mfa", tags=["mfa"])

class MFASetupRequest(BaseModel):
    """MFA setup request model"""
    user_id: str

class MFASetupResponse(BaseModel):
    """MFA setup response model"""
    secret: str
    qr_code: str  # Base64 encoded QR code image
    provisioning_uri: str

class MFAVerifyRequest(BaseModel):
    """MFA verification request model"""
    totp_code: str

class MFAVerifyResponse(BaseModel):
    """MFA verification response model"""
    success: bool
    message: str

class MFABackupCodeRequest(BaseModel):
    """MFA backup code request model"""
    count: int = 10

class MFABackupCodeResponse(BaseModel):
    """MFA backup code response model"""
    backup_codes: list[str]

# In production, store this in a database or Redis
mfa_secrets: Dict[str, str] = {}
backup_codes: Dict[str, set] = {}

def generate_secret() -> str:
    """Generate a new TOTP secret"""
    return pyotp.random_base32()

def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes"""
    codes = []
    for _ in range(count):
        code = ''.join(secrets.choice('0123456789') for _ in range(8))
        codes.append(code)
    return codes

def generate_qr_code(provisioning_uri: str) -> str:
    """Generate QR code for TOTP setup"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 string
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: MFASetupRequest,
    user: dict = Depends(authenticate_user)
):
    """
    Setup MFA for a user.
    Returns the secret and QR code for authenticator app setup.
    """
    try:
        # Check if user is authorized to setup MFA for this user
        if user["user_id"] != request.user_id and "user_manage" not in user["permissions"]:
            raise HTTPException(status_code=403, detail="Not authorized to setup MFA for this user")
        
        # Generate new secret
        secret = generate_secret()
        mfa_secrets[request.user_id] = secret
        
        # Generate provisioning URI
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user["email"],
            issuer_name="Algorithmic Trading System"
        )
        
        # Generate QR code
        qr_code = generate_qr_code(provisioning_uri)
        
        logger.info(f"MFA setup initiated for user {request.user_id}")
        
        return MFASetupResponse(
            secret=secret,
            qr_code=qr_code,
            provisioning_uri=provisioning_uri
        )
        
    except Exception as e:
        logger.error(f"Failed to setup MFA for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup MFA")

@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    user: dict = Depends(authenticate_user)
):
    """
    Verify TOTP code for MFA.
    Marks the session as MFA verified if successful.
    """
    try:
        user_id = user["user_id"]
        secret = mfa_secrets.get(user_id)
        
        if not secret:
            raise HTTPException(status_code=400, detail="MFA not setup for this user")
        
        # Verify TOTP code
        totp = pyotp.TOTP(secret)
        if totp.verify(request.totp_code, valid_window=1):
            # Mark session as MFA verified
            auth_service.mfa_service.mark_mfa_verified(user["session_id"])
            logger.info(f"MFA verification successful for user {user_id}")
            return MFAVerifyResponse(success=True, message="MFA verification successful")
        else:
            logger.warning(f"Invalid MFA code for user {user_id}")
            return MFAVerifyResponse(success=False, message="Invalid MFA code")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify MFA for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify MFA")

@router.post("/backup-codes", response_model=MFABackupCodeResponse)
async def generate_backup_codes_endpoint(
    request: MFABackupCodeRequest,
    user: dict = Depends(authenticate_user)
):
    """
    Generate backup codes for MFA.
    These can be used when the authenticator app is unavailable.
    """
    try:
        user_id = user["user_id"]
        secret = mfa_secrets.get(user_id)
        
        if not secret:
            raise HTTPException(status_code=400, detail="MFA not setup for this user")
        
        # Generate backup codes
        codes = generate_backup_codes(request.count)
        backup_codes[user_id] = set(codes)
        
        logger.info(f"Generated {len(codes)} backup codes for user {user_id}")
        
        return MFABackupCodeResponse(backup_codes=codes)
        
    except Exception as e:
        logger.error(f"Failed to generate backup codes for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate backup codes")

@router.post("/verify-backup", response_model=MFAVerifyResponse)
async def verify_backup_code(
    request: MFAVerifyRequest,
    user: dict = Depends(authenticate_user)
):
    """
    Verify backup code for MFA.
    """
    try:
        user_id = user["user_id"]
        user_backup_codes = backup_codes.get(user_id, set())
        
        if not user_backup_codes:
            raise HTTPException(status_code=400, detail="No backup codes generated for this user")
        
        # Check if code is valid
        if request.totp_code in user_backup_codes:
            # Remove used backup code
            user_backup_codes.remove(request.totp_code)
            backup_codes[user_id] = user_backup_codes
            
            # Mark session as MFA verified
            auth_service.mfa_service.mark_mfa_verified(user["session_id"])
            
            logger.info(f"Backup code verification successful for user {user_id}")
            return MFAVerifyResponse(success=True, message="Backup code verification successful")
        else:
            logger.warning(f"Invalid backup code for user {user_id}")
            return MFAVerifyResponse(success=False, message="Invalid backup code")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify backup code for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify backup code")

@router.delete("/disable")
async def disable_mfa(user: dict = Depends(authenticate_user)):
    """
    Disable MFA for the current user.
    """
    try:
        user_id = user["user_id"]
        
        # Remove MFA secret and backup codes
        if user_id in mfa_secrets:
            del mfa_secrets[user_id]
        
        if user_id in backup_codes:
            del backup_codes[user_id]
        
        logger.info(f"MFA disabled for user {user_id}")
        
        return {"success": True, "message": "MFA disabled successfully"}
        
    except Exception as e:
        logger.error(f"Failed to disable MFA for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable MFA")