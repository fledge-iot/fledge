#include <gtest/gtest.h>
#include <pythonreading.h>
#include <string.h>
#include <string>
#include <logger.h>

using namespace std;

const char *script = R"(
def count(arg):
    readings =  arg["reading"]
    return len(readings)

def element(arg, key):
    readings =  arg["reading"]
    return readings[key]

def assetCode(arg):
    return arg["asset_code"]

def returnIt(arg):
    return arg

def isDict(arg):
    return isinstance(arg, dict)
)";

PyObject *pModule = NULL;

bool definePythonFuncs(const char *python)
{
	PyObject *pName, *pArgs, *pValue, *pFunc;
	PyObject *pGlobal = PyDict_New();
	PyObject *pLocal;

	Py_Initialize();

	//Create a new module object
	pModule = PyModule_New("testpython");
	if (!pModule)
		return false;


	PyModule_AddStringConstant(pModule, "__file__", "");

	//Get the dictionary object from my module so I can pass this to PyRun_String
	pLocal = PyModule_GetDict(pModule);

	//Define my function in the newly created module
	pValue = PyRun_String(python, Py_file_input, pGlobal, pLocal);
	if (pValue == NULL) {
		if (PyErr_Occurred()) {
			PyErr_Print();
		}
		return false;
	}
	Py_DECREF(pValue);
	return true;
}

PyObject *callPythonFunc(const char *name, PyObject *arg)
{
	PyObject *pArgs, *pValue, *pFunc;
	Logger *log = Logger::getLogger();

	//Get a pointer to the function I just defined
	pFunc = PyObject_GetAttrString(pModule, name);
	if (!pFunc)
		log->fatal("failed to find function %s", name);
	if (!PyCallable_Check(pFunc))
		log->fatal("Python functin %s is not callable", name);

	//Build a tuple to hold my arguments (just the number 4 in this case)
	pArgs = PyTuple_New(1);
	PyTuple_SetItem(pArgs, 0, arg);

	//Call my function, passing it the number four
	// pValue = PyObject_CallFunctionObjArgs(pFunc, arg);
	pValue = PyObject_CallObject(pFunc, pArgs);
	//pValue = PyObject_CallFunction(pFunc, "O", arg);
	if (PyErr_Occurred())
	{
		log->fatal("Error occurred in %s", name);
		PyErr_Print();
	}
	Py_DECREF(pArgs);
	Py_XDECREF(pFunc);

	return pValue;
}

PyObject *callPythonFunc2(const char *name, PyObject *arg1, PyObject *arg2)
{
	PyObject *pArgs, *pValue, *pFunc;
	Logger *log = Logger::getLogger();

	//Get a pointer to the function I just defined
	pFunc = PyObject_GetAttrString(pModule, name);
	if (!pFunc)
		log->fatal("failed to find function %s", name);
	if (!PyCallable_Check(pFunc))
		log->fatal("Python functin %s is not callable", name);

	//Build a tuple to hold my arguments (just the number 4 in this case)
	pArgs = PyTuple_New(2);
	PyTuple_SetItem(pArgs, 0, arg1);
	PyTuple_SetItem(pArgs, 1, arg2);

	//Call my function, passing it the number four
	// pValue = PyObject_CallFunctionObjArgs(pFunc, arg);
	pValue = PyObject_CallObject(pFunc, pArgs);
	if (PyErr_Occurred())
	{
		log->fatal("Error occurred in %s", name);
		PyErr_Print();
	}
	Py_DECREF(pArgs);
	Py_XDECREF(pFunc);

	return pValue;
}

static void logErrorMessage()
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
	Logger::getLogger()->fatal("logErrorMessage: Error '%s'", pErrorMessage);
	
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

void pythonFinalize()
{
	Py_DECREF(pModule);
	Py_Finalize();
}

TEST(PythonReadingTest, SimpleSizeLong)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("count", pyReading);
		long rval = PyLong_AsLong(obj);
		ASSERT_EQ(rval, 1);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, IsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	definePythonFuncs(script);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	ASSERT_EQ(PyDict_Check(pyReading), true);
	pythonFinalize();
}

#if 0
TEST(PythonReadingTest, PyIsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	definePythonFuncs(script);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	ASSERT_EQ(PyDict_Check(pyReading), true);
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("isDict", pyReading);
		if (obj)
		{
			int truth = PyObject_IsTrue(obj);
			ASSERT_EQ(truth, 1);
		}
		else
			ASSERT_EQ(true, false);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}
#endif

TEST(PythonReadingTest, Py2IsDict)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	definePythonFuncs(script);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	ASSERT_EQ(PyDict_Check(pyReading), true);
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("returnIt", pyReading);
		if (obj)
		{
			ASSERT_EQ(PyDict_Check(obj), true);
		}
		else
			ASSERT_EQ(true, false);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, SimpleLong)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	ASSERT_EQ(PyDict_Check(pyReading), true);
	PyObject *element = PyUnicode_FromString("long");
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc2("element", pyReading, element);
		ASSERT_EQ(PyLong_Check(obj), true);
		long rval = PyLong_AsLong(obj);
		ASSERT_EQ(rval, 1234);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, DictCheck)
{
	long i = 1234;
	DatapointValue value(i);
	Reading reading("test", new Datapoint("long", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	ASSERT_EQ(PyDict_Check(pyReading), true);
	PyObject *element = PyUnicode_FromString("reading");
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc2("element", pyReading, element);
		if (obj && PyDict_Check(obj))
			ASSERT_EQ(true, true);
		else
			ASSERT_EQ(false, false);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, SimpleSizeString)
{
	DatapointValue value("just a string");
	Reading reading("test", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("count", pyReading);
		long rval = PyLong_AsLong(obj);
		ASSERT_EQ(rval, 1);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, SimpleString)
{
	DatapointValue value("just a string");
	Reading reading("test", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("str");
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc2("element", pyReading, element);
		if (obj)
		{
			ASSERT_EQ(PyUnicode_Check(obj), true);
			char *rval = PyUnicode_AsUTF8(obj);
			ASSERT_EQ(strcmp(rval, "just a string"), 0);
		}
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, AssetCode)
{
	DatapointValue value("just a string");
	Reading reading("testAsset", new Datapoint("str", value));
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("assetCode", pyReading);
		if (obj)
		{
			ASSERT_EQ(PyUnicode_Check(obj), true);
			char *rval = PyUnicode_AsUTF8(obj);
			ASSERT_EQ(strcmp(rval, "testAsset"), 0);
		}
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, TwoDataPoints)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc("count", pyReading);
		long rval = PyLong_AsLong(obj);
		ASSERT_EQ(rval, 2);
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, TwoDataPointsFetchString1)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("s1");
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc2("element", pyReading, element);
		if (obj)
		{
			ASSERT_EQ(PyUnicode_Check(obj), true);
			char *rval = PyUnicode_AsUTF8(obj);
			ASSERT_EQ(strcmp(rval, "just a string"), 0);
		}
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}

TEST(PythonReadingTest, TwoDataPointsFetchString2)
{
	vector<Datapoint *> values;
	DatapointValue value("just a string");
	values.push_back(new Datapoint("s1", value));
	values.push_back(new Datapoint("s2", value));
	Reading reading("test", values);
	PyObject *pyReading = ((PythonReading *)(&reading))->toPython();
	PyObject *element = PyUnicode_FromString("s2");
	if (definePythonFuncs(script))
	{
		PyObject *obj = callPythonFunc2("element", pyReading, element);
		if (obj)
		{
			ASSERT_EQ(PyUnicode_Check(obj), true);
			char *rval = PyUnicode_AsUTF8(obj);
			ASSERT_EQ(strcmp(rval, "just a string"), 0);
		}
	}
	else
		ASSERT_EQ(true, false);
	pythonFinalize();
}
