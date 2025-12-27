"""
TTS Training Prefect flow.
"""

from prefect import flow, task
from mumbl_orchestration.batch_types import BatchManifest
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import DatasetRepository

# Import TTS trainer modules - package should be installed
try:
    from tts_trainer.config import TrainingConfig
    from tts_trainer.trainer import TTSTrainer
    from tts_trainer.evaluator import ModelEvaluator
    from tts_trainer.registry import ModelRegistry
except ImportError as e:
    raise ImportError(
        f"Could not import tts_trainer. Install with: pip install -e apps/tts-trainer"
    ) from e


@task
def load_dataset_task(man: BatchManifest) -> BatchManifest:
    """
    Load dataset for training.
    """
    dataset_id = man.outputs.get("dataset_id")
    if not dataset_id:
        raise ValueError("No dataset_id in manifest outputs. Run curator flow first.")
    
    # Load dataset info from database
    with get_connection() as conn:
        dataset_repo = DatasetRepository(conn)
        dataset = dataset_repo.get_by_id(dataset_id)
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Store dataset path in manifest
        manifest_path = dataset.get('artifact_uri', '').replace('.json', '.jsonl')
        man.outputs["manifest_path"] = manifest_path
        man.metrics["dataset_id"] = dataset_id
    
    return man


@task
def train_model_task(man: BatchManifest) -> BatchManifest:
    """
    Train TTS model (STUBBED).
    """
    manifest_path = man.outputs.get("manifest_path")
    if not manifest_path:
        raise ValueError("No manifest_path in manifest outputs")
    
    # Create training config
    config = TrainingConfig(
        dataset_path=manifest_path,
        language=man.language,
        dialect=man.dialect,
    )
    
    # Initialize trainer
    trainer = TTSTrainer(config)
    
    # Train model (STUBBED)
    training_result = trainer.train()
    
    # Store training results
    man.metrics["training_loss"] = training_result['loss']
    man.metrics["training_epochs"] = training_result['epoch']
    man.outputs["checkpoint_path"] = trainer.config.checkpoint_dir
    
    return man


@task
def evaluate_model_task(man: BatchManifest) -> BatchManifest:
    """
    Evaluate trained model (STUBBED).
    """
    checkpoint_path = man.outputs.get("checkpoint_path")
    if not checkpoint_path:
        raise ValueError("No checkpoint_path in manifest outputs")
    
    manifest_path = man.outputs.get("manifest_path")
    
    # Load test dataset
    from tts_trainer.dataset_loader import load_dataset
    test_dataset = load_dataset(manifest_path)[:10]  # Sample first 10 for testing
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Evaluate model (STUBBED)
    evaluation_result = evaluator.evaluate(
        model_path=checkpoint_path,
        test_dataset=test_dataset
    )
    
    # Store evaluation results
    man.metrics["mos_score"] = evaluation_result['mos_lite']['overall']
    man.metrics["pronunciation_accuracy"] = evaluation_result['pronunciation']['accuracy']
    man.metrics["stability_score"] = evaluation_result['stability']['stability_score']
    man.outputs["evaluation_metrics"] = evaluation_result
    
    return man


@task
def register_model_task(man: BatchManifest) -> BatchManifest:
    """
    Register trained model in database.
    """
    checkpoint_path = man.outputs.get("checkpoint_path")
    evaluation_metrics = man.outputs.get("evaluation_metrics", {})
    
    # Initialize registry
    registry = ModelRegistry()
    
    # Register model
    model_id = registry.register_model(
        model_path=checkpoint_path,
        language=man.language,
        dialect=man.dialect,
        model_name=f"{man.language}_{man.dialect}_tts",
        version="1.0.0",
        training_dataset_id=man.metrics.get("dataset_id"),
        metrics=evaluation_metrics,
        training_config={},
        status="dev",
    )
    
    man.outputs["model_id"] = model_id
    man.status = "succeeded"
    
    return man


@flow(name="tts-training")
def tts_training_flow(manifest: dict) -> dict:
    """
    TTS Training Prefect flow orchestrating dataset loading, training, evaluation, and registration.
    """
    man = BatchManifest(**manifest)
    
    # Load dataset
    man = load_dataset_task.submit(man).result()
    
    # Train model
    man = train_model_task.submit(man).result()
    
    # Evaluate model
    man = evaluate_model_task.submit(man).result()
    
    # Register model
    man = register_model_task.submit(man).result()
    
    return man.dict()

