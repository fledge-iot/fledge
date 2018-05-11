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

typedef enum column_type {
	INT_COLUMN,
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
				ColumnType 	getType() { return m_type; };
				const long	getInteger() const;
				const double	getNumber() const;
				const char	*getString() const;
			private:
				ColumnType	m_type;
				union {
					char		*str;
					long		ival;
					double		fval;
					}	m_value;
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
				const ColumnType	getType(unsigned int column);
				const ColumnType	getType(const std::string& name);
				const ColumnValue	*getColumn(unsigned int column) const;
				const ColumnValue	*getColumn(const std::string& name) const;
				const ColumnValue 	*operator[] (int colNo) const {
							return m_values[colNo];
						};
			private:
				std::vector<ResultSet::ColumnValue *>	m_values;
				const ResultSet				*m_resultSet;
		};

		typedef std::vector<Row *>::iterator RowIterator;

		ResultSet(const std::string& json);
		~ResultSet();
		const unsigned int		rowCount() const { return m_rowCount; };
		const unsigned int		columnCount() const { return m_columns.size(); };
		const std::string&		columnName(unsigned int column) const;
		const ColumnType		columnType(unsigned int column) const;
		const ColumnType		columnType(const std::string& name) const;
		RowIterator			firstRow();
		RowIterator			nextRow(RowIterator it);
		const bool			isLastRow(RowIterator it) const;
		const bool			hasNextRow(RowIterator it) const;
		const unsigned int		findColumn(const std::string& name) const;
		const Row *			operator[] (int rowNo) {
							return m_rows[rowNo];
						};

	private:
		class Column {
			public:
				Column(const std::string& name, ColumnType type) : m_name(name), m_type(type) {};
				const std::string& getName() { return m_name; };
				ColumnType	getType() { return m_type; };
			private:
				const std::string&	m_name;
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

