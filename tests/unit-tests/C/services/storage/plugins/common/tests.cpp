#include <gtest/gtest.h>
#include <sql_buffer.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}

/**
 * Test appending characters to the buffer
 */
TEST(SQLBufferTest, charappend) {
SQLBuffer	sql;

	for (int i = 0; i < 100; i++)
		sql.append(' ');
	const char *buf = sql.coalesce();
	ASSERT_EQ(100, strlen(buf));
}

/**
 * Test appending more characers than will fit in a single
 * buffer.
 */
TEST(SQLBufferTest, charappendlarge) {
SQLBuffer	sql;

	for (int i = 0; i < 10000; i++)
		sql.append(' ');
	const char *buf = sql.coalesce();
	ASSERT_EQ(10000, strlen(buf));
}

/**
 * Test appending a fixed pattern - check order of appends
 */
TEST(SQLBufferTest, charappendpattern) {
SQLBuffer	sql;

	sql.append('a');
	sql.append('b');
	sql.append('c');
	sql.append('d');
	sql.append('e');
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "abcde"));
}

/**
 * Test appending a fixed pattern - check order of appends
 * across buffer boundaries.
 */
TEST(SQLBufferTest, charappendlongpattern) {
SQLBuffer	sql;
int		i;

	for (i = 0; i < 2000; i++)
	{
		char ch = 'a' + (i % 26);
		sql.append(ch);
	}
	const char *buf = sql.coalesce();
	ASSERT_EQ(2000, strlen(buf));
	int result = 0;
	/* Check the pattern matches what we put in */
	for (i = 0; i < 2000; i++)
	{
		char ch = 'a' + (i % 26);
		if (buf[i] != ch)
		{
			result = 1;
		}
	}
	ASSERT_EQ(0, result);
}

/**
 * Test appendign null terminated strings
 */
TEST(SQLBufferTest, strappend) {
SQLBuffer	sql;

	for (int i = 0; i < 100; i++)
		sql.append("    ");
	const char *buf = sql.coalesce();
	ASSERT_EQ(400, strlen(buf));
}

/**
 * Test appending long null terminated strings
 */
TEST(SQLBufferTest, strappendlarge) {
SQLBuffer	sql;

	for (int i = 0; i < 10000; i++)
		sql.append("1234567890");
	const char *buf = sql.coalesce();
	ASSERT_EQ(100000, strlen(buf));
}

/**
 * test appending an integer
 */
TEST(SQLBufferTest, intappend) {
SQLBuffer	sql;

	sql.append(1234);
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "1234"));
}

/**
 * test appending an unsigned integer
 */
TEST(SQLBufferTest, uintappend) {
SQLBuffer	sql;
unsigned int	value = 4321;

	sql.append(value);
	sql.append(value);
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "43214321"));
}

/**
 * test appending a long integer
 */
TEST(SQLBufferTest, longappend) {
SQLBuffer	sql;
long		value = 491572107;

	sql.append(value);
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "491572107"));
}

/**
 * test appending a negative long integer
 */
TEST(SQLBufferTest, negappend) {
SQLBuffer	sql;
long		value = -491572107;

	sql.append(value);
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "-491572107"));
}

/**
 * test appending a double
 */
TEST(SQLBufferTest, doubleappend) {
SQLBuffer	sql;
double		value = 3.141526;

	sql.append(value);
	const char *buf = sql.coalesce();
	ASSERT_EQ(3.141526, atof(buf));
}

/**
 * Test appending a C++ string class
 */
TEST(SQLBufferTest, stringappend) {
SQLBuffer	sql;
string		str("A C++ String");

	sql.append(str);
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(str.c_str(), buf));
}

/**
 * Test appending a mixture of types
 */
TEST(SQLBufferTest, mixedappend) {
SQLBuffer	sql;

	sql.append("Hello");
	sql.append(' ');
	sql.append(123456);
	sql.append(string(" world"));
	const char *buf = sql.coalesce();
	ASSERT_EQ(0, strcmp(buf, "Hello 123456 world"));
}

