#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pandas as pd

# Defining the class only if Mephisto is installed, since it relies on Mephisto
try:
    from mephisto.abstractions.databases.local_database import LocalMephistoDB
    from mephisto.data_model.unit import Unit
    from mephisto.tools.data_browser import DataBrowser as MephistoDataBrowser
except ImportError:
    pass


class AbstractResultsCompiler(ABC):
    """
    Abstract class for compiling results of crowdsourcing runs.

    Currently only provides utility attributes/methods for analyzing turn annotations.
    """

    @classmethod
    def setup_args(cls):
        parser = argparse.ArgumentParser('Compile crowdsourcing results')
        parser.add_argument(
            '--output-folder', type=str, help='Folder to save output files to'
        )
        return parser

    def __init__(self, opt: Dict[str, Any]):
        self.output_folder = opt.get('output_folder')

    @abstractmethod
    def compile_results(self) -> pd.DataFrame:
        """
        Method for returning the final results dataframe.

        Each row of the dataframe consists of one utterance of one conversation.
        """


class AbstractTurnAnnotationResultsCompiler(AbstractResultsCompiler):
    """
    Results compiler subclass to provide utility code for turn annotations.

    Currently incompatible with Mephisto's DataBrowser: all subclasses load results
    files directly from disk.
    TODO: make all subclasses compatible with DataBrowser
    """

    @classmethod
    def setup_args(cls):
        parser = super().setup_args()
        parser.add_argument(
            '--results-folders', type=str, help='Comma-separated list of result folders'
        )
        parser.add_argument(
            '--problem-buckets',
            type=str,
            help='Comma-separated list of buckets used for annotation',
            default='bucket_0,bucket_1,bucket_2,bucket_3,bucket_4,none_all_good',
        )
        return parser

    def __init__(self, opt: Dict[str, Any]):

        super().__init__(opt)

        # Handle inputs
        if 'results_folders' in opt:
            self.results_folders = opt['results_folders'].split(',')
        else:
            self.results_folders = None
        self.problem_buckets = opt['problem_buckets'].split(',')

        # Validate problem buckets
        if 'none_all_good' not in self.problem_buckets:
            # The code relies on a catchall "none" category if the user selects no other
            # annotation bucket
            raise ValueError(
                'There must be a "none_all_good" category in self.problem_buckets!'
            )


class AbstractDataBrowserResultsCompiler(AbstractResultsCompiler):
    """
    Provides interface for using Mephisto's DataBrowser, DB, and their methods.

    Uses Mephisto's DataBrowser to retrieve the work units and their data.
    """

    @classmethod
    def setup_args(cls):
        parser = super().setup_args()
        parser.add_argument(
            '--task-name', type=str, help='Name of the Mephisto task to open'
        )
        return parser

    def __init__(self, opt):
        self.task_name = opt["task_name"]
        self._mephisto_db = None
        self._mephisto_data_browser = None

    def get_mephisto_data_browser(self) -> MephistoDataBrowser:
        if not self._mephisto_data_browser:
            db = self.get_mephisto_db()
            self._mephisto_data_browser = MephistoDataBrowser(db=db)
        return self._mephisto_data_browser

    def get_mephisto_db(self) -> LocalMephistoDB:
        if not self._mephisto_db:
            self._mephisto_db = LocalMephistoDB()
        return self._mephisto_db

    def get_worker_name(self, worker_id: str) -> str:
        """
        Gets the global (AWS) id of a worker from their Mephisto worker_id.
        """
        db = self.get_mephisto_db()
        return db.get_worker(worker_id)["worker_name"]

    def get_task_units(self, task_name: str) -> List[Unit]:
        """
        Retrieves the list of work units from the Mephisto task.
        """
        data_browser = self.get_mephisto_data_browser()
        return data_browser.get_units_for_task_name(task_name)

    def get_units_data(self, task_units: List[Unit]) -> List[dict]:
        """
        Retrieves task data for a list of Mephisto task units.
        """
        data_browser = self.get_mephisto_data_browser()
        task_data = []
        for unit in task_units:
            task_data.append(data_browser.get_data_from_unit(unit))
        return task_data
