import json
import logging
from typing import Any, Dict, List, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from config import azure_config

logger = logging.getLogger(__name__)

class CosmosDBService:
    """Azure CosmosDB service for storing problems and patterns"""

    def __init__(self):
        if not azure_config.cosmos_endpoint or not azure_config.cosmos_key:
            logger.warning("CosmosDB credentials not configured, using local storage")
            self.client = None
            return

        try:
            self.client = CosmosClient(
                azure_config.cosmos_endpoint,
                azure_config.cosmos_key
            )
            self.database = self.client.create_database_if_not_exists(
                azure_config.cosmos_database
            )
            logger.info(f"Connected to CosmosDB database: {azure_config.cosmos_database}")
        except Exception as e:
            logger.error(f"Failed to connect to CosmosDB: {e}")
            self.client = None

    def _get_container(self, container_name: str):
        """Get or create a container"""
        if not self.client:
            return None

        try:
            container = self.database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400
            )
            return container
        except Exception as e:
            logger.error(f"Failed to get container {container_name}: {e}")
            return None

    def save_problem(self, problem: Dict[str, Any]) -> bool:
        """Save a problem to CosmosDB"""
        if not self.client:
            logger.warning("CosmosDB not available, skipping problem save")
            return False

        container = self._get_container("problems")
        if not container:
            return False

        try:
            container.upsert_item(problem)
            logger.info(f"Saved problem: {problem.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to save problem: {e}")
            return False

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """Get a problem by ID"""
        if not self.client:
            return None

        container = self._get_container("problems")
        if not container:
            return None

        try:
            return container.read_item(item=problem_id, partition_key=problem_id)
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get problem {problem_id}: {e}")
            return None

    def get_all_problems(self) -> List[Dict[str, Any]]:
        """Get all problems"""
        if not self.client:
            return []

        container = self._get_container("problems")
        if not container:
            return []

        try:
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            return items
        except Exception as e:
            logger.error(f"Failed to get all problems: {e}")
            return []

    def save_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Save a pattern to CosmosDB"""
        if not self.client:
            logger.warning("CosmosDB not available, skipping pattern save")
            return False

        container = self._get_container("patterns")
        if not container:
            return False

        try:
            container.upsert_item(pattern)
            logger.info(f"Saved pattern: {pattern.get('name', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")
            return False

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """Get all patterns"""
        if not self.client:
            return []

        container = self._get_container("patterns")
        if not container:
            return []

        try:
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            return items
        except Exception as e:
            logger.error(f"Failed to get all patterns: {e}")
            return []


class BlobStorageService:
    """Azure Blob Storage service for storing tutorials and solutions"""

    def __init__(self):
        if not azure_config.storage_account or not azure_config.storage_key:
            logger.warning("Blob Storage credentials not configured, using local storage")
            self.client = None
            return

        try:
            account_url = f"https://{azure_config.storage_account}.blob.core.windows.net"
            self.client = BlobServiceClient(
                account_url=account_url,
                credential=azure_config.storage_key
            )

            # Create container if it doesn't exist
            try:
                self.client.create_container(azure_config.storage_container)
                logger.info(f"Created blob container: {azure_config.storage_container}")
            except ResourceExistsError:
                pass
            except Exception as e:
                logger.error(f"Failed to create container: {e}")

            logger.info(f"Connected to Blob Storage container: {azure_config.storage_container}")
        except Exception as e:
            logger.error(f"Failed to connect to Blob Storage: {e}")
            self.client = None

    def save_tutorial(self, pattern_name: str, tutorial_content: str) -> Optional[str]:
        """Save a tutorial to blob storage"""
        if not self.client:
            logger.warning("Blob Storage not available, skipping tutorial save")
            return None

        try:
            blob_name = f"tutorials/{pattern_name.lower().replace(' ', '_')}.md"
            blob_client = self.client.get_blob_client(
                container=azure_config.storage_container,
                blob=blob_name
            )

            blob_client.upload_blob(tutorial_content, overwrite=True)
            logger.info(f"Saved tutorial: {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Failed to save tutorial {pattern_name}: {e}")
            return None

    def get_tutorial(self, pattern_name: str) -> Optional[str]:
        """Get a tutorial from blob storage"""
        if not self.client:
            return None

        try:
            blob_name = f"tutorials/{pattern_name.lower().replace(' ', '_')}.md"
            blob_client = self.client.get_blob_client(
                container=azure_config.storage_container,
                blob=blob_name
            )

            download_stream = blob_client.download_blob()
            return download_stream.readall().decode('utf-8')
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get tutorial {pattern_name}: {e}")
            return None

    def save_solution(self, problem_id: str, solution_content: str) -> Optional[str]:
        """Save a solution to blob storage"""
        if not self.client:
            logger.warning("Blob Storage not available, skipping solution save")
            return None

        try:
            blob_name = f"solutions/{problem_id}.md"
            blob_client = self.client.get_blob_client(
                container=azure_config.storage_container,
                blob=blob_name
            )

            blob_client.upload_blob(solution_content, overwrite=True)
            logger.info(f"Saved solution: {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Failed to save solution {problem_id}: {e}")
            return None

    def get_solution(self, problem_id: str) -> Optional[str]:
        """Get a solution from blob storage"""
        if not self.client:
            return None

        try:
            blob_name = f"solutions/{problem_id}.md"
            blob_client = self.client.get_blob_client(
                container=azure_config.storage_container,
                blob=blob_name
            )

            download_stream = blob_client.download_blob()
            return download_stream.readall().decode('utf-8')
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get solution {problem_id}: {e}")
            return None


# Global service instances
cosmos_service = CosmosDBService()
blob_service = BlobStorageService()
