#ifndef _LAZYJSON_H
#define _LAZYJSON_H
/*
 * Fledge simplified JSON parsing.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <stack>
#include <string>
#include <ctype.h>


/**
 * The LazyJSON class is an attempt to improve performane by having a highly customised
 * JSON parse avilable to Fledge. In particular this has the following behaviours
 *
 * 	Avoid memory allocation and deallocation
 * 	Don't parse into a DOM structure
 * 	Allow extraction of raw JSON objects without the need to fully parse and serialise them
 *
 * As we don't parse the JSON document completely at the start we loose the ability to immediately
 * determine if the JSON document is valid or not. This is somehting we have sacrificed for the
 * above behaviours and means we should only really use LazyJSON if we are fairly confident in the
 * validity of the JSON we are parsing.
 */
class LazyJSON {
	public:
		LazyJSON(const char *str);
		LazyJSON(const std::string& str);
		~LazyJSON();
		const char		*getAttribute(const std::string& name);
		inline bool		isObject(const char *p) { return *p == '{'; };
		inline bool		isArray(const char *p) { return *p == '['; };
		inline bool		isString(const char *p) { return *p == '"'; };
		inline bool		isNumeric(const char *p) { return isdigit(*p); };
		bool			isNull(const char *p);
		bool			isBool(const char *p);
		bool			isTrue(const char *p);
		bool			isFalse(const char *p);
		const char		*getArray(const char *p);
		const char		*nextArrayElement(const char *p);
		const char		*getObject(const char *p);
		char			*getRawObject(const char *p);
		char			*getString(const char *p);
		void			popState();
	private:
		class LazyJSONState {
			public:
				bool		inObject;
				bool		inArray;
				const char	*object;
				const char	*objectEnd;
		};
		void			skipSpace();
		const char 		*objectEnd(const char *start);
	private:
		const char 	*m_str;
		std::stack<LazyJSONState *>
				m_stateStack;
		LazyJSONState	*m_state;
		char		*m_searchFor;	// Preallocated buffer
		int		m_searchForLength;
};
#endif

