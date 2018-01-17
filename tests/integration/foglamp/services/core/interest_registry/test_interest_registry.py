# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import requests
import pytest
import uuid


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio

# Needs foglamp to start,
# replace 42921 with core_management_port
BASE_URL = 'http://localhost:42921/foglamp'
headers = {'Content-Type': 'application/json'}


@pytest.allure.feature("api")
@pytest.allure.story("interest-registry")
class TestInterestRegistryApi:

    def setup_method(self):
        pass

    def teardown_method(self):
        """clean up interest registry storage"""

        r = requests.get(BASE_URL + '/interest')
        if r.status_code in range(400, 500):
            return
        res = dict(r.json())
        t = res["interests"]
        for s in t:
            requests.delete(BASE_URL + '/interest/' + s["registrationId"])

    async def test_register_interest(self):
        data = {"category": "CC2650POLL", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert uuid.UUID(res["id"])
        assert "Interest registered successfully" == res["message"]

    async def test_unregister_interest(self):
        data = {"category": "COAP", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data), headers=headers)
        res = dict(r.json())
        assert 200 == r.status_code
        registration_id = res["id"]

        r = requests.delete(BASE_URL + '/interest/' + registration_id)
        retval = dict(r.json())
        assert 200 == r.status_code
        assert registration_id == retval["id"]
        assert "Interest unregistered" == retval["message"]

    async def test_get(self):
        data1 = {"category": "CAT1", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        registration_id1 = retval["id"]

        # Create another interest
        data2 = {"category": "CAT2", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data2), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        registration_id2 = retval["id"]

        r = requests.get(BASE_URL + '/interest')
        assert 200 == r.status_code

        retval = dict(r.json())
        interests = retval["interests"]
        assert 2 == len(interests)

        data1_interest = data2_interest = None
        for interest in interests:
            if interest["registrationId"] == registration_id1:
                data1_interest = interest
            if interest["registrationId"] == registration_id2:
                data2_interest = interest

        assert data1_interest is not None
        assert data1["category"] == data1_interest["category"]
        assert data1["service"] == data1_interest["microserviceId"]

        assert data2_interest is not None
        assert data2["category"] == data2_interest["category"]
        assert data2["service"] == data2_interest["microserviceId"]

    async def test_get_by_category(self):
        data = {"category": "CAT1", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        registration_id = retval["id"]

        r = requests.get(BASE_URL + '/interest?category={}'.format(data["category"]))
        assert 200 == r.status_code

        retval = dict(r.json())
        interest = retval["interests"]
        assert 1 == len(interest)
        assert interest is not None
        assert data["category"] == interest[0]["category"]
        assert data["service"] == interest[0]["microserviceId"]
        assert registration_id == interest[0]["registrationId"]

    async def test_get_by_microservice_id(self):
        microservice_id = str(uuid.uuid4())
        data = {"category": "CAT1", "service": microservice_id}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        registration_id = retval["id"]

        r = requests.get(BASE_URL + '/interest?microserviceid={}'.format(microservice_id))
        assert 200 == r.status_code

        retval = dict(r.json())
        interest = retval["interests"]
        assert 1 == len(interest)
        assert interest is not None
        assert data["category"] == interest[0]["category"]
        assert microservice_id == interest[0]["microserviceId"]
        assert registration_id == interest[0]["registrationId"]

    async def test_get_by_category_and_microservice_id(self):
        data1 = {"category": "CAT1", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code

        # Create another interest
        data2 = {"category": "CAT2", "service": str(uuid.uuid4())}
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data2), headers=headers)
        assert 200 == r.status_code

        r = requests.get(BASE_URL + '/interest?category={}&microserviceid={}'.format(data2["category"],
                                                                                     data2["service"]))
        assert 200 == r.status_code

        res = dict(r.json())
        interests = res["interests"]
        assert 1 == len(interests)

        assert data2["category"] == interests[0]["category"]
        assert data2["service"] == interests[0]["microserviceId"]

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('', 404, "No interest registered"),
        ('?any=123', 404, "No interest registered"),
        ('?category=blah', 404, "No interest registered for category blah"),
        ('?microserviceid=foo', 400, "Invalid microservice id foo"),
        ('?microserviceid=d2abe6d7-ce77-448a-b13f-b2ada202b63b', 404,
         'No interest registered microservice id d2abe6d7-ce77-448a-b13f-b2ada202b63b'),
        ('?microserviceid=d2abe6d7-ce77-448a-b13f-b2ada202b63b&category=foo', 404,
         'No interest registered for category foo and microservice id d2abe6d7-ce77-448a-b13f-b2ada202b63b')
    ])
    async def test_get_params_with_bad_data(self, request_params, response_code, response_message):
        r = requests.get(BASE_URL + '/interest{}'.format(request_params))
        assert response_code == r.status_code
        assert response_message == r.reason

    @pytest.mark.parametrize("data, response_code, response_message", [
        ({"category": "CAT1"}, 400, "Failed to register interest. microservice_uuid cannot be None"),
        ({"service": "0xe6ebd0"}, 400, "Invalid microservice id 0xe6ebd0"),
        ({"service": "d2abe6d7-ce77-448a-b13f-b2ada202b63b"}, 400,
         "Failed to register interest. category_name cannot be None")
    ])
    async def test_register_with_bad_data(self, data, response_code, response_message):
        r = requests.post(BASE_URL + '/interest', data=json.dumps(data), headers=headers)
        assert response_code == r.status_code
        assert response_message == r.reason

    @pytest.mark.parametrize("registration_id, response_code, response_message", [
        ('blah', 400, "Invalid registration id blah"),
        ('d2abe6d7-ce77-448a-b13f-b2ada202b63b', 404,
         "InterestRecord with registration_id d2abe6d7-ce77-448a-b13f-b2ada202b63b does not exist")
    ])
    async def test_unregister_with_bad_data(self, registration_id, response_code, response_message):
        r = requests.delete(BASE_URL + '/interest/' + registration_id)
        assert response_code == r.status_code
        assert response_message == r.reason
