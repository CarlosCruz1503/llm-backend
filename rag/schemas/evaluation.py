from enum import Enum

from pydantic import BaseModel, Field


class JudgeVerdict(str, Enum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    CORRECT_REFUSAL = "correct_refusal"
    FALSE_REFUSAL = "false_refusal"
    HALLUCINATION = "hallucination"


class JudgeGradeSchema(BaseModel):

    id: int = Field(description="The id of the question being graded")
    score: int = Field(description="Score from 1 to 5 following the rubric")
    verdict: JudgeVerdict = Field(description="The category that best describes the answer")
    reason: str = Field(description="One short sentence explaining the score")


class JudgeBatchSchema(BaseModel):

    text: str = Field(description="One or two sentences summarizing the overall quality of the answers")
    grades: list[JudgeGradeSchema] = Field(description="One grade per question, in the same order as the input")
