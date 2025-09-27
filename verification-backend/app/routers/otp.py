from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.schemas import APIResponse
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional

router = APIRouter(prefix="/api/otp", tags=["otp"])
logger = logging.getLogger(__name__)

# In-memory OTP storage (in production, use Redis or database)
otp_storage: Dict[str, Dict] = {}

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def is_valid_phone(phone: str) -> bool:
    """Validate Indian phone number format"""
    # Remove spaces and special characters
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Check if it's a valid Indian mobile number
    if len(clean_phone) == 10 and clean_phone.startswith(('6', '7', '8', '9')):
        return True
    elif len(clean_phone) == 13 and clean_phone.startswith('91') and clean_phone[2:3] in ['6', '7', '8', '9']:
        return True
    
    return False

@router.post("/send", response_model=APIResponse)
async def send_otp(
    phone_number: str = Form(...),
    user_address: str = Form(...),
    purpose: str = Form("verification"),  # verification, login, etc.
    db: Session = Depends(get_db)
):
    """
    Send OTP to phone number
    """
    try:
        logger.info(f"Sending OTP to {phone_number} for user: {user_address}")
        
        # Validate phone number
        if not is_valid_phone(phone_number):
            raise HTTPException(
                status_code=400,
                detail="Invalid Indian phone number format"
            )
        
        # Clean phone number
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"
        
        # Generate OTP
        otp_code = generate_otp()
        expiry_time = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
        
        # Store OTP (in production, use Redis with TTL)
        otp_key = f"{clean_phone}_{user_address}_{purpose}"
        otp_storage[otp_key] = {
            "otp": otp_code,
            "phone": clean_phone,
            "user_address": user_address,
            "purpose": purpose,
            "created_at": datetime.utcnow(),
            "expires_at": expiry_time,
            "attempts": 0,
            "verified": False
        }
        
        # TODO: Integrate with SMS service (Twilio, AWS SNS, etc.)
        # For now, we'll just log the OTP (remove in production)
        logger.info(f"OTP for {clean_phone}: {otp_code} (expires in 10 minutes)")
        
        # In production, send actual SMS
        # sms_sent = await send_sms(clean_phone, f"Your SuiVerify OTP is: {otp_code}. Valid for 10 minutes.")
        sms_sent = True  # Mock success
        
        if not sms_sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send OTP. Please try again."
            )
        
        return APIResponse(
            success=True,
            message="OTP sent successfully",
            data={
                "phone_number": f"+{clean_phone[:2]} {clean_phone[2:7]} {clean_phone[7:]}",
                "expires_in_minutes": 10,
                "purpose": purpose,
                # Remove in production - only for testing
                "otp_code": otp_code if purpose == "testing" else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send OTP: {str(e)}"
        )

@router.post("/verify", response_model=APIResponse)
async def verify_otp(
    phone_number: str = Form(...),
    user_address: str = Form(...),
    otp_code: str = Form(...),
    purpose: str = Form("verification"),
    db: Session = Depends(get_db)
):
    """
    Verify OTP code
    """
    try:
        logger.info(f"Verifying OTP for {phone_number}, user: {user_address}")
        
        # Clean phone number
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"
        
        # Find OTP record
        otp_key = f"{clean_phone}_{user_address}_{purpose}"
        otp_record = otp_storage.get(otp_key)
        
        if not otp_record:
            raise HTTPException(
                status_code=404,
                detail="OTP not found or expired. Please request a new OTP."
            )
        
        # Check if already verified
        if otp_record["verified"]:
            raise HTTPException(
                status_code=400,
                detail="OTP already used. Please request a new OTP."
            )
        
        # Check expiry
        if datetime.utcnow() > otp_record["expires_at"]:
            # Clean up expired OTP
            del otp_storage[otp_key]
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )
        
        # Check attempts (max 3 attempts)
        if otp_record["attempts"] >= 3:
            # Clean up after max attempts
            del otp_storage[otp_key]
            raise HTTPException(
                status_code=400,
                detail="Maximum verification attempts exceeded. Please request a new OTP."
            )
        
        # Increment attempts
        otp_record["attempts"] += 1
        
        # Verify OTP
        if otp_code != otp_record["otp"]:
            remaining_attempts = 3 - otp_record["attempts"]
            if remaining_attempts <= 0:
                del otp_storage[otp_key]
                raise HTTPException(
                    status_code=400,
                    detail="Invalid OTP. Maximum attempts exceeded."
                )
            
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
            )
        
        # Mark as verified
        otp_record["verified"] = True
        otp_record["verified_at"] = datetime.utcnow()
        
        # TODO: Update user phone verification status in database
        # user = db.query(User).filter(User.wallet_address == user_address).first()
        # if user:
        #     user.phone_number = clean_phone
        #     user.phone_verified = True
        #     db.commit()
        
        # Clean up verified OTP
        del otp_storage[otp_key]
        
        return APIResponse(
            success=True,
            message="OTP verified successfully",
            data={
                "phone_number": f"+{clean_phone[:2]} {clean_phone[2:7]} {clean_phone[7:]}",
                "user_address": user_address,
                "purpose": purpose,
                "verified_at": datetime.utcnow().isoformat(),
                "phone_verified": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify OTP: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify OTP: {str(e)}"
        )

@router.post("/resend", response_model=APIResponse)
async def resend_otp(
    phone_number: str = Form(...),
    user_address: str = Form(...),
    purpose: str = Form("verification"),
    db: Session = Depends(get_db)
):
    """
    Resend OTP to phone number
    """
    try:
        logger.info(f"Resending OTP to {phone_number} for user: {user_address}")
        
        # Clean phone number
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"
        
        # Check if there's an existing OTP
        otp_key = f"{clean_phone}_{user_address}_{purpose}"
        existing_otp = otp_storage.get(otp_key)
        
        # Check rate limiting (allow resend only after 1 minute)
        if existing_otp:
            time_since_last = datetime.utcnow() - existing_otp["created_at"]
            if time_since_last.total_seconds() < 60:
                remaining_seconds = 60 - int(time_since_last.total_seconds())
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {remaining_seconds} seconds before requesting a new OTP"
                )
        
        # Generate new OTP
        otp_code = generate_otp()
        expiry_time = datetime.utcnow() + timedelta(minutes=10)
        
        # Update or create OTP record
        otp_storage[otp_key] = {
            "otp": otp_code,
            "phone": clean_phone,
            "user_address": user_address,
            "purpose": purpose,
            "created_at": datetime.utcnow(),
            "expires_at": expiry_time,
            "attempts": 0,
            "verified": False
        }
        
        # TODO: Send SMS
        logger.info(f"Resent OTP for {clean_phone}: {otp_code}")
        sms_sent = True  # Mock success
        
        if not sms_sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to resend OTP. Please try again."
            )
        
        return APIResponse(
            success=True,
            message="OTP resent successfully",
            data={
                "phone_number": f"+{clean_phone[:2]} {clean_phone[2:7]} {clean_phone[7:]}",
                "expires_in_minutes": 10,
                "purpose": purpose
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend OTP: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resend OTP: {str(e)}"
        )
