from pydantic import BaseModel, Field, field_validator


class ChatbotRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("message must not be blank")
        return message


class ChatbotResponse(BaseModel):
    answer: str
