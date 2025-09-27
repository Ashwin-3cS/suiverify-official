"""
Complete KYC verification flow
"""
from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile
from typing import List
import logging
import base64
import uuid

from app.models.schemas import APIResponse
from app.models.user import VerificationLog
from app.services.user_service import get_user_service, UserService
from app.services.ocr_service import get_ocr_service, OCRService
from app.services.face_recognition_service import get_face_recognition_service, HighAccuracyFaceService
from app.services.otp_service import get_otp_service, OTPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kyc", tags=["KYC Verification"])

# Store temporary verification data (in production, use Redis)
temp_verification_data = {}

@router.post("/start-verification", response_model=APIResponse)
async def start_kyc_verification(
    verification_type: str = Form(..., description="Type: 'above18' or 'citizenship'"),
    aadhaar_image: UploadFile = File(...),
    face_images: List[UploadFile] = File(...),
    ocr_service: OCRService = Depends(get_ocr_service),
    face_service: HighAccuracyFaceService = Depends(get_face_recognition_service),
    otp_service: OTPService = Depends(get_otp_service)
):
    """Start KYC verification: Process Aadhaar + Face images, then send OTP"""
    try:
        # Validate verification type
        if verification_type not in ['above18', 'citizenship']:
            raise HTTPException(
                status_code=400,
                detail="verification_type must be 'above18' or 'citizenship'"
            )
        
        # Generate unique session ID for this verification
        session_id = str(uuid.uuid4())
        
        # Step 1: Process Aadhaar document
        aadhaar_bytes = await aadhaar_image.read()
        
        try:
            aadhaar_data = ocr_service.extract_aadhaar_data(aadhaar_bytes)
            aadhaar_photo = ocr_service.extract_photo_from_aadhaar(aadhaar_bytes)
            
            if not aadhaar_data.get('name') or not aadhaar_data.get('aadhaar_number'):
                raise ValueError("Could not extract essential Aadhaar information")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Aadhaar processing failed: {str(e)}")
        
        # Step 2: Process face images and perform face matching
        if len(face_images) < 3:
            raise HTTPException(
                status_code=400, 
                detail="At least 3 face images required for verification"
            )
        
        face_match_results = []
        
        try:
            # Convert face images to base64
            face_images_b64 = []
            for face_img in face_images:
                face_bytes = await face_img.read()
                face_b64 = base64.b64encode(face_bytes).decode('utf-8')
                face_images_b64.append(face_b64)
            
            # Convert Aadhaar photo to base64
            if aadhaar_photo:
                aadhaar_photo_b64 = base64.b64encode(aadhaar_photo).decode('utf-8')
                
                # Compare each face image with Aadhaar photo
                for i, face_b64 in enumerate(face_images_b64):
                    try:
                        match_result = face_service.compare_faces(aadhaar_photo_b64, face_b64)
                        face_match_results.append({
                            'image_index': i,
                            'match_result': match_result
                        })
                    except Exception as e:
                        logger.warning(f"Face comparison failed for image {i}: {e}")
                        face_match_results.append({
                            'image_index': i,
                            'match_result': {'verified': False, 'error': str(e)}
                        })
            else:
                raise ValueError("Could not extract photo from Aadhaar card")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Face matching failed: {str(e)}")
        
        # Step 3: Evaluate face verification result
        successful_matches = sum(1 for result in face_match_results 
                               if result['match_result'].get('verified', False))
        
        face_verification_passed = successful_matches >= 2  # At least 2 out of 3+ images should match
        
        if not face_verification_passed:
            raise HTTPException(
                status_code=400, 
                detail=f"Face verification failed. Only {successful_matches} out of {len(face_images)} images matched."
            )
        
        # Step 4: Extract phone number and send OTP
        phone_number = aadhaar_data.get('phone_number')  # Updated key name
        if not phone_number:
            raise HTTPException(
                status_code=400,
                detail="Phone number not found in Aadhaar. Please ensure your Aadhaar has a registered mobile number."
            )
        
        # Clean phone number
        phone_clean = phone_number.replace('+91', '').replace('-', '').replace(' ', '').strip()
        
        # Store verification data temporarily (use session_id as key)
        temp_verification_data[session_id] = {
            'aadhaar_data': aadhaar_data,
            'phone_number': phone_clean,
            'face_verification_passed': True,
            'face_matches': successful_matches,
            'total_face_images': len(face_images),
            'verification_type': verification_type,  # Store verification type
            'did': 0 if verification_type == 'above18' else 1  # Set DID based on type
        }
        
        # Generate and send OTP
        try:
            otp = otp_service.generate_otp(phone_clean)
            sms_sent = otp_service.send_otp_sms(phone_clean, otp)
            
            logger.info(f"OTP sent to {phone_clean} for session {session_id}")
            
            return APIResponse(
                success=True,
                message="Aadhaar and face verification successful. OTP sent to registered mobile number.",
                data={
                    'session_id': session_id,
                    'phone_number': phone_clean,
                    'aadhaar_verified': True,
                    'face_verified': True,
                    'otp_sent': sms_sent,
                    'expires_in_minutes': otp_service.otp_expiry_minutes,
                    'extracted_data': {
                        'name': aadhaar_data.get('name'),
                        'aadhaar_number': aadhaar_data.get('aadhaar_number', '').replace(' ', ''),
                        'date_of_birth': aadhaar_data.get('dob'),
                        'gender': aadhaar_data.get('gender')
                    }
                }
            )
            
        except Exception as e:
            # Clean up temp data on OTP failure
            if session_id in temp_verification_data:
                del temp_verification_data[session_id]
            raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start KYC verification: {e}")
        raise HTTPException(status_code=500, detail=f"KYC verification failed: {str(e)}")


@router.post("/complete-verification", response_model=APIResponse)
async def complete_kyc_verification(
    session_id: str = Form(...),
    otp: str = Form(...),
    user_service: UserService = Depends(get_user_service),
    otp_service: OTPService = Depends(get_otp_service)
):
    """Complete KYC verification: Verify OTP and save user data to database"""
    try:
        # Step 1: Check if session exists
        if session_id not in temp_verification_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID or session expired. Please start verification again."
            )
        
        verification_data = temp_verification_data[session_id]
        phone_clean = verification_data['phone_number']
        
        # Step 2: Verify OTP
        try:
            otp_verified = otp_service.verify_otp(phone_clean, otp)
            if not otp_verified:
                raise HTTPException(status_code=400, detail="Invalid OTP")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"OTP verification failed: {str(e)}")
        
        # Step 3: Generate dummy wallet address and save user data
        dummy_wallet_address = f"0x{uuid.uuid4().hex[:64]}"  # Generate 64-char dummy wallet address
        aadhaar_data = verification_data['aadhaar_data']
        did_value = verification_data['did']
        
        # Create user data
        from app.models.user import UserCreate
        user_create_data = UserCreate(
            wallet_address=dummy_wallet_address,
            phone_number=phone_clean,
            aadhaar_number=aadhaar_data.get('aadhaar_number', '').replace(' ', ''),
            date_of_birth=aadhaar_data.get('dob'),
            full_name=aadhaar_data.get('name'),
            gender=aadhaar_data.get('gender'),
            is_verified=1,  # Set verification flag to 1
            did=did_value   # Set DID based on verification type
        )
        
        # Save to database
        try:
            created_user = await user_service.create_user(user_create_data)
            
            # Log successful verification
            log_data = VerificationLog(
                wallet_address=dummy_wallet_address,
                verification_type="kyc_complete",
                status="success",
                details={
                    "aadhaar_data": aadhaar_data,
                    "face_matches": verification_data['face_matches'],
                    "total_face_images": verification_data['total_face_images'],
                    "phone_verified": True,
                    "user_verified": True,
                    "session_id": session_id
                }
            )
            await user_service.log_verification_attempt(log_data)
            
            # Clean up temporary data
            del temp_verification_data[session_id]
            
            logger.info(f"KYC verification completed successfully for wallet: {dummy_wallet_address}")
            
            return APIResponse(
                success=True,
                message="KYC verification completed successfully! User data saved to database.",
                data={
                    'wallet_address': dummy_wallet_address,
                    'verification_status': 'VERIFIED',
                    'is_verified': 1,
                    'user_data': {
                        'wallet_address': dummy_wallet_address,
                        'phone_number': phone_clean,
                        'aadhaar_number': aadhaar_data.get('aadhaar_number', '').replace(' ', ''),
                        'date_of_birth': aadhaar_data.get('dob'),
                        'full_name': aadhaar_data.get('name'),
                        'gender': aadhaar_data.get('gender'),
                        'is_verified': 1,
                        'did': did_value,
                        'verification_type': verification_data['verification_type']
                    },
                    'verification_details': {
                        'aadhaar_verified': True,
                        'face_verified': True,
                        'phone_verified': True,
                        'face_matches': verification_data['face_matches'],
                        'total_face_images': verification_data['total_face_images']
                    }
                }
            )
            
        except Exception as e:
            # Clean up temp data on database error
            if session_id in temp_verification_data:
                del temp_verification_data[session_id]
            raise HTTPException(status_code=500, detail=f"Failed to save user data: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in complete KYC verification: {e}")
        raise HTTPException(status_code=500, detail=f"KYC verification failed: {str(e)}")


# Keep the old endpoint for backward compatibility
@router.post("/legacy-complete-verification", response_model=APIResponse)
async def legacy_complete_kyc_verification(
    wallet_address: str = Form(...),
    phone: str = Form(...),
    otp: str = Form(...),
    aadhaar_image: UploadFile = File(...),
    face_images: List[UploadFile] = File(...),
    user_service: UserService = Depends(get_user_service),
    ocr_service: OCRService = Depends(get_ocr_service),
    face_service: HighAccuracyFaceService = Depends(get_face_recognition_service),
    otp_service: OTPService = Depends(get_otp_service)
):
    """Legacy complete KYC verification flow (for backward compatibility)"""
    try:
        # Step 1: Verify OTP first (independent of user/wallet)
        phone_clean = phone.replace('+91', '').replace('-', '').replace(' ', '').strip()
        
        try:
            otp_verified = otp_service.verify_otp(phone_clean, otp)
            if not otp_verified:
                raise HTTPException(status_code=400, detail="Invalid OTP")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"OTP verification failed: {str(e)}")
        
        # Step 2: Process Aadhaar document
        aadhaar_bytes = await aadhaar_image.read()
        
        try:
            aadhaar_data = ocr_service.extract_aadhaar_data(aadhaar_bytes)
            aadhaar_photo = ocr_service.extract_photo_from_aadhaar(aadhaar_bytes)
            
            if not aadhaar_data.get('name') or not aadhaar_data.get('aadhaar_number'):
                raise ValueError("Could not extract essential Aadhaar information")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Aadhaar processing failed: {str(e)}")
        
        # Step 3: Process face images and perform face matching
        if len(face_images) < 3:
            raise HTTPException(
                status_code=400, 
                detail="At least 3 face images required for verification"
            )
        
        face_match_results = []
        
        try:
            # Convert face images to base64
            face_images_b64 = []
            for face_img in face_images:
                face_bytes = await face_img.read()
                face_b64 = base64.b64encode(face_bytes).decode('utf-8')
                face_images_b64.append(face_b64)
            
            # Convert Aadhaar photo to base64
            if aadhaar_photo:
                aadhaar_photo_b64 = base64.b64encode(aadhaar_photo).decode('utf-8')
                
                # Compare each face image with Aadhaar photo
                for i, face_b64 in enumerate(face_images_b64):
                    try:
                        match_result = face_service.compare_faces(aadhaar_photo_b64, face_b64)
                        face_match_results.append({
                            'image_index': i,
                            'match_result': match_result
                        })
                    except Exception as e:
                        logger.warning(f"Face comparison failed for image {i}: {e}")
                        face_match_results.append({
                            'image_index': i,
                            'match_result': {'verified': False, 'error': str(e)}
                        })
            else:
                raise ValueError("Could not extract photo from Aadhaar card")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Face matching failed: {str(e)}")
        
        # Step 4: Evaluate overall verification result
        successful_matches = sum(1 for result in face_match_results 
                               if result['match_result'].get('verified', False))
        
        face_verification_passed = successful_matches >= 2  # At least 2 out of 3+ images should match
        
        # Step 5: Save user data to database if all verifications pass
        verification_successful = face_verification_passed
        
        if verification_successful:
            # Create or update user with complete verification data
            from app.models.user import UserCreate, UserUpdate
            
            # Check if user already exists
            existing_user = await user_service.get_user_by_wallet(wallet_address)
            
            if existing_user:
                # Update existing user
                user_update_data = UserUpdate(
                    phone_number=phone_clean,
                    aadhaar_number=aadhaar_data.get('aadhaar_number'),
                    date_of_birth=aadhaar_data.get('dob'),
                    full_name=aadhaar_data.get('name'),
                    gender=aadhaar_data.get('gender'),
                    is_verified=1  # Set verification flag to 1
                )
                updated_user = await user_service.update_user(wallet_address, user_update_data)
            else:
                # Create new user with all data
                user_create_data = UserCreate(
                    wallet_address=wallet_address,
                    phone_number=phone_clean,
                    aadhaar_number=aadhaar_data.get('aadhaar_number'),
                    date_of_birth=aadhaar_data.get('dob'),
                    full_name=aadhaar_data.get('name'),
                    gender=aadhaar_data.get('gender'),
                    is_verified=1  # Set verification flag to 1
                )
                updated_user = await user_service.create_user(user_create_data)
            
            # Log successful verification
            log_data = VerificationLog(
                wallet_address=wallet_address,
                verification_type="kyc_complete",
                status="success",
                details={
                    "aadhaar_data": aadhaar_data,
                    "face_matches": successful_matches,
                    "total_face_images": len(face_images),
                    "phone_verified": True,
                    "user_verified": True
                }
            )
            await user_service.log_verification_attempt(log_data)
            
            logger.info(f"KYC verification completed successfully for wallet: {wallet_address}")
            
            return APIResponse(
                success=True,
                message="KYC verification completed successfully - User is now verified!",
                data={
                    'wallet_address': wallet_address,
                    'verification_status': 'VERIFIED',
                    'is_verified': 1,  # Verification flag set to 1
                    'user_data': {
                        'wallet_address': wallet_address,
                        'phone_number': phone_clean,
                        'aadhaar_number': aadhaar_data.get('aadhaar_number', '').replace(' ', ''),
                        'date_of_birth': aadhaar_data.get('dob'),
                        'full_name': aadhaar_data.get('name'),
                        'gender': aadhaar_data.get('gender'),
                        'is_verified': 1
                    },
                    'verification_details': {
                        'aadhaar_verified': True,
                        'face_verified': face_verification_passed,
                        'phone_verified': True,
                        'face_matches': successful_matches,
                        'total_face_images': len(face_images)
                    }
                }
            )
        else:
            # Log failed verification
            log_data = VerificationLog(
                wallet_address=wallet_address,
                verification_type="kyc_complete",
                status="failed",
                details={
                    "face_matches": successful_matches,
                    "total_face_images": len(face_images),
                    "face_verification_passed": face_verification_passed,
                    "reason": "Insufficient face matches"
                }
            )
            await user_service.log_verification_attempt(log_data)
            
            return APIResponse(
                success=False,
                message="KYC verification failed",
                data={
                    'wallet_address': wallet_address,
                    'verification_status': 'FAILED',
                    'face_verification': {
                        'successful_matches': successful_matches,
                        'total_images': len(face_images),
                        'verification_passed': face_verification_passed,
                        'required_matches': 2
                    },
                    'reason': 'Face verification failed - insufficient matches with Aadhaar photo'
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in complete KYC verification: {e}")
        
        # Log general error
        try:
            log_data = VerificationLog(
                wallet_address=wallet_address,
                verification_type="kyc_complete",
                status="error",
                details={"error": str(e)}
            )
            await user_service.log_verification_attempt(log_data)
        except:
            pass  # Don't fail if logging fails
        
        raise HTTPException(
            status_code=500,
            detail=f"KYC verification failed: {str(e)}"
        )

@router.get("/status/{wallet_address}", response_model=APIResponse)
async def get_kyc_status(
    wallet_address: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get complete KYC verification status and user data"""
    try:
        user = await user_service.get_user_by_wallet(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get verification logs
        logs = await user_service.get_user_verification_logs(wallet_address)
        
        # Prepare user data response
        user_data = {
            'wallet_address': user.wallet_address,
            'phone_number': user.phone_number,
            'aadhaar_number': user.aadhaar_number,
            'date_of_birth': user.date_of_birth,
            'full_name': user.full_name,
            'gender': user.gender,
            'is_verified': user.is_verified,
            'verification_flag': user.is_verified,  # 0 = not verified, 1 = verified
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat()
        }
        
        # Check what verifications are complete
        verification_status = {
            'overall_verified': user.is_verified == 1,
            'has_phone': user.phone_number is not None,
            'has_aadhaar': user.aadhaar_number is not None,
            'has_personal_data': user.full_name is not None and user.date_of_birth is not None
        }
        
        return APIResponse(
            success=True,
            message="KYC status retrieved successfully",
            data={
                'user_data': user_data,
                'verification_status': verification_status,
                'verification_logs': [log.dict() for log in logs[:10]]  # Last 10 logs
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting KYC status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/verified-users", response_model=APIResponse)
async def get_verified_users(
    user_service: UserService = Depends(get_user_service)
):
    """Get all verified users (admin endpoint)"""
    try:
        verified_users = await user_service.get_all_verified_users()
        user_counts = await user_service.get_user_count_by_verification_status()
        
        return APIResponse(
            success=True,
            message="Verified users retrieved successfully",
            data={
                'verified_users': [user.dict() for user in verified_users],
                'statistics': user_counts,
                'total_verified': len(verified_users)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting verified users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")