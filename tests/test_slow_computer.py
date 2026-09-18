from dera.tasks.slow_computer import SlowComputerInvestigation


class Observer:
    def snapshot(self) -> dict:
        return {"cpu": {"usage_percent": 10}, "memory": {"usage_percent": 50, "available_gb": 8}, "storage": {"usage_percent": 50, "free_gb": 50}, "top_processes": []}


class Store:
    def save(self, task: object) -> None:
        pass


def test_investigation_finishes_without_a_detected_issue() -> None:
    task = SlowComputerInvestigation(observer=Observer(), store=Store()).run()
    assert task.state == "completed"
    assert task.result["highest_severity"] == "info"
