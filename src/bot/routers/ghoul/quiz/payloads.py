from selfrot import CallbackPayload


class QuizAnswer(CallbackPayload, prefix="quiz_answer"):
    question_id: int
    option: int
    streak: int
    mode: int
    owner_id: int


class QuizRestart(CallbackPayload, prefix="quiz_restart"):
    owner_id: int
