import getpass
from unittest.mock import call, Mock

import pytest
from typer.testing import CliRunner

from cli.schedule import app, delete_app

runner = CliRunner()


@pytest.fixture
def task_list(mocker):
    mock_task_list = mocker.patch("cli.schedule.TaskList")
    mock_task_list.return_value.tasks = [Mock(task_id=1), Mock(task_id=2)]
    return mock_task_list


@pytest.fixture
def mock_confirm(mocker):
    return mocker.patch("cli.schedule.typer.confirm")


class TestCreate:
    def test_calls_all_stuff_in_right_order(self, mocker):
        mock_task_to_be_created = mocker.patch("cli.schedule.Task.to_be_created")

        runner.invoke(
            app,
            [
                "create",
                "--command",
                "echo foo",
                "--hour",
                "8",
                "--minute",
                "10",
            ],
        )

        assert mock_task_to_be_created.call_args == call(
            command="echo foo", hour=8, minute=10, disabled=False
        )
        assert mock_task_to_be_created.return_value.method_calls == [
            call.create_schedule()
        ]

    def test_validates_minutes(self):
        result = runner.invoke(app, ["create", "-c", "echo foo", "-h", "8", "-m", "66"])

        assert "Invalid value" in result.stdout
        assert "66 is not in the valid range of 0 to 59" in result.stdout

    def test_validates_hours(self):
        result = runner.invoke(app, ["create", "-c", "echo foo", "-h", "66", "-m", "1"])
        assert "Invalid value" in result.stdout
        assert "66 is not in the valid range of 0 to 23" in result.stdout


class TestDeleteAllTasks:
    def test_deletes_all_tasks_with_user_permission(self, task_list, mock_confirm):
        mock_confirm.return_value = True

        runner.invoke(delete_app, ["nuke"])

        assert mock_confirm.call_args == call(
            "This will irrevocably delete all your tasks, proceed?"
        )
        assert task_list.call_count == 1
        for task in task_list.return_value.tasks:
            assert task.method_calls == [call.delete_schedule()]

    def test_exits_when_user_changes_mind(self, task_list, mock_confirm):
        mock_confirm.return_value = False

        runner.invoke(
            delete_app,
            [
                "nuke",
            ],
        )

        assert task_list.call_count == 0

    def test_deletes_all_tasks_when_forced(self, task_list, mock_confirm):
        runner.invoke(delete_app, ["nuke", "--force"])

        assert mock_confirm.call_count == 0
        assert task_list.call_count == 1
        for task in task_list.return_value.tasks:
            assert task.method_calls == [call.delete_schedule()]


class TestDeleteTaskById:
    def test_deletes_one_task(self, mocker):
        mock_task_from_id = mocker.patch("cli.schedule.get_task_from_id")

        runner.invoke(delete_app, ["id", "42"])

        assert mock_task_from_id.call_args == call(42, no_exit=True)
        assert mock_task_from_id.return_value.method_calls == [call.delete_schedule()]

    def test_deletes_some_tasks(self, mocker):
        mock_task_from_id = mocker.patch("cli.schedule.get_task_from_id")

        runner.invoke(delete_app, ["id", "24", "42"])

        assert mock_task_from_id.call_args_list == [
            call(24, no_exit=True),
            call(42, no_exit=True),
        ]
        assert mock_task_from_id.return_value.method_calls == [
            call.delete_schedule(),
            call.delete_schedule(),
        ]


@pytest.fixture()
def task_from_id(mocker):
    user = getpass.getuser()
    specs = {
        "can_enable": False,
        "command": "echo foo",
        "enabled": True,
        "expiry": "2999-01-13",
        "hour": 10,
        "interval": "daily",
        "logfile": f"/user/{user}/files/foo",
        "minute": 23,
        "printable_time": "10:23",
        "task_id": 42,
        "username": user,
    }
    task = mocker.patch("cli.schedule.get_task_from_id")
    for spec, value in specs.items():
        setattr(task.return_value, spec, value)
    yield task


class TestGet:
    def test_logs_all_task_specs_using_tabulate(self, mocker, task_from_id):
        mock_tabulate = mocker.patch("cli.schedule.tabulate")
        mock_snakesay = mocker.patch("cli.schedule.snakesay")
        mock_logger = mocker.patch("cli.schedule.get_logger").return_value

        runner.invoke(app, ["get", "42"])

        assert task_from_id.call_args == call(42)
        assert mock_snakesay.call_count == 0
        assert mock_tabulate.call_args == call(
            [
                ["command", "echo foo"],
                ["enabled", True],
                ["expiry", "2999-01-13"],
                ["hour", 10],
                ["interval", "daily"],
                ["logfile", f"/user/{getpass.getuser()}/files/foo"],
                ["minute", 23],
                ["printable_time", "10:23"],
            ],
            tablefmt="simple",
        )
        assert mock_logger.info.call_args_list == [
            call("Task 42 specs: "),
            call(mock_tabulate.return_value)
        ]

    def test_logs_all_task_specs_using_snakesay(self, mocker, task_from_id):
        mock_tabulate = mocker.patch("cli.schedule.tabulate")
        mock_snakesay = mocker.patch("cli.schedule.snakesay")
        mock_logger = mocker.patch("cli.schedule.get_logger").return_value

        runner.invoke(app, ["get", "42", "--snakesay"])

        assert task_from_id.call_args == call(42)
        snake_args = (
            "Task 42 specs: <command>: echo foo, <enabled>: True, <expiry>: 2999-01-13, "
            f"<hour>: 10, <interval>: daily, <logfile>: /user/{getpass.getuser()}/files/foo, "
            "<minute>: 23, <printable_time>: 10:23"
        )
        assert mock_snakesay.call_args == call(snake_args)
        assert mock_tabulate.call_count == 0
        assert mock_logger.info.call_args == call(mock_snakesay.return_value)

    def test_logs_requested_task_spec(self, mocker, task_from_id):
        mock_tabulate = mocker.patch("cli.schedule.tabulate")

        runner.invoke(app, ["get", "42", "--command"])

        assert task_from_id.call_args == call(42)
        assert mock_tabulate.call_args == call([["command", "echo foo"]], tablefmt="simple")

    def test_logs_only_value_of_requested_task_spec(self, mocker, task_from_id):
        mock_tabulate = mocker.patch("cli.schedule.tabulate")
        mock_snakesay = mocker.patch("cli.schedule.snakesay")
        mock_logger = mocker.patch("cli.schedule.get_logger")

        runner.invoke(app, ["get", "42", "--printable-time", "--no-spec"])

        assert mock_tabulate.call_count == 0
        assert mock_snakesay.call_count == 0
        assert task_from_id.call_args == call(42)
        assert mock_logger.call_args == call(set_info=True)
        assert mock_logger.return_value.info.call_args == call("10:23")
