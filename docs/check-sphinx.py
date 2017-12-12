import subprocess
import pytest


# noinspection PyClassHasNoInit
@pytest.allure.feature("TestDoc")
class TestDoc:

    def test_linkcheck(self, tmpdir):
        doctrees = tmpdir.join("doctrees")
        htmldir = tmpdir.join("html")
        subprocess.check_call(["sphinx-build", "-W", "-blinkcheck", "-d", str(doctrees), ".", str(htmldir)])

    def test_build_docs(self, tmpdir):
        doctrees = tmpdir.join("doctrees")
        htmldir = tmpdir.join("html")
        subprocess.check_call(["sphinx-build", "-W", "-bhtml", "-d", str(doctrees), ".", str(htmldir)])
