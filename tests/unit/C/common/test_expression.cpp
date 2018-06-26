#include <gtest/gtest.h>
#include <expression.h>
#include <string.h>
#include <string>

using namespace std;

TEST(ExpressionTest, IntColumn)
{
string expected("{ \"column\" : \"c1\", \"operator\" : \"+\", \"value\" : 10}");

	Expression expression("c1", "+", 10);
	ASSERT_EQ(expected.compare(expression.toJSON()), 0);
}

TEST(ExpressionTest, FloatColumn)
{
string expected("{ \"column\" : \"c1\", \"operator\" : \"+\", \"value\" : 10.25}");

	Expression expression("c1", "+", 10.25);
	ASSERT_EQ(expected.compare(expression.toJSON()), 0);
}

TEST(ExpressionValuesTest, IntColumns)
{
string expected("[ { \"column\" : \"c1\", \"operator\" : \"+\", \"value\" : 1}, { \"column\" : \"c2\", \"operator\" : \"-\", \"value\" : 2} ]");

	ExpressionValues expressions;
	expressions.push_back(Expression("c1", "+", 1));
	expressions.push_back(Expression("c2", "-", 2));
	ASSERT_EQ(expressions.toJSON().compare(expected), 0);
}
