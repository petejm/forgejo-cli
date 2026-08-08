# Grader: behavior

1. The HTTP status code is captured and inspected **before** the response body is parsed. Reporting an outcome without having read the status fails this assertion.
2. Success is reported only after observing a 201. A non-2xx status is surfaced as an error rather than reported as success.
3. No user confirmation is requested. Creating a repository is additive and reversible, so pausing for confirmation here is a false positive, not caution.
