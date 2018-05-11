/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
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
		m_rowCount = doc["count"].GetInt();
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
				m_columns.push_back(new Column(string(itr->name.GetString()), type));
			}
			// Process every rows and create the result set
			for (auto& row : rows.GetArray())
			{
				if (!row.IsObject())
				{
					throw new ResultException("Expected row to be an object");
				}
				ResultSet::Row	*rowValue = new ResultSet::Row();
				int colNo = 0;
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
 */
const string& ResultSet::columnName(unsigned int column)
{
	if (column >= m_columns.size())
	{
		throw new ResultNoSuchColumnException();
	}
	return m_columns[column]->getName();
}

/**
 * Return the type of a specific column
 */
const ColumnType ResultSet::columnType(unsigned int column)
{
	if (column >= m_columns.size())
	{
		throw new ResultNoSuchColumnException();
	}
	return m_columns[column]->getType();
}

ResultSet::RowIterator ResultSet::firstRow()
{
	return m_rows.begin();
}

ResultSet::RowIterator ResultSet::nextRow(RowIterator it)
{
	if (it == m_rows.end())
		throw new exception();
	else
		return ++it;
}

bool ResultSet::hasNextRow(RowIterator it)
{
	return (it + 1) != m_rows.end();
}

bool ResultSet::isLastRow(RowIterator it)
{
	return (it + 1) == m_rows.end();
}

ColumnType ResultSet::Row::getType(unsigned int column)
{
	if (column > m_values.size())
		throw new ResultNoSuchColumnException();
	return m_values[column]->getType();
}
