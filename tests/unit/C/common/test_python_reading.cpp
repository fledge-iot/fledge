#include <gtest/gtest.h>
#include <pythonreading.h>
#include <string.h>
#include <string>
#include <logger.h>
#include <pyruntime.h>

using namespace std;

namespace {

const char *script = R"(
def count(arg):
    readings =  arg["readings"]
    return len(readings)

def element(arg, key):
    readings =  arg["readings"]
    return readings[key]

def assetCode(arg):
    return arg["asset"]

def returnIt(arg):
    return arg

def isDict(arg):
    return isinstance(arg, dict)

def setAsset(arg, name):
    arg["asset"] = name
    return arg

def array_element_0(arg, key):
    readings = arg["readings"];
    arr = readings[key];
    return arr[0]

def array_swap(arg, key):
    readings = arg["readings"];
    arr = readings[key];
    tmp = arr[0]
    arr[0] = arr[1]
    arr[1] = tmp
    return arg

def image_swap(arg, key):
    readings = arg["readings"];
    img = readings[key];
    return arg

def row_swap(arg, key):
    readings = arg["readings"];
    a2d = readings[key];
    newlist = [a2d[1], a2d[0]]
    readings[key] = newlist
    return arg
)";

class  PythonReadingTest : public testing::Test {
 protected:
	void SetUp() override
	{
		m_python = PythonRuntime::getPythonRuntime();
	}

	void TearDown() override
	{
	}


   public:
	PythonRuntime *m_python;

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

TEST_F(PythonReadingTest, SimpleSizeLong)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *obj = callPythonFunc("count", pyReading);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 1);
}

TEST_F(PythonReadingTest, IsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
}

TEST_F(PythonReadingTest, PyIsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *obj = callPythonFunc("isDict", pyReading);
	if (obj)
	{
		int truth = PyObject_IsTrue(obj);
		EXPECT_EQ(truth, 1);
	}
	else
		EXPECT_STREQ("Expected object to be returned", "");
}

TEST_F(PythonReadingTest, Py2IsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *obj = callPythonFunc("returnIt", pyReading);
	if (obj)
	{
		EXPECT_EQ(PyDict_Check(obj), true);
	}
	else
		EXPECT_EQ(true, false);
}

TEST_F(PythonReadingTest, SimpleLong)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *element = PyUnicode_FromString("long");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	EXPECT_EQ(PyLong_Check(obj), true);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 1234);
}

TEST_F(PythonReadingTest, SimpleDouble)
{
	double i = 1234.5;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("double", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *element = PyUnicode_FromString("double");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	EXPECT_EQ(PyFloat_Check(obj), true);
	double rval = PyFloat_AS_DOUBLE(obj);
	EXPECT_EQ(rval, 1234.5);
}

TEST_F(PythonReadingTest, DictCheck)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
}

TEST_F(PythonReadingTest, SimpleSizeString)
{
	DatapointValue value("just a string");
	Reading reading("test", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *obj = callPythonFunc("count", pyReading);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 1);
}

TEST_F(PythonReadingTest, SimpleString)
{
	DatapointValue value("just a string");
	Reading reading("test", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("str");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyUnicode_Check(obj), true);
		const char *rval = PyUnicode_AsUTF8(obj);
		EXPECT_STREQ(rval, "just a string");
	}
	else
	{
		EXPECT_STREQ("Expected a string object", "");
	}
}

TEST_F(PythonReadingTest, AssetCode)
{
	DatapointValue value("just a string");
	Reading reading("testAsset", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *obj = callPythonFunc("assetCode", pyReading);
	if (obj)
	{
		EXPECT_EQ(PyUnicode_Check(obj), true);
		const char *rval = PyUnicode_AsUTF8(obj);
		EXPECT_STREQ(rval, "testAsset");
	}
	else
	{
		EXPECT_STREQ("Expected a string object", "");
	}
}

TEST_F(PythonReadingTest, TwoDataPoints)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *obj = callPythonFunc("count", pyReading);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 2);
}

TEST_F(PythonReadingTest, TwoDifferentDataPoints)
{
	vector<Datapoint *> values;
	DatapointValue v1("just a string");
	DatapointValue v2((long)12345678);
	values.push_back(new Datapoint("s", v1));
	values.push_back(new Datapoint("l", v2));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *obj = callPythonFunc("count", pyReading);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 2);
	PyObject *element = PyUnicode_FromString("s");
	obj = callPythonFunc2("element", pyReading, element);
	EXPECT_EQ(PyUnicode_Check(obj), true);
	const char *sval = PyUnicode_AsUTF8(obj);
	EXPECT_STREQ(sval, "just a string");
	element = PyUnicode_FromString("l");
	obj = callPythonFunc2("element", pyReading, element);
	rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 12345678);
}

TEST_F(PythonReadingTest, TwoDataPointsFetchString1)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("s1");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyUnicode_Check(obj), true);
		const char *rval = PyUnicode_AsUTF8(obj);
		EXPECT_STREQ(rval, "just a string");
	}
	else
	{
		EXPECT_STREQ("Expected a string object", "");
	}
}

TEST_F(PythonReadingTest, TwoDataPointsFetchString2)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("s2");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyUnicode_Check(obj), true);
		const char *rval = PyUnicode_AsUTF8(obj);
		EXPECT_STREQ(rval, "just a string");
	}
	else
	{
		EXPECT_STREQ("Expected a string object", "");
	}
}

TEST_F(PythonReadingTest, DoubleListDataPoint)
{
	vector<double> values;
	values.push_back(1.4);
	values.push_back(3.7);
	DatapointValue value(values);
	Reading reading("test", new Datapoint("array", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("array");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyList_Check(obj), true);
	}
	else
	{
		EXPECT_STREQ("Expected a LIST object", "");
	}
}

TEST_F(PythonReadingTest, DictDataPoint)
{
	vector<Datapoint *> *values = new vector<Datapoint *>;
	DatapointValue value("just a string");
	values->push_back(new Datapoint("s1", value));
	values->push_back(new Datapoint("s2", value));
	DatapointValue dict(values, true);
	Reading reading("test", new Datapoint("child", dict));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("child");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyDict_Check(obj), true);
	}
	else
	{
		EXPECT_STREQ("Expected a DICT object", "");
	}
}

TEST_F(PythonReadingTest, DataBuffer)
{
	DataBuffer *buffer = new DataBuffer(sizeof(uint16_t), 10);
	uint16_t *ptr = (uint16_t *)buffer->getData();
	*ptr = 1234;
	*(ptr + 1) = 5678;
	DatapointValue buf(buffer);
	Reading reading("test", new Datapoint("buffer", buf));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("buffer");
	PyObject *obj = callPythonFunc2("element", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PythonReading::isArray(obj), true);
	}
	else
	{
		EXPECT_STREQ("Expected an array object", "");
	}
	obj = callPythonFunc2("array_element_0", pyReading, element);
	if (obj)
	{
		EXPECT_STREQ(obj->ob_type->tp_name, "numpy.uint16");
	}
	else
	{
		EXPECT_STREQ("Expected a long object", "");
	}
}

TEST_F(PythonReadingTest, SimpleLongRoundTrip)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *obj = callPythonFunc("returnIt", pyReading);
	if (obj)
	{
		PythonReading pyr(obj);
		EXPECT_STREQ(pyr.getAssetName().c_str(), "test");
		EXPECT_EQ(pyr.getDatapointCount(), 1);
		Datapoint *dp = pyr.getDatapoint("long");
		if (!dp)
		{
			EXPECT_STREQ("Expected datapoint missing", "");
		}
		else
		{
			EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_INTEGER);
			EXPECT_EQ(dp->getData().toInt(), 1234);
		}
	}
	else
	{
		EXPECT_STREQ("Expect PythonReading object missing", "");
	}
}

TEST_F(PythonReadingTest, SimpleStringRoundTrip)
{
	DatapointValue value("this is a string");
	Reading reading("test", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *obj = callPythonFunc("returnIt", pyReading);
	if (obj)
	{
		PythonReading pyr(obj);
		EXPECT_STREQ(pyr.getAssetName().c_str(), "test");
		EXPECT_EQ(pyr.getDatapointCount(), 1);
		Datapoint *dp = pyr.getDatapoint("str");
		if (!dp)
		{
			EXPECT_STREQ("Expected datapoint missing", "");
		}
		else
		{
			EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_STRING);
			EXPECT_STREQ(dp->getData().toStringValue().c_str(),
					"this is a string");
		}
	}
	else
	{
		EXPECT_STREQ("Expect PythonReading object missing", "");
	}
}

TEST_F(PythonReadingTest, DataBufferSwapRoundTrip)
{
	DataBuffer *buffer = new DataBuffer(sizeof(uint16_t), 10);
	uint16_t *ptr = (uint16_t *)buffer->getData();
	*ptr = 1234;
	*(ptr + 1) = 5678;
	DatapointValue buf(buffer);
	Reading reading("test", new Datapoint("buffer", buf));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("buffer");
	PyObject *obj = callPythonFunc2("array_swap", pyReading, element);
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
	
		EXPECT_EQ(*ptr, 5678);
		EXPECT_EQ(*(ptr + 1), 1234);
	}
}

TEST_F(PythonReadingTest, ImageRoundTrip)
{
	void *data = malloc(64 * 96);
	DPImage  *image = new DPImage(64, 96, 8, data);
	DatapointValue img(image);
	Reading reading("test", new Datapoint("image", img));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("image");
	PyObject *obj = callPythonFunc2("image_swap", pyReading, element);
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
		EXPECT_EQ(image2->getDepth(), image->getDepth());
	}
}

TEST_F(PythonReadingTest, UpdateAssetCode)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	EXPECT_EQ(PyDict_Check(pyReading), true);
	PyObject *newName = PyUnicode_FromString("shorter");
	PyObject *obj = callPythonFunc2("setAsset", pyReading, newName);
	if (obj)
	{
		PythonReading pyr(obj);
		EXPECT_STREQ(pyr.getAssetName().c_str(), "shorter");
		EXPECT_EQ(pyr.getDatapointCount(), 1);
		Datapoint *dp = pyr.getDatapoint("long");
		if (!dp)
		{
			EXPECT_STREQ("Expected datapoint missing", "");
		}
		else
		{
			EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_INTEGER);
			EXPECT_EQ(dp->getData().toInt(), 1234);
		}
	}
	else
	{
		EXPECT_STREQ("Expect PythonReading object missing", "");
	}
}

TEST_F(PythonReadingTest, Double2DArray)
{
	vector<vector<double>* > array;
	for (int i = 0; i < 2; i++)
	{
		vector<double> *row = new vector<double>;
		row->push_back(1.4 + i);
		row->push_back(3.7 + i);
		array.push_back(row);
	}

	DatapointValue value(array);
	Reading reading("test2d", new Datapoint("array", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("array");
	PyObject *obj = callPythonFunc2("row_swap", pyReading, element);
	if (obj)
	{
		EXPECT_EQ(PyDict_Check(obj), true);
		PythonReading pyr(obj);
		EXPECT_STREQ(pyr.getAssetName().c_str(), "test2d");
		EXPECT_EQ(pyr.getDatapointCount(), 1);
		Datapoint *dp = pyr.getDatapoint("array");
		EXPECT_EQ(dp->getData().getType(), DatapointValue::dataTagType::T_2D_FLOAT_ARRAY);
		vector<vector<double> *> *a2d = dp->getData().getDp2DArr();
		EXPECT_EQ(a2d->at(0)->at(0), 2.4);
		EXPECT_EQ(a2d->at(0)->at(1), 4.7);
		EXPECT_EQ(a2d->at(1)->at(0), 1.4);
		EXPECT_EQ(a2d->at(1)->at(1), 3.7);
	}
	else
	{
		EXPECT_STREQ("Expected a LIST object", "");
	}
}

};
