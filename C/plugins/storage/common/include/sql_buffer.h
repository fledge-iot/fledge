#ifndef _SQL_BUFFER_H
#define _SQL_BUFFER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <string>
#include <list>

#define BUFFER_CHUNK	1024

/**
 * Buffer class designed to hold SQL statement that can
 * as required but have minimal copy semantics.
 */
class SQLBuffer {
	class Buffer {
		public:
			Buffer();
			Buffer(unsigned int);
			~Buffer();
			char		*detach();
			char		*data;
			unsigned int	offset;
			unsigned int	length;
			bool		attached;
	};

        public:
                SQLBuffer();
                ~SQLBuffer();

		bool			isEmpty() { return buffers.empty() || (buffers.size() == 1 && buffers.front()->offset == 0); }
		void			append(const char);
		void			append(const char *);
		void			append(const int);
		void			append(const unsigned int);
		void			append(const long);
		void			append(const unsigned long);
		void			append(const double);
		void			append(const std::string&);
		void			quote(const std::string&);
		const char		*coalesce();
		void			clear();

	private:
		std::list<Buffer *>	buffers;
};

#endif
