/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <resultset.h>
#include <string>
#include <rapidjson/document.h>
#include <sstream>
#include <iostream>

using namespace std;
using namespace rapidjson;

/**
 * Construct a result set from a JSON document returned from
 * the FogLAMP storage service.
 *
 * @param json	The JSON document to construct the result set from
 */
ResultSet::ResultSet(const std::string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		throw new ResultException("Unable to parse results json document");
	}
	if (doc.HasMember("count"))
	{
		m_rowCount = doc["count"].GetUint();
		if (m_rowCount)
		{
			const Value& rows = doc["rows"];
			if (!doc.HasMember("rows"))
			{
				throw new ResultException("Missing rows array");
			}
			if (rows.IsArray())
			{
				// Process first row to get column names and types
				const Value& firstRow = rows[0];
				for (Value::ConstMemberIterator itr = firstRow.MemberBegin(); itr != firstRow.MemberEnd(); ++itr)
				{
					ColumnType type = STRING_COLUMN;
					if (itr->value.IsObject())
					{
						type = JSON_COLUMN;
					}
					else if (itr->value.IsNumber() && itr->value.IsDouble())
					{
						type = NUMBER_COLUMN;
					}
					else if (itr->value.IsNumber())
					{
						type = INT_COLUMN;
					}
					else if (itr->value.IsBool())
					{
						type = BOOL_COLUMN;
					}
					else if (itr->value.IsString())
					{
						type = STRING_COLUMN;
					}
					else
					{
						throw new ResultException("Unable to determine column type");
					}
					m_columns.push_back(new Column(string(itr->name.GetString()), type));
				}
				// Process every rows and create the result set
				for (auto& row : rows.GetArray())
				{
					if (!row.IsObject())
					{
						throw new ResultException("Expected row to be an object");
					}
					ResultSet::Row	*rowValue = new ResultSet::Row(this);
					unsigned int colNo = 0;
					for (Value::ConstMemberIterator item = row.MemberBegin(); item != row.MemberEnd(); ++item)
					{
						switch (m_columns[colNo]->getType())
						{
						case STRING_COLUMN:
							rowValue->append(new ColumnValue(string(item->value.GetString())));
							break;
						case INT_COLUMN:
							rowValue->append(new ColumnValue(item->value.GetInt()));
							break;
						case NUMBER_COLUMN:
							rowValue->append(new ColumnValue(item->value.GetDouble()));
							break;
						case JSON_COLUMN:
							rowValue->append(new ColumnValue(item->value));
							break;
						case BOOL_COLUMN:
							// TODO Add support
							rowValue->append(new ColumnValue(string("TODO")));
							break;
						}
						colNo++;
					}
					m_rows.push_back(rowValue);
				}
			}
			else
			{
				throw new ResultException("Expected array of rows in result set");
			}
		}
	}
	else
	{
		m_rowCount = 0;
	}
}

/**
 * Destructor for a result set
 */
ResultSet::~ResultSet()
{
	/* Delete the columns */
	for (auto it = m_columns.cbegin(); it != m_columns.cend(); it++)
	{
		delete *it;
	}
	/* Delete the rows */
	for (auto it = m_rows.cbegin(); it != m_rows.cend(); it++)
	{
		delete *it;
	}
}

/**
 * Return the name of a specific column
 *
 * @param column - the column number of the column to return.
 * Columns are numbered from 0
 * @return string& The name of the column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the result set
 */
const string& ResultSet::columnName(unsigned int column) const
{
	if (column >= m_columns.size())
	{
		throw new ResultNoSuchColumnException();
	}
	return m_columns[column]->getName();
}

/**
 * Return the type of a specific column
 *
 * @param column - the column number of the column to return.
 * Columns are numbered from 0
 * @return ColumnType	The type of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the result set
 */
ColumnType ResultSet::columnType(unsigned int column) const
{
	if (column >= m_columns.size())
	{
		throw new ResultNoSuchColumnException();
	}
	return m_columns[column]->getType();
}

/**
 * Return the type of a specific column
 *
 * @param name - the name of the column to return.
 * @return ColumnType	The type of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the result set
 */
ColumnType ResultSet::columnType(const string& name) const
{
	unsigned int column = findColumn(name);
	return m_columns[column]->getType();
}

/**
 * Fetch an iterator for the rows in a result set.
 * The iterator is positioned at the first row in the
 * result set.
 */
ResultSet::RowIterator ResultSet::firstRow()
{
	return m_rows.begin();
}

/**
 * Given an iterator over the rows in a result set move to the
 * next row in the result set.
 *
 * @param it	Iterator returned by the firstRow() method
 * @return RowIterator	New value of the iterator
 * @throw ResultNoMoreRowsException	There are no more rows in the result set
 */
ResultSet::RowIterator ResultSet::nextRow(RowIterator it)
{
	if (it == m_rows.end())
		throw new ResultNoMoreRowsException();
	else
		return ++it;
}

/**
 * Given an iterator over the rows in a result set return if there
 * are any more rows in the result set.
 *
 * @param it	Iterator returned by the firstRow() method
 * @return bool	True if there are more rows in the result set
 */
bool ResultSet::hasNextRow(RowIterator it) const
{
	return (it + 1) != m_rows.end();
}

/**
 * Given an iterator over the rows in a result set return if there
 * this is the last row in the result set.
 *
 * @param it	Iterator returned by the firstRow() method
 * @return bool	True if there are no more rows in the result set
 */
bool ResultSet::isLastRow(RowIterator it) const
{
	return (it + 1) == m_rows.end();
}

/**
 * Return the type of the given column in this row.
 *
 * @param column	The column number in the row, columns are numbered from 0
 * @return ColumnType	The column type of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the row
 */
ColumnType ResultSet::Row::getType(unsigned int column)
{
	if (column > m_values.size())
		throw new ResultNoSuchColumnException();
	return m_values[column]->getType();
}

/**
 * Return the type of the given column in this row.
 *
 * @param name		The column name in the row
 * @return ColumnType	The column type of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the row
 */
ColumnType ResultSet::Row::getType(const string& name)
{
	unsigned int column = m_resultSet->findColumn(name);
	return m_values[column]->getType();
}

/**
 * Return the column value of the given column in this row.
 *
 * @param column	The column number in the row, columns are numbered from 0
 * @return ColumnValue	The column value of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the row
 */
ResultSet::ColumnValue *ResultSet::Row::getColumn(unsigned int column) const
{
	if (column > m_values.size())
		throw new ResultNoSuchColumnException();
	return m_values[column];
}

/**
 * Return the column value of the given column in this row.
 *
 * @param name		The column name in the row
 * @return ColumnValue	The column value of the specified column
 * @throw ResultNoSuchColumnException	The specified column does not exist in the row
 */
ResultSet::ColumnValue *ResultSet::Row::getColumn(const string& name) const
{
	unsigned int column = m_resultSet->findColumn(name);
	return m_values[column];
}

/**
 * Find the named column in the result set and return the column index.
 *
 * @param name	The name of the column to return
 * @return unsigned int		The index of the named column
 * @throw ResultNoSuchColumnException	The named column does not exist in the result set
 */
unsigned int ResultSet::findColumn(const string& name) const
{
	for (unsigned int i = 0; i != m_columns.size(); i++)
	{
		if (m_columns[i]->getName().compare(name) == 0)
		{
			return i;
		}
	}
	throw ResultNoSuchColumnException();
}

/**
 * Retrieve a column value as an integer
 * 
 * @return long Integer value
 * @throw ResultIncorrectTypeException	The column can not be returned as an integer
 */
long ResultSet::ColumnValue::getInteger() const
{
	switch (m_type)
	{
	case INT_COLUMN:
		return m_value.ival;
	case NUMBER_COLUMN:
		return (long)m_value.fval;
	default:
		throw new ResultIncorrectTypeException();
	}
}

/**
 * Retrieve a column value as a floating point number
 * 
 * @return double Floating point value
 * @throw ResultIncorrectTypeException	The column can not be returned as a double
 */
double ResultSet::ColumnValue::getNumber() const
{
	switch (m_type)
	{
	case INT_COLUMN:
		return (double)m_value.ival;
	case NUMBER_COLUMN:
		return m_value.fval;
	default:
		throw new ResultIncorrectTypeException();
	}
}

/**
 * Retrieve a column value as a string
 * 
 * @return double Floating point value
 * @throw ResultIncorrectTypeException	The column can not be returned as a double
 */
char *ResultSet::ColumnValue::getString() const
{
	switch (m_type)
	{
	case STRING_COLUMN:
		return m_value.str;
	default:
		throw new ResultIncorrectTypeException();
	}
}
