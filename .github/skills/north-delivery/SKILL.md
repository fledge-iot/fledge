---
name: north-delivery
description: "Model-check the north service's delivery position (streams.last_object) with TLA+ and TLC. Use when changing C/services/north data_load.cpp, data_send.cpp, data_load.h, data_sender.h, the north shutdown sequence in north.cpp, how plugin_send's return count is used, the north filter pipeline end, or anything that reads streams.last_object such as purge's retain unsent; or when asked whether the north service can skip, lose or resend readings."
---

# North delivery position

**Rule.** The position saved in `streams.last_object` never passes a reading that the north plugin has not accepted and the filters did not remove.

**Harm.** A restart resumes after that position, and purge's "retain unsent" treats everything at or below it as sent (`python/fledge/tasks/purge/purge.py:140-197`). A reading the position passes is silently never delivered.

The question is about the order of steps across three threads: the load thread, the send thread, and the main thread's shutdown. Tests rarely hit the bad interleavings, so this skill checks every interleaving of a small model with TLC.

## Run

From the repo root:

```sh
python .github/skills/north-delivery/scripts/check.py                   # every config
python .github/skills/north-delivery/scripts/check.py today --trace     # one config, counterexample in code terms
```

The script needs Python 3 and either Java 11+ (`$JAVA`, or `java` on PATH) or Docker; with neither, it fails. TLC 1.7.4 is downloaded once into `~/.cache/fledge-north-delivery/`, checked against a pinned sha256, or taken from `$TLA2TOOLS`. Each config takes a few seconds. It exits 0 only when every config gives its expected result.

| Config | Defects modeled | Expected | Distinct states (one worker) |
|---|---|---|---|
| `today` | all three, as the code is now | breaks `PositionNeverPassesUnsent` | 732 (stops at the first break) |
| `partial-send` | F1 only | breaks `PositionNeverPassesUnsent` | 4,844 |
| `filter-end` | F2a only | breaks `PositionNeverPassesUnsent` | 1,641 |
| `sender-filtered` | F2b only | breaks `PositionNeverPassesUnsent` | 9,771 |
| `fixed` | none | holds | 39,829 (complete) |
| `witness-send` | none | breaks `CannotDeliverAll` | 37,333 |
| `witness-filter` | none | breaks `CannotFilterAll` | 35,886 |

The witnesses break on purpose. Each shows that the corrected model can still do the work: every reading accepted by the plugin (or removed by the filters), a clean stop, and position N saved. If a witness stops breaking, the model has lost that path and a pass on `fixed` proves nothing.

To read a result as a picture, use the `/statechart` skill on `model/NorthDelivery.tla` with a config. It draws the bug path as a state chart.

## Files

- `model/NorthDelivery.tla`: the spec. Every action has a comment naming its code site.
- `model/*.cfg`: one config per row above. `Defects` selects which of today's code paths the model follows; leaving a defect out models the corrected path.
- `scripts/check.py`: runs TLC, compares results with `EXPECTED`, and prints traces using `SITES` (action to code site).

## Coverage

Confirmed against the tree at commit `87e4f70365d6d44f77ca491895acfeaafeaa4028`. The north files last changed at `fc3813b2e` (FOGL-10281). Move this commit forward only after re-reading every site below against the new code.

| Code | Model action |
|---|---|
| `DataLoad::DataLoad` (`data_load.cpp:42-47`): `m_lastFetched`, `m_streamSent` from `getLastSentId()`; `m_nextStreamUpdate = 1` | `Init` |
| `DataLoad::loadThread` (`:128`), `waitForReadRequest` (`:150`) | `LoadWaitForRequest` |
| `DataLoad::readBlock` (`:179`): fetch, `m_lastFetched = getLastId()` (`:232`) | `LoadReadBlock` |
| `readBlock` idle loop: `flushLastSentId()` after repeated empty fetches (`:251`) | `LoadIdleFlush` |
| `readBlock` exit on `m_shutdown` | `LoadIdleExit` |
| `bufferReadings` (`:383`) -> filter pipeline -> `pipelineEnd` (`:628`), including `updateLastSentId(m_lastFetched)` (`:661`) | `LoadFilter`, `LoadFlush` |
| `pipelineEnd`: `m_queue.push_back`, `m_fetchCV.notify_all` | `LoadPush` |
| `DataLoad::fetchReadings` (`:428`), `triggerRead` (`:167`) | `SendFetch`, `SendWake` |
| `DataSender::sendThread` (`data_send.cpp:96`) loop and NULL return | `SendTop` |
| `DataSender::send` (`:170`): `plugin_send`, `lastSent`, erase | `SendPlugin` |
| `sendThread` "All readings filtered out": `updateLastSentId(getLastFetched())` (`:139`) | `SendFiltered` |
| `sendThread` shutdown branch: `readings = NULL` | `SendDispatchShutdown` |
| `DataLoad::updateLastSentId` (`data_load.cpp:509`) | `SetStreamSent`, `SendUpdate` |
| `DataLoad::flushLastSentId` (`:523`) from either thread | `LoadFlush`, `SendFlush`, `LoadIdleFlush` |
| `NorthService::start` shutdown (`north.cpp:585-590`): `m_dataLoad->shutdown()`, `delete m_dataSender`, `delete m_dataLoad` | `Stop`, `StopSender`, `JoinSender`, `JoinLoad` |
| `DataLoad::~DataLoad` (`data_load.cpp:56-80`): join, `if (m_flushRequired) flushLastSentId()`, drop queue | `JoinLoad` |

## Does a change touch the verified code?

Run `git diff --stat <sync commit>..HEAD -- C/services/north docs/plugin_developers_guide/04_north_plugins.rst python/fledge/tasks/purge/purge.py`. A change touches the model when it:

- moves, adds or removes a call to `updateLastSentId` or `flushLastSentId`;
- changes how `send()` picks `lastSent` or which readings it erases;
- changes `pipelineEnd`, `fetchReadings`, `readBlock`, `loadThread` or `sendThread` control flow, or what they lock;
- changes the shutdown order in `NorthService::start` or the `DataLoad` destructor;
- changes the `plugin_send` contract (what the returned count means), or how purge reads `last_object`.

Logging, statistics, asset tracking, and the debugger, isolate and suspend features are outside the model.

## Real bug or modeling error?

Every break is a claim about the code. Before reporting one:

1. Run the config with `--trace`. Each step names its code site.
2. Walk the trace through the real source at the sites in Coverage. Each step must be something the code can actually do, in that order, with the locks it holds.
3. If a step is impossible in the code, the model is wrong: fix the action to match the code and say so. Never weaken `PositionNeverPassesUnsent`, drop a witness, or shrink the bounds to make a break go away.
4. If every step is possible, it is a real bug. Report it with the trace; do not change product code unless asked.

## When the code changes on purpose

- **A defect is fixed.** If the real fix matches the model's corrected path (the branch taken when the defect is not in `Defects`), keep it; otherwise change the action to follow the real fix. Then remove the defect from `Defects` in `today.cfg` and delete its single-defect config and `EXPECTED` entry. When `today` has no defects left, set `EXPECTED["today"] = "ok"`.
- **Other changes.** Update the action and its code-site comment, update `SITES` in `check.py` if an action is added or renamed, rerun every config, then move the sync commit in Coverage.
- After any model edit, confirm the model can still catch a bug. Temporarily break the matching code path in the model (for example, make `SendPlugin` advance the position when `k = 0`), check that `fixed` breaks, then revert.

## Findings at the sync commit (not fixed)

Each was found by TLC and walked through the code by reading; the north service has no C++ unit tests.

**F1, partial send** (`partial-send`, 16 steps). `send()` sets `lastSent` to the last reading with an id in the whole set, whatever count the plugin returned, then erases every reading at or below it (`data_send.cpp:219-272`). If a plugin accepts 1 of 2, both are erased and the position moves to 2; the stop flushes it, and reading 2 is never sent. The plugin guide allows partial counts (`docs/plugin_developers_guide/04_north_plugins.rst:380`); the in-repo OMF plugin returns all or nothing, so only plugins that return partial counts are hit.

**F2a, filters remove a block** (`filter-end`, 13 steps). `pipelineEnd` calls `updateLastSentId(m_lastFetched)` when the filters leave no reading with an id (`data_load.cpp:657-662`). It runs on the load thread, so it can move the position past readings still queued or held for retry by the sender. Path: 1-2 queued, plugin accepts 1, filters drop 3-4, position 4 is saved, reading 2 is still waiting.

**F2b, sender sees an empty block** (`sender-filtered`, 19 steps). The "All readings filtered out" branch calls `updateLastSentId(m_loader->getLastFetched())` (`data_send.cpp:130-143`). `m_lastFetched` is where the load thread is now, not the end of the empty block, so the position passes readings the load thread has read but not yet queued. Path: 1-4 filtered out, 5 read, the sender takes the empty block and saves position 5 before 5 is sent.

**Together** (`today`, 12 steps): 1-2 filtered (position 2 in memory, not saved), 3-4 read, the sender takes the empty block, sets position 4 and saves it while 3-4 are still in the pipeline.

The fix the `fixed` config checks: `send()` returns the id of the last reading the plugin accepted, and an empty block advances the position only to its own last fetched id, from the send thread only.

Side note, not modeled: `north.cpp:539` checks `itemExists("prefetchLimnit")`, so the `prefetchLimit` setting is never applied at startup and the limit stays 2.

## Bounds and assumptions

- N = 5 readings, block size 2, prefetch limit 2, `streamUpdate` 1 (the default: the position is saved on every second update).
- All readings are in the buffer from the start; new arrivals are not modeled.
- The filters may drop any subset of a block; they never add readings without an id.
- The plugin accepts the first k readings of a block, for any k from 0 to the block size.
- `m_nextStreamUpdate--` is modeled as atomic, although `updateLastSentId` takes no lock and runs on both threads. A lost decrement moves when a save happens; the model does not explore those extra or missing save points.
- A crash can happen at any state; the rule is checked at every state, so crashes need no separate step.
- Not covered: purge itself, liveness (the model checks that nothing bad is saved, not that delivery finishes), `streamUpdate` above 1, the debugger, isolate and suspend features, plugin reconfiguration while running, and `~NorthService`, which deletes `m_dataLoad` before `m_dataSender` but only reaches them when `start()` returned before its own shutdown sequence.
