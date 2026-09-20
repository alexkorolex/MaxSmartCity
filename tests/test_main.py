import runpy

from pytest import CaptureFixture

from main import main


def test_main_prints_greeting(capsys: CaptureFixture[str]) -> None:
    main()

    output = capsys.readouterr()
    assert output.out == "Hello from maxsmartcity!\n"
    assert output.err == ""


def test_module_entrypoint_prints_greeting(capsys: CaptureFixture[str]) -> None:
    runpy.run_module("main", run_name="__main__")

    output = capsys.readouterr()
    assert output.out == "Hello from maxsmartcity!\n"
    assert output.err == ""
