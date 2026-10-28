# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from unittest.mock import patch

import pytest

from fledge.services.core.api import python_packages


class FakeDistribution:
    def __init__(self, name, version):
        self.metadata = {'Name': name}
        self.version = version


def distributions(*dists):
    return patch.object(python_packages.metadata, 'distributions', return_value=list(dists))


class TestPythonPackages:

    @pytest.mark.parametrize("raw, expected", [
        ("typing_extensions", "typing-extensions"),
        ("jaraco.context", "jaraco-context"),
        ("Flask__Cors", "flask-cors"),
        ("requests", "requests"),
    ])
    def test_canonical_name(self, raw, expected):
        assert python_packages.canonical_name(raw) == expected

    def test_get_packages_installed(self):
        with distributions(FakeDistribution("typing_extensions", "4.1"), FakeDistribution("PyJWT", "2.4.0")):
            assert python_packages.get_packages_installed() == [
                {'package': 'typing-extensions', 'version': '4.1'},
                {'package': 'PyJWT', 'version': '2.4.0'}]

    def test_first_distribution_on_path_wins(self):
        with distributions(FakeDistribution("numpy", "1.26.4"), FakeDistribution("numpy", "2.0.0")):
            assert python_packages.get_installed_distributions() == {'numpy': ('numpy', '1.26.4')}

    def test_distribution_without_name_is_skipped(self):
        with distributions(FakeDistribution(None, "1.0"), FakeDistribution("requests", "2.0")):
            assert list(python_packages.get_installed_distributions()) == ['requests']

    def test_lookup_ignores_separator_and_case(self):
        with distributions(FakeDistribution("typing_extensions", "4.1")):
            installed = python_packages.get_installed_distributions()
        assert installed[python_packages.canonical_name("Typing.Extensions")] == ('typing-extensions', '4.1')

    @pytest.mark.parametrize("raw, expected", [
        ("typing_extensions", "typing-extensions"),
        ("jaraco.context", "jaraco.context"),
        ("Flask__Cors", "Flask-Cors"),
        ("requests", "requests"),
    ])
    def test_display_name_matches_pkg_resources_project_name(self, raw, expected):
        assert python_packages.display_name(raw) == expected
