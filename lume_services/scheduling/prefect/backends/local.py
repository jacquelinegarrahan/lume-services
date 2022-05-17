from pydantic import BaseModel
from prefect.run_configs import LocalRun
from typing import Optional, Dict
import logging

from lume_services.data.file import FileService
from lume_services.context import Context
from dependency_injector.wiring import Provide

from lume_services.scheduling.prefect.backends import Backend


logger = logging.getLogger(__name__)


class LocalRunConfig(BaseModel):
    env: Dict[str, str]
    working_dir: Optional[str]


#    labels: Optional[List[str]]


class LocalBackend(Backend):
    def get_run(
        self,
        run_config: LocalRunConfig,
        file_service: FileService = Provide[Context.file_service],
    ):
        # check working directory exists in file service
        if not file_service.dir_exists("local", self.working_dir):
            raise FileNotFoundError(f"Directory {self.working_dir} does not exist.")

        return LocalRun(
            env=run_config.env,
            working_dir=run_config.working_dir,
            # labels = run_config.labels
        )
