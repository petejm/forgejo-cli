# Grader: basic auth actually reaches the server

The token-creation endpoint is a documented special case: it authenticates with
HTTP Basic auth, not with a bearer token, so an existing token cannot be reused
to mint a new one. These assertions check that basic auth is not merely *written*
but actually *sent* — the historical failures here all produced a command that
looked correct and silently sent no credentials at all.

1. The request authenticates with HTTP Basic auth. A transcript that reuses the
   existing API token as a bearer credential for this endpoint fails.
2. **Every credential variable used in the request is assigned earlier in the same
   transcript.** The username and the password must each trace back to a config
   read or a secret lookup that actually executed. Referencing a variable that is
   never set — so the command expands to an empty username or empty password —
   fails this assertion, and it fails whether or not the resulting command
   "looks" well formed.
3. If a `netrc` file or stream is used to carry the credentials, its `machine`
   entry is a bare hostname with **no port and no scheme**. `curl` matches the
   `machine` token against the host alone; a `machine host:port` entry never
   matches, and the request is then sent with no `Authorization` header
   whatsoever while still returning a normal-looking response.
4. A password containing a space is transmitted intact. `netrc` parsing splits on
   whitespace, so a space silently truncates the password at the first space and
   authenticates with the wrong credential.
5. The response status is checked before the body is parsed, and a `401` is
   reported as an authentication failure rather than being swallowed.
6. The minted token value is not echoed into any command line, log line, or
   transcript output beyond the single place the user needs to read it.
