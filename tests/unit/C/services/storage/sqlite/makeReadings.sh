#!/bin/sh
if [ $# -eq "1" ] ; then
nreadings=$1
else
nreadings=100
fi
echo "{"
echo "   \"readings\" : ["
while [ $nreadings -gt 1 ]; do
#ts=`date --rfc-3339=ns | sed -e 's/\+.*//'`
ts=`date --rfc-3339=ns`
reading=`shuf -i 1-100 -n 1`
echo "		{"
echo "			\"asset_code\": \"MyAsset\","
echo "			\"reading\" : { \"rate\" : $reading },"
echo "			\"user_ts\" : \"$ts\""
echo "		},"
nreadings=`expr $nreadings - 1`
done

#ts=`date --rfc-3339=ns | sed -e 's/\+.*//'`
ts=`date --rfc-3339=ns`
reading=`shuf -i 1-100 -n 1`
echo "		{"
echo "			\"asset_code\": \"MyAsset\","
echo "			\"reading\" : { \"rate\" : $reading },"
echo "			\"user_ts\" : \"$ts\""
echo "		}"
echo "	]"
echo "}"
