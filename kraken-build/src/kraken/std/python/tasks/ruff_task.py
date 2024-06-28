from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from kraken.common import Supplier
from kraken.core import Project, Property
from kraken.std.python.tasks.pex_build_task import pex_build

from .base_task import EnvironmentAwareDispatchTask


class RuffTask(EnvironmentAwareDispatchTask):
    """A task to run `ruff` in either format, fix, or check mode."""

    description = "Lint Python source files with Ruff."
    python_dependencies = ["ruff"]

    ruff_bin: Property[str] = Property.default("ruff")
    ruff_task: Property[str] = Property.default("")
    config_file: Property[Path]
    additional_args: Property[Sequence[str]] = Property.default_factory(list)

    def get_execute_command(self) -> list[str]:
        command = [
            self.ruff_bin.get(),
            self.ruff_task.get(),
            str(self.settings.source_directory),
            *self.settings.get_tests_directory_as_args(),
        ]
        command += [str(directory) for directory in self.settings.lint_enforced_directories]
        if self.config_file.is_filled():
            command += ["--config", str(self.config_file.get().absolute())]
        command += self.additional_args.get()
        return command


@dataclass
class RuffTasks:
    check: RuffTask
    fix: RuffTask
    format: RuffTask


def ruff(
    *,
    name: str = "python.ruff",
    project: Project | None = None,
    config_file: Path | Supplier[Path] | None = None,
    additional_args: Sequence[str] | Supplier[Sequence[str]] = (),
    additional_requirements: Sequence[str] = (),
    version_spec: str | None = None,
) -> RuffTasks:
    """Creates three tasks for formatting and linting your Python project with Ruff.

    :param version_spec: If specified, the Ruff tool will be installed as a PEX and does not need to be installed
        into the Python project's virtual env.
    """

    project = project or Project.current()

    if version_spec is not None:
        ruff_bin = pex_build(
            "ruff",
            requirements=[f"ruff{version_spec}", *additional_requirements],
            console_script="ruff",
            project=project,
        ).output_file.map(str)
    else:
        ruff_bin = Supplier.of("ruff")

    check_task = project.task(f"{name}.check", RuffTask, group="lint")
    check_task.ruff_bin = ruff_bin
    check_task.ruff_task = "check"
    check_task.config_file = config_file
    check_task.additional_args = additional_args

    fix_task = project.task(f"{name}.check", RuffTask, group="fmt")
    fix_task.ruff_bin = ruff_bin
    fix_task.ruff_task = "check --fix"
    fix_task.config_file = config_file
    fix_task.additional_args = additional_args

    format_task = project.task(f"{name}.format", RuffTask, group="fmt")
    format_task.ruff_bin = ruff_bin
    format_task.ruff_task = "format"
    format_task.config_file = config_file
    format_task.additional_args = additional_args

    return RuffTasks(check_task, fix_task, format_task)
