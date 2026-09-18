from dera.models.interpreter import InvestigationInterpreter
from dera.tasks.task import Task


class Provider:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self.response


def task() -> Task:
    item = Task(objective="Test")
    item.findings = [{"code": "storage.low_space", "severity": "warning", "title": "Storage low", "evidence": {"free_gb": 2}}]
    item.result = {"recommended_next_step": "Review folders."}
    return item


def test_grounded_json_is_accepted() -> None:
    response = '{"summary":"Storage needs review.","finding_ids":["storage.low_space"],"next_step":"Review folders."}'
    assert InvestigationInterpreter(Provider(response)).explain(task())["grounded"] is True


def test_numeric_model_claim_falls_back() -> None:
    response = '{"summary":"Storage is 2 GB.","finding_ids":["storage.low_space"],"next_step":"Review folders."}'
    assert InvestigationInterpreter(Provider(response)).explain(task())["grounded"] is False
