#  Copyright 2021 The QUARK Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import annotations
from abc import abstractmethod
from typing import Protocol, Any, runtime_checkable

class Core(Protocol):
    """
    Core Module for QUARK, used by all other Modules that are part of a benchmark process.
    """

    @abstractmethod
    def preprocess(self, data: Any) -> Any:
        """
        Essential method for the benchmarking process. This is always executed before traversing down
        to the next module, passing the data returned by this function.

        :param data: Data for the module, comes from the parent module if that exists
        :return: The processed data
        """
        raise NotImplementedError()

    @abstractmethod
    def postprocess(self, data: Any) -> Any:
        """
        Essential Method for the benchmarking process. Is always executed after the submodule is finished. The data by
        this method is passed up to the parent module.

        :param data: Input data comes from the submodule if that exists
        :return: The processed data
        """
        raise NotImplementedError()


@runtime_checkable
class Visualizable(Protocol):

    @abstractmethod
    def visualize(self, path:str) -> None:
        """
        Visualizes result.
        """
        raise NotImplementedError()
