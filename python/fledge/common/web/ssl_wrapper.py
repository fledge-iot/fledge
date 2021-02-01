# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Python SSL wrapper for openssl"""

import time
import datetime
import subprocess
from fledge.common import logger

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)


class SSLVerifier(object):
    class VerificationError(ValueError):
        pass

    user_cert = None
    ca_cert = None

    def __init__(self, cert_user=None, cert_ca=None):
        self.__class__.user_cert = cert_user
        self.__class__.ca_cert = cert_ca

    @classmethod
    def verify(cls):
        if cls.user_cert is None:
            raise OSError("No user certificate supplied.")
        cls.verify_against_revoked()
        result = cls.verify_against_ca()[0].split("stdin:")[1]
        return result.strip()

    @classmethod
    def verify_expired(cls, attime=str(time.time())):
        if cls.user_cert is None:
            raise OSError("No user certificate supplied.")

        echo_process = subprocess.Popen(['echo', cls.user_cert], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        a = subprocess.Popen(["openssl", "verify", "-CAfile", cls.ca_cert, "-x509_strict", "-attime", attime], stdin=echo_process.stdout, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        outs, errs = a.communicate()
        if outs is None and errs is None:
            raise OSError(
                'Verification error in executing command "{}"'.format("openssl verify -CAfile {} -x509_strict".format(cls.ca_cert)))
        if a.returncode != 0:
            raise OSError(
                'Verification error in executing command "{}". Error: {}, returncode: {}'.format("openssl verify -CAfile {} -x509_strict".format(cls.ca_cert), errs.decode('utf-8').replace('\n', ''), a.returncode))
        d = [b for b in outs.decode('utf-8').split('\n') if b != '']
        return False if "OK" in d[0] else True

    @classmethod
    def get_revoked_fingerprint(cls):
        # TODO: Work out a mechanism to populate REVOKED_CERTS like
        # REVOKED_CERTS = [
        #     'F8:7F:30:7B:12:15:15:47:07:93:D4:99:8F:7B:2E:DF:'
        #     '12:5A:2C:0F:C4:BD:5E:56:B8:5C:93:A3:65:CB:63:9B',
        #     '00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:'
        #     '12:5A:2C:0F:C4:BD:5E:56:B8:5C:93:A3:65:CB:63:9B',
        #     '36:9F:36:7F:0C:90:26:A1:AD:A3:79:E9:A9:8B:F5:74:'
        #     '21:B1:29:4B:67:73:78:B4:DE:CF:FA:C5:A6:42:BA:03',
        # ]
        REVOKED_CERTS = []
        return REVOKED_CERTS

    @classmethod
    def verify_against_revoked(cls):
        revoked_fingerprints = cls.get_revoked_fingerprint()
        fp = cls.get_fingerprint()
        if fp in revoked_fingerprints:
            raise SSLVerifier.VerificationError(
                str(), 'matches revoked fingerprint', fp)

    @classmethod
    def verify_against_ca(cls):
        echo_process = subprocess.Popen(['echo', cls.user_cert], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        a = subprocess.Popen(["openssl", "verify", "-CAfile", cls.ca_cert, "-x509_strict"], stdin=echo_process.stdout, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        outs, errs = a.communicate()
        if outs is None and errs is None:
            raise OSError(
                'Verification error in executing command "{}"'.format("openssl verify -CAfile {} -x509_strict".format(cls.ca_cert)))
        if a.returncode != 0:
            raise OSError(
                'Verification error in executing command "{}". Error: {}, returncode: {}'.format("openssl verify -CAfile {} -x509_strict".format(cls.ca_cert), errs.decode('utf-8').replace('\n', ''), a.returncode))
        d = [b for b in outs.decode('utf-8').split('\n') if b != '']
        if "OK" not in d[0]:
            raise SSLVerifier.VerificationError(
                str(), 'failed verification', errs)
        return d


    """
        Common x509 options:
         -serial         - print serial number value
         -subject_hash   - print subject hash value
         -subject_hash_old   - print old-style (MD5) subject hash value
         -issuer_hash    - print issuer hash value
         -issuer_hash_old    - print old-style (MD5) issuer hash value
         -hash           - synonym for -subject_hash
         -subject        - print subject DN
         -issuer         - print issuer DN
         -email          - print email address(es)
         -startdate      - notBefore field
         -enddate        - notAfter field
         -purpose        - print out certificate purposes
         -dates          - both Before and After dates
         -modulus        - print the RSA key modulus
         -pubkey         - output the public key
         -fingerprint    - print the certificate fingerprint
         -alias          - output certificate alias
    """

    @classmethod
    def get_x509(cls, cmd):
        if cls.user_cert is None:
            raise OSError("No user certificate supplied.")
        echo_process = subprocess.Popen(['echo', cls.user_cert], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        a = subprocess.Popen(["openssl", "x509", "-noout", "-nameopt", "sep_comma_plus_space", cmd], stdin=echo_process.stdout, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        outs, errs = a.communicate()
        if outs is None and errs is None:
            raise OSError(
                'Error in executing command "{}"'.format("openssl x509 -noout {}".format(cmd)))
        if a.returncode != 0:
            raise OSError(
                'Error in executing command "{}". Error: {}, return code: {}'.format(cmd, errs.decode('utf-8').replace('\n', ''), a.returncode))
        d = [b for b in outs.decode('utf-8').split('\n') if b != '']
        return d

    @classmethod
    def get_serial(cls):
        cmd = '-serial'
        serial = cls.get_x509(cmd=cmd)[0].split("serial=")[1].strip()
        return serial

    @classmethod
    def get_purposes(cls):
        cmd = '-purpose'
        purposes = cls.get_x509(cmd=cmd)
        return purposes

    @classmethod
    def get_issuer_common_name(cls):
        cmd = '-issuer'
        issuer = cls.get_x509(cmd=cmd)[0].split("issuer=")[1].strip()
        return issuer

    @classmethod
    def get_subject(cls):
        cmd = '-subject'
        subject_text = cls.get_x509(cmd=cmd)[0].split("subject=")[1].strip()
        subject = subject_text.strip().split(", ")

        country = next(filter(lambda x: x.startswith("C="), subject), None)
        state = next(filter(lambda x: x.startswith("ST="), subject), None)
        organisation = next(filter(lambda x: x.startswith("O="), subject), None)
        commonName = next(filter(lambda x: x.startswith("CN="), subject), None)
        email = next(filter(lambda x: x.startswith("emailAddress="), subject), None)

        subject_dict = {
            "country": "" if country is None else country.split("C=")[1],
            "state": "" if state is None else state.split("ST=")[1],
            "organisation": "" if organisation is None else organisation.split("O=")[1],
            "commonName": "" if commonName is None else commonName.split("CN=")[1],
            "email": "" if email is None else email.split("emailAddress=")[1],
        }
        return subject_dict

    @classmethod
    def get_fingerprint(cls):
        cmd = '-fingerprint'
        fp = cls.get_x509(cmd=cmd)[0].split("SHA1 Fingerprint=")[1].strip()
        return fp

    @classmethod
    def get_pubkey(cls):
        cmd = '-pubkey'
        pk = cls.get_x509(cmd=cmd)[0].strip()
        return pk

    @classmethod
    def get_startdate(cls):
        cmd = '-startdate'
        stdt = cls.get_x509(cmd=cmd)[0].split("notBefore=")[1].strip()
        return stdt

    @classmethod
    def get_enddate(cls):
        cmd = '-enddate'
        enddt = cls.get_x509(cmd=cmd)[0].split("notAfter=")[1].strip()
        return enddt

    @classmethod
    def is_expired(cls):
        enddt = cls.get_enddate()
        dt_format = "%b %d %X %Y %Z"  # Mar 12 12:31:57 2020 GMT
        cert_time = time.mktime(datetime.datetime.strptime(enddt, dt_format).timetuple())
        curr_time = time.time()
        return True if cert_time < curr_time else False

    @classmethod
    def set_ca_cert(cls, cert):
        cls.ca_cert = cert

    @classmethod
    def set_user_cert(cls, cert):
        cls.user_cert = cert
