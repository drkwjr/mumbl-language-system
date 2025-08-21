from prefect import flow, task
from mumbl_orchestration.batch_types import BatchManifest

@task
def preflight(man: BatchManifest) -> BatchManifest:
    man.metrics["hours_estimated"] = 0.5  # TODO real probe
    return man

@task
def asr_diar_align_normalize(man: BatchManifest) -> BatchManifest:
    # TODO wire providers and emit CSV + clips
    man.outputs["csv"] = f"s3://stub/{man.batch_id}/paired_speech_corpus.csv"
    man.outputs["clips_dir"] = f"s3://stub/{man.batch_id}/clips/"
    man.metrics["clips"] = 300.0
    return man

@task
def validate_audio_outputs(man: BatchManifest) -> BatchManifest:
    # TODO call validate-audio-dataset
    return man

@flow(name="audio-lane")
def audio_lane_flow(manifest: dict) -> dict:
    man = BatchManifest(**manifest)
    man = preflight.submit(man).result()
    man = asr_diar_align_normalize.submit(man).result()
    man = validate_audio_outputs.submit(man).result()
    man.status = "succeeded"
    return man.dict()
