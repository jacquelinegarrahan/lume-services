from typing import List
from sqlalchemy import insert, select, desc
import logging

from lume_services.services.models.db import ModelDB
from lume_services.services.models.db.schema import (
    Base,
    DependencyType,
    DeploymentDependency,
    Model,
    Deployment,
    Flow,
    Project,
    FlowOfFlows,
)

from lume_services.services.models.utils import validate_kwargs_exist
from lume_services.errors import (
    FlowNotFoundError,
    ModelNotFoundError,
    DeploymentNotFoundError,
    ProjectNotFoundError,
    FlowOfFlowsNotFoundError,
)


logger = logging.getLogger(__name__)


class ModelDBService:
    def __init__(self, model_db: ModelDB):
        self._model_db = model_db
        self._model_registry = {}

    @validate_kwargs_exist(Model)
    def store_model(
        self,
        author: str,
        laboratory: str,
        facility: str,
        beampath: str,
        description: str,
    ) -> int:
        """Store a model.

        Returns:
            int: ID of inserted model
        """

        # store in db
        insert_stmt = insert(Model).values(
            author=author,
            laboratory=laboratory,
            facility=facility,
            beampath=beampath,
            description=description,
        )

        result = self._model_db.insert(insert_stmt)

        if len(result):
            return result[0]

        else:
            return None

    def store_deployment(
        self,
        model_id: int,
        version: str,
        source: str,
        sha256: str,
        image: str,
        is_live: bool = False,
        asset_dir=None,
    ) -> int:
        """Store a deployment.

        Args:
            model_id (int): Associated model id.
            version (str): Version of model.
            source (str): Source of deployment code.
            sha256 (str): Hash of source
            image (str): Container image to be used with this deployment.
            is_live (bool=False): Whether deployment is live.
            asset_dir (str): Directory for assets stored on filesystem.

        Returns:
            int: ID of inserted deployment id
        """

        # store in db
        insert_stmt = insert(Deployment).values(
            model_id=model_id,
            version=version,
            source=source,
            sha256=sha256,
            image=image,
            is_live=is_live,
            asset_dir=asset_dir,
        )

        result = self._model_db.insert(insert_stmt)

        if len(result):
            return result[0]

        else:
            return None

    def store_project(self, project_name: str, description: str) -> str:
        """Store a project.

        Args:
            project_name (str): Name of project (as created in Prefect).
            decription (str): Short description of project.

        Returns:
            str: Inserted project name
        """

        insert_stmt = insert(Project).values(
            project_name=project_name, description=description
        )

        # store in db
        result = self._model_db.insert(insert_stmt)

        # Return inserted project name
        if len(result):
            return result[0]

        else:
            return None

    def store_flow(
        self, deployment_id: int, flow_id: str, flow_name: str, project_name: str
    ) -> str:
        """Store a flow in the model database.

        Args:
            deployment_id (int): ID of deployment associated with the flow.
            flow_id (str): ID of flow (generated by Prefect).
            flow_name (str): Name of flow (same as used to register with Prefect).
            project_name (str): Name of project (same as used to register with Prefect).

        Returns:
            str: Inserted flow id
        """

        insert_stmt = insert(Flow).values(
            flow_id=flow_id,
            deployment_id=deployment_id,
            flow_name=flow_name,
            project_name=project_name,
        )

        results = self._model_db.insert(insert_stmt)

        # flow_id is result of first insert
        if len(results):
            return results[0]

        else:
            return None

    @validate_kwargs_exist(Model)
    def get_model(self, **kwargs) -> Model:
        """Get a model from criteria

        Returns:
            Model
        """
        # execute query
        query = select(Model).filter_by(**kwargs)

        result = self._model_db.select(query)

        if len(result):
            if len(result) > 1:
                # formatted this way to eventually move towards interpolated schema
                logger.warning(
                    "Multiple models returned from query. get_model is returning the \
                        first result with %s %s",
                    "model_id",
                    result[0].model_id,
                )

            return result[0]

        else:
            raise ModelNotFoundError(query)

    @validate_kwargs_exist(Deployment)
    def get_deployment(self, **kwargs) -> Deployment:
        """Get a deployment based on criteria

        Returns:
            Deployment
        """

        query = select(Deployment).filter_by(**kwargs)
        result = self._model_db.select(query)

        if len(result):
            if len(result) > 1:
                # formatted this way to eventually move towards interpolated schema
                logger.warning(
                    "Multiple deployments returned from query. get_deployment is \
                        returning the first result with %s %s",
                    "deployment_id",
                    result[0].deployment_id,
                )

            return result[0]

        else:
            raise DeploymentNotFoundError(query)

    @validate_kwargs_exist(Deployment)
    def get_latest_deployment(self, **kwargs) -> Deployment:
        """Get the latest deployment

        Returns:
            Deployment

        raises:
            ValueError: Passed kwarg not in Project schema
        """

        query = (
            select(Deployment)
            .filter_by(**kwargs)
            .order_by(desc(Deployment.deploy_date))
        )
        result = self._model_db.select(query)

        if len(result):
            return result[0]

        else:
            raise DeploymentNotFoundError(query)

    @validate_kwargs_exist(Project)
    def get_project(self, **kwargs) -> Project:
        """Get a single Project

        Returns:
            Project

        raises:
            ValueError: Passed kwarg not in Project schema
        """

        # execute query
        query = select(Project).filter_by(**kwargs)
        result = self._model_db.select(query)

        if len(result):
            if len(result) > 1:
                # formatted this way to eventually move towards interpolated schema
                logger.warning(
                    "Multiple projects returned from query. get_project is returning \
                        the first result with %s %s",
                    "name",
                    result[0].project_name,
                )

            return result[0]

        else:
            raise ProjectNotFoundError(query)

    @validate_kwargs_exist(Flow)
    def get_flow(self, **kwargs) -> Flow:
        """Get a flow from criteria

        Returns:
            Flow: Select a flow from the database.

        raises:
            ValueError: Passed kwarg not in Project schema
        """

        query = select(Flow).filter_by(**kwargs)
        result = self._model_db.select(query)

        if len(result):
            if len(result) > 1:
                # formatted this way to eventually move towards interpolated schema
                logger.warning(
                    "Multiple flows returned from query. get_flow is returning the \
                        first result with %s %s",
                    "flow_id",
                    result[0].flow_id,
                )

            return result[0]

        else:
            raise FlowNotFoundError(query)

    @validate_kwargs_exist(FlowOfFlows)
    def get_flow_of_flows(self, **kwargs) -> Flow:
        """Get a flow from criteria

        Returns:
            FlowOfFlows: Select a flow of flows from the database.

        raises:
            ValueError: Passed kwarg not in Project schema
        """

        query = select(FlowOfFlows).filter_by(**kwargs)
        result = self._model_db.select(query)

        if len(result):
            return [res.flow for res in result]

        else:
            raise FlowOfFlowsNotFoundError(query)

    def apply_schema(self) -> None:
        """Applies database schema to connected service."""

        Base.metadata.create_all(self._model_db.engine)

    def get_dependencies(self, deployment_id: int) -> DeploymentDependency:
        """Get the dependencies for a deployment. Performs joined load of
        DeploymentType.

        Args:
            deployment_id (int): Id of deployment for which to fetch dependencies.

        Returns:
            DeploymentDependency

        Raises:
            DeploymentNotFoundError: Deployment was not found.

        """
        from sqlalchemy.orm import joinedload

        query = (
            select(DeploymentDependency)
            .filter_by(deployment_id=deployment_id)
            .options(joinedload(DeploymentDependency.dependency_type))
        )

        deps = self._model_db.select(query)
        if len(deps):
            return deps

        else:
            raise DeploymentNotFoundError(query)

    def store_dependencies(self, dependencies: List[dict], deployment_id: int):
        """Store dependencies for a deployment.

        Args:
            dependencies (List[dict]): List of dependencies in the form:
                {"name": ..., "type": ..., "source": ..., "local_source": ... ,
                "version": ...}
            deployment_id (int): Id of deployment for which to store dependencies.

        """

        stmts = []

        for dep in dependencies:
            type_stmt = (
                select(DependencyType.id).filter_by(type=dep["type"]).as_scalar()
            )

            insert_stmt = insert(DeploymentDependency).values(
                deployment_id=deployment_id,
                name=dep["name"],
                source=dep["source"],
                local_source=dep.get("local_source"),
                version=dep["version"],
                dependency_type_id=type_stmt,
            )
            stmts.append(insert_stmt)

        result = self._model_db.insert_many(stmts)

        # return inserted ids
        if len(result):
            return result

        else:
            return None
