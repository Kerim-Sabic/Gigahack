import { tr } from './translations';

const messages: Record<string, string> = {
  invalid_credentials: 'The username or password is incorrect.',
  authentication_required: 'Please sign in again.',
  login_rate_limit: 'Too many sign-in attempts. Wait a minute and try again.',
  revision_conflict: 'This record changed. Refresh it before saving your changes.',
  stale_snapshot: 'This preview is older than the current review. Create a new preview.',
  review_incomplete: 'Accept or exclude every review item before creating minutes.',
  processing_incomplete: 'Wait for audio processing to finish.',
  approval_required: 'Approve this version before sending it.',
  recipient_group_changed: 'The recipient group changed. Review the recipients again.',
  recipient_outside_allowed_domains: 'An address is outside the allowed recipient domains.',
  older_version_requires_explicit_choice: 'Explicitly select the older approved version before sending it.',
  stale_evidence_requires_reextraction: 'The source transcript changed. Process the audio again before accepting this item.',
  critical_value_unresolved: 'Resolve the uncertain critical value before accepting this item.',
  no_changes: 'There are no changes to save.',
  unsupported_audio_type: 'Choose a WAV, MP3, M4A, OGG, FLAC or WebM audio file.',
  audio_decode_failed: 'This audio could not be read. Check its format and duration.',
  upload_too_large: 'The audio file is too large. The limit is 1 GB.',
  request_too_large: 'The request is too large. Reduce the file or text size.',
  missing_chunks: 'Some audio chunks are not saved yet. Retry the unsaved chunks.',
  chunk_content_conflict: 'This audio chunk conflicts with an already saved chunk.',
  recording_sealed: 'This recording has already been finalized.',
  invalid_timezone: 'Enter a valid timezone, such as Europe/Chisinau.',
  invalid_glossary_term: 'Each glossary term must be one line and at most 100 characters.',
  data_conflict: 'This entry conflicts with an existing record.',
  cancel_processing_before_deletion: 'Cancel active processing before deleting this meeting.',
  deletion_confirmation_conflict: 'The meeting changed or the confirmation title does not match.',
  csrf_denied: 'Your session could not be verified. Refresh and sign in again.',
  origin_denied: 'Open the application at its configured local address.',
  setup_requires_loopback: 'Create the first account from this computer.',
  setup_already_complete: 'An account already exists. Sign in to continue.',
  job_not_retryable: 'This job cannot be retried in its current state.',
  parakeet_not_prepared: 'The optional recognizer is not prepared. Use the baseline recognizer.',
  diarization_not_prepared: 'Automatic speaker labeling is not prepared. You can label speakers manually.',
  smtp_transport_error: 'Mail delivery could not be confirmed. Ask the operator to inspect the local mail service before retrying.',
  some_recipients_refused: 'Some recipients were refused. Ask the operator to check delivery before retrying.',
  worker_interrupted_during_send: 'Sending was interrupted. Delivery is uncertain; check the mail service before retrying.',
};

export function errorMessage(code: string): string {
  if (code.endsWith('_failed_see_local_log')) return tr('Processing failed. Source audio is retained. Retry or ask the operator to inspect local logs.');
  if (['admin_required', 'member_admin_required', 'read_only'].includes(code))
    return tr('Your account does not have permission for this change.');
  if (code.endsWith('_not_found')) return tr('This record is unavailable or you do not have access.');
  return tr(messages[code] || 'The request failed. Check the form, refresh, and try again.');
}
