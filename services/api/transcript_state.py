"""Transcript changes invalidate interpretation, never immutable historical snapshots."""


def changed(c, meeting_id, asset_id):
    c.execute("INSERT INTO transcript_analysis_state(asset_id,meeting_id) VALUES(?,?) ON CONFLICT DO NOTHING",
              (asset_id, meeting_id))
    # New speech can change the meaning of existing statements on the same recording.
    c.execute("UPDATE candidates SET review='needs_review' WHERE review!='excluded' AND id IN "
              "(SELECT e.candidate_id FROM evidence e JOIN segments s ON s.id=e.segment_id WHERE s.asset_id=?)",
              (asset_id,))
    c.execute("UPDATE meetings SET revision=revision+1,status='awaiting_review' WHERE id=?", (meeting_id,))
