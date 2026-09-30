# Shared hosting and hosted-validation runbook

Use this runbook whenever a Vachan task needs shared cloud infrastructure, deployment, hosted verification, or an externally accessible environment. It is a reusable team procedure, not specific to any particular task. Hosted validation is normally `DEFERRED` while local feature work can continue; change it to `BLOCKED` only when a task genuinely cannot proceed without the hosted result.

The current deferred entries are T1's external hosted skeleton check and T2's Firestore persistence-across-restart check. Their task-specific procedures appear below as examples and should be followed when the team chooses to validate them.

## Security and team-safety rules

This is a shared repository and a shared cloud environment. Treat deployment access as team infrastructure, not as project source code.

- **Never commit credentials.** Do not add service-account keys, Firebase tokens, API keys, application-default-credential files, `.env` files, emulator exports, browser session data, or generated deployment logs to Git.
- The repository already ignores `.env*`, credential JSON, Firebase state, and logs. Before every commit, run `git status --short` and inspect staged changes with `git diff --cached`. If a credential-like file appears, unstage it and remove it from the working tree; do not try to redact and commit it.
- Use the team-approved shared identity: an existing authenticated `gcloud`/Firebase session, Workload Identity, or the Cloud Build service account. **Do not** create or download a long-lived service-account key solely for this deployment.
- GCP/Firebase project IDs, regions, service names, bucket names, and public URLs are not credentials, but they are shared-environment configuration. Change tracked deployment configuration only in a reviewed commit/PR after coordinating with the team; do not overwrite someone else's active settings.
- Keep secret runtime values in Secret Manager or Cloud Run environment/secret configuration, never in `cloudbuild.yaml`, `firebase.json`, committed source, or `VITE_*` variables. `VITE_*` values are public in the browser bundle.
- Use an isolated local file (for example, the ignored `backend/.env`) for temporary local configuration. Copy from the committed `.env.example`; never edit the example to include real values.

## Before starting

1. Coordinate in the team channel: name the shared GCP project, Firebase project, region, Cloud Run service name, deployment owner, and intended time window. Confirm no one else is changing the deployment files or running a release.

2. Start from a clean, current branch and record the commit SHA to be deployed:

   ```sh
   git status --short
   git rev-parse --short HEAD
   git diff --cached
   ```

3. Confirm the shared identity without printing secrets:

   ```sh
   gcloud auth list
   gcloud config get-value project
   ```

   The active identity must have only the roles agreed by the team. Use the existing team deployment identity where possible rather than personal credentials.

4. Export only non-secret shell values for the current terminal. Do not put these in a committed file:

   ```sh
   export VACHAN_PROJECT_ID="shared-project-id"
   export VACHAN_REGION="asia-south1"
   export VACHAN_API_SERVICE="vachan-api"
   export VACHAN_BUCKET="shared-vachan-vault"
   ```

5. Run the local safety checks that should already be green:

   ```sh
   cd backend
   ./.venv/bin/python -m pytest -q
   ./.venv/bin/python -m manifest_schema.linter fixtures/p0_single_beat.json --strict
   ```

   In a second terminal, build the frontend using the repository's supported Node version.

## Reusable procedure for any hosted task

For every new hosted requirement, create or update its task entry in `PLAN_TRACKER.md` and follow this sequence:

1. **Define the hosted acceptance criterion.** State the externally observable result, the required environment (emulator, staging, or shared production-like project), and the non-secret evidence that proves success.
2. **Coordinate the shared change.** Record the deployment owner, target environment, commit SHA, time window, and rollback owner before modifying shared resources.
3. **Validate locally first.** Run the relevant tests, linter, and frontend build before deploying. Do not use the hosted environment as the first integration test.
4. **Configure without secrets.** Put secrets in the approved secret store or runtime configuration; use reviewed, non-secret deployment configuration only.
5. **Deploy through the approved path.** Prefer the shared CI/CD trigger and managed identity. Record build/deployment IDs and public URLs, not credentials.
6. **Prove the criterion independently.** Use a second device/network or a fresh process where that is part of the claim. Capture only non-sensitive evidence in the tracker.
7. **Close or defer honestly.** Mark the task `DONE` only when its hosted evidence exists. Otherwise leave it `DEFERRED` with a link to this runbook and the exact remaining proof. Use `BLOCKED` only if the absence of hosting stops required work.

### Add a future hosted-validation entry

Add a row to the **Hosted validation register** in `PLAN_TRACKER.md` with: task ID, status, target environment, owner, remaining proof, and a link to any task-specific section added to this runbook. Use the same structure as the current T1/T2 examples below.

## Current deferred validation — T1 hosted walking skeleton

### 1. Provision shared infrastructure

The deployment owner should confirm—not create ad hoc duplicates of—the following shared resources:

1. A billing-enabled GCP project and linked Firebase project.
2. Enabled APIs: Cloud Run, Cloud Build, Artifact Registry, Cloud Storage, and Firebase Hosting.
3. An Artifact Registry Docker repository named `vachan` in the agreed region.
4. The shared GCS bucket used by `GCS_BUCKET`.
5. Least-privilege access for the Cloud Run runtime service account to read/write the bucket, and for the Cloud Build identity to build/deploy.

Do not paste IAM bindings, tokens, or service-account JSON into issues, chat, Git history, or this repository.

### 2. Configure the deployment without secrets

1. Agree with the team whether the non-secret shared project ID belongs in tracked deployment files. If yes, submit it as a small reviewed change; otherwise configure it in the Cloud Build trigger/substitutions and Firebase project settings.

2. Resolve the current placeholders in the approved deployment path:

   - `frontend/.firebaserc` needs the shared Firebase project ID.
   - `cloudrun-service.yaml` needs the agreed project, region, and image location when it is used directly.
   - The Cloud Build trigger needs `_PROJECT_ID`, `_REGION`, and `_API_SERVICE`.

3. Do not add `GEMINI_API_KEY`, Firebase CLI tokens, or service-account credentials to these files. The frontend API URL is public configuration and may be injected at build time as `VITE_API_BASE_URL`.

### 3. Deploy through the agreed team path

Prefer the configured Cloud Build trigger. If the team uses a manual invocation, make the substitutions explicit and avoid storing them in files:

```sh
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_PROJECT_ID="$VACHAN_PROJECT_ID",_REGION="$VACHAN_REGION",_API_SERVICE="$VACHAN_API_SERVICE"
```

Wait for the build to finish. Record the build ID, deployed Cloud Run URL, Firebase Hosting URL, commit SHA, and time in the tracker—but never copy credentials or full environment dumps.

### 4. Validate the actual T1 criteria

From a different device or network (not only the deployer's machine):

1. Open the Firebase Hosting URL. Confirm the single-beat player loads and the English/Hindi text swap changes only the layer, not the plate.
2. Confirm browser developer tools show the frontend can call the Cloud Run API without a CORS failure.
3. Upload the Vega fixture to `POST /v1/sources/upload`; confirm a `source_id` is returned.
4. Using approved cloud-console access, confirm the corresponding raw source object exists in the shared GCS bucket. Do not download it into a credential-bearing directory or commit it.
5. Have the second tester report success from their own device/network.

Record the URLs, build ID, external-device tester, and result under T1 in `PLAN_TRACKER.md`. Once all three P0 exit criteria are evidenced, set T1 to `DONE`.

## Current deferred validation — T2 Firestore persistence across restart

T2's remaining proof is persistence, not extraction quality. The existing in-memory tests cover Gate 1 behavior within one process, but cannot prove a process restart.

### 1. Choose the test environment

Use one of these team-approved options:

- **Firestore emulator:** preferred for a repeatable local/CI integration test. It uses no production credentials, but its host/port configuration stays in an ignored local environment file.
- **Shared Firestore project:** use only when the team is ready to test the hosted application. Confirm the database and runtime service account already exist; do not create personal service-account key files.

### 2. Configure the API

For an emulator, set only in your ignored local environment/session:

```sh
GOOGLE_CLOUD_PROJECT="$VACHAN_PROJECT_ID"
FIRESTORE_EMULATOR_HOST="localhost:8088"
```

For shared Firestore, set `GOOGLE_CLOUD_PROJECT` through the approved Cloud Run configuration. Authenticate using the shared identity/Workload Identity or Cloud Run's service account—never an exported key file.

### 3. Execute the persistence proof

1. Start a fresh API process connected to Firestore.
2. Ingest the Vega fixture and run `POST /v1/brain/build`.
3. Send `POST /v1/gates/{run_id}/ground` with a deliberate edit to a fact's `text` or `value`.
4. Save the `source_id`, `run_id`, edited `fact_id`, and expected edited value in the test notes.
5. Stop that API process/container completely.
6. Start a new API process/container with the same Firestore configuration.
7. Call `GET /v1/brain/{source_id}` and verify the exact edited value, fact ID, span ID, and Gate 1 completion status remain.
8. Confirm the API has not silently fallen back to `_MemoryStore` (the cross-process data read is the practical proof; Cloud Run/API logs should also report the Firestore backend).

### 4. Make the proof repeatable

Add or enable an emulator-backed integration test for the sequence above if the team permits emulator infrastructure in CI. It should start a fresh application/store instance after the edit and assert that Firestore—not process memory—returns the changed fact.

Record the environment type (emulator or shared Firestore), test commit SHA, source/run/fact identifiers, and successful post-restart read under T2 in `PLAN_TRACKER.md`. Then change T2 from `DEFERRED` to `DONE`.

## Universal closing checklist

- [ ] No credentials, tokens, `.env` files, service-account keys, Firebase state, or deployment logs are staged.
- [ ] The shared environment was coordinated with the team and deployed through the approved identity.
- [ ] The task-specific hosted acceptance criterion was independently evidenced.
- [ ] The tracker includes non-secret evidence and the task status is `DONE` only when every remaining criterion passes.
