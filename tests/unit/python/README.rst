******************
FogLAMP Unit Tests
******************

Unit tests are the first category of test in FogLAMP. These test ensures that every single function of your code under
test is generating the desired output.

FogLAMP unit tests heavily use test doubles to replace a production object. A typical example is a code fragment that
requires a database connection. Instead of creating a database connection, we create a mock object that can be used.
By doing this, we can make sure that our unit-tests are not dependent on external systems. This approach also helps to
minimise the test execution time of unit tests. For example:
::
    def mock_request(data):
        payload = StreamReader(loop=loop)
        payload.feed_data(data.encode())
        payload.feed_eof()

        protocol = mock.Mock()
        app = mock.Mock()
        headers = CIMultiDict([('CONTENT-TYPE', 'application/json')])
        req = make_mocked_request('POST', '/sensor-reading', headers=headers, protocol=protocol, payload=payload, app=app)
        return req

This code creates a mock request and can replace a POST request to the the endpoint ``/sensor-readings``., like:
::
    async def test_post_sensor_reading_ok(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""
        with patch.object(Ingest, 'add_readings', return_value=asyncio.ensure_future(asyncio.sleep(0.1))) as mock_method1:
            with patch.object(Ingest, 'is_available', return_value=True) as mock_method2:
                request = mock_request(data)
                r = await HttpSouthIngest.render_post(request)
                retval = json.loads(r.body.decode())
                # Assert the POST request response
                assert 200 == retval['status']
                assert 'success' == retval['result']

Note the use of ``mock_request``, we are mocking a request to the endpoint ``/sensor-readings`` and not making any actual request.
