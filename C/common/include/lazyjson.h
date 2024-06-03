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

#define	INTERNAL_BUFFER_INIT_LENGTH	128	// The initial length of internal buffers

/**
 * A resusable string buffer used to limit use of malloc and free. The
 * buffer works by maintianign a current size and reusing the same memory
 * if the required buffer will fit in the current memory. If not it will
 * free the current memory and allocated new memory. 
 *
 * This class is used both internally by the LazyJSON class and in its interface. In
 * the later case the expected use pattern is for a user to create a buffer for
 * particular attributes in a JSON document and reuse that buffer when fetching
 * new attributes. This is particularly useful when iterating over arrays of
 * data, suhc as readings, in a JSON payload.
 */
class LazyJSONBuffer {
	public:
		LazyJSONBuffer();
		~LazyJSONBuffer();
		inline char 	*str() { return m_str; };
		int		size(size_t request);
		int		size() { return m_size; };
	private:
		char		*m_str;
		size_t		m_size;
};

/**
 * The LazyJSON class is an attempt to improve performane by having a highly customised
 * JSON parse avilable to Fledge. In particular this has the following behaviours
 *
 * 	Avoid memory allocation and deallocation
 * 	Don't parse into a DOM structure
 * 	Allow extraction of raw JSON objects without the need to fully parse and serialise them
 *
 * As we don't parse the JSON document completely at the start we loose the ability to immediately
 * determine if the JSON document is valid or not. This is something we have sacrificed for the
 * above behaviours and means we should only really use LazyJSON if we are fairly confident in the
 * validity of the JSON we are parsing.
 *
 * In order to reduce the number of free and malloc calls made the class uses pre-allocated buffers
 * that may grow as required. The user is returned one of these by the getRawObject call. This buffer
 * must not be free'd by the user and must be used before the next call to getRawObject as the contents
 * will be overwritten.
 */
class LazyJSON {
	public:
		LazyJSON(const char *str);
		LazyJSON(const std::string& str);
		~LazyJSON();
		const char		*getDocument() {return m_str; };
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
		int			getArraySize(const char *p);
		const char		*getObject(const char *p);
		char			*getRawObject(const char *p);
		char			*getRawObject(const char *p, const char esc);
		char			*getString(const char *p);
		bool			getString(const char *p, LazyJSONBuffer& buffer);
		long			getInt(const char *p);
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
		LazyJSONBuffer	m_searchFor;	// Preallocated buffer
		LazyJSONBuffer	m_rawBuffer;
};
#endif

