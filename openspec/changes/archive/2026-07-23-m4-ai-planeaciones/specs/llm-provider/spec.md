# LLM Provider Specification

## Purpose

Defines the `LLMProvider` port as a provider-agnostic dependency selected entirely via
environment configuration, and the failure-surfacing contract for generation errors.

## Requirements

### Requirement: Provider Selection Is Config-Driven, Not Code-Driven

The system MUST select the active LLM provider implementation via the `LLM_PROVIDER`
environment variable, defaulting to a self-hosted vLLM (OpenAI-compatible) adapter when
unset. Switching providers (e.g., to Claude) MUST require only configuration changes
(`LLM_PROVIDER`, and provider-specific settings), never a code change or redeploy of
provider-selection logic. Connection details MUST be read from `LLM_BASE_URL`,
`LLM_MODEL`, and `LLM_API_KEY` for the OpenAI-compatible adapter, and from `ANTHROPIC_*`
settings for the Claude adapter.

#### Scenario: Default configuration selects the vLLM adapter

- GIVEN `LLM_PROVIDER` is unset in the environment
- WHEN the system resolves the active `LLMProvider` implementation
- THEN it MUST select the OpenAI-compatible (vLLM) adapter
- AND MUST configure it from `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`

#### Scenario: Switching to Claude requires only configuration

- GIVEN `LLM_PROVIDER` is set to the Claude adapter identifier
- AND `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` are configured
- WHEN the system resolves the active `LLMProvider` implementation
- THEN it MUST select the Claude adapter without any code change to the generation service

### Requirement: Generation Failures Surface as a Failed Status With a Reason

Any error raised by the configured `LLMProvider` — including connection errors,
timeouts, and response schema-parse failures — MUST be caught at the generation
boundary and MUST result in the associated `LessonPlan` being marked `status=failed`
with a recorded reason. Such failures MUST NOT propagate as an unhandled exception that
crashes the calling task or leaves the `LessonPlan` row in an inconsistent state.

#### Scenario: Provider timeout is surfaced as a failed LessonPlan

- GIVEN the configured `LLMProvider` times out during a generation call
- WHEN the generation task handles the timeout
- THEN the associated `LessonPlan` MUST be set to `status=failed`
- AND a failure reason MUST be recorded

#### Scenario: Response fails schema validation

- GIVEN the `LLMProvider` returns a response that does not conform to the ABPC Pydantic schema
- WHEN the generation task validates the response
- THEN the associated `LessonPlan` MUST be set to `status=failed`
- AND the raw provider exception MUST NOT propagate uncaught out of the task

#### Scenario: Claude-fallback on repeated vLLM parse failure (optional)

- GIVEN the default vLLM provider has failed schema validation on a retry attempt for the same request
- WHEN a Claude-fallback policy is configured
- THEN the system MAY retry the same generation request against the Claude adapter before marking the `LessonPlan` as `failed`
