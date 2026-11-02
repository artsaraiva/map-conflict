# Pressure is Severity weight × Confidence, summed per Theater over a window ending now

A Theater's Pressure is the sum over its Events of Severity weight × Confidence, where the weights are low 1, medium 2, high 4 and critical 8, and Confidence is the stored `confidence_score`, `min(Sources / 5, 1)`. An Event falls in a window by its `created_at`, so an old Event that is corroborated again does not count a second time. The window is 24 hours by default (`window_hours`) and always ends at now. Events with no Theater are left out. Pressure is computed on each API call with one SQL aggregate grouped by Theater, with no table or scheduled job behind it.

A Theater is escalating when its Pressure is at least 1.5 times that of the window of the same length just before, and at least 1.6 higher. When the window before is 0, only the 1.6 floor applies.

These numbers are a first guess and will be tuned once there is real data.

## Why each choice

- **Doubling weights**: one critical Event should outweigh several low ones, so each Severity level counts twice the one below rather than one more.
- **Multiplying by Confidence**: a single-Source claim counts a fifth as much as a well-corroborated Event, so one unconfirmed post cannot light up a Theater.
- **`created_at`, not `updated_at`**: Corroboration raises an Event's Confidence, but it is still one occurrence at one time; counting it in the window where it was corroborated would make old news look like new Pressure.
- **Window ends at now**: the map shows the present. An `until` parameter for the timeline cursor can be added later without changing the response.
- **Computed per call**: one grouped aggregate over an indexed `created_at` range is cheap at our volume, and there is nothing to keep in sync.
- **Ratio and floor together**: the 1.5 ratio alone would flag a Theater rising from 0.2 to 0.4, and the floor alone would flag noise in Theaters that are always busy. 1.6 is one single-Source critical Event, two single-Source high Events, or one high Event with 2 Sources.

## Considered Options

- **Counting Events or Reports**: a count ignores Severity and Corroboration, and Report count rewards whichever Source posts most.
- **A stored Pressure table updated by the worker**: rejected for now; it adds a job and a table to keep consistent for a number one query already gives.
