from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    # ORM 객체도 Response 모델로 변환시킬 수 있게 해줌
    model_config: ConfigDict = ConfigDict(from_attributes=True)


class BaseSuccessResponse(BaseResponse):
    message: str = Field(
        ...,
        description="성공 메시지",
        examples=["성공 메시지"],
    )
