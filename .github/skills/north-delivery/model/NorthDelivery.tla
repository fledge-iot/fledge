---------------------------- MODULE NorthDelivery ----------------------------
(***************************************************************************)
(* The north service's delivery position (streams.last_object).           *)
(*                                                                         *)
(* Three threads of one north service process:                             *)
(*   load thread  DataLoad::loadThread, readBlock, bufferReadings,         *)
(*                pipelineEnd          (C/services/north/data_load.cpp)    *)
(*   send thread  DataSender::sendThread, send                             *)
(*                                     (C/services/north/data_send.cpp)    *)
(*   main thread  the shutdown sequence at the end of NorthService::start  *)
(*                                     (C/services/north/north.cpp)        *)
(* Shared state is DataLoad's members (m_streamSent, m_nextStreamUpdate,   *)
(* m_flushRequired, m_lastFetched, m_queue, m_readRequest) and the streams *)
(* row in storage.                                                         *)
(*                                                                         *)
(* Readings 1..N are already in the storage buffer. The filter pipeline    *)
(* may drop any subset of each block. The plugin's plugin_send accepts the *)
(* first k readings of the block, for any k from 0 to the block size.      *)
(*                                                                         *)
(* Defects selects which current code paths the model follows. Each one    *)
(* names a path in today's code; leaving it out models the corrected path. *)
(*   "partialSend"            DataSender::send takes lastSent from the     *)
(*                            last reading in the block, not the last one  *)
(*                            the plugin accepted, and erases the block.   *)
(*   "filterEndAdvance"       DataLoad::pipelineEnd calls                  *)
(*                            updateLastSentId(m_lastFetched) when the     *)
(*                            filters remove the whole block.              *)
(*   "senderFilteredAdvance"  DataSender::sendThread's "All readings       *)
(*                            filtered out" branch calls                   *)
(*                            updateLastSentId(getLastFetched()).          *)
(***************************************************************************)
EXTENDS Integers, Sequences, FiniteSets

CONSTANTS
    N,              \* readings in the storage buffer, ids 1..N
    BlockSize,      \* DataLoad::m_blockSize ("blockSize")
    PrefetchLimit,  \* DataLoad::m_prefetchLimit (2: north.cpp never applies "prefetchLimit")
    StreamUpdate,   \* DataLoad::m_streamUpdate ("streamUpdate", default 1)
    Defects

ASSUME N \in Nat /\ BlockSize \in Nat \ {0} /\ PrefetchLimit \in Nat \ {0}
ASSUME StreamUpdate \in Nat \ {0}
ASSUME Defects \subseteq {"partialSend", "filterEndAdvance", "senderFilteredAdvance"}

\* The send thread holds no block (`readings == NULL`). A record, so TLC can
\* compare it with real blocks; src 0 is never a real block's last id.
None == [ids |-> <<>>, src |-> 0]

VARIABLES
    stored,         \* streams.last_object in storage
    streamSent,     \* DataLoad::m_streamSent
    flushRequired,  \* DataLoad::m_flushRequired
    nextUpdate,     \* DataLoad::m_nextStreamUpdate
    lastFetched,    \* DataLoad::m_lastFetched
    queue,          \* DataLoad::m_queue: blocks of [ids, src] (src = last id fetched for the block)
    readRequest,    \* DataLoad::m_readRequest > 0
    lpc,            \* load thread position
    lfetched,       \* load thread: ids fetched by readBlock for the block in hand
    lsurv,          \* load thread: ids left after the filter pipeline
    spc,            \* send thread position
    held,           \* DataSender::sendThread's local `readings`, or None
    pending,        \* send thread: id about to be passed to updateLastSentId
    delivered,      \* ids the plugin has accepted
    filtered,       \* ids the filter pipeline removed
    loadShutdown,   \* DataLoad::m_shutdown
    sendShutdown,   \* DataSender::m_shutdown
    mpc             \* main thread position

vars == <<stored, streamSent, flushRequired, nextUpdate, lastFetched, queue,
          readRequest, lpc, lfetched, lsurv, spc, held, pending, delivered,
          filtered, loadShutdown, sendShutdown, mpc>>

Range(s) == {s[i] : i \in DOMAIN s}
Last(s) == s[Len(s)]
Min(a, b) == IF a < b THEN a ELSE b
Ids(lo, hi) == [i \in 1..(hi - lo + 1) |-> lo + i - 1]
RECURSIVE Sorted(_)
Sorted(S) == IF S = {} THEN <<>>
             ELSE LET m == CHOOSE x \in S : \A y \in S : x <= y
                  IN <<m>> \o Sorted(S \ {m})

(* DataLoad::updateLastSentId up to its flush decision:                   *)
(*   m_streamSent = id; m_flushRequired = true;                           *)
(*   if (m_nextStreamUpdate-- <= 0) { flushLastSentId(); ... }            *)
SetStreamSent(id) ==
    /\ streamSent' = id
    /\ flushRequired' = TRUE
    /\ nextUpdate' = nextUpdate - 1
FlushDue == nextUpdate <= 0

Init ==
    /\ stored = 0                   \* createNewStream inserts last_object 0
    /\ streamSent = 0               \* DataLoad constructor: getLastSentId()
    /\ flushRequired = FALSE
    /\ nextUpdate = StreamUpdate    \* setStreamUpdate
    /\ lastFetched = 0
    /\ queue = <<>>
    /\ readRequest = FALSE
    /\ lpc = "wait" /\ lfetched = <<>> /\ lsurv = <<>>
    /\ spc = "top" /\ held = None /\ pending = 0
    /\ delivered = {} /\ filtered = {}
    /\ loadShutdown = FALSE /\ sendShutdown = FALSE
    /\ mpc = "run"

(***************************************************************************)
(* Load thread                                                             *)
(***************************************************************************)

\* DataLoad::waitForReadRequest returns on a read request or shutdown.
LoadWaitForRequest ==
    /\ lpc = "wait"
    /\ loadShutdown \/ readRequest
    /\ readRequest' = FALSE
    /\ lpc' = IF loadShutdown THEN "done" ELSE "fetch"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, lfetched, lsurv, spc, held, pending, delivered,
                   filtered, loadShutdown, sendShutdown, mpc>>

\* loadThread's `while (!m_shutdown && m_queue.size() < m_prefetchLimit)`,
\* then readBlock's m_storage->readingFetch(m_lastFetched + 1, blockSize)
\* and `m_lastFetched = readings->getLastId()`.
LoadReadBlock ==
    /\ lpc = "fetch"
    /\ IF loadShutdown THEN
           /\ lpc' = "done"
           /\ UNCHANGED <<lastFetched, lfetched>>
       ELSE IF Len(queue) >= PrefetchLimit THEN
           /\ lpc' = "wait"
           /\ UNCHANGED <<lastFetched, lfetched>>
       ELSE IF lastFetched < N THEN
           LET hi == Min(lastFetched + BlockSize, N)
           IN /\ lfetched' = Ids(lastFetched + 1, hi)
              /\ lastFetched' = hi
              /\ lpc' = "filter"
       ELSE
           \* readBlock's do/while: no readings, sleep and retry
           /\ lpc' = "idle"
           /\ UNCHANGED <<lastFetched, lfetched>>
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, queue,
                   readRequest, lsurv, spc, held, pending, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

\* readBlock: after repeated empty fetches, flushLastSentId().
LoadIdleFlush ==
    /\ lpc = "idle"
    /\ ~loadShutdown
    /\ stored # streamSent
    /\ stored' = streamSent
    /\ UNCHANGED <<streamSent, flushRequired, nextUpdate, lastFetched, queue,
                   readRequest, lpc, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, loadShutdown, sendShutdown, mpc>>

\* readBlock's do/while ends on shutdown.
LoadIdleExit ==
    /\ lpc = "idle"
    /\ loadShutdown
    /\ lpc' = "done"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, loadShutdown, sendShutdown, mpc>>

\* bufferReadings runs the filter pipeline; DataLoad::pipelineEnd receives
\* the survivors and, when none have an id, calls
\* updateLastSentId(m_lastFetched).
LoadFilter ==
    /\ lpc = "filter"
    /\ \E keep \in SUBSET Range(lfetched) :
         LET advance == keep = {} /\ "filterEndAdvance" \in Defects
         IN /\ lsurv' = Sorted(keep)
            /\ filtered' = filtered \cup (Range(lfetched) \ keep)
            /\ IF advance
                  THEN /\ SetStreamSent(lastFetched)
                       /\ lpc' = IF FlushDue THEN "flush" ELSE "push"
                  ELSE /\ lpc' = "push"
                       /\ UNCHANGED <<streamSent, flushRequired, nextUpdate>>
    /\ UNCHANGED <<stored, lastFetched, queue, readRequest, lfetched, spc, held,
                   pending, delivered, loadShutdown, sendShutdown, mpc>>

\* updateLastSentId -> flushLastSentId on the load thread.
LoadFlush ==
    /\ lpc = "flush"
    /\ stored' = streamSent
    /\ nextUpdate' = StreamUpdate
    /\ lpc' = "push"
    /\ UNCHANGED <<streamSent, flushRequired, lastFetched, queue, readRequest,
                   lfetched, lsurv, spc, held, pending, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

\* pipelineEnd: m_queue.push_back(readingSet) under m_qMutex.
LoadPush ==
    /\ lpc = "push"
    /\ queue' = Append(queue, [ids |-> lsurv, src |-> Last(lfetched)])
    /\ lfetched' = <<>>
    /\ lsurv' = <<>>
    /\ lpc' = "fetch"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   readRequest, spc, held, pending, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

(***************************************************************************)
(* Send thread                                                             *)
(***************************************************************************)

\* sendThread: `while (!m_shutdown) { if (readings == NULL) fetchReadings(true) ...`
SendTop ==
    /\ spc = "top"
    /\ spc' = IF sendShutdown THEN "done"
              ELSE IF held = None THEN "fetch" ELSE "dispatch"
    /\ held' = IF sendShutdown THEN None ELSE held
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, pending, delivered,
                   filtered, loadShutdown, sendShutdown, mpc>>

\* DataLoad::fetchReadings under m_qMutex: pop the front block and
\* triggerRead when fewer than m_prefetchLimit remain; on an empty queue,
\* triggerRead and wait on m_fetchCV, or return NULL after shutdown.
SendFetch ==
    /\ spc = "fetch"
    /\ IF queue # <<>> THEN
           /\ held' = Head(queue)
           /\ queue' = Tail(queue)
           /\ readRequest' = (readRequest \/ (Len(Tail(queue)) < PrefetchLimit /\ ~loadShutdown))
           /\ spc' = "dispatch"
       ELSE IF loadShutdown THEN
           /\ spc' = "done"
           /\ UNCHANGED <<held, queue, readRequest>>
       ELSE
           /\ readRequest' = TRUE
           /\ spc' = "waiting"
           /\ UNCHANGED <<held, queue>>
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   lpc, lfetched, lsurv, pending, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

\* m_fetchCV is notified by a push or by DataLoad::shutdown.
SendWake ==
    /\ spc = "waiting"
    /\ queue # <<>> \/ loadShutdown
    /\ spc' = "fetch"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, held, pending,
                   delivered, filtered, loadShutdown, sendShutdown, mpc>>

\* sendThread: `if (m_shutdown == false && readings->getCount() > 0)`
\* -> DataSender::send -> m_plugin->send(readings) returns k readings sent.
\* On k > 0 send() picks lastSent and erases every reading with id <= lastSent.
SendPlugin ==
    /\ spc = "dispatch"
    /\ ~sendShutdown
    /\ held.ids # <<>>
    /\ \E k \in 0..Len(held.ids) :
         /\ delivered' = delivered \cup {held.ids[i] : i \in 1..k}
         /\ IF k = 0
               THEN /\ spc' = "top"            \* send() returns 0; readings kept for retry
                    /\ UNCHANGED <<held, pending>>
               ELSE LET lastSent == IF "partialSend" \in Defects
                                       THEN Last(held.ids)
                                       ELSE held.ids[k]
                    IN /\ held' = [held EXCEPT !.ids = SelectSeq(@, LAMBDA x : x > lastSent)]
                       /\ pending' = lastSent
                       /\ spc' = "update"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, filtered,
                   loadShutdown, sendShutdown, mpc>>

\* sendThread's "All readings filtered out" branch.
SendFiltered ==
    /\ spc = "dispatch"
    /\ ~sendShutdown
    /\ held.ids = <<>>
    /\ pending' = IF "senderFilteredAdvance" \in Defects THEN lastFetched ELSE held.src
    /\ held' = None
    /\ spc' = "update"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

\* sendThread: shutdown seen after the fetch, `readings = NULL`.
SendDispatchShutdown ==
    /\ spc = "dispatch"
    /\ sendShutdown
    /\ held' = None
    /\ spc' = "done"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, pending, delivered,
                   filtered, loadShutdown, sendShutdown, mpc>>

\* sendThread: m_loader->updateLastSentId(...); then
\* `removeReadings = vec->size() == 0`.
SendUpdate ==
    /\ spc = "update"
    /\ SetStreamSent(pending)
    /\ spc' = IF FlushDue THEN "flush" ELSE "top"
    /\ held' = IF held # None /\ held.ids = <<>> THEN None ELSE held
    /\ pending' = 0
    /\ UNCHANGED <<stored, lastFetched, queue, readRequest, lpc, lfetched, lsurv,
                   delivered, filtered, loadShutdown, sendShutdown, mpc>>

\* updateLastSentId -> flushLastSentId on the send thread.
SendFlush ==
    /\ spc = "flush"
    /\ stored' = streamSent
    /\ nextUpdate' = StreamUpdate
    /\ spc' = "top"
    /\ UNCHANGED <<streamSent, flushRequired, lastFetched, queue, readRequest,
                   lpc, lfetched, lsurv, held, pending, delivered, filtered,
                   loadShutdown, sendShutdown, mpc>>

(***************************************************************************)
(* Main thread: end of NorthService::start                                 *)
(*   m_dataLoad->shutdown(); delete m_dataSender; delete m_dataLoad;       *)
(***************************************************************************)

\* m_dataLoad->shutdown(): the service is stopping or restarting.
Stop ==
    /\ mpc = "run"
    /\ loadShutdown' = TRUE
    /\ mpc' = "stopSender"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, sendShutdown>>

\* ~DataSender sets m_shutdown, then joins the send thread.
StopSender ==
    /\ mpc = "stopSender"
    /\ sendShutdown' = TRUE
    /\ mpc' = "joinSender"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, loadShutdown>>

JoinSender ==
    /\ mpc = "joinSender"
    /\ spc = "done"
    /\ mpc' = "joinLoad"
    /\ UNCHANGED <<stored, streamSent, flushRequired, nextUpdate, lastFetched,
                   queue, readRequest, lpc, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, loadShutdown, sendShutdown>>

\* ~DataLoad joins the load thread, then `if (m_flushRequired) flushLastSentId()`
\* and discards the queue.
JoinLoad ==
    /\ mpc = "joinLoad"
    /\ lpc = "done"
    /\ stored' = IF flushRequired THEN streamSent ELSE stored
    /\ queue' = <<>>
    /\ mpc' = "stopped"
    /\ UNCHANGED <<streamSent, flushRequired, nextUpdate, lastFetched,
                   readRequest, lpc, lfetched, lsurv, spc, held, pending,
                   delivered, filtered, loadShutdown, sendShutdown>>

Stopped ==
    /\ mpc = "stopped"
    /\ UNCHANGED vars

Next ==
    \/ LoadWaitForRequest \/ LoadReadBlock \/ LoadIdleFlush \/ LoadIdleExit
    \/ LoadFilter \/ LoadFlush \/ LoadPush
    \/ SendTop \/ SendFetch \/ SendWake \/ SendPlugin \/ SendFiltered
    \/ SendDispatchShutdown \/ SendUpdate \/ SendFlush
    \/ Stop \/ StopSender \/ JoinSender \/ JoinLoad \/ Stopped

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* Rules                                                                   *)
(***************************************************************************)

\* The position saved in streams.last_object never passes a reading that the
\* plugin has not accepted and the filters did not remove. A restart resumes
\* after that position, and purge's "retain unsent" treats everything at or
\* below it as sent, so a reading it passes is never delivered.
PositionNeverPassesUnsent ==
    \A id \in 1..stored : id \in delivered \cup filtered

\* Witnesses, expected to break: the service can get every reading through
\* the plugin (or through the filters), stop cleanly, and save position N.
\* If either ever holds, the model can no longer do that work and a pass on
\* the rule above means nothing.
CannotDeliverAll ==
    ~(mpc = "stopped" /\ stored = N /\ delivered = 1..N)

CannotFilterAll ==
    ~(mpc = "stopped" /\ stored = N /\ filtered = 1..N)

TypeOK ==
    /\ stored \in 0..N /\ streamSent \in 0..N /\ lastFetched \in 0..N
    /\ flushRequired \in BOOLEAN /\ readRequest \in BOOLEAN
    /\ nextUpdate \in -2..StreamUpdate
    /\ lpc \in {"wait", "fetch", "idle", "filter", "flush", "push", "done"}
    /\ spc \in {"top", "fetch", "waiting", "dispatch", "update", "flush", "done"}
    /\ mpc \in {"run", "stopSender", "joinSender", "joinLoad", "stopped"}
    /\ delivered \subseteq 1..N /\ filtered \subseteq 1..N
=============================================================================
