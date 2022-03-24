#! /usr/bin/env bash
set -euxo pipefail

#
# Extract the DRS localization "fallback" timestamps from workflow logs
# under a directory on the local file system to create time series data
# for graphing the DRS data access rate.
#
# DRS localization fallback occurs when the Terra workflow DRS localizer
# did not receive a signed URL within the allotted time and therefore
# fell back to using a cloud-native URI and service account key.
#

function parse_options {

  function usage {
    cmd_basename=$(basename "$0")
    echo "Usage: "${cmd_basename}" -d <workflow test results directory path>" 1>&2; exit 1;
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

function extract_drs_localization_fallback_log_entries {
  # Extract the DRS localization log entries in which a "fallback" occurred.
  # Identifying the log entries in which fallback occurred requires searching
  # across multiple lines. This is performed using the GNU grep support for
  # PERL-compatible Regular Expressions (PCRE).
  # shellcheck disable=SC2038
  time (find "$WORKFLOW_LOG_DIR" -type f | xargs grep --no-filename -Pzo "\d\d\d\d/\d\d/\d\d.*Localizing input drs:.*\nRequester Pays project ID is.*\nAttempting to download.*\nSuccessfully activated service account.*" | sed -z -e 's/\n/  /g' | tr '\0' '\n' > "${DRS_LOCALIZATION_FALLBACK_LOG_LINES}")
}

function extract_drs_localization_fallback_timestamps {
  # Extract the timestamps from the workflow DRS localization log entries.
  cut -c 1-20 "${DRS_LOCALIZATION_FALLBACK_LOG_LINES}" | sort > "${DRS_LOCALIZATION_FALLBACK_TIMESTAMPS}"
}

function convert_timestamps_to_timeseries() {
  echo -e 'Timestamp\tCount' > "${DRS_LOCALIZATION_FALLBACK_TIMESERIES}"
  sed -e 's/$/\t1/' "${DRS_LOCALIZATION_FALLBACK_TIMESTAMPS}" >> "${DRS_LOCALIZATION_FALLBACK_TIMESERIES}"
}

parse_options "$@"

WORKFLOW_LOG_DIR="${WF_TEST_RESULTS_DIR}/workflow-logs"
DRS_LOCALIZATION_FALLBACK_LOG_LINES="${WF_TEST_RESULTS_DIR}/drs_localization_fallback_log_lines.txt"
DRS_LOCALIZATION_FALLBACK_TIMESTAMPS="${WF_TEST_RESULTS_DIR}/drs_localization_fallback_timestamps.txt"
DRS_LOCALIZATION_FALLBACK_TIMESERIES="${WF_TEST_RESULTS_DIR}/drs_localization_fallback_timeseries.tsv"

extract_drs_localization_fallback_log_entries
extract_drs_localization_fallback_timestamps
convert_timestamps_to_timeseries

echo Done extracting DRS localization fallback time series data to: "${DRS_LOCALIZATION_FALLBACK_TIMESERIES}"
