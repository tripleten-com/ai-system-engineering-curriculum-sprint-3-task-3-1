# Task 3.1 release record

This record supports the Project Defense. It is not graded by the automated checks; they
read `submission.yaml`, `compose.yaml`, and the running stack. Replace every italic
placeholder line below with your own evidence; `poe verify` fails while any placeholder
remains. State the command, the time window, and what you saw. Keep the supplied evidence
pack separate from your own runs.

## Step 1 - The pinned release

Which images are named, which tag is the default, and how you confirmed that `poe start`
no longer produces an unnamed build.

_Write your evidence here._

## Step 2 - Roll forward and back

The `poe roll-forward` record: how long Compose waited, what the first probe saw, which
build answered. Then the same for `poe roll-back`. Say what you changed in the health check
and why the first probe changed with it.

_Write your evidence here._

## Step 3 - Resource bounds

The limits you chose, the sample you sized them from, and the `poe release-status` output
that shows Docker applied them.

_Write your evidence here._

## What this local rollout does not prove

One sentence per limitation you would raise before calling this a production rollout.

_Write your evidence here._
