#include <gtest/gtest.h>
#include <pythonreadingset.h>
#include <string.h>
#include <string>
#include <logger.h>
#include <pyruntime.h>

using namespace std;

namespace {

const char *script = R"(
def count(set):
    return len(set)
)";

class  PythonReadingSetTest : public testing::Test {
 protected:
	void SetUp() override
	{
		m_python = PythonRuntime::getPythonRuntime();
	}

	void TearDown() override
	{
	}

   public:
	PythonRuntime	*m_python;

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

TEST_F(PythonReadingSetTest, SingleReading)
{  
	vector<Reading *> *readings = new vector<Reading *>;
	long i = 1234;
	DatapointValue value(i);
	readings->push_back(new Reading("test", new Datapoint("long", value)));
	ReadingSet set(readings);
	PyObject *pySet = ((PythonReadingSet *)(&set))->toPython();
	PyObject *obj = callPythonFunc("count", pySet);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 1);
}

TEST_F(PythonReadingSetTest, MultipleReadings)
{
	vector<Reading *> *readings = new vector<Reading *>;
	long i = 1234;
	DatapointValue value(i);
	readings->push_back(new Reading("test", new Datapoint("long", value)));
	readings->push_back(new Reading("test", new Datapoint("long", value)));
	readings->push_back(new Reading("test", new Datapoint("long", value)));
	ReadingSet set(readings);
	PyObject *pySet = ((PythonReadingSet *)(&set))->toPython();
	PyObject *obj = callPythonFunc("count", pySet);
	long rval = PyLong_AsLong(obj);
	EXPECT_EQ(rval, 3);
}
}
