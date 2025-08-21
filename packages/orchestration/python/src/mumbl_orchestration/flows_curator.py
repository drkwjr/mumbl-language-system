from prefect import flow, task
from mumbl_orchestration.batch_types import BatchManifest

@task
def score_and_dedupe(man: BatchManifest) -> BatchManifest:
    # TODO: scoring and dedupe; produce curated manifest.jsonl for TTS builder
    man.outputs["curated_manifest"] = f"s3://stub/{man.batch_id}/tts/manifest.jsonl"
    return man

@task
def snapshot_and_register(man: BatchManifest) -> BatchManifest:
    # TODO: write dataset snapshot and register it
    man.outputs["dataset_dir"] = f"s3://stub/{man.batch_id}/tts/"
    return man

@flow(name="curator")
def curator_flow(manifest: dict) -> dict:
    man = BatchManifest(**manifest)
    man = score_and_dedupe.submit(man).result()
    man = snapshot_and_register.submit(man).result()
    man.status = "succeeded"
    return man.dict()
