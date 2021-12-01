#ifndef _PYRUNTIME_H
#define _PYRUNTIME_H
/*
 * Fledge Python Runtime.
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <Python.h>

class PythonRuntime {
	public:
		static PythonRuntime	*getPythonRuntime();
		void 	execute(const std::string& python);
		PyObject	*call(const std::string& name, const std::string& fmt, ...);
	private:
		PythonRuntime();
		PythonRuntime(const PythonRuntime& rhs);
		PythonRuntime& operator=(const PythonRuntime& rhs);
		void		logException(const std::string& name);

		static PythonRuntime	*m_instance;

};

#endif

