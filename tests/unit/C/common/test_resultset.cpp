#include <gtest/gtest.h>
#include <resultset.h>
#include <string.h>
#include <string>

using namespace std;

TEST(ResultSetTest, RowCount)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 1);
}

TEST(ResultSetTest, NoRows)
{
string	json("{ \"count\" : 0, \"rows\" : [  ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 0);
}

TEST(ResultSetTest, ColumnCount1)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnCount(), 1);
}

TEST(ResultSetTest, ColumnCount2)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1, \"c2\" : 1.45 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnCount(), 2);
}

TEST(ResultSetTest, ColumnName)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnName(0).compare("c1"), 0);
}

TEST(ResultSetTest, ColumnTypeInt)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnType(0), INT_COLUMN);
}

TEST(ResultSetTest, ColumnTypeIntAfterJSON)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : {}, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnType(1), INT_COLUMN);
	ASSERT_EQ(result.columnName(1).compare("c1"), 0);
}

TEST(ResultSetTest, ColumnTypeIntByNameAfterJSON)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : {}, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnType("c1"), INT_COLUMN);
}

TEST(ResultSetTest, GetColumnAfterJSON)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : {}, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	ASSERT_EQ((*rowIter)->getColumn(1)->getInteger(), 1);
}

TEST(ResultSetTest, GetColumnByNameAfterJSON)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : {}, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	ASSERT_EQ((*rowIter)->getColumn("c1")->getInteger(), 1);
}

TEST(ResultSetTest, ColumnTypeNumber)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"c1\" : 1.4 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnType(0), NUMBER_COLUMN);
}

TEST(ResultSetTest, RowIterator)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	int i = 1;
	ResultSet::RowIterator rowIter = result.firstRow();
	while (result.hasNextRow(rowIter))
	{
		rowIter = result.nextRow(rowIter);
		i++;
	}
	ASSERT_EQ(result.rowCount(), i);
}

TEST(ResultSetTest, RowIteratorIsLast)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	int i = 1;
	ResultSet::RowIterator rowIter = result.firstRow();
	while (! result.isLastRow(rowIter))
	{
		rowIter = result.nextRow(rowIter);
		i++;
	}
	ASSERT_EQ(result.rowCount(), i);
}

TEST(ResultSetTest, RowIteratorType)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	ResultSet::RowIterator rowIter = result.firstRow();
	ASSERT_EQ(INT_COLUMN, (*rowIter)->getType(0));
	while (result.hasNextRow(rowIter))
	{
		rowIter = result.nextRow(rowIter);
		ASSERT_EQ(INT_COLUMN, (*rowIter)->getType(0));
	}
}

TEST(ResultSetTest, RowIteratorIntValue)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 }, { \"c1\" : 3 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	ResultSet::RowIterator rowIter = result.firstRow();
	int i = 1;
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn(0);
	ASSERT_EQ(i, value->getInteger());
	while (result.hasNextRow(rowIter))
	{
		i++;
		rowIter = result.nextRow(rowIter);
		ASSERT_EQ(i, (*rowIter)->getColumn(0)->getInteger());
	}
}

TEST(ResultSetTest, RowIteratorIntValueByName)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 }, { \"c1\" : 3 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	ResultSet::RowIterator rowIter = result.firstRow();
	int i = 1;
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn("c1");
	ASSERT_EQ(i, value->getInteger());
	while (result.hasNextRow(rowIter))
	{
		i++;
		rowIter = result.nextRow(rowIter);
		ASSERT_EQ(i, (*rowIter)->getColumn("c1")->getInteger());
	}
}

TEST(ResultSetTest, RowIndexIntValueByName)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 }, { \"c1\" : 3 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	for (int i = 0; i < result.rowCount(); i++)
	{
		ASSERT_EQ(i + 1, result[i]->getColumn("c1")->getInteger());
	}
}

TEST(ResultSetTest, RowIndexIntValueByIndex)
{
string	json("{ \"count\" : 2, \"rows\" : [ { \"c1\" : 1 }, { \"c1\" : 2 }, { \"c1\" : 3 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.rowCount(), 2);

	for (int i = 0; i < result.rowCount(); i++)
	{
		ASSERT_EQ(i + 1, (*result[i])[0]->getInteger());
	}
}

TEST(ResultSetTest, JSONColumn)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : { \"j1\" : \"test\" }, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ASSERT_EQ(result.columnType(0), JSON_COLUMN);
}

TEST(ResultSetTest, JSONColumnType)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : { \"j1\" : \"test\" }, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn("json");
	ASSERT_EQ(result.columnType(0), JSON_COLUMN);
}

TEST(ResultSetTest, JSONColumnObjectType)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : { \"j1\" : \"test\" }, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn("json");
	const rapidjson::Value *v = value->getJSON();
	ASSERT_EQ(v->IsObject(), true);
}

TEST(ResultSetTest, JSONColumnHasMember)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : { \"j1\" : \"test\" }, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn("json");
	const rapidjson::Value *v = value->getJSON();
	ASSERT_EQ(v->HasMember("j1"), true);
}

TEST(ResultSetTest, JSONColumnGetString)
{
string	json("{ \"count\" : 1, \"rows\" : [ { \"json\" : { \"j1\" : \"test\" }, \"c1\" : 1 } ] }");

	ResultSet result(json);
	ResultSet::RowIterator rowIter = result.firstRow();
	const ResultSet::ColumnValue *value = (*rowIter)->getColumn("json");
	const rapidjson::Value *v = value->getJSON();
	ASSERT_EQ(strcmp((*v)["j1"].GetString(), "test"), 0);
}
