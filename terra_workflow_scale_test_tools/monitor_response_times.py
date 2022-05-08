import argparse
import csv
import functools
import json
import logging
import os
import psutil
import threading
import time

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Thread
from typing import Tuple, Optional, Any

import requests
import schedule


class DeploymentInfo:
    _project = None
    _terra_deployment_tier = None
    _terra_deployment_info = None
    _gen3_deployment_info = None

    class Project(Enum):
        ANVIL = 1
        BDC = 2
        CRDC = 3
        KF = 4

    @classmethod
    def set_project(cls, project_name: str) -> None:
        project = project_name.strip().upper()
        try:
            project_value = cls.Project[project]
        except KeyError as ex:
            raise Exception(f"Unsupported project name: '{project_name}'", ex)
        cls._project = project_value

    class TerraDeploymentTier(Enum):
        DEV = 1
        ALPHA = 2
        PERF = 3
        STAGING = 4
        PROD = 5

    @classmethod
    def set_terra_deployment_tier(cls, tier_name: str) -> None:
        tier = tier_name.strip().upper()
        try:
            tier_value = cls.TerraDeploymentTier[tier]
        except KeyError as ex:
            raise Exception(f"Invalid Terra deployment tier name: '{tier_name}'", ex)
        cls._terra_deployment_tier = tier_value

    @dataclass
    class TerraDeploymentInfo:
        bond_host: str
        bond_provider: str
        martha_host: str

    __terra_bdc_dev = TerraDeploymentInfo("broad-bond-dev.appspot.com",
                                          "fence",
                                          "us-central1-broad-dsde-dev.cloudfunctions.net")

    __terra_bdc_alpha = TerraDeploymentInfo("broad-bond-alpha.appspot.com",
                                            "fence",
                                            "us-central1-broad-dsde-alpha.cloudfunctions.net")

    __terra_bdc_prod = TerraDeploymentInfo("broad-bond-prod.appspot.com",
                                            "fence",
                                            "us-central1-broad-dsde-prod.cloudfunctions.net")

    __terra_crdc_dev = TerraDeploymentInfo("broad-bond-dev.appspot.com",
                                           "dcf-fence",
                                           "us-central1-broad-dsde-dev.cloudfunctions.net")

    __terra_crdc_alpha = TerraDeploymentInfo("broad-bond-alpha.appspot.com",
                                             "dcf-fence",
                                             "us-central1-broad-dsde-alpha.cloudfunctions.net")

    __terra_crdc_prod = TerraDeploymentInfo("broad-bond-prod.appspot.com",
                                             "dcf-fence",
                                             "us-central1-broad-dsde-prod.cloudfunctions.net")

    @dataclass
    class Gen3DeploymentInfo:
        gen3_host: str
        public_drs_uri: str
        cloud_uri_scheme: str = "gs"

    __gen3_bdc_staging = Gen3DeploymentInfo("staging.gen3.biodatacatalyst.nhlbi.nih.gov",
                                            "drs://dg.712C:dg.712C/fa640b0e-9779-452f-99a6-16d833d15bd0")

    __gen3_bdc_prod = Gen3DeploymentInfo("gen3.biodatacatalyst.nhlbi.nih.gov",
                                         "drs://dg.4503:dg.4503/15fdd543-9875-4edf-8bc2-22985473dab6")

    __gen3_crdc_staging = Gen3DeploymentInfo("nci-crdc-staging.datacommons.io",
                                            "drs://dg.4DFC:ddacaa74-97a9-4a0e-aa36-3e65fc8382d5")

    __gen3_crdc_prod = Gen3DeploymentInfo("nci-crdc.datacommons.io",
                                          "drs://dg.4DFC:011a6a54-1bfe-4df9-ae24-990b12a812d3")

    class UnsupportedConfigurationException(Exception):
        pass

    @classmethod
    def terra_factory(cls) -> TerraDeploymentInfo:
        if cls._terra_deployment_info is None:
            if cls._project == cls.Project.BDC:
                if cls._terra_deployment_tier == cls.TerraDeploymentTier.DEV:
                    cls._terra_deployment_info = cls.__terra_bdc_dev
                elif cls._terra_deployment_tier == cls.TerraDeploymentTier.ALPHA:
                    cls._terra_deployment_info = cls.__terra_bdc_alpha
                elif cls._terra_deployment_tier == cls.TerraDeploymentTier.PROD:
                    cls._terra_deployment_info = cls.__terra_bdc_prod
            elif cls._project == cls.Project.CRDC:
                if cls._terra_deployment_tier == cls.TerraDeploymentTier.DEV:
                    cls._terra_deployment_info = cls.__terra_crdc_dev
                elif cls._terra_deployment_tier == cls.TerraDeploymentTier.ALPHA:
                    cls._terra_deployment_info = cls.__terra_crdc_alpha
                elif cls._terra_deployment_tier == cls.TerraDeploymentTier.PROD:
                    cls._terra_deployment_info = cls.__terra_crdc_prod

            if cls._terra_deployment_info is None:
                raise cls.UnsupportedConfigurationException(
                    f"Response time monitoring for the combination of project \'{cls._project.name}\' and Terra deployment tier \'{cls._terra_deployment_tier.name}\' is currently unsupported.")
        return cls._terra_deployment_info

    @classmethod
    def gen3_factory(cls) -> Gen3DeploymentInfo:
        if cls._gen3_deployment_info is None:
            if cls._project == cls.Project.BDC:
                if cls._terra_deployment_tier == cls.TerraDeploymentTier.PROD:
                    cls._gen3_deployment_info = cls.__gen3_bdc_prod
                else:
                    cls._gen3_deployment_info = cls.__gen3_bdc_staging
            elif cls._project == cls.Project.CRDC:
                if cls._terra_deployment_tier == cls.TerraDeploymentTier.PROD:
                    cls._gen3_deployment_info = cls.__gen3_crdc_prod
                else:
                    cls._gen3_deployment_info = cls.__gen3_crdc_staging

            if cls._gen3_deployment_info is None:
                raise cls.UnsupportedConfigurationException(
                    f"Response time monitoring for the combination of project '{cls._project.name}' and Terra deployment tier '{cls._terra_deployment_tier.name}' is currently unsupported.")
        return cls._gen3_deployment_info


class MonitoringUtilityMethods:
    def __init__(self):
        super().__init__()

    @staticmethod
    def format_timestamp_as_utc(seconds_since_epoch: float):
        return datetime.fromtimestamp(seconds_since_epoch, timezone.utc).strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def monitoring_info(start_time: float, response: requests.Response):
        response_duration = round(time.time() - start_time, 3)
        response_code = response.status_code
        response_reason = response.reason
        return dict(start_time=start_time, response_duration=response_duration,
                    response_code=response_code, response_reason=response_reason)

    def flatten_monitoring_info_dict(self, monitoring_info_dict: dict) -> dict:
        flattened = dict()
        for operation_name, mon_info in monitoring_info_dict.items():
            for metric, value in mon_info.items():
                if metric in ['start_time', 'response_duration', 'response_code', 'response_reason']:
                    if metric == 'start_time' and type(value) == float:
                        value = self.format_timestamp_as_utc(value)
                    flattened[f"{operation_name}.{metric}"] = value
        return flattened

    @staticmethod
    def get_output_filepath(output_filename: str):
        global output_dir
        return os.path.join(output_dir, output_filename)

    def write_monitoring_info_to_csv(self, monitoring_info_dict: dict, output_filename: str) -> None:
        output_filename = self.get_output_filepath(output_filename)
        write_header = False if Path(output_filename).exists() else True

        row_info = self.flatten_monitoring_info_dict(monitoring_info_dict)
        with open(output_filename, 'a', newline='') as csvfile:
            fieldnames = sorted(row_info.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row_info)


class TerraMethods(MonitoringUtilityMethods):
    def __init__(self):
        super().__init__()
        self._terra_info = DeploymentInfo.terra_factory()
        self._gen3_info = DeploymentInfo.gen3_factory()

    # When run in Terra, this returns the Terra user pet SA token
    @staticmethod
    def get_terra_user_pet_sa_token() -> str:
        import google.auth.transport.requests
        creds, projects = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        token = creds.token
        return token

    def get_external_identity_link_url_from_bond(self) -> Tuple[str, dict]:
        headers = {
            'content-type': "*/*"
        }
        start_time = time.time()
        resp = requests.options(
            f"https://{self._terra_info.bond_host}/api/link/v1/{self._terra_info.bond_provider}/authorization-url?scopes=openid&scopes=google_credentials&scopes=data&scopes=user&redirect_uri=https://app.terra.bio/#fence-callback&state=eyJwcm92aWRlciI6ImZlbmNlIn0=",
            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        link_url = resp.url if resp.ok else None
        return link_url, self.monitoring_info(start_time, resp)

    def get_external_identity_status_from_bond(self, terra_user_token: str) -> Tuple[dict, dict]:
        headers = {
            'authorization': f"Bearer {terra_user_token}",
            'content-type': "application/json"
        }
        start_time = time.time()
        resp = requests.get(f"https://{self._terra_info.bond_host}/api/link/v1/{self._terra_info.bond_provider}",
                            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        resp_json = resp.json() if resp.ok else None
        return resp_json, self.monitoring_info(start_time, resp)

    def get_fence_token_from_bond(self, terra_user_token: str) -> Tuple[str, dict]:
        headers = {
            'authorization': f"Bearer {terra_user_token}",
            'content-type': "application/json"
        }
        start_time = time.time()
        resp = requests.get(
            f"https://{self._terra_info.bond_host}/api/link/v1/{self._terra_info.bond_provider}/accesstoken",
            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        token = resp.json().get('token') if resp.ok else None
        return token, self.monitoring_info(start_time, resp)

    def get_service_account_key_from_bond(self, terra_user_token: str) -> Tuple[dict, dict]:
        headers = {
            'authorization': f"Bearer {terra_user_token}",
            'content-type': "application/json"
        }
        start_time = time.time()
        resp = requests.get(
            f"https://{self._terra_info.bond_host}/api/link/v1/{self._terra_info.bond_provider}/serviceaccount/key",
            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        sa_key = resp.json().get('data') if resp.ok else None
        return sa_key, self.monitoring_info(start_time, resp)

    def get_martha_drs_response(self, terra_user_token: str, drs_uri: str = None) -> Tuple[dict, dict]:
        if drs_uri is None:
            drs_uri = self._gen3_info.public_drs_uri

        headers = {
            'authorization': f"Bearer {terra_user_token}",
            'content-type': "application/json"
        }

        # Request the same fields as the Terra workflow DRS Localizer does.
        data = json.dumps(dict(url=drs_uri, fields=['gsUri', 'googleServiceAccount', 'accessUrl', 'hashes']))

        start_time = time.time()
        resp = requests.post(f"https://{self._terra_info.martha_host}/martha_v3/",
                             headers=headers, data=data)
        logger.debug(f"Request URL: {resp.request.url}")
        resp_json = resp.json() if resp.ok else None
        return resp_json, self.monitoring_info(start_time, resp)


class Gen3Methods(MonitoringUtilityMethods):
    def __init__(self):
        super().__init__()
        self.gen3_info = DeploymentInfo.gen3_factory()

    def get_gen3_drs_resolution(self, drs_uri: str = None) -> Tuple[dict, dict]:
        if drs_uri is None:
            drs_uri = self.gen3_info.public_drs_uri

        assert drs_uri.startswith("drs://")
        object_id = drs_uri.split(":")[-1]

        headers = {
            'content-type': "application/json"
        }

        start_time = time.time()
        resp = requests.get(f"https://{self.gen3_info.gen3_host}/ga4gh/drs/v1/objects/{object_id}",
                            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        resp_json = resp.json() if resp.ok else None
        return resp_json, self.monitoring_info(start_time, resp)

    @staticmethod
    def _get_drs_access_id(drs_response: dict, cloud_uri_scheme: str) -> Optional[Any]:
        for access_method in drs_response['access_methods']:
            if access_method['type'] == cloud_uri_scheme:
                return access_method['access_id']
        return None

    def get_gen3_drs_access(self, fence_user_token: str, drs_uri: str = None,
                            access_id: str = "gs") -> Tuple[dict, dict]:

        if drs_uri is None:
            drs_uri = self.gen3_info.public_drs_uri

        assert drs_uri.startswith("drs://")
        object_id = drs_uri.split(":")[-1]

        headers = {
            'authorization': f"Bearer {fence_user_token}",
            'content-type': "application/json"
        }

        start_time = time.time()
        resp = requests.get(f"https://{self.gen3_info.gen3_host}/ga4gh/drs/v1/objects/{object_id}/access/{access_id}",
                            headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        access_url = resp.json().get('url') if resp.ok else None
        return access_url, self.monitoring_info(start_time, resp)

    def get_fence_userinfo(self, fence_user_token: str):
        headers = {
            'authorization': f"Bearer {fence_user_token}",
            'content-type': "application/json",
            'accept': '*/*'
        }

        start_time = time.time()
        resp = requests.get(f"https://{self.gen3_info.gen3_host}/user/user/", headers=headers)
        logger.debug(f"Request URL: {resp.request.url}")
        resp_json = resp.json() if resp.ok else None
        return resp_json, self.monitoring_info(start_time, resp)


class Scheduler:
    def __init__(self):
        super().__init__()
        self.stop_run_continuously = None

    @staticmethod
    def run_continuously(interval=1):
        """Continuously run, while executing pending jobs at each
        elapsed time interval.
        @return cease_continuous_run: threading. Event which can
        be set to cease continuous run. Please note that it is
        *intended behavior that run_continuously() does not run
        missed jobs*. For example, if you've registered a job that
        should run every minute, and you set a continuous run
        interval of one hour then your job won't be run 60 times
        at each interval but only once.
        """
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            def __init__(self):
                super().__init__()

            def run(self):
                while not cease_continuous_run.is_set():
                    schedule.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease_continuous_run

    @staticmethod
    def run_threaded(job_func):
        job_thread = Thread(target=job_func)
        job_thread.start()

    def start_monitoring(self):
        logger.info("Starting background response time monitoring")
        self.stop_run_continuously = self.run_continuously()

    def stop_monitoring(self):
        logger.info("Stopping background response time monitoring")
        self.stop_run_continuously.set()


def catch_exceptions(cancel_on_failure=False):
    def catch_exceptions_decorator(job_func):
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):
            # noinspection PyBroadException
            try:
                return job_func(*args, **kwargs)
            except:
                import traceback
                logger.error(traceback.format_exc())
                if cancel_on_failure:
                    return schedule.CancelJob

        return wrapper

    return catch_exceptions_decorator


class ResponseTimeMonitor(Scheduler):
    interval_seconds = 30

    def __init__(self):
        super().__init__()

    class AbstractResponseTimeReporter(ABC):
        def __init__(self, output_filename):
            super().__init__()
            self.output_filename = output_filename

        @abstractmethod
        def measure_and_report(self):
            pass

    class DrsFlowResponseTimeReporter(AbstractResponseTimeReporter, TerraMethods, Gen3Methods):
        def __init__(self, output_filename):
            super().__init__(output_filename)

        def measure_response_times(self) -> dict:
            monitoring_infos = dict()
            try:
                terra_user_token = self.get_terra_user_pet_sa_token()

                # Get DRS metadata from Gen3 Indexd
                drs_metadata, mon_info = self.get_gen3_drs_resolution()
                monitoring_infos['indexd_get_metadata'] = mon_info

                # Get service account key from Bond
                sa_key, mon_info = self.get_service_account_key_from_bond(terra_user_token)
                monitoring_infos['bond_get_sa_key'] = mon_info

                # Get Fence user token from Bond
                fence_user_token, mon_info = self.get_fence_token_from_bond(terra_user_token)
                monitoring_infos['bond_get_access_token'] = mon_info
                assert fence_user_token is not None, "Failed to get Fence user token."

                # Get signed URL from Fence
                access_url, mon_info = self.get_gen3_drs_access(fence_user_token)
                monitoring_infos['fence_get_signed_url'] = mon_info

            except Exception as ex:
                logger.warning(f"Exception occurred: {ex}")

            return monitoring_infos

        def measure_and_report(self):
            monitoring_infos = self.measure_response_times()
            self.write_monitoring_info_to_csv(monitoring_infos, self.output_filename)

    class MarthaResponseTimeReporter(AbstractResponseTimeReporter, TerraMethods):
        def __init__(self, output_filename):
            super().__init__(output_filename)

        def measure_response_times(self) -> dict:
            monitoring_infos = dict()
            terra_user_token = self.get_terra_user_pet_sa_token()

            # Get Martha response time

            resp_json, mon_info = self.get_martha_drs_response(terra_user_token)
            monitoring_infos['martha'] = mon_info
            return monitoring_infos

        def measure_and_report(self):
            monitoring_infos = self.measure_response_times()
            self.write_monitoring_info_to_csv(monitoring_infos, self.output_filename)

    class BondExternalIdentityResponseTimeReporter(AbstractResponseTimeReporter, TerraMethods):
        def __init__(self, output_filename):
            super().__init__(output_filename)

        def measure_response_times(self) -> dict:
            monitoring_infos = dict()
            terra_user_token = self.get_terra_user_pet_sa_token()

            # Get Bond external identity link URL response time
            link_url, mon_info = self.get_external_identity_link_url_from_bond()
            monitoring_infos['bond_get_link_url'] = mon_info

            # Get Bond external identity status response time
            resp_json, mon_info = self.get_external_identity_status_from_bond(terra_user_token)
            monitoring_infos['bond_get_link_status'] = mon_info

            return monitoring_infos

        def measure_and_report(self):
            monitoring_infos = self.measure_response_times()
            self.write_monitoring_info_to_csv(monitoring_infos, self.output_filename)

    class FenceUserInfoResponseTimeReporter(AbstractResponseTimeReporter, TerraMethods, Gen3Methods):
        def __init__(self, output_filename):
            super().__init__(output_filename)

        def measure_response_times(self) -> dict:
            monitoring_infos = dict()
            terra_user_token = self.get_terra_user_pet_sa_token()
            fence_user_token, _ = self.get_fence_token_from_bond(terra_user_token)

            # Get Fence user info response time as a response time indicator for the
            # Gen3 Fence k8s portition for auth services, which is separate
            # from the partition for signed URL requests.
            resp_json, mon_info = self.get_fence_userinfo(fence_user_token)
            monitoring_infos['fence_user_info'] = mon_info
            return monitoring_infos

        def measure_and_report(self):
            monitoring_infos = self.measure_response_times()
            self.write_monitoring_info_to_csv(monitoring_infos, self.output_filename)

    @catch_exceptions()
    def check_drs_flow_response_times(self):
        output_filename = "drs_flow_response_times.csv"
        reporter = self.DrsFlowResponseTimeReporter(output_filename)
        reporter.measure_and_report()

    @catch_exceptions()
    def check_martha_response_time(self):
        output_filename = "martha_response_time.csv"
        reporter = self.MarthaResponseTimeReporter(output_filename)
        reporter.measure_and_report()

    @catch_exceptions()
    def check_bond_external_identity_response_times(self):
        output_filename = "bond_external_idenity_response_times.csv"
        reporter = self.BondExternalIdentityResponseTimeReporter(output_filename)
        reporter.measure_and_report()

    @catch_exceptions()
    def check_fence_user_info_response_time(self):
        output_filename = "fence_user_info_response_time.csv"
        reporter = self.FenceUserInfoResponseTimeReporter(output_filename)
        reporter.measure_and_report()

    def configure_monitoring(self):
        schedule.every(self.interval_seconds).seconds.do(super().run_threaded, self.check_drs_flow_response_times)
        schedule.every(self.interval_seconds).seconds.do(super().run_threaded, self.check_martha_response_time)
        schedule.every(self.interval_seconds).seconds.do(super().run_threaded,
                                                         self.check_bond_external_identity_response_times)
        schedule.every(self.interval_seconds).seconds.do(super().run_threaded, self.check_fence_user_info_response_time)


def configure_logging(output_directory_path: str) -> logging.Logger:
    log_filename = Path(os.path.join(output_directory_path, "monitor_response_times.log")).resolve().as_posix()
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(threadName)-12s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        filename=log_filename,
        filemode="w",
        level=logging.DEBUG)
    logging.Formatter.converter = time.gmtime
    print(f"Logging to file: {log_filename}")
    return logging.getLogger()


def parse_arg_list(arg_list: list = None) -> argparse.Namespace:
    utc_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-name', type=str, required=True,
                        help="Project to monitor. Supported values: BDC")
    parser.add_argument('--terra-deployment-tier', type=str, required=True,
                        help="Project to monitor. Supported values: DEV, ALPHA")
    parser.add_argument('--output-dir', type=str, required=False,
                        default=f"./monitoring_output_{utc_timestamp}",
                        help="Directory to contain monitoring output files")
    args = parser.parse_args(arg_list)
    return args


def create_output_directory(directory_path: str) -> None:
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def set_configuration(args: argparse.Namespace) -> None:
    global output_dir, logger
    DeploymentInfo.set_project(args.project_name)
    DeploymentInfo.set_terra_deployment_tier(args.terra_deployment_tier)

    # Call these now to raise any errors now rather than later while running.
    DeploymentInfo.terra_factory()
    DeploymentInfo.gen3_factory()

    create_output_directory(args.output_dir)
    output_dir = args.output_dir
    logger = configure_logging(args.output_dir)

    logger.info("Monitoring Configuration:")
    logger.info(f"Project: {args.project_name}")
    logger.info(f"Terra Deployment Tier: {args.terra_deployment_tier}")


responseTimeMonitor: ResponseTimeMonitor = None


def main(arg_list: list = None) -> None:
    args = parse_arg_list(arg_list)
    set_configuration(args)

    # Configure and start monitoring
    global responseTimeMonitor
    responseTimeMonitor = ResponseTimeMonitor()
    responseTimeMonitor.configure_monitoring()
    responseTimeMonitor.start_monitoring()

#
# Start/Stop monitoring in the current (callers) process
#

def start_monitoring_in_current_process(terra_deployment_tier: str,
                                        project_to_monitor: str,
                                        monitoring_output_directory: str) -> None:

    arg_list = ["--terra-deployment-tier", terra_deployment_tier,
                "--project", project_to_monitor,
                "--output-dir", monitoring_output_directory]
    main(arg_list)


def stop_monitoring_in_current_process() -> None:
    global responseTimeMonitor
    responseTimeMonitor.stop_monitoring()


#
# Start/Stop monitoring using a new background process
#


def start_monitoring_background_process(terra_deployment_tier: str,
                                        project_to_monitor: str,
                                        monitoring_output_directory: str)\
        -> psutil.Process:
    print("Starting monitoring background process ...")
    process = psutil.Popen(["python3",
                            __file__,
                            "--terra-deployment-tier", terra_deployment_tier,
                            "--project", project_to_monitor,
                            "--output-dir", monitoring_output_directory])
    print(f"Started {process}")
    return process


def stop_monitoring_background_process(process: psutil.Process) -> None:
    _termination_wait_seconds = 60
    print("Stopping monitoring background process ...")
    process.terminate()
    print("Waiting up {_termination_wait_seconds} seconds for process to terminate.")
    process.wait(_termination_wait_seconds)
    print("Stopped monitoring background process.")


if __name__ == "__main__":
    main()

    # # Run for a while
    # sleep_seconds = 90
    # print(f"Sleeping for {sleep_seconds} ...")
    # time.sleep(sleep_seconds)
    # print("Done sleeping")
    #
    # # Stop monitoring
    # responseTimeMonitor.stop_monitoring()

