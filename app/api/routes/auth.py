from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta, timezone, datetime
from app.database import supabase, get_db
from app.schemas.CommonResponse import ApiResponse
from app.schemas.auth import RegisterResponse, UserCreate, loginRequest, VerifyOtpRequest, UserResponse, OtpRequestResend, TokenResponse, resetOtpRequest, resetPasswordRequest, forgotPasswordRequest
from app.core.security import hash_password, verify_password, create_access_token, create_reset_password_token, verify_reset_password_token
from app.core.email import generate_otp, send_otp_email, send_password_reset_email
from app.core.config import settings
from app.api.deps import get_current_user, require_admin


def resend_otp_to_email(email: str):
    result = supabase.table('users').select('username').eq('email', email).execute()
    if not result.data:
        return False
    username = result.data[0]['username']
    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    update_result = supabase.table('users').update({'otp_code': otp, 'otp_expires_at': otp_expires_at.isoformat(), 'otp_attempts': 0}).eq('email', email).execute()
    if not update_result.data:
        return False
    return send_otp_email(email, otp, username)





router = APIRouter(prefix='/auth', tags=['Authentication'])




@router.post('/register', response_model=ApiResponse[RegisterResponse])
async def register(data: UserCreate):
    existing = supabase.table('users').select('id, is_verified').eq('email', data.email).execute()
    if existing.data:
        user = existing.data[0]
        if user['is_verified']:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=(f'An account with {data.email} already exists. '
                                        'Please login instead. ')
                                )
        else:
            resend_otp_to_email(data.email)
            return ApiResponse[RegisterResponse](
                success=True,
                statusCode=200,
                message=(f'An unverified account with {data.email} already exists.'),
                data=RegisterResponse(
                    message=(f'A new OTP has been sent to your email. Please verify your account.'),
                    email=data.email,
                    otp_expires_in_minute=settings.OTP_EXPIRE_MINUTES
                )
            )
        
    hashed = hash_password(data.password)
    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    result = supabase.table('users').insert({
        'username': data.username,
        'email': data.email,
        'hashed_password': hashed,
        'role': 'user',
        'is_verified': False,
        'is_approved': False,
        'is_blocked': False,
        'otp_code': otp,
        'otp_expires_at': otp_expires_at.isoformat(),
        'otp_attempts': 0,
        'created_at': datetime.now(timezone.utc).isoformat()
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Registraion failed')
    
    email_send = send_otp_email(data.email, otp, data.username)
    if not email_send:
        supabase.table('users').delete().eq('email', data.email).execute()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to sent OTP')
    
    return ApiResponse[RegisterResponse](
        success=True,
        statusCode=201,
        message='Registration successful. Please check your email for the OTP code to verify your account.',
        data=RegisterResponse(
            message='Registration successful. Please check your email for the OTP code to verify your account.',
            email=data.email,
            otp_expires_in_minute=settings.OTP_EXPIRE_MINUTES
        )
    )





    
@router.post('/verify-otp', response_model=ApiResponse[dict])
async def verify_otp(data: VerifyOtpRequest):
    result = supabase.table('users').select('*').eq('email', data.email).execute()
    if not result.data:
        return ApiResponse(
            success= False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message=f'No account found for {data.email} email',
            data=None
        )
    
    user = result.data[0]
    
    if user['is_verified']:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='Account already verified, please login',
            data=None
        )
    input_otp = str(data.otp_code).strip()
    stored_otp = str(user['otp_code']).strip() if user['otp_code'] is not None else None
    if stored_otp != input_otp:
        supabase.table('users').update({'otp_attempts': user['otp_attempts'] + 1}).eq('email', data.email).execute()
        remaining_attempts = settings.OTP_MAX_ATTEMPTS - (user['otp_attempts'] + 1)
        if remaining_attempts <= 0:
            supabase.table('users').update({'otp_attempts': 0, 'otp_code': None, 'otp_expires_at': None}).eq('email', data.email).execute()
            return ApiResponse(
                success=False,
                statusCode=status.HTTP_400_BAD_REQUEST,
                message='Too many failed OTP attempts. Please request a new OTP.',
                data=None
            )
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=f'Invalid OTP code. {remaining_attempts} attempts remaining.',
            data=None
        )
    
    if datetime.fromisoformat(user['otp_expires_at']) < datetime.now(timezone.utc):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='OTP code has expired. Please request a new OTP.',
            data=None
        )
    
    supabase.table('users').update({'is_verified': True, 'otp_code': None, 'otp_expires_at': None, 'otp_attempts': 0}).eq('email', data.email).execute()
    
    return ApiResponse[dict](
        success=True,
        statusCode=200,
        message='Account verified successfully. You can now login.'
    )

 
 
 
 
 
    
    
@router.post('/login', response_model=ApiResponse[TokenResponse])
async def login(data: loginRequest):
    
    if (data.email == settings.ADMIN_EMAIL and data.password == settings.ADMIN_PASSWORD):
        admin_token = create_access_token({'sub': settings.ADMIN_EMAIL, 'role': 'admin'})
        return ApiResponse[TokenResponse](
            success=True,
            statusCode=200,
            message="Admin login successful",
            data=TokenResponse(
                access_token=admin_token,
                token_type='bearer',
                user=UserResponse(
                    id=0,
                    username='Admin',
                    email=settings.ADMIN_EMAIL,
                    role='admin',
                    is_verified=True,
                    is_approved=True,
                    is_blocked=False
                )
            )
        )
        
    result = supabase.table('users').select('*').eq('email',data.email).execute()
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message='Invalid email or password',
            data=None
        )
    
    user = result.data[0]
    
    if not verify_password(data.password, user['hashed_password']):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message='Invalid email or password',
            data=None
        )
    
    if not user['is_verified']:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Please verify your account before login or resend OTP to your email',
            data=None
        )
    
    user_token = create_access_token({'sub': user['email'], 'role': user['role'], 'user_id': user['id']})
    return ApiResponse[TokenResponse](
        success=True,
        statusCode=200,
        message="Login successful",
        data=TokenResponse(
            access_token=user_token,
            token_type='bearer',
            user=UserResponse(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                role=user['role'],
                is_verified=user['is_verified'],
                is_approved=user['is_approved'],
                is_blocked=user['is_blocked']
            )
        )
    )

 
 
 
 
 
    
    
@router.post('/forgot-password', response_model=ApiResponse[dict])
async def forgot_password(data: forgotPasswordRequest):
    result = supabase.table('users').select('id, username, is_verified').eq('email', data.email).execute()
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message=f'No account found for {data.email} email',
            data=None
        )
    
    user = result.data[0]
    
    if not user['is_verified']:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Account not verified. Please verify your account before resetting password.',
            data=None
        )
    
    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_OTP_EXPIRE_MINUTES)
    supabase.table('users').update({'otp_code': otp, 'otp_expires_at': otp_expires_at.isoformat(), 'otp_attempts': 0}).eq('email', data.email).execute()
        
    email_sent = send_password_reset_email(data.email, otp, user['username'])
    if not email_sent:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message='Failed to send password reset OTP email',
            data=None
        )
    
    return ApiResponse[dict](
        success=True,
        statusCode=200,
        message=f"Password reset OTP sent to {data.email} if an account exists.",
        data={'email': data.email, 'otp_expires_in_minute': settings.RESET_OTP_EXPIRE_MINUTES}
    )








@router.post('/verify-reset-otp', response_model=ApiResponse[dict])
async def verify_reset_otp(data: resetOtpRequest):
    result = supabase.table('users').select('id, is_verified, otp_code, otp_expires_at, otp_attempts').eq('email', data.email).execute()
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message=f'No account found for {data.email} email',
            data=None
        )
    
    user = result.data[0]
    
    if not user['is_verified']:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Account not verified. Please verify your account before resetting password.',
            data=None
        )
    
    input_otp = str(data.otp_code).strip()
    stored_otp = str(user['otp_code']).strip() if user['otp_code'] is not None else None
    if stored_otp != input_otp:
        supabase.table('users').update({'otp_attempts': user['otp_attempts'] + 1}).eq('email', data.email).execute()
        remaining_attempts = settings.RESET_OTP_MAX_ATTEMPTS - (user['otp_attempts'] + 1)
        if remaining_attempts <= 0:
            supabase.table('users').update({'otp_attempts': 0, 'otp_code': None, 'otp_expires_at': None}).eq('email', data.email).execute()
            return ApiResponse(
                success=False,
                statusCode=status.HTTP_400_BAD_REQUEST,
                message='Too many failed OTP attempts. Please request a new OTP.',
                data=None
            )
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=f'Invalid OTP code. {remaining_attempts} attempts remaining.',
            data=None
        )
    
    if datetime.fromisoformat(user['otp_expires_at']) < datetime.now(timezone.utc):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='OTP code has expired. Please request a new OTP.',
            data=None
        )
    
    reset_token = create_reset_password_token(data.email)
    
    return ApiResponse[dict](
        success=True,
        statusCode=200,
        message='OTP verified successfully. You can now reset your password.',
        data={'reset_token': reset_token}
    )









@router.post('/reset-password', response_model=ApiResponse[dict])
async def reset_password(data: resetPasswordRequest):
    email = verify_reset_password_token(data.reset_token) #decode the reset token to get the email
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid or expired reset token')
    
    result = supabase.table('users').select('id, is_verified, hashed_password').eq('email', email).execute()
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message=f'No account found for {email} email',
            data=None
        )
    
    user = result.data[0]
    
    if verify_password(data.new_password, user['hashed_password']):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='New password cannot be the same as the old password',
            data=None
        )
    
    hashed = hash_password(data.new_password)
    supabase.table('users').update({'hashed_password': hashed, 'otp_code': None, 'otp_expires_at': None, 'otp_attempts': 0}).eq('email', email).execute()
    
    return ApiResponse[dict](
        success=True,
        statusCode=200,
        message='Password reset successful. You can now login with your new password.',
        data=None
    )








@router.post('/resend-otp', response_model=ApiResponse[dict])
async def resend_otp(data: OtpRequestResend):
    result = supabase.table('users').select('is_verified').eq('email', data.email).execute()
    
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message=f'No account found for {data.email} email',
            data=None
        )
    
    user = result.data[0]
    if user['is_verified']:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='Already account verified, please login',
            data=None
        )
    
    resend_otp_success = resend_otp_to_email(data.email)
    
    if not resend_otp_success:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message='Failed to send OTP',
            data=None
        )
    
    
    return ApiResponse[dict](
        success=True,
        statusCode=200,
        message=f'OTP resent to {data.email} if an unverified account exists.',
        data={'email': data.email, 'otp_expires_in_minute': settings.OTP_EXPIRE_MINUTES}
    )








@router.get('/user', response_model=ApiResponse[UserResponse])
async def get_user(current_user: dict = Depends(get_current_user)):
    email = current_user.get('email')
    result = supabase.table('users').select('id, username, email, role, is_verified, is_approved, is_blocked').eq('email', email).execute()
    if not result.data:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )
    user = result.data[0]
    return ApiResponse[UserResponse](
        success=True,
        statusCode=200,
        message="User fetched successfully",
        data=UserResponse(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            role=user['role'],
            is_verified=user['is_verified'],
            is_approved=user['is_approved'],
            is_blocked=user['is_blocked']
        )
    )
