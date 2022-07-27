#include <gtest/gtest.h>
#include <query.h>
#include <string.h>
#include <string>

using namespace std;

TEST(QueryTest, Simple)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" } }");

	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, IsNull)
{
Query query(new Where("c1", IsNull));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"isnull\" } }");

	json = query.toJSON();
	ASSERT_STREQ(json.c_str(), expected.c_str());
}

TEST(QueryTest, NotNull)
{
Query query(new Where("c1", NotNull));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"notnull\" } }");

	json = query.toJSON();
	ASSERT_STREQ(json.c_str(), expected.c_str());
}

TEST(QueryTest, And)
{
Query query2(new Where("c1", Equals, "10", new Where("c2", LessThan, "15")));
string json2;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\", \"and\" : { \"column\" : \"c2\", \"condition\" : \"<\", \"value\" : \"15\" } } }");

	json2 = query2.toJSON();
	ASSERT_EQ(json2.compare(expected), 0);
}

TEST(QueryTest, Aggregate)
{
Query query2(new Where("c1", Equals, "10", new Where("c2", LessThan, "15")));
string json2;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\", \"and\" : { \"column\" : \"c2\", \"condition\" : \"<\", \"value\" : \"15\" } }, \"aggregate\" : { \"column\" : \"c3\", \"operation\" : \"min\" } }");

	query2.aggregate(new Aggregate("min", "c3"));
	json2 = query2.toJSON();

	ASSERT_EQ(json2.compare(expected), 0);
}

TEST(QueryTest, AggregateList)
{
Query query2(new Where("c1", Equals, "10", new Where("c2", LessThan, "15")));
string json2;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\", \"and\" : { \"column\" : \"c2\", \"condition\" : \"<\", \"value\" : \"15\" } }, \"aggregate\" : [ { \"column\" : \"c3\", \"operation\" : \"min\" }, { \"column\" : \"c3\", \"operation\" : \"max\" } ] }");

	query2.aggregate(new Aggregate("min", "c3"));
	query2.aggregate(new Aggregate("max", "c3"));
	json2 = query2.toJSON();

	ASSERT_EQ(json2.compare(expected), 0);
}

TEST(QueryTest, Group)
{
Query query2(new Where("c1", Equals, "10", new Where("c2", LessThan, "15")));
string json2;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\", \"and\" : { \"column\" : \"c2\", \"condition\" : \"<\", \"value\" : \"15\" } }, \"aggregate\" : { \"column\" : \"c3\", \"operation\" : \"min\" }, \"group\" : \"c5\" }");

	query2.aggregate(new Aggregate("min", "c3"));
	query2.group("c5");
	json2 = query2.toJSON();

	ASSERT_EQ(json2.compare(expected), 0);
}

TEST(QueryTest, Sort)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"sort\" : { \"column\" : \"c2\", \"direction\" : \"asc\" } }");

	query.sort(new Sort("c2"));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, Sort2)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"sort\" : { \"column\" : \"c2\", \"direction\" : \"desc\" } }");

	query.sort(new Sort("c2", true));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, Limit)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"limit\" : 10 }");

	query.limit(10);
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, Timebucket)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"timebucket\" : { \"timestamp\" : \"user_ts\", \"size\" : \"10\", \"format\" : \"DD-MM-YYYY HH:MI:SS\", \"alias\" : \"bucket\" } }");

	query.timebucket(new Timebucket("user_ts", 10, "DD-MM-YYYY HH:MI:SS", "bucket"));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, AggregateConstructor)
{
Query query2(new Aggregate("min", "c3"), new Where("c1", Equals, "10"));
string json2;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"aggregate\" : { \"column\" : \"c3\", \"operation\" : \"min\" } }");

	json2 = query2.toJSON();
	ASSERT_EQ(json2.compare(expected), 0);
}

TEST(QueryTest, TimebucketConstructor)
{
Query query(new Timebucket("user_ts", 10, "DD-MM-YYYY HH:MI:SS", "bucket"),
	    new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"timebucket\" : { \"timestamp\" : \"user_ts\", \"size\" : \"10\", \"format\" : \"DD-MM-YYYY HH:MI:SS\", \"alias\" : \"bucket\" } }");

	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, TimebucketConstructorLimit)
{
Query query(new Timebucket("user_ts", 10, "DD-MM-YYYY HH:MI:SS", "bucket"),
	    new Where("c1", Equals, "10"), 10);
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"timebucket\" : { \"timestamp\" : \"user_ts\", \"size\" : \"10\", \"format\" : \"DD-MM-YYYY HH:MI:SS\", \"alias\" : \"bucket\" }, \"limit\" : 10 }");

	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, SingleReturn)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"return\" : [ \"c2\" ] }");

	query.returns(new Returns("c2"));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, MultipleReturn)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"return\" : [ \"c1\", \"c2\", \"c3\" ] }");

	query.returns(new Returns("c1"));
	query.returns(new Returns("c2"));
	query.returns(new Returns("c3"));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, MultipleReturn2)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"return\" : [ \"c1\", { \"column\" : \"c2\", \"alias\" : \"Col2\" }, { \"column\" : \"c3\", \"alias\" : \"Col3\", \"format\" : \"DD-MM-YY HH:MI:SS\" } ] }");

	query.returns(new Returns("c1"));
	query.returns(new Returns("c2", "Col2"));
	query.returns(new Returns("c3", "Col3", "DD-MM-YY HH:MI:SS"));
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, MultipleReturnVector)
{
Query query(new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"return\" : [ \"c1\", \"c2\", \"c3\" ] }");

	query.returns(vector<Returns *> {new Returns("c1"),
				         new Returns("c2"),
				         new Returns("c3")});
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, MultipleReturnConstrcutor)
{
Query query(vector<Returns *> {new Returns("c1"),
			       new Returns("c2"),
			       new Returns("c3")}, 
            new Where("c1", Equals, "10"));
string json;
string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"=\", \"value\" : \"10\" }, \"return\" : [ \"c1\", \"c2\", \"c3\" ] }");

	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, fullTable)
{
Query query(new Returns("c1"));
string json;
string expected("{ \"return\" : [ \"c1\" ] }");

	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, distinctTable)
{
Query query(new Returns("c1"));
string json;
string expected("{ \"return\" : [ \"c1\" ], \"modifier\" : \"distinct\" }");

	query.distinct();
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, whereInSingle)
{
	// Add one element for IN
	Query query(new Where("c1", In, "10"));

	string json;
	string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"in\", \"value\" : [\"10\"] } }");
        
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}

TEST(QueryTest, whereIn)
{
	// Add one element for IN
	Where* two = new Where("c1", In, "10");
	// Add second element
	two->addIn("20");
	Query query(two);

	string json;
	string expected("{ \"where\" : { \"column\" : \"c1\", \"condition\" : \"in\", \"value\" : [\"10\", \"20\"] } }");
        
	json = query.toJSON();
	ASSERT_EQ(json.compare(expected), 0);
}
