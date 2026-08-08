# Grader: behavior

1. Pagination is handled: a full page of results triggers a request for the next page, and paging stops on the first short or empty page.
2. The accumulated result set that reaches the user is non-empty whenever the API returned items. A pagination loop that terminates early and reports nothing fails this assertion even though it exits cleanly.
3. The reported output identifies each issue by number, title, and state.
4. No user confirmation is requested. This is a read-only `GET`.
