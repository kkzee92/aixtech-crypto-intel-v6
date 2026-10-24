# Security Architecture (v0.6)

## Zero-Trust Principles
- All actions pass through `check_policy` allowlist before audit append.
- Paper-only enforced at runtime; live modes raise PermissionError.
- Secrets never stored; redaction applied to all logs and details.
- Hash-chained audit with lineage attestation and optional sealed digests.
- Rate and sequence anomaly detection for unusual activity patterns.

## Data Classification
See `CLASSIFICATION` in security.py. Secrets (keys, seeds, tokens) are never stored or logged.

## Redaction
Expanded patterns cover Telegram bots, Discord tokens, GitHub, AWS, JWTs, BIP39 seeds, WIF, hex keys, emails, etc.

## Controls Summary
1. Paper-only execution gate.
2. Zero-trust action policy.
3. Secret redaction and detection tripwire.
4. Append-only hash chain with anomaly flags.
5. Source integrity digests.

This is a research demonstration, not a production security product. Combine with external secrets managers, IP allowlists, and hardware enclaves for real deployments.
