# from __future__ import print_function

from enum import Enum
from copy import deepcopy

import json
import sys

from .network import NetworkHandler

from procset import ProcSet
import zmq
import logging



class Batsim(object):

    WORKLOAD_JOB_SEPARATOR = "!"
    ATTEMPT_JOB_SEPARATOR = "#"
    WORKLOAD_JOB_SEPARATOR_REPLACEMENT = "%"

    def __init__(self, scheduler,
                 network_endpoint,
                 timeout,
                 event_endpoint=None):


        self.logger = logging.getLogger(__name__)

        self.running_simulation = False
        self.network = NetworkHandler(network_endpoint, timeout=timeout)
        self.network.bind()

        # event hendler is optional
        self.event_publisher = None
        if event_endpoint is not None:
            self.event_publisher = NetworkHandler(event_endpoint, type=zmq.PUB)
            self.event_publisher.bind()

        self.jobs = dict()

        sys.setrecursionlimit(10000)

        self.scheduler = scheduler

        # initialize some public attributes
        self.nb_jobs_submitted_from_batsim = 0
        self.nb_jobs_submitted_from_scheduler = 0
        self.nb_jobs_submitted = 0
        self.nb_jobs_killed = 0
        self.nb_jobs_rejected = 0
        self.nb_jobs_scheduled = 0
        self.nb_jobs_in_submission = 0
        self.nb_jobs_completed = 0
        self.nb_jobs_successful = 0
        self.nb_jobs_failed = 0
        self.nb_jobs_timeout = 0

        self.jobs_manually_changed = set()

        self.no_more_static_jobs = False
        self.no_more_external_events = False
        self.use_storage_controller = False

        self.scheduler.bs = self
        # import pdb; pdb.set_trace()
        # Wait the "simulation starts" message to read the number of machines
        self._read_bat_msg()

        self.scheduler.onAfterBatsimInit()

    def publish_event(self, event):
        """Sends a message to subscribed event listeners (e.g. external processes which want to
        observe the simulation).
        """
        if self.event_publisher is not None:
            self.event_publisher.send_string(event)

    def time(self):
        return self._current_time

    def consume_time(self, t):
        self._current_time += float(t)
        return self._current_time

    def wake_me_up_at(self, time):
        self._events_to_send.append(
            {"timestamp": self.time(),
             "type": "CALL_ME_LATER",
             "data": {"timestamp": time}})

    def notify_registration_finished(self):
        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "NOTIFY",
            "data": {
                    "type": "registration_finished",
            }
        })

    def notify_registration_continue(self):
        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "NOTIFY",
            "data": {
                    "type": "continue_registration",
            }
        })

    def send_message_to_job(self, job, message):
        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "TO_JOB_MSG",
            "data": {
                    "job_id": job.id,
                    "msg": message,
            }
        })

    def start_jobs(self, jobs, res):
        """ DEPRECATED: please use execute_jobs instead """
        """ args:res: is list of int (resources ids) """
        for job in jobs:
            self._events_to_send.append({
                "timestamp": self.time(),
                "type": "EXECUTE_JOB",
                "data": {
                        "job_id": job.id,
                        "alloc": str(ProcSet(*res[job.id]))
                }
            }
            )
            self.nb_jobs_scheduled += 1

    def execute_job(self, job, io_job = None):
        """ ergs.job: Job to execute
            job.allocation MUST be not None and should be a non-empty ProcSet
        """
        assert job.allocation is not None
        message = {
            "timestamp": self.time(),
            "type": "EXECUTE_JOB",
            "data": {
                    "job_id": job.id,
                    "alloc": str(job.allocation)
            }
        }

        self.jobs[job.id].allocation = job.allocation
        self.jobs[job.id].state = Job.State.RUNNING

        if io_job is not None:
            message["data"]["additional_io_job"] = io_job

        if hasattr(job, "mapping"):
            message["data"]["mapping"] = job.mapping
            self.jobs[job.id].mapping = job.mapping

        if hasattr(job, "storage_mapping"):
            message["data"]["storage_mapping"] = job.storage_mapping
            self.jobs[job.id].storage_mapping = job.storage_mapping

        self.jobs[job.id].allocation = job.allocation

        self._events_to_send.append(message)
        self.nb_jobs_scheduled += 1

    def execute_jobs(self, jobs, io_jobs=None):
        """ args:jobs: list of jobs to execute
            job.allocation MUST be not None and should be a non-empty ProcSet
        """
        for job in jobs:
            if io_jobs is not None:
                self.execute_job(job, io_jobs[job.id])
            else:
                self.execute_job(job)

    def reject_jobs_by_id(self, job_ids):
        """ Reject the given jobs."""
        assert len(job_ids) > 0, "The list of jobs to reject is empty"
        for job_id in job_ids:
            self._events_to_send.append({
                "timestamp": self.time(),
                "type": "REJECT_JOB",
                "data": {
                    "job_id": job_id
                }
            })
            self.jobs[job_id].state = Job.State.REJECTED
        self.nb_jobs_rejected += len(job_ids)

    def reject_jobs(self, jobs):
        """Reject the given jobs."""
        assert len(jobs) > 0, "The list of jobs to reject is empty"
        job_ids = [x.id for x in jobs]
        self.reject_jobs_by_id(job_ids)


    def change_job_state(self, job, state):
        """Change the state of a job."""
        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "CHANGE_JOB_STATE",
            "data": {
                    "job_id": job.id,
                    "job_state": state.name,
            }
        })
        self.jobs_manually_changed.add(job)

    def kill_jobs(self, jobs):
        """Kill the given jobs."""
        assert len(jobs) > 0, "The list of jobs to kill is empty"
        for job in jobs:
            job.job_state = Job.State.IN_KILLING
        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "KILL_JOB",
            "data": {
                    "job_ids": [job.id for job in jobs],
            }
        })

    def register_profiles(self, workload_name, profiles):
        for profile_name, profile in profiles.items():
            msg = {
                "timestamp": self.time(),
                "type": "REGISTER_PROFILE",
                "data": {
                    "workload_name": workload_name,
                    "profile_name": profile_name,
                    "profile": profile,
                }
            }
            self._events_to_send.append(msg)
            if not workload_name in self.profiles:
                self.profiles[workload_name] = {}
                self.logger.debug("A new dynamic workload of name '{}' has been created".format(workload_name))
            self.logger.debug("Registering profile: {}".format(msg["data"]))
            self.profiles[workload_name][profile_name] = profile

    def register_job(
            self,
            id,
            res,
            walltime,
            profile_name,
            dependencies,
            subtime=None):
        """ Returns the registered Job """

        if subtime is None:
            subtime = self.time()
        job_dict = {
            "profile": profile_name,
            "id": id,
            "res": res,
            "walltime": walltime,
            "subtime": subtime,
            "dependencies": dependencies,
        }
        msg = {
            "timestamp": self.time(),
            "type": "REGISTER_JOB",
            "data": {
                "job_id": id,
                "job": job_dict,
            }
        }
        self._events_to_send.append(msg)
        job = Job.from_json_dict(job_dict)
        job.job_state = Job.State.IN_SUBMISSON
        
        if self.ack_of_dynamic_jobs:
            self.nb_jobs_in_submission += 1
        else:
            self.nb_jobs_submitted += 1
            self.nb_jobs_submitted_from_scheduler += 1

        # Keep a pointer of the profile in the job structure
        assert job.profile in self.profiles[job.workload]
        job.profile_dict = self.profiles[job.workload][job.profile]

        self.jobs[id] = job
        return job

    def set_resource_state(self, resources, state):
        """ args:resources: is a ProcSet containing a list of resources.
            args:state: is a state identifier configured in the platform specification.
        """

        self._events_to_send.append({
            "timestamp": self.time(),
            "type": "SET_RESOURCE_STATE",
            "data": {
                    "resources": str(resources),
                    "state": str(state)
            }
        })

    def get_job_and_profile(self, event):
        json_dict = event["data"]["job"]
        job = Job.from_json_dict(json_dict)

        if "profile" in event["data"]:
            profile = event["data"]["profile"]
        else:
            profile = {}

        return job, profile


    def request_consumed_energy(self): #TODO CHANGE NAME
        self._events_to_send.append(
            {
                "timestamp": self.time(),
                "type": "QUERY",
                "data": {
                    "requests": {"consumed_energy": {}}
                }
            }
        )

    def notify_resources_added(self, resources):
        self._events_to_send.append(
            {
                "timestamp": self.time(),
                "type": "RESOURCES_ADDED",
                "data": {
                    "resources": str(resources)
                }
            }
        )

    def notify_resources_removed(self, resources):
        self._events_to_send.append(
            {
                "timestamp": self.time(),
                "type": "RESOURCES_REMOVED",
                "data": {
                    "resources": str(resources)
                }
            }
        )

    def set_job_metadata(self, job_id, metadata):
        # Consume some time to be sure that the job was created before the
        # metadata is set

        self._events_to_send.append(
            {
                "timestamp": self.time(),
                "type": "SET_JOB_METADATA",
                "data": {
                    "job_id": str(job_id),
                    "metadata": str(metadata)
                }
            }
        )
        self.jobs[job_id].metadata = metadata


    def resubmit_job(self, job):
        """
        The given job is resubmited but in a dynamic workload. The name of this
        workload is "resubmit=N" where N is the number of resubmission.
        The job metadata is filled with a dict that contains the original job
        full id in "parent_job" and the number of resubmissions in "nb_resubmit".
        """

        if job.metadata is None:
            metadata = {"parent_job": job.id, "nb_resubmit": 1}
        else:
            metadata = deepcopy(job.metadata)
            if "nb_resubmit" not in metadata:
                metadata["nb_resubmit"] = 1
            else:
                metadata["nb_resubmit"] = metadata["nb_resubmit"] + 1
            if "parent_job" not in metadata:
                metadata["parent_job"] = job.id

        # Keep the current workload and add a resubmit number
        splitted_id = job.id.split(Batsim.ATTEMPT_JOB_SEPARATOR)
        if len(splitted_id) == 1:
            new_job_name = deepcopy(job.id)
        else:
            # This job has already an attempt number
            new_job_name = splitted_id[0]
            assert splitted_id[1] == str(metadata["nb_resubmit"] - 1)
        new_job_name =  new_job_name + Batsim.ATTEMPT_JOB_SEPARATOR + str(metadata["nb_resubmit"])
        # log in job metadata parent job and nb resubmit

        job_dependencies = []
        if hasattr(job, "dependencies") and job.dependencies is not None:
            job_dependencies = deepcopy(job.dependencies)
        
        new_job = self.register_job(
                new_job_name,
                job.requested_resources,
                job.requested_time,
                job.profile,
                job_dependencies)

        self.set_job_metadata(new_job_name, metadata)
        return new_job

    def do_next_event(self):
        return self._read_bat_msg()

    def start(self):
        cont = True
        while cont:
            cont = self.do_next_event()

    def _read_bat_msg(self):
        msg = None
        while msg is None:
            msg = self.network.recv(blocking=not self.running_simulation)
            if msg is None:
                self.scheduler.onDeadlock()
                continue
        self.logger.info("Message Received from Batsim: {}".format(msg))

        self._current_time = msg["now"]

        self._events_to_send = []

        finished_received = False

        self.scheduler.onBeforeEvents()

        for event in msg["events"]:
            event_type = event["type"]
            event_data = event.get("data", {})
            if event_type == "SIMULATION_BEGINS":
                assert not self.running_simulation, "A simulation is already running (is more than one instance of Batsim active?!)"
                self.running_simulation = True
                self.nb_resources = event_data["nb_resources"]
                self.nb_compute_resources = event_data["nb_compute_resources"]
                self.nb_storage_resources = event_data["nb_storage_resources"]
                compute_resources = event_data["compute_resources"]
                storage_resources = event_data["storage_resources"]
                self.machines = {"compute": compute_resources, "storage": storage_resources}
                self.batconf = event_data["config"]
                self.allow_compute_sharing = event_data["allow_compute_sharing"]
                self.allow_storage_sharing = event_data["allow_storage_sharing"]
                self.profiles_forwarded_on_submission = self.batconf["profiles-forwarded-on-submission"]
                self.dynamic_job_registration_enabled = self.batconf["dynamic-jobs-enabled"]
                self.ack_of_dynamic_jobs = self.batconf["dynamic-jobs-acknowledged"]
                self.forward_unknown_events = self.batconf["forward-unknown-events"]

                if self.dynamic_job_registration_enabled:
                    self.logger.warning("Dynamic registration of jobs is ENABLED. The scheduler must send a NOTIFY event of type 'registration_finished' to let Batsim end the simulation.")

                # Retro compatibility for old Batsim API > 1.0 < 3.0
                if "resources_data" in event_data:
                    res_key = "resources_data"
                else:
                    res_key = "compute_resources"
                self.compute_resources = {
                        res["id"]: res for res in event_data[res_key]}
                self.storage_resources = {
                        res["id"]: res for res in event_data["storage_resources"]}

                self.profiles = event_data["profiles"]

                self.workloads = event_data["workloads"]

                self.scheduler.onSimulationBegins()

            elif event_type == "SIMULATION_ENDS":
                assert self.running_simulation, "No simulation is currently running"
                self.running_simulation = False
                self.logger.info("All jobs have been submitted and completed!")
                finished_received = True
                self.scheduler.onSimulationEnds()

            elif event_type == "JOB_SUBMITTED":
                # Received WORKLOAD_NAME!JOB_ID
                job_id = event_data["job_id"]
                job, profile = self.get_job_and_profile(event)
                job.job_state = Job.State.SUBMITTED
                self.nb_jobs_submitted += 1

                # Store profile if not already present
                if profile is not None:
                    if job.workload not in self.profiles:
                        self.profiles[job.workload] = {}
                    if job.profile not in self.profiles[job.workload]:
                        self.profiles[job.workload][job.profile] = profile

                # Keep a pointer in the job structure
                assert job.profile in self.profiles[job.workload]
                job.profile_dict = self.profiles[job.workload][job.profile]

                # Warning: override dynamic job but keep metadata
                if job_id in self.jobs:
                    self.logger.warn(
                        "The job '{}' was alredy in the job list. "
                        "Probaly a dynamic job that was submitted "
                        "before: \nOld job: {}\nNew job: {}".format(
                            job_id,
                            self.jobs[job_id],
                            job))
                    if self.jobs[job_id].job_state == Job.State.IN_SUBMISSON:
                        self.nb_jobs_in_submission = self.nb_jobs_in_submission - 1
                    # Keeping metadata and profile
                    job.metadata = self.jobs[job_id].metadata
                    self.nb_jobs_submitted_from_scheduler += 1
                else:
                    # This was submitted from batsim
                    self.nb_jobs_submitted_from_batsim += 1
                self.jobs[job_id] = job

                if (self.use_storage_controller) and (job.workload == "dyn-storage-controller"):
                    # This job comes from the StorageController, it' just an ack so forget about it
                    pass
                else:
                    self.scheduler.onJobSubmission(job)

            elif event_type == "JOB_KILLED":
                # get progress
                killed_jobs = []
                for jid in event_data["job_ids"]:
                    j = self.jobs[jid]
                    # The job_progress can only be empty if the job has completed
                    # between the order of killing and the killing itself.
                    # So in that case just dont put it in the killed jobs
                    # because it was already mark as complete.
                    if len(event_data["job_progress"]) != 0:
                        j.progress = event_data["job_progress"][jid]
                        killed_jobs.append(j)
                if len(killed_jobs) != 0:
                    self.scheduler.onJobsKilled(killed_jobs)

            elif event_type == "JOB_COMPLETED":
                job_id = event_data["job_id"]
                j = self.jobs[job_id]
                j.finish_time = event["timestamp"]

                try:
                    j.job_state = Job.State[event["data"]["job_state"]]
                except KeyError:
                    j.job_state = Job.State.UNKNOWN
                j.return_code = event["data"]["return_code"]

                if j.job_state == Job.State.COMPLETED_WALLTIME_REACHED:
                    self.nb_jobs_timeout += 1
                elif j.job_state == Job.State.COMPLETED_FAILED:
                    self.nb_jobs_failed += 1
                elif j.job_state == Job.State.COMPLETED_SUCCESSFULLY:
                    self.nb_jobs_successful += 1
                elif j.job_state == Job.State.COMPLETED_KILLED:
                    self.nb_jobs_killed += 1
                self.nb_jobs_completed += 1

                if (self.use_storage_controller) and (j.workload == "dyn-storage-controller"):
                    # This job comes from the Storage Controller
                    self.storage_controller.data_staging_completed(j)
                else:
                    self.scheduler.onJobCompletion(j)

            elif event_type == "FROM_JOB_MSG":
                job_id = event_data["job_id"]
                j = self.jobs[job_id]
                timestamp = event["timestamp"]
                msg = event_data["msg"]
                self.scheduler.onJobMessage(timestamp, j, msg)

            elif event_type == "RESOURCE_STATE_CHANGED":
                intervals = event_data["resources"].split(" ")
                for interval in intervals:
                    nodes = interval.split("-")
                    if len(nodes) == 1:
                        nodeInterval = (int(nodes[0]), int(nodes[0]))
                    elif len(nodes) == 2:
                        nodeInterval = (int(nodes[0]), int(nodes[1]))
                    else:
                        raise Exception("Multiple intervals are not supported")
                    self.scheduler.onMachinePStateChanged(
                        nodeInterval, event_data["state"])

            elif event_type == "ANSWER":
                if "consumed_energy" in event_data:
                    consumed_energy = event_data["consumed_energy"]
                    self.scheduler.onReportEnergyConsumed(consumed_energy)

            elif event_type == 'REQUESTED_CALL':
                self.scheduler.onRequestedCall()

            elif event_type == 'ADD_RESOURCES':
                self.scheduler.onAddResources(ProcSet.from_str(event_data["resources"]))

            elif event_type == 'REMOVE_RESOURCES':
                self.scheduler.onRemoveResources(ProcSet.from_str(event_data["resources"]))

            elif event_type == "NOTIFY":
                notify_type = event_data["type"]
                if notify_type == "no_more_static_job_to_submit":
                    self.no_more_static_jobs = True
                    self.scheduler.onNoMoreJobsInWorkloads()
                elif notify_type == "no_more_external_event_to_occur":
                    self.no_more_external_events = True
                    self.scheduler.onNoMoreExternalEvents()
                elif notify_type == "event_machine_unavailable":
                    self.scheduler.onNotifyEventMachineUnavailable(ProcSet.from_str(event_data["resources"]))
                elif notify_type == "event_machine_available":
                    self.scheduler.onNotifyEventMachineAvailable(ProcSet.from_str(event_data["resources"]))
                elif self.forward_unknown_events:
                    self.scheduler.onNotifyGenericEvent(event_data)
                else:
                    raise Exception("Unknown NOTIFY type {}".format(notify_type))
            else:
                raise Exception("Unknown event type {}".format(event_type))

        self.scheduler.onNoMoreEvents()

        if len(self._events_to_send) > 0:
            # sort msgs by timestamp
            self._events_to_send = sorted(
                self._events_to_send, key=lambda event: event['timestamp'])

        new_msg = {
            "now": self._current_time,
            "events": self._events_to_send
        }
        self.network.send(new_msg)
        self.logger.info("Message Sent to Batsim: {}".format(new_msg))


        if finished_received:
            self.network.close()
            if self.event_publisher is not None:
                self.event_publisher.close()

        return not finished_received

class Job(object):

    class State(Enum):
        UNKNOWN = -1
        IN_SUBMISSON = 0
        SUBMITTED = 1
        RUNNING = 2
        COMPLETED_SUCCESSFULLY = 3
        COMPLETED_FAILED = 4
        COMPLETED_WALLTIME_REACHED = 5
        COMPLETED_KILLED = 6
        REJECTED = 7
        IN_KILLING = 8

    def __init__(
            self,
            id,
            subtime,
            walltime,
            res,
            profile,
            dependencies,
            json_dict):
        self.id = id
        self.submit_time = subtime
        self.requested_time = walltime
        self.requested_resources = res
        self.profile = profile
        self.dependencies = dependencies
        self.finish_time = None  # will be set on completion by batsim
        self.job_state = Job.State.UNKNOWN
        self.return_code = None
        self.progress = None
        self.json_dict = json_dict
        self.profile_dict = None
        self.allocation = None
        self.metadata = None

    def __repr__(self):
        return(
            ("{{Job {0}; sub:{1} res:{2} reqtime:{3} prof:{4} "
                "state:{5} ret:{6} alloc:{7}, meta:{8}, dep:{9}}}\n").format(
            self.id, self.submit_time, self.requested_resources,
            self.requested_time, self.profile,
            self.job_state,
            self.return_code, self.allocation, self.metadata, self.dependencies))

    @property
    def workload(self):
        return self.id.split(Batsim.WORKLOAD_JOB_SEPARATOR)[0]

    @staticmethod
    def from_json_string(json_str):
        json_dict = json.loads(json_str)
        return Job.from_json_dict(json_dict)

    @staticmethod
    def from_json_dict(json_dict):
        dependencies = []
        if "dependencies" in json_dict:
            dependencies = json_dict["dependencies"]

        return Job(json_dict["id"],
                   json_dict["subtime"],
                   json_dict.get("walltime", -1),
                   json_dict["res"],
                   json_dict["profile"],
                   dependencies,
                   json_dict)
    # def __eq__(self, other):
        # return self.id == other.id
    # def __ne__(self, other):
        # return not self.__eq__(other)


class BatsimScheduler(object):

    def __init__(self, options = {}):
        self.options = options
        self.logger = logging.getLogger(__name__)

    def onAfterBatsimInit(self):
        # You now have access to self.bs and all other functions
        pass

    def onSimulationBegins(self):
        self.logger.info("Hello from custom pybatsim :)")
        pass

    def onSimulationEnds(self):
        pass

    def onDeadlock(self):
        raise ValueError(
            "[PYBATSIM]: Batsim is not responding (maybe deadlocked)")

    def onJobSubmission(self, job):
        raise NotImplementedError()

    def onJobCompletion(self, job):
        raise NotImplementedError()

    def onJobMessage(self, timestamp, job, message):
        raise NotImplementedError()

    def onJobsKilled(self, jobs):
        raise NotImplementedError()

    def onMachinePStateChanged(self, nodeid, pstate):
        raise NotImplementedError()

    def onReportEnergyConsumed(self, consumed_energy):
        raise NotImplementedError()

    def onAddResources(self, to_add):
        raise NotImplementedError()

    def onRemoveResources(self, to_remove):
        raise NotImplementedError()

    def onRequestedCall(self):
        raise NotImplementedError()

    def onNoMoreJobsInWorkloads(self):
        self.logger.info("There is no more static jobs in the workload")

    def onNoMoreExternalEvents(self):
        self.logger.info("There is no more external events to occur")

    def onNotifyEventMachineUnavailable(self, machines):
        raise NotImplementedError()

    def onNotifyEventMachineAvailable(self, machines):
        raise NotImplementedError()

    def onNotifyGenericEvent(self, event_data):
        raise NotImplementedError()

    def onDatasetArrivedOnStorage(self, dataset_id, source_id, dest_id): # Called by the Storage Controller, if any
        raise NotImplementedError()

    def onDataTransferNotTerminated(self, dataset_id, source_id, dest_id): # Called by the Storage Controller, if any
        raise NotImplementedError()

    def onBeforeEvents(self):
        pass

    def onNoMoreEvents(self):
        pass