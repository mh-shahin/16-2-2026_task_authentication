from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from app.api.routes.auth import router
from app.core.startup import ensure_admin_user
from app.database import init_db
from app.api.routes import auth, eventManager, event, admin, chat, payment
from app.schemas.CommonResponse import ApiResponse


app = FastAPI()

def format_errors(errors):
    messages = []
    for e in errors:
        msg = e.get("msg", "Invalid input")
        messages.append(msg)
    return messages




@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            data={"errors": format_errors(exc.errors())}
        ).model_dump()
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse(
            success=False,
            statusCode= status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            data={"errors": format_errors(exc.errors())}
        ).model_dump()
    )
@app.on_event("startup")
async def startup():
    init_db()            
    ensure_admin_user()  




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





app.include_router(auth.router)
app.include_router(eventManager.router)
app.include_router(event.router)
app.include_router(admin.router)
app.include_router(payment.router)
app.include_router(chat.router)





@app.get("/root")
async def root():
    return {"message": "Backend running..."}
