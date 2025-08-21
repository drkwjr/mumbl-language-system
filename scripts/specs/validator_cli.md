# Spec — profile-validate CLI

Command:
```bash
python -m mumbl_data_contracts.tools.profile_validate --path PATH/TO/profile.json
```

Behavior:
- Load JSON.
- Validate against pydantic model.
- Print errors with JSON Pointer paths.
- Exit code 0 on success, 1 on failure.

Extensions:
- `--resolve` to apply inheritance Dialect → Language → Group when parents are provided.
