#!/bin/bash

# set -vx

offset=100
limit=5
pattern=""
# level="debug"
logfile="/var/log/syslog"

while [ "$#" -gt 0 ]; do
  case "$1" in
    -pattern) pattern="$2"; shift 2;;
    -offset) offset="$2"; shift 2;;
    -limit) limit="$2"; shift 2;;
    -level) level="$2"; shift 2;;
    -logfile) logfile="$2"; shift 2;;
  esac
done

: <<'COMMENT1'
levelStr=""
if [[ "$level" == 'info' ]]; then
	levelStr="(INFO|WARNING|ERROR|FATAL)"
elif [[ "$level" == 'warning' ]]; then
	levelStr="(WARNING|ERROR|FATAL)"
elif [[ "$level" == 'error' ]]; then
	levelStr="(ERROR|FATAL)"
fi
COMMENT1

# [ "$svcName" != "" ] && pattern=$( echo -n "Fledge "; echo -n $svcName; echo -n '\[') || pattern=$(echo -n "Fledge"; echo -n '.*\[' )
# [ ! -z "$levelStr" ] && pattern=$( echo -n ${pattern}.*$levelStr )

sum=$(($offset + $limit))
echo "offset=$offset, limit=$limit, sum=$sum, pattern=$pattern" >&2

# factor=2
factor=$((2000 / $sum))
[[ $factor -lt 2 ]] && factor=2
echo "Starting with factor=$factor" >&2
# [ -f /tmp/fledge_syslog_factor ] && factor=$(cat /tmp/fledge_syslog_factor) && echo "Read factor value of $factor from /tmp/fledge_syslog_factor"

tmpfile=$(mktemp)

while [ 1 ];
do
	filesz=$(stat -c%s $logfile)
	filesz_dbl=$(($filesz * 2))

	lines=$(($factor * $sum))
	[[ $lines -gt $filesz_dbl ]] && echo "Cannot increase factor value any further; filesz=$filesz" >&2 && cat $tmpfile | tail -n $sum | head -n $limit && rm $tmpfile && break

	cmd="tail -n $lines $logfile | grep -a -E '${pattern}' > $tmpfile"
	echo "cmd=$cmd" >&2
	# tail -n $lines $logfile | grep -a -E '${pattern}' > $tmpfile
	eval "$cmd"
	count=$(wc -l < $tmpfile)
	echo "Got $count matching log lines in last $lines lines of syslog file" >&2
	if [[ $count -ge $sum ]]; then
		echo "Got sufficient number of matching log lines, current factor value of $factor is good" >&2
		cat $tmpfile | tail -n $sum | head -n $limit
		rm $tmpfile
		# echo $factor > /tmp/fledge_syslog_factor
		break
	else
        new_factor=$factor
		[[ $count -ne 0 ]] && ( new_factor=$(($lines / $count)) && new_factor=$(($new_factor + 1)) )  # || new_factor=$(($new_factor * 2))
		echo "factor=$factor, new_factor=$new_factor" >&2
		[[ $new_factor -eq $factor ]] && factor=$(($factor * 2)) || factor=$new_factor
		echo "Didn't get sufficient number of matching log lines, trying factor=$factor" >&2
	fi
done

