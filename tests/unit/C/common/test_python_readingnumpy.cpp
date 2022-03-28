#include <gtest/gtest.h>
#include <pythonreading.h>
#include <string.h>
#include <string>
#include <logger.h>
#include <pyruntime.h>

using namespace std;

namespace {

const char *script = R"(
import numpy as np

def array_sort(arg, key):
    readings = arg["readings"];
    arr = readings[key];
    readings[key] = np.sort(arr)
    return arg

def image_normalise(arg, key):
    readings = arg["readings"]
    ar = readings[key]
    mn = np.min(ar)
    mx = np.max(ar)
    norm = (ar - mn) * (1.0 / (mx - mn))
    readings[key] = norm
    return arg
)";

class  PythonReadingNumpyTest : public testing::Test {
 protected:
	void SetUp() override
	{
		m_python = PythonRuntime::getPythonRuntime();
	}

	void TearDown() override
	{
	}

	PythonRuntime *m_python;

   public:
	void logErrorMessage(const char *name)
	{
		PyObject* type;
		PyObject* value;
		PyObject* traceback;


		PyErr_Fetch(&type, &value, &traceback);
		PyErr_NormalizeException(&type, &value, &traceback);

		PyObject* str_exc_value = PyObject_Repr(value);
		PyObject* pyExcValueStr = PyUnicode_AsEncodedString(str_exc_value, "utf-8", "Error ~");
		const char* pErrorMessage = value ?
					    PyBytes_AsString(pyExcValueStr) :
					    "no error description.";
		Logger::getLogger()->fatal("logErrorMessage: %s: Error '%s'", name, pErrorMessage);
		
		// Check for numpy/pandas import errors
		const char *err1 = "implement_array_function method already has a docstring";
		const char *err2 = "cannot import name 'check_array_indexer' from 'pandas.core.indexers'";

		
		std::string fcn = "";
		fcn += "def get_pretty_traceback(exc_type, exc_value, exc_tb):\n";
		fcn += "    import sys, traceback\n";
		fcn += "    lines = []\n"; 
		fcn += "    lines = traceback.format_exception(exc_type, exc_value, exc_tb)\n";
		fcn += "    output = '\\n'.join(lines)\n";
		fcn += "    return output\n";

		PyRun_SimpleString(fcn.c_str());
		PyObject* mod = PyImport_ImportModule("__main__");
		if (mod != NULL) {
			PyObject* method = PyObject_GetAttrString(mod, "get_pretty_traceback");
			if (method != NULL) {
				PyObject* outStr = PyObject_CallObject(method, Py_BuildValue("OOO", type, value, traceback));
				if (outStr != NULL) {
					PyObject* tmp = PyUnicode_AsASCIIString(outStr);
					if (tmp != NULL) {
						std::string pretty = PyBytes_AsString(tmp);
						Logger::getLogger()->fatal("%s", pretty.c_str());
						Logger::getLogger()->printLongString(pretty.c_str());
					}
					Py_CLEAR(tmp);
				}
				Py_CLEAR(outStr);
			}
			Py_CLEAR(method);
		}

		// Reset error
		PyErr_Clear();

		// Remove references
		Py_CLEAR(type);
		Py_CLEAR(value);
		Py_CLEAR(traceback);
		Py_CLEAR(str_exc_value);
		Py_CLEAR(pyExcValueStr);
		Py_CLEAR(mod);
	}

	PyObject *callPythonFunc(const char *name, PyObject *arg)
	{
		PyObject *rval = NULL;

		m_python->execute(script);
		rval = m_python->call(name, "(O)", arg);
		return rval;
	}

	PyObject *callPythonFunc2(const char *name, PyObject *arg1, PyObject *arg2)
	{
		PyObject *rval = NULL;

		m_python->execute(script);
		rval = m_python->call(name, "OO", arg1, arg2);
		return rval;
	}

};


TEST_F(PythonReadingNumpyTest, ArraySort)
{
	DataBuffer *buffer = new DataBuffer(sizeof(uint16_t), 5);
	uint16_t *ptr = (uint16_t *)buffer->getData();
	*ptr = 5;
	*(ptr + 1) = 4;
	*(ptr + 2) = 3;
	*(ptr + 3) = 2;
	*(ptr + 4) = 1;
	DatapointValue buf(buffer);
	Reading reading("test", new Datapoint("buffer", buf));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("buffer");
	PyObject *obj = callPythonFunc2("array_sort", pyReading, element);
	PythonReading pyr(obj);
	EXPECT_STREQ(pyr.getAssetName().c_str(), "test");
	EXPECT_EQ(pyr.getDatapointCount(), 1);
	Datapoint *dp = pyr.getDatapoint("buffer");
	if (!dp)
	{
		EXPECT_STREQ("Expected datapoint missing", "");
	}
	else
	{
		EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_DATABUFFER);
		DataBuffer *dpbuf = dp->getData().getDataBuffer();
		ptr = (uint16_t *)dpbuf->getData();
	
		EXPECT_EQ(*ptr, 1);
		EXPECT_EQ(*(ptr + 1), 2);
		EXPECT_EQ(*(ptr + 2), 3);
		EXPECT_EQ(*(ptr + 3), 4);
		EXPECT_EQ(*(ptr + 4), 5);
	}
}

TEST_F(PythonReadingNumpyTest, ImageFloat)
{
	void *data = malloc(64 * 96);
	uint8_t *ptr = (uint8_t *)data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 96; j++)
			*ptr = i;
	DPImage  *image = new DPImage(64, 96, 8, data);
	DatapointValue img(image);
	Reading reading("test", new Datapoint("image", img));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("image");
	PyObject *obj = callPythonFunc2("image_normalise", pyReading, element);
	EXPECT_NE(obj, (PyObject *)NULL);
	PythonReading pyr(obj);
	EXPECT_STREQ(pyr.getAssetName().c_str(), "test");
	EXPECT_EQ(pyr.getDatapointCount(), 1);
	Datapoint *dp = pyr.getDatapoint("image");
	if (!dp)
	{
		EXPECT_STREQ("Expected datapoint missing", "");
	}
	else
	{
		EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_IMAGE);
		DPImage *image2 = dp->getData().getImage();
		uint8_t *ptr = (uint8_t *)image2->getData();
		EXPECT_EQ(image2->getWidth(), image->getWidth());
		EXPECT_EQ(image2->getHeight(), image->getHeight());
		EXPECT_EQ(image2->getDepth(), 64);

		double *dptr = (double *)image2->getData();
		for (int i = 0; i < 64; i++)
		{
			for (int j = 0; j < 96; j++)
			{
				EXPECT_TRUE(*dptr >= 0.0 && *dptr <= 1.0);
				dptr++;
			}
		}
	}
}
}
