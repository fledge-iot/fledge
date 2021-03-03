# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test fledge/common/web/ssl_wrapper.py """

import time
import datetime
import pytest
from fledge.common.web.ssl_wrapper import SSLVerifier

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "web")
class TestSSLVerifier:
    @pytest.fixture
    def user_cert(self):
        user_cert = """-----BEGIN CERTIFICATE-----
MIIDeDCCAWACAQEwDQYJKoZIhvcNAQELBQAwHTELMAkGA1UEBhMCVVMxDjAMBgNV
BAMMBU1ZLUNBMB4XDTE5MTIxOTEwMDAyOVoXDTIwMTIxODEwMDAyOVowazELMAkG
A1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExEDAOBgNVBAoMB09TSXNvZnQx
DTALBgNVBAMMBHVzZXIxJjAkBgkqhkiG9w0BCQEWF2ZsZWRnZUBnb29nbGVncm91
cHMuY29tMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC2vbHDyp5teGbEaLb/
G5BnRcXcLMs9fbimyYYt7Xhb5OEVuiGPD8npwBfsd0aE12BfoJVARjn/xjkk1rib
Zj0LEocKWfQoYgRjIwzVSdR/uczF/0Xpj68UlvcRxoPsP3LzYQ7i8Smdqn5NI9R1
P4i8GGOSY/+c+8umd44T6H/jBwIDAQABMA0GCSqGSIb3DQEBCwUAA4ICAQAU+lnr
ImUhPb8U6Tmf4diphJCTADK3zy3qYNmqndLiVutsK32Q/1Gg+My8rtxv7gpPztpF
H+xPtSsYLfdJtcI2xM9nnx3G442/3Zf5tEGDZdsIvedzPw6kjO9coKD1lwkKtXkl
Ky9TjsnUIkHe91l5c7KwVcxu6b/Zb2ye7uS/CQEC14QVeKbitsovNzAuNZt1JgHl
cwPAsrobjL+VgJ1O8l/PLijCh6bgeUZQlTdPqIAZN5hFusx8vPYzfRclNteUQGAh
K020oXuZNRIb9bb8z8wL6g2JBs4c9cDz6/JgdQs226UEsMrUiTGZTyxR5PucCqc7
09l8vVHInD+mC1HNW4n3aJNSl2qGUAWLU9dWmsKOKQYPxZ8R3UShJnNsxJY476iQ
dIU5RZzJqVTmFiYLs62Tap+1thTQDjIqf8bKR7bZ3vL08eyiayEeMRGbkClqWIbl
duLdJ28ZzNMDfSuPF5yk/y8L5dc2XCbYCj3puOXgzrMlmVdAPUdGX6952dLLlqxz
87hMLe+ZB709EN/sPGt9SmifLal3rx+/dv5ZiHsiCSi/FXdVBRpim+aLh99MG2WS
PYPBNg5UKCYfUESU1F7V8fZMwH9Go3Qi+YjfL+K9wjN+c+Il/VXBYsLxypJy7QF0
5eCXag4hEQPihXbjPAgO+LNezaaOuNeW79upfw==
-----END CERTIFICATE-----
"""
        return user_cert

    @pytest.fixture
    def err_cert(self):
        err_cert = """-----BEGIN CERTIFICATE-----
MIICVTCCAb4CCQDhiCBFZbIH6DANBgkqhkiG9w0BAQsFADBvMQswCQYDVQQGEwJV
UzETMBEGA1UECAwKQ2FsaWZvcm5pYTEQMA4GA1UECgwHT1NJc29mdDEQMA4GA1UE
AwwHZm9nbGFtcDEnMCUGCSqGSIb3DQEJARYYZm9nbGFtcEBnb29nbGVncm91cHMu
Y29tMB4XDTE5MDMxMjA4NTM0MVoXDTIwMDMxMTA4NTM0MVowbzELMAkGA1UEBhMC
VVMxEzARBgNVBAgMCkNhbGlmb3JuaWExEDAOBgNVBAoMB09TSXNvZnQxEDAOBgNV
BAMMB2ZvZ2xhbXAxJzAlBgkqhkiG9w0BCQEWGGZvZ2xhbXBAZ29vZ2xlZ3JvdXBz
LmNvbTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAn1uwj9sV2q339JJHgI/N
gQbN9She64YgcO/pKlstd+luWPKNQSa/xHQVjPvqAMppFaCcCV4diJ+ExjDteKPU
I7PG1txD2FH/6o79oG2MC25qD79xFIZjYa4LFXZapozKIPfUdayG9StNRkgaLkAW
DNTWZW26lTFj2YCsy39S0EMCAwEAATANBgkqhkiG9w0BAQsFAAOBgQAOZPUVTARo
AShK4DM84LGNChzbdD6EVAl066+d9FRDuoX0KJj2/qepeevh2LC8dqG/QHcl75Ef
6FhhGzmSosgTHT4GVpFVS3V7fe1TVRfW8QG9MToF3N4nCOHzYRzLQVA+3qXpEy9y
49JyAKd2BhhczmXi/xtSrhn2JctKf/1MFA=
-----END CERTIFICATE-----
"""
        return err_cert

    def test_x509_values_with_valid_cert(self, user_cert):
        SSLVerifier.set_user_cert(user_cert)
        assert '01' == SSLVerifier.get_serial()
        assert ['Certificate purposes:', 'SSL client : Yes',
                'SSL client CA : No', 'SSL server : Yes', 'SSL server CA : No',
                'Netscape SSL server : Yes', 'Netscape SSL server CA : No',
                'S/MIME signing : Yes', 'S/MIME signing CA : No',
                'S/MIME encryption : Yes', 'S/MIME encryption CA : No',
                'CRL signing : Yes', 'CRL signing CA : No', 'Any Purpose : Yes',
                'Any Purpose CA : Yes', 'OCSP helper : Yes',
                'OCSP helper CA : No', 'Time Stamp signing : No',
                'Time Stamp signing CA : No'] == SSLVerifier.get_purposes()
        assert 'C=US, CN=MY-CA' == SSLVerifier.get_issuer_common_name()
        assert {'email': 'fledge@googlegroups.com', 'commonName': 'user',
                'organisation': 'OSIsoft', 'state': 'California',
                'country': 'US'} == SSLVerifier.get_subject()
        assert '69:5A:CC:85:3C:8E:D4:14:05:65:21:31:E3:91:9B:BA:35:74:4D:A3' == SSLVerifier.get_fingerprint()
        assert '-----BEGIN PUBLIC KEY-----' == SSLVerifier.get_pubkey()
        assert 'Dec 19 10:00:29 2019 GMT' == SSLVerifier.get_startdate()
        assert 'Dec 18 10:00:29 2020 GMT' == SSLVerifier.get_enddate()

        # Test is_expired(). It should return False if cert end time is yet to come.
        dt_format = "%b %d %X %Y %Z"
        cert_end_time = time.mktime(
            datetime.datetime.strptime('Dec 18 10:00:29 2020 GMT',
                                       dt_format).timetuple())
        run_time = time.time()
        expected = False if cert_end_time > run_time else True

        assert expected == SSLVerifier.is_expired()

    def test_x509_values_with_invalid_cert(self, err_cert):
        SSLVerifier.set_user_cert(err_cert)
        with pytest.raises(OSError):
            assert '01' == SSLVerifier.get_serial()
