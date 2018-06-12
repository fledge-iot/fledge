#ifndef _RESULTSET_H
#define _RESULTSET_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <string.h>
#include <sstream>
#include <iostream>
#include <vector>
#include <rapidjson/document.h>

typedef enum column_type {
	INT_COLUMN = 1,
	NUMBER_COLUMN,
	STRING_COLUMN,
	BOOL_COLUMN,
	JSON_COLUMN
} ColumnType;


/**
 * Result set
 */
class ResultSet {
	public:
		class ColumnValue {
			public:
				ColumnValue(const std::string& value)
				{
					m_value.str = (char *)malloc(value.length() + 1);
					strncpy(m_value.str, value.c_str(), value.length() + 1);
					m_type = STRING_COLUMN;
				};
				ColumnValue(const int value)
				{
					m_value.ival = value;
					m_type = INT_COLUMN;
				};
				ColumnValue(const long value)
				{
					m_value.ival = value;
					m_type = INT_COLUMN;
				};
				ColumnValue(const double value)
				{
					m_value.fval = value;
					m_type = NUMBER_COLUMN;
				};
				ColumnValue(const rapidjson::Value& value)
				{
					m_doc = new rapidjson::Document();
					rapidjson::Document::AllocatorType& a = m_doc->GetAllocator();
					m_value.json = new rapidjson::Value(value, a);
					m_type = JSON_COLUMN;
				};
				~ColumnValue()
				{
					if (m_type == STRING_COLUMN)
						free(m_value.str);
					else if (m_type == JSON_COLUMN)
					{
						delete m_doc;
						delete m_value.json;
					}
				};
				ColumnType 	getType() { return m_type; };
				long	getInteger() const;
				double	getNumber() const;
				char	*getString() const;
				const rapidjson::Value *getJSON() const { return m_value.json; };
			private:
				ColumnValue(const ColumnValue&);
				ColumnValue&	operator=(ColumnValue const&);
				ColumnType	m_type;
				union {
					char			*str;
					long			ival;
					double			fval;
					rapidjson::Value	*json;
					}	m_value;
				rapidjson::Document *m_doc;
		};

		class Row {
			public:
				Row(ResultSet *resultSet) : m_resultSet(resultSet) {};
				~Row()
				{
					for (auto it = m_values.cbegin();
							it != m_values.cend(); it++)
						delete *it;
				}
				void append(ColumnValue *value)
				{
					m_values.push_back(value);
				};
				ColumnType	getType(unsigned int column);
				ColumnType	getType(const std::string& name);
				ColumnValue	*getColumn(unsigned int column) const;
				ColumnValue	*getColumn(const std::string& name) const;
				ColumnValue 	*operator[] (unsigned long colNo) const {
							return m_values[colNo];
						};
			private:
				Row(const Row&);
				Row&					operator=(Row const&);
				std::vector<ResultSet::ColumnValue *>	m_values;
				const ResultSet				*m_resultSet;
		};

		typedef std::vector<Row *>::iterator RowIterator;

		ResultSet(const std::string& json);
		~ResultSet();
		unsigned int			rowCount() const { return m_rowCount; };
		unsigned int			columnCount() const { return m_columns.size(); };
		const std::string&		columnName(unsigned int column) const;
		ColumnType			columnType(unsigned int column) const;
		ColumnType			columnType(const std::string& name) const;
		RowIterator			firstRow();
		RowIterator			nextRow(RowIterator it);
		bool				isLastRow(RowIterator it) const;
		bool				hasNextRow(RowIterator it) const;
		unsigned int			findColumn(const std::string& name) const;
		const Row *			operator[] (unsigned long rowNo) {
							return m_rows[rowNo];
						};

	private:
		ResultSet(const ResultSet &);
		ResultSet&			operator=(ResultSet const&);
		class Column {
			public:
				Column(const std::string& name, ColumnType type) : m_name(name), m_type(type) {};
				const std::string& getName() { return m_name; };
				ColumnType	getType() { return m_type; };
			private:
				const std::string	m_name;
				ColumnType		m_type;
		};


		unsigned int				m_rowCount;
		std::vector<ResultSet::Column *>	m_columns;
		std::vector<ResultSet::Row *>		m_rows;

};

class ResultException : public std::exception {

	public:
		ResultException(const char *what)
		{
			m_what = strdup(what);
		};
		~ResultException()
		{
			if (m_what)
				free(m_what);
		};
		virtual const char *what() const throw()
		{
			return m_what;
		};
	private:
		char *m_what;
};

class ResultNoSuchColumnException : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "Column does not exist";
		}
};

class ResultNoMoreRowsException : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "No more rows in the result set";
		}
};

class ResultIncorrectTypeException : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "No more rows in the result set";
		}
};

#endif

