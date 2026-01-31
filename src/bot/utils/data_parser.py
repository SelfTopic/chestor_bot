import json
from pathlib import Path
from typing import Union


def parse_qa_to_json(
    questions_file: str | Path, answers_file: str | Path, output_file: str | Path
) -> None:
    questions: list[str] = []
    answers: list[str] = []

    try:
        with open(questions_file, "r", encoding="utf8") as file:
            questions = [line.split(".")[1].strip() for line in file if line.strip()]

    except FileNotFoundError:
        print(f"File {questions_file} not found. Fix path")
        return

    try:
        with open(answers_file, "r", encoding="utf8") as file:
            answers = [line.split(".")[1].strip() for line in file if line.strip()]

    except FileNotFoundError:
        print(f"File {questions_file} not found. Fix path")
        return

    if len(questions) != len(answers):
        print(
            f"Длина вопросов и ответов отличается. Длина вопросов: {len(questions)}. Длина ответов: {len(answers)}"
        )

    min_len = min(len(questions), len(answers))

    qa_list: list[dict[str, Union[int, str]]] = []

    for i in range(min_len):
        qa_item = {"id": i + 1, "question": questions[i], "answer": answers[i]}
        qa_list.append(qa_item)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(qa_list, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ошибка при записи в Json файл: {e}")
        return


if __name__ == "__main__":
    parse_qa_to_json(
        questions_file="src/assets/data/raw/questions_ghoul.txt",
        answers_file="src/assets/data/raw/answers.txt",
        output_file="src/assets/data/processed/questions_ghoul.json",
    )
