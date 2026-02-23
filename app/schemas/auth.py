from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    

    @validator('password')
    def password_strength_check(cls, v):
        if len(v.encode("utf-8")) > 100:
            raise ValueError("Password is too long (max 72 bytes). Use a shorter password.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


    @validator('username')
    def username_min_length(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v.strip()



    
class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: int
    

    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not (100000 <= v <= 999999):
            raise ValueError("OTP code must be a 6-digit number.")
        return v




    
class OtpRequestResend(BaseModel):
    email: EmailStr
    
    
 
 
    
class loginRequest(BaseModel):
    email: EmailStr
    password: str
    




class forgotPasswordRequest(BaseModel):
    email: EmailStr   




class resetOtpRequest(BaseModel):
    email: EmailStr
    otp_code: int
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not (100000 <= v <= 999999):
            raise ValueError("OTP code must be a 6-digit number.")
        return v
 
 
 
       
    
class resetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str
    confirm_password: str
    
    @validator('new_password')
    def password_strength_check(cls, v):
        if len(v.encode("utf-8")) > 100:
            raise ValueError("Password is too long (max 72 bytes). Use a shorter password.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v
 
 
 
 
    
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_verified: bool
    is_approved: bool
    is_blocked: bool
 
 
 
 
    
class RegisterResponse(BaseModel):
    message: str
    email: EmailStr
    otp_expires_in_minute: int
    
 
 
 
 
    
class TokenResponse(BaseModel):
    access_token : str
    token_type: str = 'bearer'
    user: UserResponse
 
 
 
 
    
class SuccessResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    data: dict | None = None
 
 
 
 
    
class ErrorResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    errorsDetails: dict | None = None
    requestBody: dict | None = None