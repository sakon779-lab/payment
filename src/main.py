from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, field_validator
from starlette.responses import JSONResponse

app = FastAPI()

class PasswordRequest(BaseModel):
    password: str

    @field_validator('password')
    def check_empty_password(cls, v):
        if not v:
            raise HTTPException(status_code=400, detail='Password cannot be empty')
        return v

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.post('/check-password')
def check_password(request: PasswordRequest):
    score = 0
    feedbacks = []

    # Rule 1: Length
    if len(request.password) >= 8:
        score += 1
    else:
        feedbacks.append('Password is too short')

    # Rule 2: Number
    if any(char.isdigit() for char in request.password):
        score += 1
    else:
        feedbacks.append('Add a number')

    # Rule 3: Uppercase
    if any(char.isupper() for char in request.password):
        score += 1
    else:
        feedbacks.append('Add an uppercase letter')

    # Rule 4: Special Character
    special_chars = '!@#$%^&*'
    if any(char in special_chars for char in request.password):
        score += 1
    else:
        feedbacks.append('Add a special character')

    strength_mapping = {
        (0, 1): 'Weak',
        (2, 3): 'Medium',
        4: 'Strong'
    }

    for score_range, strength in strength_mapping.items():
        if isinstance(score_range, tuple):
            start, end = score_range
            if start <= score <= end:
                return {'score': score, 'strength': strength, 'feedbacks': feedbacks}
        else:
            if score == score_range:
                return {'score': score, 'strength': strength, 'feedbacks': feedbacks}