#!/bin/bash

__author__="Amandeep Singh Arora"
__version__="1.0"


# open a log file at FD 2 for debugging purposes
> /tmp/fl_syslog.log
exec 2<&-
exec 2<>/tmp/fl_syslog.log

RECALC_AFTER_N_SCRIPT_RUNS=100
NUM_LOGFILE_LINES_TO_CHECK_INITIALLY=2000

offset=100
limit=5
pattern=""
level="debug"
logfile="/var/log/syslog"
sourceApp="fledge"

while [ "$#" -gt 0 ]; do
  case "$1" in
    -pattern) pattern="$2"; shift 2;;
    -offset) offset="$2"; shift 2;;
    -limit) limit="$2"; shift 2;;
    -level) level="$2"; shift 2;;
    -source) sourceApp="$2"; shift 2;;
    -logfile) logfile="$2"; shift 2;;
  esac
done

sum=$(($offset + $limit))
echo "" >&2
echo "****************************************************************************************" >&2
echo "************************************* START ********************************************" >&2

# keep script run count in /tmp/fl_syslog_script_runs; when it reaches RECALC_AFTER_N_SCRIPT_RUNS, recalculate factor
if [ -f /tmp/fl_syslog_script_runs ]; then
	script_runs=$(cat /tmp/fl_syslog_script_runs)
	script_runs=$(($script_runs + 1))
else
	script_runs=0
fi

echo "script_runs=$script_runs" >&2
if [[ $script_runs -gt ${RECALC_AFTER_N_SCRIPT_RUNS} ]]; then
	echo "Resetting script_runs" >&2
	script_runs=0
	echo -n "$script_runs" > /tmp/fl_syslog_script_runs
fi
echo -n "$script_runs" > /tmp/fl_syslog_script_runs
echo "offset=$offset, limit=$limit, sum=$sum, pattern=$pattern, sourceApp=$sourceApp, level=$level, script_runs=$script_runs" >&2

# calculate how many log lines are to be checked to get 'n' result lines for a given service and log level
# if for getting 100 lines of interest, 6400 last syslog lines need to be checked, then factor would be 64
factor=2
if [[ $script_runs -eq 0 ]]; then
	factor=$((${NUM_LOGFILE_LINES_TO_CHECK_INITIALLY} / $sum))
	[[ $factor -lt 2 ]] && factor=2
else
	if [ -f /tmp/fl_syslog_factor ]; then
		echo "Reading factor value from /tmp/fl_syslog_factor" >&2
		factor=$(grep "$sourceApp:$level:" /tmp/fl_syslog_factor | cut -d: -f3)
		echo "Read factor value of '$factor' from /tmp/fl_syslog_factor" >&2
		[ -z $factor ] && factor=2 && echo "Using factor value of $factor" >&2
	else
		[ -z $factor ] && factor=2 && echo "Using factor value of $factor; file '/tmp/fl_syslog_factor' is missing" >&2
		echo "Starting with factor=$factor" >&2
	fi
fi

tmpfile=$(mktemp)
loop_iters=0

# check the last 'n' lines of syslog for log lines of interest, else keep doubling 'n' till syslog file size
while [ 1 ];
do
	t1=$(date +%s%N)
	filesz=$(stat -c%s $logfile)
	filesz_dbl=$(($filesz * 2))

	lines=$(($factor * $sum))

	echo "loop_iters=$loop_iters: factor=$factor, lines=$lines, tmpfile=$tmpfile" >&2

	cmd="tail -n $lines $logfile | grep -a -E '${pattern}' > $tmpfile"
	echo "cmd=$cmd, filesz=$filesz" >&2
	eval "$cmd"
	t2=$(date +%s%N)
	t_diff=$(((t2 - t1)/1000000))
	count=$(wc -l < $tmpfile)
	echo "Got $count matching log lines in last $lines lines of syslog file; processing time=${t_diff}ms" >&2

	if [[ $count -ge $sum ]]; then
		echo "Got sufficient number of matching log lines, current factor value of $factor is good" >&2
		cat $tmpfile | tail -n $sum | head -n $limit
		rm $tmpfile

		touch /tmp/fl_syslog_factor
		grep -v "$sourceApp:$level:" /tmp/fl_syslog_factor > /tmp/fl_syslog_factor.out; mv /tmp/fl_syslog_factor.out /tmp/fl_syslog_factor
		echo "$sourceApp:$level:$factor" >> /tmp/fl_syslog_factor
		break
	else
        	new_factor=$factor
		[[ $count -ne 0 ]] && ( new_factor=$(($lines / $count)) && new_factor=$(($new_factor + 1)) )
		echo "factor=$factor, new_factor=$new_factor" >&2
		[[ $new_factor -eq $factor ]] && [[ $lines -lt $filesz_dbl ]] && factor=$(($factor * 2)) || factor=$new_factor
		echo "Didn't get sufficient number of matching log lines, trying factor=$factor" >&2
	fi

	if [[ $lines -gt $filesz_dbl ]]; then
		echo "Cannot increase factor value any further; filesz=$filesz, lines=$lines" >&2

		cat $tmpfile | tail -n $sum | head -n $limit
		echo "Log results START:" >&2
		cat $tmpfile | tail -n $sum | head -n $limit >&2
		echo "Log results END:" >&2
		rm $tmpfile
		touch /tmp/fl_syslog_factor
		grep -v "$sourceApp:$level:" /tmp/fl_syslog_factor > /tmp/fl_syslog_factor.out; mv /tmp/fl_syslog_factor.out /tmp/fl_syslog_factor
		echo "$sourceApp:$level:$factor" >> /tmp/fl_syslog_factor
		break
	fi

	loop_iters=$(($loop_iters + 1))
done

echo "******************************** END ***************************************************" >&2
echo "" >&2
