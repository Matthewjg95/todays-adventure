"""One authoritative task master; every view reads a snapshot of it.

The prototype's master is a committed fixture (tasks_fixture.json).
A later companion service can replace the loader without touching the
views, as long as it keeps the same shape: stable string IDs and one
of STATUSES per task.

Handwriting may PROPOSE a change. A proposal is appended to a separate
queue file and never alters the snapshot; applying it is a decision
for the task master's owner, not for the Paper.
"""

import json

STATUSES = ("inbox", "next", "active", "waiting", "later", "done", "dropped")
FIXTURE = "tasks_fixture.json"
PROPOSALS = "task_proposals.json"


class TaskError(ValueError):
    pass


def _validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise TaskError("task master must be an object with a tasks list")
    seen = set()
    for task in data["tasks"]:
        tid = task.get("id") if isinstance(task, dict) else None
        if not isinstance(tid, str) or not tid:
            raise TaskError("every task needs a string id")
        if tid in seen:
            raise TaskError("duplicate task id: " + tid)
        seen.add(tid)
        if task.get("status") not in STATUSES:
            raise TaskError("bad status for %s: %r" % (tid, task.get("status")))
        if not isinstance(task.get("title"), str):
            raise TaskError("task %s needs a title" % tid)
    return data


class Snapshot:
    """Read-only view: tasks are copied, so callers cannot edit the master."""

    def __init__(self, data):
        data = _validate(data)
        self.source = data.get("source", "unknown")
        self.revision = data.get("revision", 0)
        self.is_fixture = bool(data.get("fixture", False))
        self._tasks = tuple(tuple(sorted(t.items())) for t in data["tasks"])

    def tasks(self, status=None):
        out = [dict(t) for t in self._tasks]
        if status is not None:
            wanted = (status,) if isinstance(status, str) else tuple(status)
            out = [t for t in out if t["status"] in wanted]
        return out

    def get(self, task_id):
        for t in self._tasks:
            d = dict(t)
            if d["id"] == task_id:
                return d
        return None


class TaskMaster:
    def __init__(self, path=FIXTURE, proposals_path=PROPOSALS):
        self.path = path
        self.proposals_path = proposals_path

    def snapshot(self):
        with open(self.path) as f:
            return Snapshot(json.load(f))

    def propose(self, task_id, status, source, note=""):
        """Queue a proposed status change; returns the proposal.

        The snapshot is untouched: tasks keep their status until the
        master applies the proposal elsewhere."""
        if status not in STATUSES:
            raise TaskError("bad status: %r" % (status,))
        snap = self.snapshot()
        current = snap.get(task_id)
        if current is None:
            raise TaskError("unknown task id: %s" % task_id)
        proposal = {"task_id": task_id, "from": current["status"],
                    "to": status, "source": source, "note": note,
                    "revision": snap.revision, "state": "proposed"}
        queue = self.proposals()
        queue.append(proposal)
        with open(self.proposals_path, "w") as f:
            json.dump(queue, f)
        return proposal

    def proposals(self):
        try:
            with open(self.proposals_path) as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []
