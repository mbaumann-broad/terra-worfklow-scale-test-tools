#! /usr/bin/env bash
set -euo pipefail

#
# Extract all the DRS localization timestamps from workflow logs
# under a directory on the local file system to create time series data
# for graphing the DRS data access rate.
#

function parse_options {

  function usage {
    echo "Usage: "$(basename $0)" -d <workflow test results directory path>" 1>&2; exit 1;
  }

  local OPTIND
  while getopts "d:" o; do
      case "${o}" in
          d)
              WF_TEST_RESULTS_DIR="${OPTARG}"
              ;;
          *)
              usage
              ;;
      esac
  done
  shift $((OPTIND-1))

  set +u
  if [ -z "${WF_TEST_RESULTS_DIR}" ]; then
      usage
  fi
  set -u
}

function extract_drs_localization_log_entries {
  # Extract the DRS localization log entries from the workflow logs on the local file system
  # shellcheck disable=SC2038
  time (find "$WORKFLOW_LOG_DIR" -type f | xargs grep -F --no-filename "Localizing input drs://" > "${DRS_LOCALIZATION_LOG_LINES}")
}

function extract_drs_localization_timestamps {
  # Extract the timestamps from the workflow DRS localization log entries.
  cut -c 1-20 "${DRS_LOCALIZATION_LOG_LINES}" | sort > "${DRS_LOCALIZATION_TIMESTAMPS}"
}

function convert_timestamps_to_timeseries {
  echo -e 'Timestamp\tCount' > "${DRS_LOCALIZATION_TIMESERIES}"
  sed -e 's/$/\t1/' "${DRS_LOCALIZATION_TIMESTAMPS}" >> "${DRS_LOCALIZATION_TIMESERIES}"
}

parse_options $@

WORKFLOW_LOG_DIR="${WF_TEST_RESULTS_DIR}/workflow-logs"
DRS_LOCALIZATION_LOG_LINES="${WF_TEST_RESULTS_DIR}/drs_localization_log_lines.txt"
DRS_LOCALIZATION_TIMESTAMPS="${WF_TEST_RESULTS_DIR}/drs_localization_timestamps.txt"
DRS_LOCALIZATION_TIMESERIES="${WF_TEST_RESULTS_DIR}/drs_localization_timeseries.tsv"

extract_drs_localization_log_entries
extract_drs_localization_timestamps
convert_timestamps_to_timeseries

echo Done extracting DRS localization time series data to: "${DRS_LOCALIZATION_TIMESERIES}"
