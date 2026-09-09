from pydantic import BaseModel, Field

class StepsFunctionCalls(BaseModel):
    function_name: str = Field(..., description="The EXACT name of the function to call (the function name as was set in the tools)", strict=True)
    arguments: dict = Field(..., description="Arguments to call the function, them will be passed like `function(**<arguments>)`", strict=True)

class ToolResponse(BaseModel):

    text: str = Field(
        ...,
        description='The final natural-language reply for the user. This field is REQUIRED on every response: use "" while `function_calls` still has pending steps, and put your real final answer here once `function_calls` is empty, this reply can contain aks for the users to execute tools',
    )
    function_calls: list[StepsFunctionCalls] = Field(
        default_factory=list,
        description="Functions that still need to be called before you can answer. Leave this as an empty list once you're ready to answer directly in `text`.",
    )