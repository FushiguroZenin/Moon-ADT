from pathlib import Path

from dera.memory.task_store import TaskStore
from dera.tasks.task import Task


def test_task_and_follow_up_are_persistent(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "moon.db")
    task = Task(objective="Inspect storage")
    store.save(task)
    store.add_event(task.id, "follow_up_completed", {"request": "Show evidence"})
    loaded = store.get(task.id)
    assert loaded["id"] == task.id
    assert loaded["activity"][0]["kind"] == "follow_up_completed"
