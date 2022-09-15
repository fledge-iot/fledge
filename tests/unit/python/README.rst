******************
Fledge Unit Tests
******************

Unit tests are the first category of test in Fledge. These test ensures that every single function of your code under
test is generating the desired output.

Fledge unit tests heavily use test doubles to replace a production object. A typical example is a code fragment that
requires a database connection. Instead of creating a database connection, we create a mock object that can be used.
By doing this, we can make sure that our unit-tests are not dependent on external systems. This approach also helps to
minimise the test execution time of unit tests. For example:
::
    def mock_request(data, loop):
        payload = StreamReader("http", loop=loop, limit=1024)
        payload.feed_data(data.encode())
        payload.feed_eof()

        protocol = mock.Mock()
        app = mock.Mock()
        headers = CIMultiDict([('CONTENT-TYPE', 'application/json')])
        req = make_mocked_request('POST', '/sensor-reading', headers=headers,
                                  protocol=protocol, payload=payload, app=app)
        return req

This code creates a mock request and can be used as follows:
::
    async def test_post_sensor_reading_ok(self, event_loop):
        # event_loop is a fixture from pytest-asyncio
        data = """{
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
        with patch.object(Ingest, 'add_readings', return_value=asyncio.ensure_future(asyncio.sleep(0.1))):
            with patch.object(Ingest, 'is_available', return_value=True):
                request = mock_request(data, event_loop)
                r = await HttpSouthIngest.render_post(request)
                retval = json.loads(r.body.decode())
                # Assert the POST request response
                assert 200 == retval['status']
                assert 'success' == retval['result']


Note the use of patch object context managers, we are patching the ``add_readings`` and ``is_available`` methods of ``Ingest`` class,
further we are also using the mock object created above for creating a POST request to ``/sensor-readings`` endpoint.
