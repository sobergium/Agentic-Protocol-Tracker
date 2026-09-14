# Universal source and publication policy

## Principle

Systems Over Signals is primary-source-first. Automated publication is allowed
only for registered sources and remains visibly provisional until weekly human
review. Review is post-publication and corrections are additive.

## Source roles

1. **Canonical** — official specification, steward, provider, regulator or
   standards body.
2. **Implementation** — official SDK, conformance suite, deployment or verified
   contract.
3. **Discovery** — media, third-party tracker or social signal. Discovery may
   propose a source but cannot substantiate a public claim.

The initial registry intentionally contains canonical sources only.

## Universal domains

The schema covers agent interoperability, agentic commerce, agentic payments,
identity and authorization, transaction infrastructure, blockchain payments,
foundation models, agent runtimes, financial services, regulation and research.
Adding an entity inside one of these domains is a registry operation, not a
schema redesign.

## Automation boundary

Scanners may retrieve untrusted external bytes, record response metadata,
normalize content and compute hashes. Retrieved content is never evaluated,
imported, executed or inserted as executable HTML.

A change event requires:

- a registered source;
- a valid entity relationship;
- a successful retrieval;
- a new content hash;
- source and retrieval evidence;
- an explicit provisional publication state.

## Review

Every Sunday the review workflow opens a GitHub issue for the preceding seven
days. Each item is confirmed, corrected, rejected, escalated for deeper research
or superseded. No correction silently deletes the original observation.

## Retention

Git stores normalized snapshots, event records and review outcomes. Raw source
responses are intentionally not committed. Workflow logs retain scan-level
operational evidence without turning the repository into an unbounded archive.
