from prefect import flow, task
from mumbl_orchestration.batch_types import BatchManifest

@task
def chunk_and_label(man: BatchManifest) -> BatchManifest:
    # TODO integrate LangExtract
    man.outputs["jsonl"] = f"s3://stub/{man.batch_id}/text_dialogue_corpus.jsonl"
    man.outputs["html_report"] = f"s3://stub/{man.batch_id}/spotcheck/index.html"
    man.metrics["segments"] = 100.0
    return man

@task
def validate_outputs(man: BatchManifest) -> BatchManifest:
    # TODO call validate-text-jsonl
    return man

@flow(name="text-lane")
def text_lane_flow(manifest: dict) -> dict:
    man = BatchManifest(**manifest)
    man = chunk_and_label.submit(man).result()
    man = validate_outputs.submit(man).result()
    man.status = "succeeded"
    return man.dict()
