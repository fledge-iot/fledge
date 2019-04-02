# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/web/ssl_wrapper.py """

import time
import datetime
import pytest
from foglamp.common.web.ssl_wrapper import SSLVerifier

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
MIIDeTCCAWECAQEwDQYJKoZIhvcNAQELBQAwHTELMAkGA1UEBhMCVVMxDjAMBgNV
BAMMBU1ZLUNBMB4XDTE5MDMxMjAzNTAzM1oXDTIwMDMxMTAzNTAzM1owbDELMAkG
A1UEBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExEDAOBgNVBAoMB09TSXNvZnQx
DTALBgNVBAMMBHVzZXIxJzAlBgkqhkiG9w0BCQEWGGZvZ2xhbXBAZ29vZ2xlZ3Jv
dXBzLmNvbTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAukBTH+FVzIQfawlF
VX+YBe5E8b/NDXYaauDrX9s61Crm+eezs50U2Lr1lCN2nDdiSYsyIulsK11dNFaf
/ka/Uyz4Ty89dxcQbZ0on0zOE2sRrEnpznPC5D5dbdFOlTDq04YoNj4XrACxnzD/
GrHdwRdwFbkL/exT77+yS0K4IQMCAwEAATANBgkqhkiG9w0BAQsFAAOCAgEA1SRb
z8YMLLQJxKDRpasdt07jxNwzOHK592YXiNHKZjMMqqOWbixnLQEg9socDmqq8AFA
m1jm6RXIL9rr79monNRRhbWf61cq4CnV2YlzcmVgcSRC9eK1OMHsrRUSX45V6Urx
X9S2mj8VR48R31pJ5u0wAMN35Dcw2KuUlMykfVgCGVXRKkvNx5Ju6CvOLyS+SgAk
vxe2wOQ771aG6o2ej8y68kfcgdh4mUBbbTQ8ZmvSIdn5Je9Fru4Xa9/ubz68Jplh
+odQ78wSEgduNYcRAbZKdRgXJF26Zv8JfbClJ9ByKn1OuYNi6Q/fzre9WxUu8ebh
vb3fFM1M5Jr1N/cP7PYGqlLclbUzV2CQDNPjFK2eIqt2y/1RdeHF+gQOU324UBEV
UOwDqaXkY/a8oHQuosU4UBBAvdWT4iWv1ohNB2IO0JOh3tfyQ4czxYH2x8CAB1vl
oWtOz3Rc8Qft9sboD9ZohDNpGP7mxgQ9D6Nr45yNU4u+9BrvknLSivqj0/Rgkm58
v70YDJwNZbe8YH2HXeZeT2MxoPeCo1fGz+E4zdo5VOtnfKx3+LB654Wvjj4zPSaw
7s75YazaQIaa52eDABGrHEjHLc/s4TeMGT+G/03RvHhf3BlS/Yp3fJMXpepbxaDh
49uU39h2BzBoHqvPLjW4sFZIe562Y3u2a9SKYoo=
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
        assert {'email': 'foglamp@googlegroups.com', 'commonName': 'user',
                'organisation': 'OSIsoft', 'state': 'California',
                'country': 'US'} == SSLVerifier.get_subject()
        assert 'E1:25:2F:8E:53:54:FE:EE:D2:F0:CD:D3:25:33:D3:5E:85:DD:FA:25' == SSLVerifier.get_fingerprint()
        assert '-----BEGIN PUBLIC KEY-----' == SSLVerifier.get_pubkey()
        assert 'Mar 12 03:50:33 2019 GMT' == SSLVerifier.get_startdate()
        assert 'Mar 11 03:50:33 2020 GMT' == SSLVerifier.get_enddate()

        # Test is_expired(). It should return False if cert end time is yet to come.
        dt_format = "%b %d %X %Y %Z"  # Mar 12 12:31:57 2020 GMT
        cert_end_time = time.mktime(
            datetime.datetime.strptime('Mar 11 03:50:33 2020 GMT',
                                       dt_format).timetuple())
        run_time = time.time()
        expected = False if cert_end_time > run_time else True

        assert expected == SSLVerifier.is_expired()

    def test_x509_values_with_invalid_cert(self, err_cert):
        SSLVerifier.set_user_cert(err_cert)
        with pytest.raises(OSError):
            assert '01' == SSLVerifier.get_serial()
