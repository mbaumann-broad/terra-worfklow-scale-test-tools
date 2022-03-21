#! /usr/bin/env bash
set -euo pipefail

# Copy selected Terra workflow log files from a Terra workspace bucket
# to the local file system to facilitate exploratory mining of them.
#
# Note: Using gsutil directly for this doesn't work because when copying from
# a bucket path to the local filesystem, the path is discarded and only the
# file name is used for the local file systems. Because all the selected
# log files have the same file name, the same file is overwritten many times.

function parse_options {

  function usage {
    echo "Usage: `basename $0` -s <GCS URI of submison folder> -d <local file system directory path>" 1>&2; exit 1;
  }

  local OPTIND
  while getopts "s:d:" o; do
      case "${o}" in
          s)
              GCS_SUBMISSION_FOLDER="${OPTARG}"
              ;;
          d)
              WORKFLOW_LOG_DIR="${OPTARG}"
              ;;
          *)
              usage
              ;;
      esac
  done
  shift $((OPTIND-1))

  if [ -z "${GCS_SUBMISSION_FOLDER}" ] || [ -z "${WORKFLOW_LOG_DIR}" ]; then
      usage
  fi
}

function configure_for_wf_shape1 {
  WF_NAME="ga4ghMd5"
  WF_TASK_NAME='call-md5'
  WF_DRS_LOG_FILENAME='md5.log'
  # shellcheck disable=SC2034
  GSUTIL_DRS_LOG_PATH="${GCS_SUBMISSION_FOLDER}/${WF_NAME}/**/${WF_TASK_NAME}/${WF_DRS_LOG_FILENAME}"
}

function configure_for_wf_shape2 {
  WF_NAME="md5_n_by_m_scatter"
  WF_TASK_NAME='call-md5s'
  WF_DRS_LOG_FILENAME='*.log'
  # shellcheck disable=SC2034
  GSUTIL_DRS_LOG_PATH="${GCS_SUBMISSION_FOLDER}/${WF_NAME}/**/${WF_TASK_NAME}/**/${WF_DRS_LOG_FILENAME}"
}

function configure_for_workflow_shape {
  if gsutil ls "${GCS_SUBMISSION_FOLDER}/ga4ghMd5" > /dev/null 2>&1; then
    configure_for_wf_shape1
  elif gsutil ls "${GCS_SUBMISSION_FOLDER}/md5_n_by_m_scatter" > /dev/null 2>&1; then
    configure_for_wf_shape2
  else
    echo "Unrecognized workflow name, cannot determine workflow \"shape\":"
    gsutil ls "${GCS_SUBMISSION_FOLDER}/"
    exit 1
  fi
}

function copy_gcs_uris_to_local_fs {
  gcs_uris_file="$1"
  local_fs_dest_dir="$2"

  MAX_CONCURRENT_GSUTIL_PROCS=20

  # Create a file containing the source and destination parameters for gsutil copy.
  GSUTIL_COPY_ARGS_FILE=$WORKFLOW_LOG_DIR/drs_log_gsutil_copy_args.txt
  rm -f "$GSUTIL_COPY_ARGS_FILE"
  while read -r drs_log_gcs_uri; do
      # Construct the local path based on the GCS URI
      uri_path="$(echo "$drs_log_gcs_uri" | cut -d / -f 4-)"
      local_path="$local_fs_dest_dir/$uri_path"

      # Write the gsutil copy source URI and destination file
      echo "$drs_log_gcs_uri $local_path" >> "$GSUTIL_COPY_ARGS_FILE"
  done < "$gcs_uris_file"

  # Verify the line count of the in log list file and the args file is the same.
  # TODO Programmatically verify this and if not true exit with an error
  wc -l "$GSUTIL_COPY_ARGS_FILE"

  # Perform concurrent gsutil copies using xargs to provide the process control.
  xargs -P $MAX_CONCURRENT_GSUTIL_PROCS -a "$GSUTIL_COPY_ARGS_FILE" -n 2 gsutil cp
}

parse_options $@
echo "GCS_SUBMISSION_FOLDER=${GCS_SUBMISSION_FOLDER}"
echo "WORKFLOW_LOG_DIR=${WORKFLOW_LOG_DIR}"

# Configure for the workflow shape of the provided WF_SUBMISSION_ID
configure_for_workflow_shape "${GCS_SUBMISSION_FOLDER}"

mkdir -p "$WORKFLOW_LOG_DIR"

DRS_LOG_LIST="${WORKFLOW_LOG_DIR}/drs_log_list.txt"
# rm -f "$DRS_LOG_LIST"

# Create a list of selected log file GCS URIs
time (gsutil ls -r "${GSUTIL_DRS_LOG_PATH}" > "$DRS_LOG_LIST")
wc -l "$DRS_LOG_LIST"

time copy_gcs_uris_to_local_fs "${DRS_LOG_LIST}" "${WORKFLOW_LOG_DIR}"

echo Done copying workflow log files!
