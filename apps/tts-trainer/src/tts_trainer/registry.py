"""
Model registry integration.
"""

from typing import Any, Dict, Optional

from mumbl_storage.db import get_connection
from mumbl_storage.repositories import ModelRegistryRepository


class ModelRegistry:
    """
    Register trained models in database.
    """

    def __init__(self):
        """Initialize registry."""
        pass

    def register_model(
        self,
        model_path: str,
        language: str,
        dialect: Optional[str],
        model_name: str,
        version: str,
        training_dataset_id: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        artifact_uri: Optional[str] = None,
        status: str = "dev",
    ) -> int:
        """
        Register a trained model in the database.

        Args:
            model_path: Path to model file
            language: Language code
            dialect: Dialect code (optional)
            model_name: Name of the model
            version: Semantic version
            training_dataset_id: ID of training dataset
            metrics: Evaluation metrics dict
            training_config: Training configuration dict
            artifact_uri: URI to model artifact (S3 path, etc.)
            status: Model status ("dev", "staging", "prod")

        Returns:
            Model registry ID
        """
        with get_connection() as conn:
            registry_repo = ModelRegistryRepository(conn)

            registry_id = registry_repo.register(
                kind="tts",
                language=language,
                dialect=dialect,
                model_name=model_name,
                version=version,
                training_dataset_id=training_dataset_id,
                metrics=metrics,
                training_config=training_config,
                artifact_uri=artifact_uri or model_path,
                status=status,
            )

            return registry_id
