#!/bin/sh

session_path=$1
if [[ -z $session_path ]]; then
    session_path="."
fi

# termination - start
term_start_timestamps=(`echo "$(grep -r "terminating prte" $session_path/* | cut -f2 -d: | tr -d '\n')"` )
# termination - stop
term_stop_timestamps=(`echo "$(grep -r "TERMINATING DVM...DONE" $session_path/* | cut -f2 -d: | tr -d '\n')"` )
# termination - duration
term_duration_avg=0

timestamps_length=${#term_start_timestamps[@]}
for (( j=0; j<${timestamps_length}; j++ )); do
    term_duration="$(echo "${term_stop_timestamps[$j]} - ${term_start_timestamps[$j]}" | bc -l)"
    term_duration_avg="$(echo "$term_duration_avg + $term_duration" | bc -l)"
done

term_duration_avg="$(echo "$term_duration_avg / $timestamps_length" | bc -l)"
printf "DVM termination time (avg): %.*f sec\n" 2 $term_duration_avg

