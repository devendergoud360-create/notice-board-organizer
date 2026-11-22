"""Command pattern: actions as objects in a registry.

CLI and HTTP layers dispatch through this registry rather than ad-hoc or
reflection-based dispatch.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Command(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def execute(self, app, params: Dict[str, Any]) -> Any:
        """Execute against the application facade with a params dict."""


class AddNoticeCommand(Command):
    name, description = "add", "Add a new notice"
    REQUIRED = ("title", "category", "date_posted", "expiry_date")

    def execute(self, app, params):
        from domain.entities import parse_date
        for key in self.REQUIRED:
            if key not in params:
                raise ValueError(f"missing required field: {key}")
        fields = dict(params)
        fields["date_posted"] = parse_date(fields["date_posted"])
        fields["expiry_date"] = parse_date(fields["expiry_date"])
        return app.add(**fields).to_dict()


class ListNoticesCommand(Command):
    name, description = "list", "View all notices"

    def execute(self, app, params):
        items = NoticeService_sort(app.notices, params.get("sort", "expiry"))
        return [n.to_dict() for n in items]


class SearchCommand(Command):
    name, description = "search", "Search / filter notices"

    def execute(self, app, params):
        items = app.search(params.get("keyword", ""), params.get("category", ""))
        return [n.to_dict() for n in items]


class UpdateNoticeCommand(Command):
    name, description = "update", "Update a notice"

    def execute(self, app, params):
        from domain.entities import parse_date
        changes = dict(params)
        changes.pop("id", None)
        for key in ("date_posted", "expiry_date"):
            if key in changes:
                changes[key] = parse_date(changes[key]).isoformat()
        n = app.update(int(params["id"]), **changes)
        return n.to_dict() if n else None


class DeleteNoticeCommand(Command):
    name, description = "delete", "Delete a notice"

    def execute(self, app, params):
        return app.delete(int(params["id"]))


class SummaryCommand(Command):
    name, description = "summary", "Executive summary"

    def execute(self, app, params):
        return app.summary()


class WarningsCommand(Command):
    name, description = "warnings", "Threshold warnings"

    def execute(self, app, params):
        return app.warnings()


class RiskCommand(Command):
    name, description = "risk", "Notice risk score"

    def execute(self, app, params):
        return app.risk(int(params["id"]))


class RankCommand(Command):
    name, description = "rank", "Rank notices by risk"

    def execute(self, app, params):
        return app.ranked()


class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def names(self) -> List[str]:
        return list(self._commands)

    def execute(self, name: str, app, params: Dict[str, Any] | None = None):
        cmd = self.get(name)
        if cmd is None:
            raise KeyError(f"unknown command: {name}")
        return cmd.execute(app, params or {})


def NoticeService_sort(notices, key):
    from domain import NoticeService
    return NoticeService.sort(notices, key)


registry = CommandRegistry()
for _cmd in (
    AddNoticeCommand(), ListNoticesCommand(), SearchCommand(),
    UpdateNoticeCommand(), DeleteNoticeCommand(), SummaryCommand(),
    WarningsCommand(), RiskCommand(), RankCommand(),
):
    registry.register(_cmd)
