# H1C0.R3.01.B3.8.2 — Sanitized Media Evidence Bundle

This is a local sanitized evidence bundle for `D:\rafa\pinho music`. It contains hashes, structural metadata, Mutagen tag keys, normalized tag fields, sidecar matching stats, and filename candidates. It does not include audio/video payloads, full lyrics, image payloads, embedded artwork, or base64/binary content.

## Totals

- Total files: `1051`
- Total media files: `928`
- Files by extension: `{'jpg': 2, 'lrc': 121, 'm4a': 921, 'mp3': 5, 'mp4': 2}`
- Media identity classifications: `{'observed_media_without_identity_tags': 704, 'observed_identity_title_artist': 214, 'mutagen_no_valid_evidence': 10}`
- Media with title+artist tags: `214`
- Media without identity tags: `704`
- Mutagen no valid evidence: `10`
- Unsupported or parse error: `0`
- LRC files: `121`
- LRC likely audio matches: `116`
- LRC without likely audio matches: `5`

## Protection

- Audio/video uploaded: `false`
- Full `.lrc` uploaded: `false`
- Image/capa payload uploaded: `false`
- Embedded artwork payload uploaded: `false`
- Binary/base64 payload uploaded: `false`

## Likely Cause Of `MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT`

The local corpus has many playable media files whose Mutagen-opened tags do not contain governed track_title/artist/album/album_artist fields. Filename-derived candidates exist but remain candidate_only_not_truth. Sidecar .lrc files are matchable structurally but cannot satisfy media identity truth without a governed lyrics/relationship policy.

## B3.9 Recommendation

Introduce a row applicability/sufficiency taxonomy that distinguishes media rows with governed tags, media rows with only technical metadata, unsupported media candidates, and sidecar relationship candidates. Preserve filename/lyrics candidates as non-truth hints unless a governed policy explicitly promotes them with evidence/provenance.

## Reports

- `inventory_manifest.json`
- `mutagen_tag_probe.json`
- `identity_coverage_by_file.json`
- `lyrics_sidecar_relation.json`
- `filename_candidate_identity.json`
- `unsupported_m4a_probe.json`
