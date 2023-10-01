from .batsim import Job

from collections import namedtuple, defaultdict
from procset import ProcSet

DataTransfer = namedtuple('DataTransfer', ['source_id', 'dest_id', 'dataset_id'])

class Dataset:
    def __init__(self, id, size):
        self.id = id                       # UID of the dataset
        self.size = size                   # Size in bytes of the dataset (float)

    def get_id(self):
        """ Returns the id of the Dataset """
        return self.id

    def get_size(self):
        """ Returns the size of the Dataset """
        return self.size
# End of class Dataset


class Storage:
    def __init__(self, id, name, storage_capacity):
        self.id = id                                   # Batsim resource id of the storage
        self.name = name                               # Name of the storage

        self.is_main_storage = True if name == "main_storage" else  False

        self.storage_capacity = storage_capacity       # In bytes (float), the total capacity
        self.available_space = storage_capacity        # In bytes (float), the free space
        self.reserved_space = 0                        # In bytes (float), the space reserved for datasets being transferred

        self.datasets = dict()                         # Dict of dataset_id -> Dataset object
        self.dataset_timestamps = dict()               # Dict of dataset_id -> Dataset timestamp
        # The timestamp corresponds to the last time the Dataset has been requested or a tag was added

        self.dataset_tags = defaultdict(set)           # Dict of dataset_id -> set of tags
        # A tagged dataset cannot be removed from the storage

    def load_datasets_from_list(self, dataset_list, timestamp):
        # Function to populate a Storage at a given timestamp
        # Each element of the list should be a dict of the form:
        # {"id" : "the_dataset_id", "size" : the_dataset_size_in_bytes}
        for elt in dataset_list:
            if not (self.add_dataset(Dataset(elt["id"], elt["size"]), timestamp)):
                # There is not enough space in the Storage
                assert False, f"Not enough storage capacity for {self.name} ({self.id}), could not load the entire list of datasets"

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def is_main_storage(self):
        return self.is_main_storage

    def get_available_space(self):
        """ Returns the available space on the Storage """
        return self.available_space

    def get_storage_capacity(self):
        """ Returns the storage capacity of the Storage """
        return self.storage_capacity

    def get_reserved_space(self):
        """ Returns the reserved space on the Storage """
        return self.reserved_space

    def get_datasets(self):
        """ Returns the list of datasets on the Storage """
        return self.datasets.values()

    def get_dataset_from_id(self, dataset_id):
        """ Returns a Dataset corresponding to the dataset_id if it exists """
        return self.datasets[dataset_id] if self.has_dataset(dataset_id) else None

    def has_dataset(self, dataset_id):
        """ Returns whether a Dataset is in the Storage """
        return dataset_id in self.datasets

    def add_dataset(self, dataset, timestamp):
        """ Adds a Dataset to the Storage and updates the available space
        If the dataset is already present, its timestamp is updated
        Returns False if the Dataset could not be added due to lack of available space
        """
        # Check if the storage already has the dataset with this id. If yes, do not subtract available space
        dataset_id = dataset.get_id()
        if not self.has_dataset(dataset_id):
            if self.available_space < dataset.get_size():
                return False # Not enough available space
            else:
                self.datasets[dataset_id] = dataset
                self.available_space = self.available_space - dataset.get_size()

        # Then update the timestamp of last use
        self.dataset_timestamps[dataset_id] = timestamp
        return True

    def delete_dataset_from_id(self, dataset_id):
        """ Delete the Dataset on Storage corresponding to the dataset_id
        When deleting a Dataset, its size is added to remaining storage space on Storage.
        Returns False if the Dataset was not present in this Storage or if it still had tags
        Returns True if the Dataset was correctly removed.
        """
        if not self.has_dataset(dataset_id):
            return False # The Dataset is not present

        if len(self.dataset_tags[dataset_id]) > 0:
            # There are still tags for this Dataset
            return False

        dataset = self.datasets.pop(dataset_id)
        self.available_space = self.available_space + dataset.get_size()
        del self.dataset_timestamps[dataset_id]

        return True

    def has_enough_free_space(self, size):
        """ Returns true if the Storage has enough space to store a dataset corresponding to the
        provided size.
        """
        return (self.available_space - size) >= 0

    def update_timestamp(self, dataset_id, timestamp):
        """
        :param dataset_id: Dataset id to update timestamp with
        :return: False if dataset with id not present, True otherwise
        """
        if not self.has_dataset(dataset_id):
            return False
        else:
            self.dataset_timestamps[dataset_id] = timestamp
            return True


    def make_space(self, asked_space):
        """ Tries to evict datasets from storage until enough space is available for asked_space
        The default implementation is the LRU policy: the Least Recently Used dataset
        which has no tag in the storage is designed to be evicted.
        The process is repeated until enough space was made.

        This method can be changed to implement other evicting strategies as needed.

        Returns True if enough space was made for asked_space. Some datasets were evicted
        Returns False otherwise and NO datasets were evicted
        """

        to_evict = []
        timestamps = list(self.dataset_timestamps.items())
        timestamps.sort(key=lambda tup:tup[1]) # Sort the datasets by increasing timestamps

        space_to_make = asked_space - self.available_space
        i = 0
        while (space_to_make > 0) and (i < len(timestamps)):
            dataset_id, _ = timestamps[i]

            if len(self.dataset_tags[dataset_id]) == 0:
                # This dataset has no tag, we can evict it
                to_evict.append(dataset_id)
                space_to_make -= self.get_dataset_from_id(dataset_id).get_size()

            i+= 1

        if space_to_make <= 0:
            # We have enough space to free
            for dataset_id in to_evict:
                self.delete_dataset_from_id(dataset_id)
            return True
        else:
            # We could not evict enough datasets
            # So don't evict any dataset
            return False


    def add_tag_on_dataset(self, dataset_id, tag_name, timestamp):
        """ Adds a tag on the dataset and updates the timestamp of the Dataset
        Returns False if the Dataset is not present in the Storage
        Returns True if the tag is correctly added
        """
        if not self.has_dataset(dataset_id):
            return False

        self.dataset_tags[dataset_id].add(tag_name)
        self.dataset_timestamps[dataset_id] = timestamp
        return True

    def remove_tag_on_dataset(self, dataset_id, tag_name):
        """ Removes the tag on the dataset """
        if tag_name in self.dataset_tags[dataset_id]:
            self.dataset_tags[dataset_id].remove(tag_name)

    def remove_tag_on_all_datasets(self, tag_name):
        """ Removes the tag on all datasets of this storage """
        for dataset_id in self.dataset_tags.keys():
            self.remove_tag_on_dataset(dataset_id, tag_name)
# End of class Storage


class StorageController:
    def __init__(self, storage_resources, bs, scheduler, options):
        self.storages = dict()          # Maps the storage Batsim resource id to the Storage object
        self.main_storage_id = -1       # The Batsim resource id of the main_storage, if any
        self.next_staging_job_id = 0
        self.bs = bs               # Pybatsim
        self.scheduler = scheduler # Scheduler
        self.logger = bs.logger
        self.options = options

        self.current_transfers = {} # Maps a data staging Batsim Job to a DataTransfer tuple (source_id, dest_id, dataset_id)

        self.bs.use_storage_controller = True
        self.bs.storage_controller = self

        # Some metrics about transfers
        self.total_transferred_from_main = 0 # In Bytes
        self.nb_transfers_zero = 0 # The number of times a dataset was already present on storage when asked to transfer it
        self.nb_transfers_real = 0 # The number of "real" transfers (i.e., when the dataset was not already present on storage)

        assert self.bs.dynamic_job_registration_enabled, "Dynamic job registration must be enabled to use the Storage Controller"

        for res in storage_resources:
            new_storage = Storage(res["id"], res["name"], float(res["properties"]["size"]))

            # If it is the main_storage remember its id
            if res["name"] == "main_storage":
                self.main_storage_id = res["id"]

            self.add_storage(new_storage)

        self.logger.info(f"[{self.bs.time()}] StorageController initialization completed, main storage id is {self.main_storage_id} and there are {len(self.storages)-1} other storage resources in total")


    def has_storage(self, storage_id):
        return storage_id in self.storages

    def get_storage(self, storage_id):
        """ Returns the Storage corresponding to given storage_id if it exists or returns None. """
        return self.storages[storage_id] if self.has_storage(storage_id) else None

    def get_storages_dict(self):
        """ Returns the Storages dict of the Storage Controller """
        return self.storages

    def add_storage(self, storage):
        """ Add storage to storages dict """
        self.storages[storage.id] = storage


    def add_dataset_to_storage(self, storage_id, dataset, timestamp):
        """ Adds a dataset to the given storage and
        updates its timestamp if it was already present in the storage
        This function is called after completion of a Batsim data_staging job
        Returns False if the Storage does not exist
        Returns True otherwise
        Precondition: The dataset has enough space in the storage
        """
        storage = self.get_storage(storage_id)
        dataset_id = dataset.get_id()

        if storage == None:
            return False

        # Check if the storage already has the dataset
        if storage.get_dataset_from_id(dataset_id) != None:
            self.logger.debug("[{}] Dataset {} already present in storage with id {}".format(self.bs.time(), dataset_id, storage_id))

            storage.update_timestamp(dataset_id, timestamp)
        else:
            storage.add_dataset(dataset, timestamp)

        return True


    def has_dataset_on_storage(self, dataset_id, storage_id):
        """ Checks if a storage has a dataset """
        storage = self.get_storage(storage_id)

        assert storage != None, f"The requested storage {storage_id} does not exist."

        return storage.has_dataset(dataset_id)


    def issue_data_staging(self, source, dest, dataset):
        """
        Creates a Batsim data_staging job to transfer an amount of bytes the size of the dataset
        from source Storage to dest Storage
        Preconditions: The Dataset is in source, source and dest Storages exist, dest has enough available space
        """
        # Register a new Profile
        profile_name = "staging" + str(self.next_staging_job_id)
        move_profile = {
            profile_name :
            {
                'type' : 'data_staging',
                'nb_bytes' : dataset.get_size(),
                'from' : "source",
                'to' : "dest"
            },
        }
        self.bs.register_profiles("dyn-storage-controller", move_profile)

        source_id = source.get_id()
        dest_id = dest.get_id()

        # Register a new Job
        job_id = "dyn-storage-controller!staging" + str(self.next_staging_job_id)
        new_job = self.bs.register_job(id=job_id, res=2, walltime=-1, profile_name=profile_name)
        self.next_staging_job_id += 1

        # Execute the Job
        new_job.allocation = ProcSet(source_id, dest_id)
        new_job.storage_mapping = {
            "source" : source_id,
            "dest" : dest_id
        }
        self.bs.execute_job(new_job)
        self.current_transfers[job_id] = DataTransfer(source_id, dest_id, dataset.get_id())

        self.logger.info(f"[ {self.bs.time()} ] Storage Controller staging job for dataset {dataset.get_id()} "
                         f"from {source_id} to {dest_id} started")


    def ask_data_transfer(self, dataset_id, source_id, dest_id):
        """
        Asks the Storage Controller to transfer a dataset from source to dest Storages.
        If not enough space in destination, free space is made by deleting datasets with the clearing strategy (default is LRU)
        Returns True if the dataset is already present on dest or is currently being transferred to dest
        Returns False if dataset is not in source, if source or dest Storages do not exist,
        or dest does not have enough available space after clearing (this can happen due to tags on datasets in the destination Storage)
        An assertion fails if the dataset does not fit in the whole destination Storage
        """
        self.logger.debug(f"StorageController: Request for dataset {dataset_id} to transfer from {source_id} to {dest_id}")

        source = self.get_storage(source_id)
        dest = self.get_storage(dest_id)
        dataset = source.get_dataset_from_id(dataset_id)

        # First check if destination exists
        if not self.has_storage(dest_id):
            #entry['status'] = 'null_dest'
            #self.traces = self.traces.append(entry, ignore_index=True)
            self.logger.info("StorageController: Destination storage with id {} not found".format(dest_id))
            return False

        # Now check if destination already has the dataset requested
        if dest.has_dataset(dataset_id):
            #entry['status'] = 'data_present_dest'
            #self.traces = self.traces.append(entry, ignore_index=True)
            self.logger.debug("StorageController: Dataset with id {} already present in destination with id {}.".format(dataset_id, dest_id))
            self.nb_transfers_zero+=1
            return True


        # Check if the source exists
        if not self.has_storage(source_id):
            #entry['status'] = 'null_source'
            #self.traces = self.traces.append(entry, ignore_index=True)
            self.logger.info("StorageController: Source storage with id {} not found".format(source_id))
            return False

        # Now check if the source has the dataset requested
        if not source.has_dataset(dataset_id):
            #entry['status'] = 'data_absent_source'
            #self.traces = self.traces.append(entry, ignore_index=True)
            self.logger.info("StorageController: Source with id {} does not have dataset with id {}.".format(source_id, dataset_id))
            return False

        dataset_size = dataset.get_size()

        # Now we check if the destination has enough storage
        assert (dest.get_storage_capacity() >= dataset_size), f"StorageController : Dataset {dataset_id} does not fit into Storage {dest.get_name()} ({dest_id})"

        if not dest.has_enough_free_space(dataset_size):
            #entry['status'] = 'insufficient_space'
            if not self.make_space_in_storage(dest, dataset_size):
                # Not enough space could be made, cannot transfer the dataset
                return False

        dest.reserved_space += dataset_size
        self.nb_transfers_real += 1
        if source_id == self.main_storage_id:
            self.total_transferred_from_main += dataset_size

        self.issue_data_staging(source, dest, dataset)
        return True


    def make_space_in_storage(self, storage, asked_space):
        """  Asks the storage to evict datasets until
        it has enough space to store the given dataset
        Returns True if enough space was freed for the dataset
        Returns False otherwise
        """
        return storage.make_space(asked_space)



    def data_staging_completed(self, job):
        """ This function is automatically called during event handling,
        when a JOB_COMPLETED event is received with the "dyn-storage-controller" workload
        """
        data_transfer = self.current_transfers.pop(job.id)
        dataset = self.get_storage(data_transfer.source_id).get_dataset_from_id(data_transfer.dataset_id)
        dest = self.get_storage(data_transfer.dest_id)
        dest.reserved_space -= dataset.get_size()

        if job.job_state == Job.State.COMPLETED_SUCCESSFULLY:
            self.add_dataset_to_storage(data_transfer.dest_id, dataset, job.finish_time)
            self.scheduler.onDatasetArrivedOnStorage(*data_transfer)
        else:
            # The data_staging job was either killed or it failled
            self.scheduler.onDataTransferNotTerminated(*data_transfer)


    def stop_all_data_transfers(self):
        """ Kills all ongoing data transfers """
        to_kill = [self.bs.jobs[x] for x in self.current_transfers.keys()]
        self.logger.info(f"[{self.bs.time()}] StorageController stopping {len(to_kill)} data transfers")
        if len(to_kill) > 0:
            self.bs.kill_jobs(to_kill)
