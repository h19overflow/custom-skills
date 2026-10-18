# The 60 Architectural Patterns Catalog
Complete reference of all 60 production agent patterns from *The AI Agent Engineer's Guide: 60 Patterns for Building Autonomous Systems* (Vahe Aslanyan).
Organized strictly by the **8 Core Capabilities**.

---
## Capability: Perception: Turning Signals into Percepts
Covers Agents 1 through 7.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 1** | The Multimodal Grounding Agent | *Aligns linguistic references to the visual or audio referents they describe.* | Visual Question Decomposition (Agent 5), Provenance Tracker (Agent 55), Document Layout (Agent 2). |
| **Agent 2** | The Document Layout Agent | *Turns a PDF or scanned image into a typed tree of semantic regions.* | Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Multimodal Grounding (Agent 1). |
| **Agent 3** | The Temporal Sensor-Fusion Agent | *Aligns asynchronous streams into a single time-indexed percept.* | Ambient Context (Agent 6), Anomaly Spotter (Agent 4), Drift Detector (Agent 59). |
| **Agent 4** | The Anomaly-Spotter Agent | *Surfaces deviations from the expected pattern in a stream of observations.* | Drift Detector (Agent 59), Reflection (Agent 47), Temporal Sensor-Fusion (Agent 3). |
| **Agent 5** | The Visual Question Decomposition Agent | *Breaks a complex visual query into sub-queries answerable by simpler perception calls.* | Multimodal Grounding (Agent 1), Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55). |
| **Agent 6** | The Ambient Context Agent | *Passively integrates environmental signals the user didn't explicitly provide.* | Privacy-Preserving (Agent 57), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25). |
| **Agent 7** | The Schema-Inference Agent | *Discovers the structure of an unknown data source by sampling and probing.* | Document Layout (Agent 2), Database Query Synthesizer (Agent 35), API-Schema Adapter (Agent 31). |

### Detailed Pattern Breakdowns

### Agent 1 — The Multimodal Grounding Agent

> **Tagline:** *Aligns linguistic references to the visual or audio referents they describe.*

#### The Problem & Production Reality
A user says "the blue line that dips around March," and the agent has to attach that phrase to a specific element of a chart, a specific frame of a video, or a specific span of an audio file.

Or the user asks "what is the woman in the red coat looking at?" against an image with three people, and the agent has to bind "the woman in the red coat" to a particular detection, then bind "looking at" to her gaze vector, then ground that gaze vector to whatever object lies along it.

Or the agent has to attach a meeting action item to the precise speaker who accepted it, by name, in a multi-speaker audio recording.

The general problem is referential drift: between the moment the user says "the blue line" and the moment the agent has to do anything with that reference, the connection between the linguistic phrase and the actual visual or audio element can be lost. Without a structured grounding step, the agent ends up reasoning about its own paraphrase of the input rather than the input itself, which fails subtly and at scale.

#### Why Naïve Approaches Fail
There are three common ones. Here's what they are and why each fails:

"Send the image and the question to a multimodal model and hope." This works for direct questions ("what color is the car?") and fails for compound or referential questions ("what is the car the woman is looking at doing?"). The model produces plausible-sounding output that's not actually grounded. Verification is impossible because there's no intermediate representation to verify against.

"Run object detection, then text generation, separately." The output names objects but can't connect them to linguistic references. The user asks about "the woman in the red coat" and the agent has a person_3 detection but no mapping between them.

"Caption the image first, then reason over the caption." The caption is itself an interpretation. Anything the captioner didn't happen to mention is lost. The downstream reasoner is reasoning about the caption's vocabulary, not the image's content.

#### The Mechanism
A grounding agent maintains an explicit map between mentioned entities and identified regions in non-textual media, refreshing the map whenever the underlying media changes or the conversation introduces new references.

Here are the architectural moves:

Detection pass: Enumerate the referenceable elements in the medium — bounding boxes for objects in images, speaker diarization for audio, chart elements for visualizations.

Attachment pass: Bind noun phrases from the user's utterance to specific detected elements, with confidence scores. The output is an explicit mention → region map.

Re-attachment loop: When the user clarifies ("no, the other blue line"), update the map rather than starting from scratch.

Structured exposure: The grounding map is exposed as a typed observation to whatever policy sits above it, never as free text.

# perception/grounding.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class Region:
    """A referenceable element in some medium."""
    id: str                                      # stable within the medium
    medium: Literal["image", "audio", "video", "chart"]
    bbox: tuple[float, float, float, float] | None  # for visual media
    time_span: tuple[float, float] | None        # for audio/video
    label: str                                   # detector's class label
    embedding: list[float]                       # for similarity-based attachment

@dataclass
class GroundingMap:
    """Mention → region map with explicit confidence."""
    attachments: dict[str, list[tuple[Region, float]]] = field(default_factory=dict)
    
    def attach(self, mention: str, region: Region, confidence: float) -> None:
        self.attachments.setdefault(mention, []).append((region, confidence))
    
    def best_for(self, mention: str) -> Region | None:
        candidates = self.attachments.get(mention, [])
        if not candidates:
            return None
        return max(candidates, key=lambda rc: rc[1])[0]
    
    def confidence_of(self, mention: str) -> float:
        candidates = self.attachments.get(mention, [])
        return max((c for _, c in candidates), default=0.0)


class MultimodalGroundingAgent:
    def __init__(self, detector, attacher, *, confidence_threshold: float = 0.6):
        self.detector = detector              # runs detection on the medium
        self.attacher = attacher              # binds mentions to detections
        self.threshold = confidence_threshold
    
    def ground(self, medium: bytes, utterance: str) -> GroundingMap:
        regions = self.detector.detect(medium)        # 1. Detection pass
        mentions = extract_referential_mentions(utterance)  # noun phrases
        m = GroundingMap()
        for mention in mentions:
            candidates = self.attacher.match(mention, regions)  # 2. Attachment pass
            for region, conf in candidates:
                m.attach(mention, region, conf)
        return m
    
    def update(self, prior: GroundingMap, clarification: str,
               medium: bytes) -> GroundingMap:
        # 3. Re-attachment loop. Carry over high-confidence attachments;
        # rerun the rest against the new utterance.
        new = GroundingMap()
        for mention, atts in prior.attachments.items():
            best = max(atts, key=lambda rc: rc[1], default=None)
            if best and best[1] > 0.9:                 # stable attachment
                new.attachments[mention] = [best]
        return self.ground(medium, clarification) | new   # union semantics

#### Trade-offs and Alternatives
Grounding is expensive. It adds a detection pass and an attachment pass before any reasoning happens.

For one-shot questions over single images where compound references are rare, the cost isn't justified, just send the image and the question to a multimodal model.

The pattern earns its cost when the medium is referenced multiple times in a conversation, when the user is likely to use compound references, or when downstream provenance is required.

A simpler alternative is named-entity annotation: have the model produce its output with explicit references to entities by ID rather than by description, which avoids re-grounding on every reference. This works when the medium and entities are stable. The full Multimodal Grounding pattern is what you need when either changes.

#### Production Failure Modes
Stale grounding: The medium changes (user scrolls a video forward or re-uploads a corrected chart) and the grounding map points to regions that no longer exist. Mitigate by invalidating the map on medium change and re-grounding lazily on next reference.

Confidence calibration drift: The attacher's confidence scores stop being calibrated against actual binding accuracy. Detect by sampling: log resolved bindings and have an evaluator periodically score them. If confidence and accuracy diverge, recalibrate.

Mention parser misses compound mentions: "The taller man's left shoe" is parsed as a single noun phrase but should be a chain of attachments. Mitigate by parsing into a head-modifier dependency tree and grounding the head first, then the modifier.

#### Case Study
A meeting-summary agent at a mid-sized professional-services firm attaches every action item it extracts to the speaker who accepted it and the timestamp where the acceptance occurred, surfaced in the summary as a clickable transcript link. The grounding agent runs diarization, detects "I'll own that" / "I can take that" speech-act patterns, attaches the linguistic action ("write the proposal draft") to the speaker who took it, and binds the attachment to a specific time-span.

Before the grounding agent was deployed, the firm's existing meeting tool produced action items as unattributed bullet points. The resulting accountability gap was a known product weakness. After deployment, the action-item completion rate measured at one-week follow-up improved from 41% to 67%.

**Composition:** Pairs with: Visual Question Decomposition (Agent 5), Provenance Tracker (Agent 55), Document Layout (Agent 2).

---

### Agent 2 — The Document Layout Agent

> **Tagline:** *Turns a PDF or scanned image into a typed tree of semantic regions.*

#### The Problem & Production Reality
Most enterprise agent work begins with a document the agent didn't generate. The native form — pages of mixed text, tables, figures, headers, footnotes, stamps, signatures, multi-column layouts, footers that change mid-document, tables that span pages — is unusable as a context input.

Pasting the OCR output into a prompt gets the agent to produce something, but the output is bad in subtle ways: it treats footers as content, it loses table structure, it merges columns, it conflates section headings with body text.

The general problem is that a document is not a string. It's a tree of typed regions with explicit spatial and semantic relationships. Pretending it is a string throws away the structure the downstream policy needs to be reliable.

#### Why Naïve Approaches Fail
"Just run OCR and concatenate the text." Loses table structure, loses multi-column ordering, conflates headers with body, includes irrelevant marginalia, and produces output whose meaning depends on the OCR engine's ordering heuristics rather than on the document's actual structure.

"Send the page images directly to a vision-language model." Works for single-page documents and small batches, but costs explode on real corpora. The model also makes its own (often wrong) decisions about what to extract. Without a structured intermediate representation, you can't audit or verify.

"Use a generic PDF library." PDFs aren't a documented structured format. They're a layout-instruction language. Two PDFs that look identical can have wildly different internal structures, and most libraries produce output that's approximately the text in approximately the order it was typeset.

#### The Mechanism
The layout agent runs a document through a layout-detection model, segments it into typed regions (heading, paragraph, table-cell, figure-caption, signature-block, footer, header), runs OCR per region with confidence-aware re-runs on low-confidence regions. It then reconstructs tables as row-and-column structures, links continued headers and tables across pages, and emits a hierarchical region graph that downstream patterns can navigate.

The output is a tree, not a flat text blob. The tree preserves spatial relationships that pure OCR throws away (a table cell knows it is in column 3, row 5, of the table titled "Q2 Revenue by Region"). Every region carries its source bounding box and page number, so downstream provenance can point at the exact pixels.

# perception/document_layout.py
from dataclasses import dataclass, field
from typing import Literal

RegionType = Literal[
    "heading", "subheading", "paragraph", "table", "table_cell",
    "figure", "figure_caption", "signature", "stamp",
    "header", "footer", "page_number", "footnote"
]

@dataclass
class DocumentRegion:
    id: str
    type: RegionType
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    ocr_confidence: float
    children: list["DocumentRegion"] = field(default_factory=list)
    parent_id: str | None = None
    # Table-specific
    table_row: int | None = None
    table_col: int | None = None
    table_header: bool = False

@dataclass
class DocumentTree:
    document_id: str
    pages: int
    root: DocumentRegion       # synthetic root containing top-level regions
    
    def regions_of_type(self, t: RegionType) -> list[DocumentRegion]:
        out = []
        def walk(r):
            if r.type == t:
                out.append(r)
            for c in r.children:
                walk(c)
        walk(self.root)
        return out
    
    def find_by_text(self, query: str) -> list[DocumentRegion]:
        return [r for r in self._flat() if query in r.text]


class DocumentLayoutAgent:
    def __init__(self, layout_detector, ocr, table_reconstructor,
                 *, low_conf_threshold: float = 0.7):
        self.layout = layout_detector
        self.ocr = ocr
        self.tables = table_reconstructor
        self.low_conf = low_conf_threshold
    
    def parse(self, pdf_bytes: bytes) -> DocumentTree:
        pages = self._rasterize(pdf_bytes)
        all_regions = []
        for page_num, page_img in enumerate(pages):
            regions = self.layout.detect(page_img)           # 1. Layout detection
            for region in regions:
                text, conf = self.ocr.read(page_img, region.bbox)  # 2. OCR
                if conf < self.low_conf:
                    # Re-run with a higher-quality OCR setting
                    text, conf = self.ocr.read(page_img, region.bbox, mode="quality")
                region.text = text
                region.ocr_confidence = conf
                if region.type == "table":
                    region.children = self.tables.reconstruct(  # 3. Table reconstruction
                        page_img, region.bbox)
            all_regions.append((page_num, regions))
        
        root = self._build_tree(all_regions)                 # 4. Cross-page linking
        return DocumentTree(
            document_id=self._hash(pdf_bytes),
            pages=len(pages),
            root=root,
        )
    
    def _build_tree(self, regions_by_page):
        """Cross-page linking: continued tables, repeated headers, etc."""
        root = DocumentRegion(id="root", type="paragraph", page=-1,
                              bbox=(0,0,0,0), text="", ocr_confidence=1.0)
        # Group headings into sections; link continued tables across pages.
        current_section = root
        for page_num, regions in regions_by_page:
            for r in regions:
                if r.type in ("header", "footer", "page_number"):
                    continue  # drop chrome
                if r.type == "heading":
                    current_section = r
                    root.children.append(r)
                else:
                    r.parent_id = current_section.id
                    current_section.children.append(r)
        return root

#### Trade-offs and Alternatives
This pattern is expensive. A real layout-detection model plus OCR plus table reconstruction is ten to a hundred times the cost of plain OCR.

The cost is justified for documents that flow downstream into agents that need structure: anything that needs to cite a specific table cell, know whether a phrase is in a heading or a body paragraph, or ignore footers.

For one-shot extractions over simple documents, plain OCR (or even direct vision-language extraction) is fine. The pattern earns its cost when documents flow into multiple downstream consumers, the same document is queried repeatedly, or provenance to specific regions is required.

#### Production Failure Modes
Layout-detector bias: Layout detectors trained on academic papers misclassify business documents (treats a sidebar as a footnote, mis-segments multi-column invoices). Detect by sampling outputs and reviewing against ground truth, and mitigate by training a layout head on documents from your actual distribution.

OCR-confidence calibration: Modern OCR engines often report high confidence on text that's wrong because the input is unusual. Mitigate by running a second, different OCR engine on a sample and comparing. Significant disagreement is a flag.

Table reconstruction degeneracy: Tables with merged cells, nested headers, or rotated text break most reconstructors. Mitigate by detecting non-rectangular tables and falling back to per-cell extraction with explicit "unstructured" flagging downstream.

Cross-page linking failure: Tables continued across page breaks are linked as separate tables. The resulting downstream queries return only half the data. Mitigate by linking on table-title repetition and column-header signature.

#### Case Study
An underwriting workflow at a specialty insurer ingests submission packets. It's typically forty pages of mixed loss runs, schedules, broker memos, and supplementary attachments. This produces a structured submission record without a human in the loop until exception.

The Document Layout Agent emits a region tree per submission. Downstream agents (a Schema-Inference Agent over the loss runs, a Symbolic-Neural Bridge translating broker narratives into structured exposure summaries, a Provenance Tracker attaching every entry in the final record back to its source region) compose into a workflow that handled 73% of submissions end-to-end after six months of tuning, with a measured one-shot accuracy on extracted fields of 96% measured against expert-reviewed ground truth.

**Composition:** Pairs with: Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Multimodal Grounding (Agent 1).

---

### Agent 3 — The Temporal Sensor-Fusion Agent

> **Tagline:** *Aligns asynchronous streams into a single time-indexed percept.*

#### The Problem & Production Reality
When an agent's inputs come from multiple streams arriving at different rates (like a webhook here, a poll there, and a websocket feed elsewhere), the policy above will misbehave unless something has already normalized them onto a single timeline. The policy ends up reasoning about events as if their arrival order were their occurrence order, which is sometimes true, often wrong, and impossible to debug after the fact.

The general problem is clock skew at the input boundary. Each stream has its own clock, its own latency, its own retry semantics, and its own ordering guarantees. A single timeline has to be constructed from them, and the construction is non-trivial.

#### Why Naïve Approaches Fail
"Just process events in arrival order." This works until two streams contradict each other and the resolution depends on which arrived first. The resolution flips arbitrarily on retries.

"Sort by event timestamp from the source." The timestamps from different sources are drifted against each other (sometimes by minutes, in poorly-managed systems by hours). You get an ordering that looks plausible and is wrong on edge cases that matter.

"Pick one stream as ground truth and align the others to it." This works for two streams and breaks for three.

#### The Mechanism
The temporal sensor-fusion agent buffers incoming events, resolves their clock skew using shared landmark events, emits time-windowed percepts at a regular cadence, and handles back-pressure when a stream stalls.

# perception/sensor_fusion.py
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

@dataclass
class StreamEvent:
    stream_id: str
    source_timestamp: float       # the stream's own clock
    received_at: float            # local monotonic
    payload: dict
    landmark_id: str | None = None  # for skew estimation

@dataclass
class FusedObservation:
    window_start: float           # fused-clock time
    window_end: float
    events_by_stream: dict[str, list[StreamEvent]]
    skew_estimates: dict[str, float]  # per-stream offset to fused clock

class TemporalSensorFusionAgent:
    def __init__(self, streams: list[str], window_seconds: float = 1.0):
        self.streams = streams
        self.window = window_seconds
        self.buffers: dict[str, list[StreamEvent]] = defaultdict(list)
        self.skew: dict[str, float] = {s: 0.0 for s in streams}
        self.landmarks: dict[str, list[tuple[str, float]]] = defaultdict(list)
    
    def ingest(self, event: StreamEvent) -> None:
        self.buffers[event.stream_id].append(event)
        if event.landmark_id:
            self.landmarks[event.landmark_id].append(
                (event.stream_id, event.source_timestamp))
            self._update_skew()
    
    def _update_skew(self) -> None:
        """Estimate per-stream offset using shared landmark events."""
        for landmark_id, observations in self.landmarks.items():
            if len({s for s, _ in observations}) < 2:
                continue
            mean_ts = sum(ts for _, ts in observations) / len(observations)
            for stream, ts in observations:
                # Exponential moving average of skew
                old = self.skew[stream]
                self.skew[stream] = 0.9 * old + 0.1 * (ts - mean_ts)
    
    def emit(self, now: float) -> FusedObservation | None:
        """Emit a window if all streams have caught up to now - window."""
        window_end = now - self.window
        if not all(self._caught_up(s, window_end) for s in self.streams):
            return None
        events_by_stream = {}
        for s in self.streams:
            keep, drain = [], []
            for e in self.buffers[s]:
                fused_ts = e.source_timestamp - self.skew[s]
                if fused_ts < window_end:
                    drain.append(e)
                else:
                    keep.append(e)
            self.buffers[s] = keep
            events_by_stream[s] = sorted(drain, key=lambda e: e.source_timestamp - self.skew[e.stream_id])
        return FusedObservation(
            window_start=window_end - self.window,
            window_end=window_end,
            events_by_stream=events_by_stream,
            skew_estimates=dict(self.skew),
        )
    
    def _caught_up(self, stream: str, window_end: float) -> bool:
        # Has the stream produced any event past window_end? If yes, caught up.
        return any(
            (e.source_timestamp - self.skew[stream]) > window_end
            for e in self.buffers[stream]
        ) or self._stream_marked_idle(stream)

#### Trade-offs and Alternatives
Fusion adds latency proportional to the window size. For agents where freshness matters more than ordering correctness (a near-realtime alerter), shrink the window or accept partial windows.

For agents where ordering correctness dominates (anything that produces a decision binding multiple streams), grow the window or refuse to emit until all streams have caught up.

A simpler alternative is eventual fusion: buffer everything for a long window (minutes or hours), sort once, and reason over the sorted set. This is appropriate for batch agents and inappropriate for any agent that has to respond in seconds.

#### Production Failure Modes
Stuck streams: One stream stalls and the window never closes. Mitigate with a per-stream liveness check and an explicit "stream-idle" marker so the fuser can proceed without it. Surface the missing stream to the downstream policy.

Skew estimate drift: Landmark events become rare or noisy, and the skew estimate diverges from reality. Detect by monitoring the variance of skew over time. Trigger a recalibration when variance exceeds a threshold.

Out-of-order arrival within a stream: Most stream interfaces eventually deliver events out of order despite their stated guarantees. Mitigate with a per-stream re-sort buffer with its own (shorter) window.

#### Case Study
A trading-floor support agent at a mid-sized broker fuses Bloomberg headlines, an internal order-management feed, and a desk-side Slack channel into per-minute situation reports for desk heads.

The fusion window is sixty seconds. Landmarks include market-open and market-close events shared across all three streams.

The downstream policy (an Anomaly-Spotter, Agent 4) reads the fused windows and surfaces anomalous combinations: a Slack mention of a counterparty paired with an OMS rejection on the same counterparty within the window, or a Bloomberg headline naming a sector paired with an unusual concentration of new orders in that sector. The fused-window approach reduced false-positive alerts by 60% compared to per-stream alerting.

**Composition:** Pairs with: Ambient Context (Agent 6), Anomaly Spotter (Agent 4), Drift Detector (Agent 59).

---

### Agent 4 — The Anomaly-Spotter Agent

> **Tagline:** *Surfaces deviations from the expected pattern in a stream of observations.*

#### The Problem & Production Reality
An agent's job is sometimes not to classify, label, or explain anomalies — those are downstream tasks. Its job is to decide which slices of incoming data are worth waking another agent up for.

The naïve "alert on every change" path produces an alert volume that destroys the value of alerting altogether. The naïve "alert only on hardcoded thresholds" path misses everything except the failure modes the engineer thought to encode.

The general problem is calibrated novelty detection: identifying observations that are interesting precisely because they're unexpected, where "unexpected" is defined against a learned baseline rather than a hand-set rule.

#### Why Naïve Approaches Fail
"Static thresholds." Catch the failures you encoded, miss everything else. Require a human to update them every time the baseline shifts.

"Alert on every X-sigma deviation from the moving average." Generates alerts every time the variance changes (which is constantly in real systems), drowns the operator.

"Use a generic anomaly-detection library." Most are tuned for industrial sensor data with very different statistical properties than business signals. Out-of-the-box false-positive rates are typically 100×+ what's tolerable.

#### The Mechanism
The anomaly-spotter maintains a model of the expected distribution of each observed signal, updates the model online, and emits an anomaly observation whenever the live signal deviates by a threshold the operator can tune.

# perception/anomaly_spotter.py
from dataclasses import dataclass
import math, time

@dataclass
class Anomaly:
    signal: str
    value: float
    expected_range: tuple[float, float]
    z_score: float
    window_start: float
    window_end: float
    severity: str          # "info" | "warn" | "critical"

class OnlineDistribution:
    """Welford's online mean/variance."""
    def __init__(self, alpha: float = 0.01):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.alpha = alpha
    
    def update(self, x: float) -> None:
        # Exponential moving statistics for non-stationary signals.
        if self.n == 0:
            self.mean = x
            self.n = 1
            return
        delta = x - self.mean
        self.mean += self.alpha * delta
        self.m2 = (1 - self.alpha) * self.m2 + self.alpha * delta * delta
        self.n += 1
    
    @property
    def sigma(self) -> float:
        return math.sqrt(self.m2)

class AnomalySpotterAgent:
    def __init__(self, signals: list[str], warn_z: float = 3.0,
                 critical_z: float = 5.0, dedup_window_s: float = 300):
        self.dists = {s: OnlineDistribution() for s in signals}
        self.warn_z = warn_z
        self.critical_z = critical_z
        self.dedup_window = dedup_window_s
        self._last_alert: dict[str, float] = {}
    
    def observe(self, signal: str, value: float, t: float = None) -> Anomaly | None:
        t = t or time.time()
        d = self.dists[signal]
        # Compute z BEFORE update so the current point doesn't dilute its own deviation.
        z = (value - d.mean) / d.sigma if d.sigma > 0 and d.n > 30 else 0.0
        d.update(value)
        if abs(z) < self.warn_z:
            return None
        # Hysteresis / deduplication
        last = self._last_alert.get(signal, 0)
        if t - last < self.dedup_window:
            return None
        severity = "critical" if abs(z) >= self.critical_z else "warn"
        self._last_alert[signal] = t
        return Anomaly(
            signal=signal,
            value=value,
            expected_range=(d.mean - 2 * d.sigma, d.mean + 2 * d.sigma),
            z_score=z,
            window_start=t - 60,
            window_end=t,
            severity=severity,
        )

#### Trade-offs and Alternatives
Online statistical detectors are cheap and work for univariate signals with stable variance. They fail on signals with strong seasonality (a daily signal will look anomalous every Monday morning until the model has seen enough Mondays) and on multivariate anomalies (each signal looks normal but their combination is unusual).

For seasonal signals, use a forecasting model (Prophet, Holt-Winters, lightweight LSTM) as the baseline rather than a moving mean. For multivariate anomalies, project to a learned latent space and detect deviations there (an autoencoder-based detector, or an Isolation Forest). The pattern remains the same. Only the baseline implementation changes.

#### Production Failure Modes
Cold-start: The detector hasn't seen enough data to have a meaningful baseline, so everything looks anomalous. Mitigate by requiring a minimum sample count before the detector emits any alarms.

Quiet failure: The signal stops arriving entirely, and the detector cheerfully reports nothing wrong. Mitigate by monitoring arrival cadence per signal as a meta-signal in the same detector.

Concept drift: The baseline shifts permanently (a system was upgraded, user behavior changed). The detector chases the shift but mid-shift produces a wave of false positives. Mitigate by detecting concept drift explicitly (Agent 59) and pausing alerts during the recalibration window.

#### Case Study
A SaaS reliability agent at an enterprise software vendor watches latency, error rate, and saturation per service across roughly four hundred internal services.

Each service gets its own Anomaly-Spotter instance with shared thresholds. When a signal deviates, a Reflection Agent (Agent 47) is invoked to draft an incident summary against the relevant trace store before a human has noticed.

The pattern moves the detection time from "user complaint" (median twenty-three minutes) to "automated alarm" (median forty-seven seconds), and reduces false-positive incidents by 80% compared to the previous static-threshold system.

**Composition:** Pairs with: Drift Detector (Agent 59), Reflection (Agent 47), Temporal Sensor-Fusion (Agent 3).

---

### Agent 5 — The Visual Question Decomposition Agent

> **Tagline:** *Breaks a complex visual query into sub-queries answerable by simpler perception calls.*

#### The Problem & Production Reality
A user asks "How does revenue compare to forecast across the three product lines whose churn rose in Q3?" against a dashboard image.

A naïve vision-language model attempts the whole thing in one pass and either fabricates or gives up. The query is compound: it requires reading one chart, filtering its results, then reading a different chart with the filter applied. Single-pass perception can't do compound queries reliably.

The general problem is compound visual reasoning: a question that requires sequencing multiple perception steps, each of which is feasible alone, but whose combination exceeds what a single forward pass can produce reliably.

#### Why Naïve Approaches Fail
"Send the dashboard and the question to a vision-language model." The model produces a confident answer that's wrong in subtle ways. Verification requires re-reading the dashboard, which defeats the purpose.

"OCR everything, then run text reasoning." Loses spatial structure. The model can't tell which numbers belong to which chart.

"Just ask the model to look at the data instead of the chart." Often impossible. The underlying data isn't accessible, or the dashboard is the consumer-facing surface.

#### The Mechanism
The decomposition agent recognizes the compound structure of the query, breaks it into a sequence of single-step perception calls, runs them in sequence, and assembles the result with explicit citations.

# perception/visual_decomposition.py
from dataclasses import dataclass, field

@dataclass
class SubQuery:
    id: str
    natural_language: str           # what the sub-query asks
    target_region: str | None       # which part of the image (None = whole)
    depends_on: list[str] = field(default_factory=list)  # other SubQuery IDs
    output_type: str = "text"       # "number" | "list" | "text" | "categorical"

@dataclass
class SubQueryResult:
    query_id: str
    answer: object
    source_region: tuple[float, float, float, float]
    confidence: float

class VisualQuestionDecompositionAgent:
    def __init__(self, planner_llm, perception_llm):
        self.planner = planner_llm           # decomposes; does not see image
        self.perceiver = perception_llm      # answers single sub-queries against image
    
    def answer(self, image: bytes, question: str) -> dict:
        plan = self._plan(question)                       # 1. Parse into sub-queries
        results: dict[str, SubQueryResult] = {}
        for q in self._topologically_sorted(plan):        # 2. Execute in dependency order
            context = {dep: results[dep].answer for dep in q.depends_on}
            sub_q = self._materialize(q, context)
            results[q.id] = self.perceiver.ask(image, sub_q, region=q.target_region)
        return self._assemble(question, plan, results)    # 3. Compose final answer
    
    def _plan(self, question: str) -> list[SubQuery]:
        plan_response = self.planner.call(
            messages=[
                {"role": "system", "content": DECOMPOSITION_PROMPT},
                {"role": "user", "content": question}
            ],
            schema=DECOMPOSITION_SCHEMA,
        )
        return [SubQuery(**q) for q in plan_response["sub_queries"]]
    
    def _topologically_sorted(self, plan: list[SubQuery]) -> list[SubQuery]:
        # Standard topo sort
        ...
    
    def _materialize(self, q: SubQuery, context: dict) -> str:
        # Substitute dependency results into the sub-query's natural language.
        text = q.natural_language
        for dep_id, value in context.items():
            text = text.replace(f"${dep_id}", str(value))
        return text
    
    def _assemble(self, question, plan, results) -> dict:
        # The composer LLM call: produces the final answer with citations.
        return self.planner.call(
            messages=[
                {"role": "system", "content": COMPOSITION_PROMPT},
                {"role": "user", "content": format_assembly_input(question, plan, results)}
            ],
            schema=COMPOSITION_SCHEMA,
        )

DECOMPOSITION_PROMPT = """\
Decompose the user's compound visual question into a list of sub-queries.
Each sub-query must be answerable by a single look at one region of the image.
Sub-queries may depend on the results of earlier sub-queries (reference them
in natural language as $sub_query_id).

Output JSON: {"sub_queries": [{"id", "natural_language", "target_region",
                               "depends_on", "output_type"}]}
"""

#### Trade-offs and Alternatives
Decomposition multiplies the number of model calls per question, increasing latency and cost. The cost is justified when compound questions are common and when single-pass accuracy is materially below decomposed accuracy on a measured evaluation set. For dashboards where users ask simple "what is X" questions, the cost isn't justified.

An alternative for stable dashboards is to pre-extract structured data once and answer all questions against the extracted data. The decomposition pattern is what you need when the dashboard is dynamic, when the data behind it is not accessible, or when one-off questions appear at low volume per dashboard configuration.

#### Production Failure Modes
Plan-execution mismatch: The decomposition produces a plan whose sub-queries can't actually be answered against the image (mentions a chart that doesn't exist). Mitigate by including a feasibility check between planning and execution, falling back to single-pass or escalating to a human.

Dependency-result drift: A sub-query's answer is slightly wrong, and downstream sub-queries that depend on it compound the error. Mitigate by recording confidence per sub-query and refusing to compose answers when any dependency confidence is below a threshold.

Composer fabrication: The composer LLM, asked to combine sub-query results, invents claims not supported by the sub-results. Mitigate by structuring the composition prompt to forbid claims not traceable to a sub-query, and validating the final output against the sub-query results.

#### Case Study
An analytics co-pilot at a B2B SaaS vendor answers free-form questions over operational dashboards. Before the decomposition agent, single-pass vision-language accuracy on compound questions was 38% measured against expert-labeled ground truth. With decomposition the accuracy rose to 84%, at three times the cost per question and 1.6× the latency. The product team accepted the trade because the wrong-answer rate of the single-pass version was undermining trust in the dashboard itself.

**Composition:** Pairs with: Multimodal Grounding (Agent 1), Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55).

---

### Agent 6 — The Ambient Context Agent

> **Tagline:** *Passively integrates environmental signals the user didn't explicitly provide.*

#### The Problem & Production Reality
Every conversation an agent participates in is bracketed by context the user assumes is obvious: who they are, where they are, what time it is, what device they are on, what they were doing five minutes ago, and what is on their calendar in an hour.

An agent without ambient context has to ask for all of it ("what timezone are you in? what calendar are you using? what is your role?") which is both annoying and impossible: the user doesn't always know the answer in a form the agent can use.

The general problem is invisible context: the signals that condition every human interaction but that the agent doesn't have unless something makes them explicit. The pattern is what makes "ambient" assistants possible without bombarding the user with questions.

#### Why Naïve Approaches Fail
"Just dump everything into the prompt." Floods the context window, costs money, leaks information the user didn't intend to share, and exposes the agent to prompt-injection attacks via context fields.

"Ask the user when needed." Works once. Annoys forever.

"Use the user's profile." Captures stable preferences. Misses everything that changes (time, calendar, location, recent activity).

#### The Mechanism
An ambient context agent gathers signals on a continuous basis from permissioned surfaces, exposes them as a structured observation, refreshes them on a defined cadence rather than only at session start, and filters them through a privacy gate before they enter the prompt.

# perception/ambient_context.py
from dataclasses import dataclass, field
from typing import Callable
import time

@dataclass
class ContextField:
    name: str
    value: object
    source: str
    fetched_at: float
    ttl_seconds: float
    privacy_class: str          # "public" | "user_visible" | "sensitive"
    
    @property
    def fresh(self) -> bool:
        return time.time() - self.fetched_at < self.ttl_seconds

@dataclass
class AmbientContext:
    fields: dict[str, ContextField] = field(default_factory=dict)
    
    def get(self, name: str) -> object | None:
        f = self.fields.get(name)
        return f.value if (f and f.fresh) else None
    
    def to_prompt(self, privacy_max: str = "user_visible") -> dict:
        levels = {"public": 0, "user_visible": 1, "sensitive": 2}
        cutoff = levels[privacy_max]
        return {f.name: f.value for f in self.fields.values()
                if f.fresh and levels[f.privacy_class] <= cutoff}

class AmbientContextAgent:
    def __init__(self, readers: dict[str, Callable[[], ContextField]]):
        self.readers = readers
        self._cache = AmbientContext()
    
    def refresh(self, field_names: list[str] | None = None) -> AmbientContext:
        to_refresh = field_names or list(self.readers.keys())
        for name in to_refresh:
            f = self._cache.fields.get(name)
            if f and f.fresh:
                continue
            self._cache.fields[name] = self.readers[name]()
        return self._cache
    
    def snapshot(self) -> AmbientContext:
        self.refresh()
        return self._cache

# Reader registration with explicit scopes
def make_calendar_reader(user_id: str):
    def read() -> ContextField:
        events = calendar_api.upcoming(user_id, hours=2)
        return ContextField(
            name="next_event",
            value=events[0] if events else None,
            source="google_calendar",
            fetched_at=time.time(),
            ttl_seconds=60,
            privacy_class="user_visible",
        )
    return read

#### Trade-offs and Alternatives
Ambient context costs prompt tokens and creates a privacy surface. Both costs are real and should be managed deliberately.

Token cost is mitigated by including only fields the current task actually needs (the Working-Memory Manager, Agent 25, handles this). Privacy cost is mitigated by the privacy gate and by the principle that fields are read at the narrowest scope sufficient for the task.

For agents where the user-explicit prompt is unambiguous and self-contained ("what is the capital of France?"), ambient context is unnecessary overhead. The pattern earns its cost when the user's prompts assume context the agent doesn't have ("when does my next meeting start?"), which is essentially every personal-assistant scenario.

#### Production Failure Modes
Stale fields: A field's TTL is too long, and the value the agent uses is wrong. Mitigate by aggressive TTLs on fast-changing fields (calendar: minutes, location: seconds, current task: per-action).

Reader failure: A reader's source is down, so the field is unavailable. The agent should degrade gracefully (mark the field as missing in the snapshot rather than dropping it silently).

Privacy-class drift: A field originally classified as user_visible accumulates sensitive information over time (a calendar event that contains contact details for a sensitive deal). Mitigate by reclassifying fields based on their content, not only their schema.

Prompt-injection via context fields: A calendar event's title contains adversarial instructions, and the agent processes them as if from the user. Mitigate by treating all context fields as untrusted text (Section 4.5).

#### Case Study
A personal-assistant agent at a productivity vendor drafts replies to messages with implicit knowledge of the recipient's role, the user's calendar conflicts that day, and the user's writing register with that specific contact. The ambient-context layer reads from calendar, contacts, message history, and presence, with per-field TTLs ranging from thirty seconds to two hours.

The product's reply-acceptance rate climbed from 41% to 73% after the ambient-context layer was added. Nearly all the improvement came from the agent now knowing things the user had previously had to type into the prompt.

**Composition:** Pairs with: Privacy-Preserving (Agent 57), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25).

---

### Agent 7 — The Schema-Inference Agent

> **Tagline:** *Discovers the structure of an unknown data source by sampling and probing.*

#### The Problem & Production Reality
The agent is pointed at a new database, a new file, a new API, or a new event stream, and is asked to figure out what's in it. The user doesn't have a schema – the schema is what the user wants. Without an inference step, the only way forward is for a human to write a config — which doesn't scale across thousands of customers, hundreds of data sources, or fast-changing schemas.

The general problem is structure discovery at runtime: producing a usable model of an unknown data source from samples, with explicit confidence and explicit unknowns, in a form downstream patterns can rely on.

#### Why Naïve Approaches Fail
"Type-infer the first row." Wrong on most data. The first row is often atypical, has missing values, or has different types than the rest of the corpus.

"Ask an LLM to look at a sample and produce a schema." Often hallucinates fields that aren't there, misses fields that are, and produces output with no calibrated confidence.

"Use a generic schema-inference library." They're tuned for relational data and break on JSON with nested arrays, on CSVs with inconsistent delimiters, or on APIs whose responses vary by tenant.

#### The Mechanism
The schema-inference agent samples records strategically, hypothesizes a schema, validates the hypothesis against more records, refines, and emits a schema document with explicit uncertainty annotations.

# perception/schema_inference.py
from dataclasses import dataclass, field
from collections import Counter

@dataclass
class FieldSchema:
    name: str
    types: dict[str, int]              # observed type -> count
    nullable: bool
    examples: list                     # 3-5 representative values
    confidence: float                  # 0-1, based on consistency
    range: tuple | None = None          # for numeric / temporal fields
    enum_candidates: list | None = None # likely-categorical
    
    @property
    def dominant_type(self) -> str:
        return max(self.types.items(), key=lambda kv: kv[1])[0]

@dataclass
class InferredSchema:
    source_id: str
    sampled_records: int
    total_records_estimate: int | None
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)  # inferred FK candidates
    confidence: float = 0.0
    open_questions: list[str] = field(default_factory=list)

class SchemaInferenceAgent:
    def __init__(self, source_adapter, sample_target: int = 1000,
                 confidence_target: float = 0.9):
        self.source = source_adapter
        self.sample_target = sample_target
        self.target = confidence_target
    
    def infer(self) -> InferredSchema:
        schema = InferredSchema(
            source_id=self.source.id,
            sampled_records=0,
            total_records_estimate=self.source.estimate_size(),
        )
        # 1. Stratified sampling: head, tail, middle, plus random
        samples = self._stratified_sample()
        for record in samples:
            self._update_schema(schema, record)
        # 2. Confidence check; if too low, sample more strategically
        if schema.confidence < self.target:
            extra = self._sample_more(schema)
            for record in extra:
                self._update_schema(schema, record)
        # 3. Categorical detection
        for field_schema in schema.fields.values():
            if self._looks_categorical(field_schema):
                field_schema.enum_candidates = self._extract_enum(field_schema)
        # 4. Relationship inference
        schema.relationships = self._infer_relationships(schema, samples)
        return schema
    
    def _update_schema(self, schema: InferredSchema, record: dict) -> None:
        for k, v in record.items():
            fs = schema.fields.setdefault(k, FieldSchema(
                name=k, types=Counter(), nullable=False, examples=[], confidence=0))
            t = type(v).__name__ if v is not None else "null"
            fs.types[t] += 1
            if v is None:
                fs.nullable = True
            elif len(fs.examples) < 5:
                fs.examples.append(v)
        schema.sampled_records += 1
        self._update_confidence(schema)
    
    def _looks_categorical(self, fs: FieldSchema) -> bool:
        if fs.dominant_type != "str":
            return False
        unique_vals = len(set(fs.examples))
        return unique_vals < 20 and unique_vals < 0.1 * len(fs.examples)

#### Trade-offs and Alternatives
Schema inference is sampling-bound: precision improves with the number of samples but with diminishing returns.

For sources where a definitive schema exists elsewhere (a managed database with INFORMATION_SCHEMA, an OpenAPI document for an API, a Protobuf descriptor for a message stream), use the authoritative source and skip inference. Schema inference earns its keep when no authoritative source exists or when the authoritative source is stale/unreliable.

A common simplification: don't infer relationships at all. Field-level schemas are most of the value and relationship inference is brittle and easy to get wrong. Leave relationships to the downstream policy unless the use case explicitly requires them.

#### Production Failure Modes
Long-tail field surprise: A field appears in 0.5% of records with a different type than the inferred dominant one, and the downstream policy crashes on it. Mitigate by sampling the long tail explicitly and capturing rare-type variants in the schema.

Confidence overshoot: The inference reports high confidence on a field that varies across tenants. Mitigate by inferring per-tenant when the source supports it, and surface tenant-variance as an explicit field property otherwise.

Categorical false positive: A field has only twelve distinct values in the sample but unbounded values in the source. Mitigate by sampling more aggressively when categorical detection is sensitive to it.

#### Case Study
A data-onboarding workflow at a B2B vendor lets new customers connect a SQL database and receive a starter analytics dashboard inside a single session. The Schema-Inference Agent runs against the customer's connected database, samples up to ten thousand rows across tables, infers field schemas and likely relationships, and produces a schema document the downstream dashboard-generation agent consumes.

Before the schema-inference step, onboarding required a customer-success engineer to write a config per customer (median three days). After, the median onboarding time dropped to under twenty minutes self-serve, with 71% of customers reaching a dashboard without any human assist.

**Composition:** Pairs with: Document Layout (Agent 2), Database Query Synthesizer (Agent 35), API-Schema Adapter (Agent 31).

---

## Capability: Reasoning: Inferring Beyond the Given
Covers Agents 8 through 15.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 8** | The Chain-of-Thought Auditor Agent | *Verifies the validity of each step in a reasoning trace before the conclusion is acted on.* | Self-Consistency Voter (Agent 15), Reflection (Agent 47), Provenance Tracker (Agent 55). |
| **Agent 9** | The Counterfactual Reasoner Agent | *Runs "what-if" branches against the current state to surface alternatives.* | Constraint-Satisfaction (Agent 11), Probabilistic Belief Updater (Agent 14), Causal Graph Builder (Agent 12). |
| **Agent 10** | The Analogical Mapping Agent | *Finds structural parallels between a current problem and previously solved ones.* | Skill-Library Builder (Agent 48), Few-Shot Prompt Tuner (Agent 50), Semantic Memory Curator (Agent 24). |
| **Agent 11** | The Constraint-Satisfaction Agent | *Solves problems by progressively narrowing the feasible region.* | Symbolic-Neural Bridge (Agent 13), Resource-Aware Scheduler (Agent 21), Counterfactual Reasoner (Agent 9). |
| **Agent 12** | The Causal Graph Builder Agent | *Induces a causal structure from observational data and uses it for intervention reasoning.* | Counterfactual Reasoner (Agent 9), Probabilistic Belief Updater (Agent 14), Constraint-Satisfaction (Agent 11). |
| **Agent 13** | The Symbolic-Neural Bridge Agent | *Translates natural-language problems into formal expressions and back.* | Constraint-Satisfaction (Agent 11), Provenance Tracker (Agent 55), Counterfactual Reasoner (Agent 9). |
| **Agent 14** | The Probabilistic Belief Updater Agent | *Maintains and revises posterior beliefs over hypotheses as new evidence arrives.* | Active Learner (Agent 52), Drift Detector (Agent 59), Counterfactual Reasoner (Agent 9). |
| **Agent 15** | The Self-Consistency Voter Agent | *Runs N independent reasoning chains and aggregates them into a more reliable answer.* | Chain-of-Thought Auditor (Agent 8), Reflection (Agent 47), Debate Moderator (Agent 39). |

### Detailed Pattern Breakdowns

### Agent 8 — The Chain-of-Thought Auditor Agent

> **Tagline:** *Verifies the validity of each step in a reasoning trace before the conclusion is acted on.*

#### The Problem & Production Reality
A language model emits a reasoning chain. Some of the steps follow from the previous ones, and some do not. The chain ends with a confident conclusion. Without a verification step, the conclusion is acted on — and it's wrong, in roughly one in fifteen chains, in a way that the final answer's surface form doesn't reveal.

The general problem is local invalidity in plausible reasoning: a chain that reads coherently but contains a step that doesn't follow, where the model has filled in the apparent connection with vocabulary that sounds like reasoning but is not. The pattern is the difference between an agent that confidently completes a wrong derivation and one that catches itself.

#### Why Naïve Approaches Fail
"Ask the model to double-check its own reasoning." Self-evaluation in the same call as the reasoning is unreliable. The model has committed to the conclusion and finds reasons to justify it.

"Use a second pass of the same model in the same role." Better than (1), but the model evaluates the chain as a whole rather than step-by-step. It tends to grade lenient on chains it would have produced itself.

"Run the chain through a different model." Helps when the two models have uncorrelated failures, often doesn't.

#### The Mechanism
The auditor reads the chain step by step, asks whether each step is supported by what came before, and flags the first invalid step it finds. It doesn't produce its own reasoning, it grades the input one. The output isn't a pass/fail but a first-invalid-step pointer, which lets the calling system re-prompt from that point rather than restarting.

# reasoning/cot_auditor.py
from dataclasses import dataclass
from enum import Enum

class StepValidity(Enum):
    VALID = "valid"
    INVALID_FROM_PREMISES = "invalid_from_premises"
    UNSUPPORTED_FACT = "unsupported_fact"
    INVALID_INFERENCE = "invalid_inference"

@dataclass
class ChainStep:
    step_number: int
    premises_referenced: list[int]    # indices of earlier steps this depends on
    operation: str                    # "fact" | "inference" | "calculation" | "definition"
    statement: str
    cited_sources: list[str]          # for "fact" steps

@dataclass
class AuditResult:
    valid: bool
    first_invalid_step: int | None
    invalid_reason: StepValidity | None
    explanation: str
    suggested_revision_point: int | None   # step from which to re-prompt

class ChainOfThoughtAuditorAgent:
    def __init__(self, auditor_llm):
        self.llm = auditor_llm
    
    def audit(self, chain: list[ChainStep]) -> AuditResult:
        for step in chain:
            verdict = self._audit_step(step, prior_steps=chain[:step.step_number])
            if verdict != StepValidity.VALID:
                return AuditResult(
                    valid=False,
                    first_invalid_step=step.step_number,
                    invalid_reason=verdict,
                    explanation=self._explain(step, prior_steps=chain[:step.step_number]),
                    suggested_revision_point=max(0, step.step_number - 1),
                )
        return AuditResult(valid=True, first_invalid_step=None,
                           invalid_reason=None, explanation="",
                           suggested_revision_point=None)
    
    def _audit_step(self, step: ChainStep,
                    prior_steps: list[ChainStep]) -> StepValidity:
        if step.operation == "fact" and not step.cited_sources:
            return StepValidity.UNSUPPORTED_FACT
        result = self.llm.call(
            messages=[
                {"role": "system", "content": AUDITOR_PROMPT},
                {"role": "user", "content": format_audit_input(step, prior_steps)}
            ],
            schema={"type": "object", "properties": {
                "verdict": {"type": "string", "enum": [v.value for v in StepValidity]},
                "explanation": {"type": "string"}
            }, "required": ["verdict", "explanation"]}
        )
        return StepValidity(result["verdict"])

AUDITOR_PROMPT = """\
You evaluate a single step in a reasoning chain for local validity.
You see the step and ALL previous steps it might depend on.
Verdicts:
  - "valid": the step follows from premises and is well-formed.
  - "invalid_from_premises": premises cited do not support the step.
  - "unsupported_fact": step asserts a fact with no source.
  - "invalid_inference": logical/mathematical/causal error in the step itself.

You do NOT evaluate the final conclusion. You evaluate THIS step.
You are STRICT. A step that is "plausible" but not supported is invalid.
"""

#### Trade-offs and Alternatives
Auditing doubles (or more) the cost of producing a reasoning chain. The cost is justified when the cost of a wrong conclusion exceeds the cost of the audit by a significant multiplier. In medical, legal, financial, or operational contexts, this is essentially always true. For low-stakes chains (a model summarizing a casual email), auditing is overhead.

An alternative for very high-stakes chains is structured proof construction, where the model is required to produce its reasoning in a formal system (a proof assistant, a Datalog database, a SAT encoding) whose validity is mechanically checked. This is the topic of the Symbolic-Neural Bridge (Agent 13): the auditor is the lighter-weight version for chains that can't easily be formalized.

#### Production Failure Modes
Auditor lenient on its own training data: The auditor was trained on similar chains and is reluctant to call them invalid. Mitigate by using a different model family for the auditor than for the reasoner, or by training the auditor on a deliberately adversarial dataset.

Premise reference errors: Steps reference premises by number but the chain has been edited or renumbered. Mitigate by normalizing references and validating them before the audit runs.

First-invalid-step pointer instability: The auditor flags different first-invalid steps on re-runs. Mitigate with self-consistency voting (Agent 15) on the auditor itself.

#### Case Study
A legal-research agent at a mid-sized firm gates every answer through a Chain-of-Thought Auditor before the answer reaches the attorney. In a six-month measurement window, the auditor caught roughly one in twelve chains as locally invalid (8.3%), with a measured false-positive rate of 2.1% (chains the auditor flagged but expert reviewers ruled valid).

The net effect: invalid-conclusion rate reaching the attorney dropped from approximately 8% in the unaudited baseline to 0.5% with the auditor in place, at a 2.4× cost per answer.

**Composition:** Pairs with: Self-Consistency Voter (Agent 15), Reflection (Agent 47), Provenance Tracker (Agent 55).

---

### Agent 9 — The Counterfactual Reasoner Agent

> **Tagline:** *Runs "what-if" branches against the current state to surface alternatives.*

#### The Problem & Production Reality
The user has a plan, a draft, a decision, and a code change. The user is about to commit. Without a counterfactual analysis, the commit goes ahead...and is rolled back two days later, when a load-bearing assumption turned out to be wrong.

The general failure mode the pattern addresses is confirmation-bias collapse: single-chain reasoning that defends the first plausible position the model produced, leaving no surface for the user to inspect alternatives.

#### Why Naïve Approaches Fail
"Ask the model to consider alternatives." The model produces a perfunctory list, then returns to defending its original answer.

"Generate three options at the start, pick the best." Treats the alternatives as candidates to choose from, not as branches whose consequences are worth tracing. The "options" are usually variations of the same answer.

"Run the analysis twice with different phrasings." Catches stochastic noise but misses systematic bias.

#### The Mechanism
The counterfactual agent identifies the load-bearing variable in the user's situation, generates one or more counterfactual states with the variable flipped, propagates the flip through whatever model of the world the agent has, and produces a comparison output. The agent doesn't advocate, it enumerates.

# reasoning/counterfactual.py
from dataclasses import dataclass, field

@dataclass
class CounterfactualBranch:
    name: str
    variable_flipped: str
    counterfactual_value: object
    propagation_steps: list[str]
    final_state: dict
    likelihood_estimate: float       # how likely this branch is in reality
    severity_if_realized: str        # "low" | "medium" | "high"

@dataclass
class CounterfactualAnalysis:
    original_state: dict
    load_bearing_variables: list[str]
    branches: list[CounterfactualBranch]
    recommendation: str              # "proceed" | "hedge" | "reconsider"

class CounterfactualReasonerAgent:
    def __init__(self, identifier_llm, propagator_llm, world_model=None):
        self.identifier = identifier_llm
        self.propagator = propagator_llm
        self.world_model = world_model    # optional structured model for propagation
    
    def analyze(self, state: dict, decision: str) -> CounterfactualAnalysis:
        # 1. Identify load-bearing variables
        load_bearing = self._identify_load_bearing(state, decision)
        # 2. Generate counterfactual values for each
        branches = []
        for var in load_bearing:
            for cf_value in self._counterfactual_values(state, var):
                branch = self._propagate(state, var, cf_value, decision)
                branches.append(branch)
        # 3. Recommend based on severity * likelihood across branches
        return CounterfactualAnalysis(
            original_state=state,
            load_bearing_variables=load_bearing,
            branches=branches,
            recommendation=self._recommend(branches),
        )
    
    def _identify_load_bearing(self, state: dict, decision: str) -> list[str]:
        """Which variables, if flipped, would change the decision?"""
        result = self.identifier.call(
            messages=[
                {"role": "system", "content": LOAD_BEARING_PROMPT},
                {"role": "user", "content": f"State: {state}\nDecision: {decision}"}
            ],
            schema={"type": "object", "properties": {
                "load_bearing_variables": {"type": "array", "items": {"type": "string"}}
            }}
        )
        return result["load_bearing_variables"]
    
    def _propagate(self, state, var, cf_value, decision) -> CounterfactualBranch:
        cf_state = {**state, var: cf_value}
        if self.world_model:
            return self.world_model.propagate(state, cf_state, decision)
        # LLM-based propagation as fallback
        result = self.propagator.call(
            messages=[
                {"role": "system", "content": PROPAGATION_PROMPT},
                {"role": "user", "content": format_propagation_input(state, cf_state, decision)}
            ],
            schema=PROPAGATION_SCHEMA,
        )
        return CounterfactualBranch(**result)

#### Trade-offs and Alternatives
Counterfactual reasoning is expensive (typically three to ten times the cost of a single forward pass) because each branch requires propagation through whatever world model is available.

The cost is justified for decisions where reversibility is low and consequence is high (investments, hiring, regulatory positions, irreversible production changes). For decisions that are easily undone, the pattern is overhead.

A lighter-weight alternative is adversarial prompting: running the same reasoning with a "now argue the opposite" instruction. This catches the most blatant cases. The full counterfactual pattern is what you need when the alternatives matter enough to be propagated, not just stated.

#### Production Failure Modes
Insufficient counterfactual diversity: The branches are minor variations of the original. Mitigate by requiring branches to flip categorically different variables, and by sampling counterfactual values from a deliberately wide distribution.

Propagator over-confidence: The propagator declares a counterfactual "would have no effect" because it can't easily trace second-order consequences. Mitigate by requiring the propagator to enumerate at least three downstream effects per branch, with explicit "I can't determine" allowed.

Likelihood-estimate fabrication: The likelihood estimates per branch are not calibrated. The recommendation reflects the model's vibes more than any evidence. Mitigate by deriving likelihoods from a separately-calibrated belief model (Agent 14) rather than asking the propagator to estimate them.

#### Case Study
An investment-committee agent at a long-short equity manager runs every recommended position through three counterfactuals: rate up two hundred basis points, sector down ten percent, and a named competitor doubles share. They attach the survivability of the position under each to the recommendation memo. Positions whose recommendation reverses under any of the three counterfactuals get a "hedge" flag and are sized down by half by default.

The pattern was credited with a 1.8 percentage point improvement in the fund's risk-adjusted return over the eighteen months after introduction, primarily by sizing down positions that would have lost catastrophically when the relevant counterfactual was realized.

**Composition:** Pairs with: Constraint-Satisfaction (Agent 11), Probabilistic Belief Updater (Agent 14), Causal Graph Builder (Agent 12).

---

### Agent 10 — The Analogical Mapping Agent

> **Tagline:** *Finds structural parallels between a current problem and previously solved ones.*

#### The Problem & Production Reality
Engineers solve problems by reference. The third time you write a rate-limiter you don't derive it, you remember which of the previous two designs to copy. An agent without analogical retrieval re-derives every problem from scratch, which is wasteful, slow, and produces worse solutions than the team's existing repertoire would.

The general problem is same-structure-different-surface retrieval: finding the prior case that maps to the current case at the level of mechanism, even when the surface vocabulary is different. Embedding-based retrieval (the default in most RAG systems) gives you surface similarity. Analogical mapping gives you structural similarity.

#### Why Naïve Approaches Fail
"Embed the problem statement and retrieve nearest neighbors." Finds cases with similar words, but misses cases with the same structure but different vocabulary. A "thundering-herd retry storm against a downstream payments API" will not embedding-retrieve "request stampede against the billing service" reliably.

"Maintain a hand-curated playbook." Works until the playbook gets stale or covers only a fraction of the problem space.

"Ask the model to recall a similar case." The model's recall is biased toward whatever was in its training corpus, not toward the team's actual prior cases.

#### The Mechanism
The analogical mapping agent stores prior cases as structured graphs (nodes = entities and relationships, not text), encodes the current case the same way, retrieves library entries by graph similarity rather than embedding similarity, aligns variables between the current and retrieved case, and translates the retrieved solution to the current case's variables.

# reasoning/analogical_mapping.py
from dataclasses import dataclass
import networkx as nx

@dataclass
class CaseGraph:
    case_id: str
    nodes: list[dict]       # [{id, type, attributes}, ...]
    edges: list[dict]       # [{from, to, relation, attributes}, ...]
    solution: dict          # the resolved solution
    metadata: dict          # date, author, success_rating

@dataclass
class StructuralMatch:
    case: CaseGraph
    structural_similarity: float
    variable_alignment: dict[str, str]   # current_variable -> retrieved_variable
    confidence: float

class AnalogicalMappingAgent:
    def __init__(self, case_library: list[CaseGraph], encoder_llm):
        self.library = case_library
        self.encoder = encoder_llm
        self._graphs = {c.case_id: self._to_nx(c) for c in case_library}
    
    def find_analogues(self, problem_description: str, k: int = 3) -> list[StructuralMatch]:
        # 1. Encode the current problem as a graph
        current = self._encode_problem(problem_description)
        current_g = self._to_nx(current)
        # 2. Score each library entry by structural similarity
        scored = []
        for case_id, g in self._graphs.items():
            sim, alignment = self._structural_similarity(current_g, g)
            scored.append((sim, case_id, alignment))
        scored.sort(key=lambda t: t[0], reverse=True)
        # 3. Return top-k with variable alignment
        return [
            StructuralMatch(
                case=next(c for c in self.library if c.case_id == case_id),
                structural_similarity=sim,
                variable_alignment=alignment,
                confidence=self._confidence(sim, alignment),
            )
            for sim, case_id, alignment in scored[:k]
        ]
    
    def _structural_similarity(self, g1: nx.Graph, g2: nx.Graph) -> tuple[float, dict]:
        """Graph edit distance + role-typed node matching."""
        # In production use a proper graph kernel (Weisfeiler-Lehman, NetSimile,
        # or a learned graph embedding). Simplified here.
        node_match = lambda a, b: a.get("type") == b.get("type")
        edge_match = lambda a, b: a.get("relation") == b.get("relation")
        try:
            gm = nx.algorithms.isomorphism.GraphMatcher(
                g1, g2, node_match=node_match, edge_match=edge_match)
            best_mapping = max(gm.subgraph_isomorphisms_iter(),
                              key=lambda m: len(m), default={})
            sim = len(best_mapping) / max(g1.number_of_nodes(), 1)
            return sim, best_mapping
        except Exception:
            return 0.0, {}
    
    def adapt_solution(self, match: StructuralMatch,
                       current_problem: str) -> dict:
        """Translate the retrieved solution to the current variables."""
        retrieved_solution = match.case.solution
        # Substitute aligned variables
        adapted = {}
        for k, v in retrieved_solution.items():
            adapted[k] = self._substitute(v, match.variable_alignment)
        return adapted

#### Trade-offs and Alternatives
Analogical mapping requires a case library encoded as structured graphs. That encoding is itself work: it has to be done at case-capture time or retroactively, and it has to be maintained. For agents whose problem domain is narrow and stable enough that a small playbook suffices, the encoding overhead is not justified.

A useful intermediate is hybrid retrieval: do embedding-based retrieval first, then re-rank by structural similarity on the top-k. This avoids encoding the entire library and gives most of the benefit at a fraction of the implementation cost.

#### Production Failure Modes
Library staleness: Cases age out of relevance, and the library returns matches that worked five years ago but don't fit current systems. Mitigate by attaching a recency-weighted score and decaying old cases unless they have been refreshed.

Alignment errors: The variable alignment between the current and retrieved case is wrong, and the adapted solution maps the wrong variable to the wrong slot. Mitigate by requiring the alignment to be validated by the user before the adapted solution is used.

Over-confident structural matches: The graph similarity is high but the cases are actually unlike, so the structure was incidental. Mitigate by adding semantic checks at the node level (do the node types in the match really mean the same thing in the two cases?) before adapting.

#### Case Study
A SOC analyst co-pilot at a managed-security provider maintains a library of approximately 26,000 prior incident graphs encoded across the customer base (anonymized cross-customer, richly encoded per-customer). Given a new alert pattern, the analogical mapper surfaces the three structurally closest historical incidents and proposes an adapted response.

Median triage time on first-touch incidents dropped from twenty-four minutes to seven, and the rate at which analysts reused (rather than overrode) the adapted response was 71%.

**Composition:** Pairs with: Skill-Library Builder (Agent 48), Few-Shot Prompt Tuner (Agent 50), Semantic Memory Curator (Agent 24).

---

### Agent 11 — The Constraint-Satisfaction Agent

> **Tagline:** *Solves problems by progressively narrowing the feasible region.*

#### The Problem & Production Reality
Many agent problems aren't search problems. Rather, they're constraint problems. The user wants a schedule that respects fifteen overlapping rules, a configuration that doesn't violate any of the eight policies, a contract that doesn't introduce any of the seven prohibited clauses, and a code change that compiles and passes the seventeen lint rules. These are problems where "search and check" is exponentially worse than "constrain and propagate."

The general problem is CSP-shaped reasoning: problems with a finite set of variables, finite domains, and constraints that interact in non-trivial ways, where the right answer is a witness of feasibility (or a minimal explanation of infeasibility), not a chain-of-thought derivation.

#### Why Naïve Approaches Fail
"Ask the model to find a valid schedule." Works on toy cases. On real cases with more than a handful of overlapping constraints, the model produces an answer that violates one or more constraints, and the violation is buried.

"Ask the model to check the answer against the constraints." Catches obvious violations, but misses subtle ones and scales poorly with the number of constraints.

"Have the model write the constraints into Python and run them." Better, but the constraint encoding step is the hard part. Most constraints in real problems are easy to state in natural language and hard to encode correctly.

#### The Mechanism
The constraint-satisfaction agent encodes the problem as variables with finite domains and constraints between them, runs a solver (a real CSP solver, not an LLM), and emits either a witness or a minimal explanation of infeasibility.

# reasoning/constraint_satisfaction.py
from dataclasses import dataclass
from ortools.sat.python import cp_model   # production CSP solver

@dataclass
class CSPVariable:
    name: str
    domain: list                       # finite enumeration of allowed values
    natural_description: str

@dataclass
class CSPConstraint:
    name: str
    variables: list[str]
    natural_description: str
    encoded: object                    # solver-specific encoding
    confidence: float                  # 0-1, the LLM's confidence in encoding

@dataclass
class CSPResult:
    feasible: bool
    assignment: dict[str, object] | None
    infeasibility_explanation: list[str] | None   # minimal conflicting subset
    encoding_confidence: float

class ConstraintSatisfactionAgent:
    def __init__(self, encoder_llm):
        self.encoder = encoder_llm
    
    def solve(self, problem_statement: str) -> CSPResult:
        # 1. LLM extracts variables and constraints with confidence per constraint
        variables, constraints = self._extract(problem_statement)
        # 2. Refuse to solve if encoding confidence too low
        min_confidence = min(c.confidence for c in constraints)
        if min_confidence < 0.7:
            return CSPResult(
                feasible=False, assignment=None,
                infeasibility_explanation=["encoding_uncertainty"],
                encoding_confidence=min_confidence,
            )
        # 3. Build solver model
        model = cp_model.CpModel()
        var_handles = self._materialize_variables(model, variables)
        for c in constraints:
            self._add_constraint(model, c, var_handles)
        # 4. Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        if status == cp_model.OPTIMAL:
            return CSPResult(
                feasible=True,
                assignment={v.name: solver.Value(var_handles[v.name]) for v in variables},
                infeasibility_explanation=None,
                encoding_confidence=min_confidence,
            )
        # 5. If infeasible, find the minimal unsatisfiable core
        return CSPResult(
            feasible=False, assignment=None,
            infeasibility_explanation=self._minimal_core(model, constraints, var_handles),
            encoding_confidence=min_confidence,
        )
    
    def _extract(self, problem_statement: str):
        # The LLM produces a structured representation of variables + constraints
        # with confidence ratings on each constraint translation.
        result = self.encoder.call(
            messages=[
                {"role": "system", "content": ENCODING_PROMPT},
                {"role": "user", "content": problem_statement}
            ],
            schema=ENCODING_SCHEMA,
        )
        return result["variables"], result["constraints"]

#### Trade-offs and Alternatives
Encoding the problem as a CSP costs an extra LLM call (and an extra layer of things that can go wrong). For problems with very few constraints, direct reasoning is cheaper. The pattern earns its cost when constraints are numerous, interact in non-obvious ways, or when the user needs an explanation of infeasibility.

For problems with continuous variables or non-linear constraints, replace the CSP solver with an SMT solver (Z3) or a linear/mixed-integer programming solver (CBC, Gurobi). The pattern is identical, and only the solver changes.

#### Production Failure Modes
Encoding error: The LLM translates a constraint into the solver's language incorrectly. The solver returns a "valid" assignment that the user immediately recognizes as wrong. Mitigate by surfacing the encoded constraints back to the user for review on first use, then auto-validating on subsequent runs against a labeled set.

Constraint omission: The LLM misses a constraint that was implicit in the problem statement. Mitigate by having a second LLM (or a different prompt) check whether the encoded set captures everything in the original statement.

Solver timeout: Real-world problems can be NP-hard. The solver runs out of time. Mitigate by setting explicit timeouts, returning best-effort partial assignments, and providing an "infeasibility under time budget" output distinct from "no solution exists."

#### Case Study
An enterprise meeting-scheduler agent books across three calendars, two physical rooms, four time-zone preferences, and a per-participant maximum daily meeting count. The Constraint-Satisfaction pattern returns either a slot or a precise reason no slot exists ("the conflict is between Alice's no-meetings-Friday rule and the room's morning-availability window").

Before the pattern was introduced, meeting requests with more than three participants failed roughly 35% of the time and the failure mode was opaque to the user. After, the failure rate dropped to 4% and every failure carried an actionable explanation.

**Composition:** Pairs with: Symbolic-Neural Bridge (Agent 13), Resource-Aware Scheduler (Agent 21), Counterfactual Reasoner (Agent 9).

---

### Agent 12 — The Causal Graph Builder Agent

> **Tagline:** *Induces a causal structure from observational data and uses it for intervention reasoning.*

#### The Problem & Production Reality
Most analytics agents stop at correlation. They tell you that two variables move together. They can't answer the question the user actually has: what happens if I change one of them?

That question requires a causal model: an explicit graph of which variables cause which. But constructing one from observational data is a real technical problem the agent has to solve, not a property the data inherently exposes.

The general problem is causal-versus-associational confusion: an agent's outputs that read as causal claims when they are only associational. The asymmetry matters because users act on causal claims and understand associational ones. Conflating them produces actions that don't have the expected effect.

#### Why Naïve Approaches Fail
"Report correlations as if they were causes." The advertising channel that "drives" conversions because the data shows correlation. Later experiments show no causal effect, and the marketing budget is wasted.

"Run a regression and call the coefficients causal." They aren't, except under specific identification assumptions the regression alone doesn't verify.

"Ask the model to figure out what causes what." The model has reasonable priors from training, no formal causal-discovery method, and tends to confidently produce graphs that fit the surface story rather than the data.

#### The Mechanism
The causal graph builder uses observational data, prior knowledge elicited from domain experts (or the LLM as a stand-in), and formal causal-discovery methods (PC, FCI, or score-based methods) to construct an explicit causal graph. The graph carries explicit edge strengths and explicit "unknown" markers for relationships the data is insufficient to resolve. The graph is then used for intervention reasoning, where a downstream policy can ask "if I set X to value Y, what is the expected effect on Z?"

# reasoning/causal_graph.py
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

class EdgeType(Enum):
    DIRECTED = "directed"        # X -> Y
    UNDIRECTED = "undirected"    # X -- Y (cannot orient from data)
    BIDIRECTED = "bidirected"    # X <-> Y (latent confounder)

@dataclass
class CausalEdge:
    source: str
    target: str
    type: EdgeType
    strength: float              # standardized effect size where applicable
    evidence: str                # "data" | "prior" | "data+prior"
    confidence: float

@dataclass
class CausalGraph:
    nodes: list[str]
    edges: list[CausalEdge]
    
    def parents(self, node: str) -> list[str]:
        return [e.source for e in self.edges
                if e.target == node and e.type == EdgeType.DIRECTED]
    
    def is_identifiable(self, treatment: str, outcome: str) -> bool:
        """Does the back-door criterion hold?"""
        ...

class CausalGraphBuilderAgent:
    def __init__(self, discovery_method="pc", prior_elicitor=None):
        self.method = discovery_method
        self.prior_elicitor = prior_elicitor   # LLM or human-curated knowledge source
    
    def build(self, data, variables: list[str]) -> CausalGraph:
        # 1. Elicit priors (which edges are domain-known)
        priors = self.prior_elicitor.elicit(variables) if self.prior_elicitor else []
        # 2. Run causal discovery on the data, respecting priors
        edges = self._discover(data, variables, priors)
        # 3. Score-based refinement
        edges = self._refine(edges, data)
        # 4. Annotate identifiability
        return CausalGraph(nodes=variables, edges=edges)
    
    def estimate_effect(self, graph: CausalGraph, treatment: str,
                        outcome: str, data) -> dict:
        if not graph.is_identifiable(treatment, outcome):
            return {"identifiable": False, "reason": "back-door criterion fails"}
        # Use the do-calculus identifiability result to construct an estimator
        adjustment_set = self._find_adjustment_set(graph, treatment, outcome)
        estimate = self._adjusted_estimate(data, treatment, outcome, adjustment_set)
        return {
            "identifiable": True,
            "estimate": estimate.value,
            "ci_95": estimate.ci_95,
            "adjustment_set": adjustment_set,
        }

#### Trade-offs and Alternatives
Causal discovery from observational data is a hard problem with well-known limits. The graph you get is always provisional, and the patterns in this chapter alone don't guarantee causal claims survive randomized experimentation. For high-stakes decisions, the causal graph is the substrate for designing experiments, not the final answer.

A simpler alternative is expert-elicited graphs: skip the discovery and let domain experts draw the graph by hand. This is appropriate when the domain is well-understood and the experts are credible. The data-driven discovery is what you need when the domain is new, when experts disagree, or when the variables are numerous enough that hand-drawing is impractical.

#### Production Failure Modes
Hidden confounders: A common cause of two variables is unmeasured. The discovery method confidently orients an edge between them that doesn't reflect direct causation. Mitigate by using methods that explicitly model latent confounders (FCI rather than PC) and by surfacing bidirected edges to the user.

Cycle artifacts: The data is too noisy for the discovery method to consistently orient edges. Cycles appear in the output. Mitigate by reporting the partial DAG and the undirected segments separately.

Prior contamination: The elicited priors are wrong (the expert believes A causes B when the data clearly shows the opposite). Mitigate by checking each prior against data conditional-independence tests before incorporation and surface conflicts explicitly.

#### Case Study
A marketing-attribution agent at a direct-to-consumer brand replaced the standard last-touch attribution model with a causal-graph attribution model. The graph was built from twelve months of channel-spend and conversion data, with priors elicited from the marketing team about channels they believed couldn't directly cause conversions (only assist).

The new attribution shifted approximately 23% of the budget away from the channels last-touch had credited toward those the causal graph identified as actual drivers. Subsequent randomized holdout tests confirmed roughly 80% of the shift produced the predicted incremental lift.

**Composition:** Pairs with: Counterfactual Reasoner (Agent 9), Probabilistic Belief Updater (Agent 14), Constraint-Satisfaction (Agent 11).

---

### Agent 13 — The Symbolic-Neural Bridge Agent

> **Tagline:** *Translates natural-language problems into formal expressions and back.*

#### The Problem & Production Reality
Large language models are bad at arithmetic, logic, and any computation whose answer is determined by a closed-form mechanism. They're very good at converting natural language into the syntax of a formal system.

The asymmetry is the agent-engineering opportunity: the model does the translation, a real solver does the computation, and the model does the translation back.

The general problem is using the wrong tool for the closed-form parts: forcing a probabilistic language model to do work a deterministic solver could do in microseconds and get exactly right. Every agent in mathematics, logic, scheduling, optimization, or formal verification needs this pattern.

#### Why Naïve Approaches Fail
"Have the model do the arithmetic." Wrong on any non-trivial problem. The model produces plausible-looking but wrong numbers.

"Use chain-of-thought to step through the math." Better, still wrong with non-trivial probability.

"Tool-call a calculator on every arithmetic step." Works for arithmetic, but doesn't generalize to logic, scheduling, optimization, theorem-proving.

#### The Mechanism
Parse the problem into a target formalism (SMT-LIB for logic, linear programming for optimization, Prolog or Datalog for relational queries, Z3 for satisfiability), invoke the solver with explicit timeouts and bounds, and interpret the solver's output back into natural language with the formal certificate preserved.

# reasoning/symbolic_neural_bridge.py
from dataclasses import dataclass
import z3, time

@dataclass
class FormalEncoding:
    formalism: str                  # "smt-lib" | "lp" | "datalog" | "z3-python"
    source: str                     # the formal expression
    variable_map: dict[str, str]    # natural -> formal name
    confidence: float

@dataclass
class FormalResult:
    success: bool
    result: object                  # solver-specific
    certificate: str                # the formal proof/model
    natural_language_explanation: str

class SymbolicNeuralBridgeAgent:
    def __init__(self, encoder_llm, formalism: str = "z3-python",
                 solver_timeout_s: float = 30):
        self.encoder = encoder_llm
        self.formalism = formalism
        self.timeout = solver_timeout_s
    
    def solve(self, natural_problem: str) -> FormalResult:
        # 1. Translate to formal language
        encoding = self._translate(natural_problem)
        if encoding.confidence < 0.7:
            return FormalResult(
                success=False, result=None, certificate="",
                natural_language_explanation=(
                    f"Translation confidence too low ({encoding.confidence:.2f}); "
                    "the problem may not have a closed-form formulation."
                ),
            )
        # 2. Invoke solver
        solver = self._make_solver()
        exec(encoding.source, {"s": solver, "z3": z3})
        solver.set("timeout", int(self.timeout * 1000))
        check = solver.check()
        # 3. Interpret result
        if check == z3.sat:
            model = solver.model()
            return FormalResult(
                success=True,
                result={name: model[var].as_long() if model[var].is_int() else str(model[var])
                        for name, var in encoding.variable_map.items()
                        if isinstance(var, z3.ExprRef)},
                certificate=str(model),
                natural_language_explanation=self._explain(model, encoding),
            )
        elif check == z3.unsat:
            return FormalResult(
                success=True, result=None,
                certificate=str(solver.unsat_core()),
                natural_language_explanation=self._explain_unsat(solver, encoding),
            )
        else:
            return FormalResult(
                success=False, result=None, certificate="",
                natural_language_explanation="Solver did not converge within timeout.",
            )
    
    def _translate(self, problem: str) -> FormalEncoding:
        result = self.encoder.call(
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT.format(formalism=self.formalism)},
                {"role": "user", "content": problem}
            ],
            schema=TRANSLATION_SCHEMA,
        )
        return FormalEncoding(**result)

#### Trade-offs and Alternatives
The pattern only works for problems that have a formal solution at all. Many real problems (interpretation of intent, qualitative judgment, narrative reasoning) don't. And forcing them through a solver produces nonsense. The pattern includes a confidence check on translation specifically to refuse those cases.

For problems on the boundary (like partially formal or partially qualitative) hybrid patterns work better. Solve the formal part with the bridge, the qualitative part with normal reasoning, and have a composer integrate. This is how serious tax-planning, contract-analysis, and trade-execution agents are typically built.

#### Production Failure Modes
Translation drift: The LLM produces a formally valid expression that solves a slightly different problem than the user asked. Mitigate by translating back to natural language and asking the user to confirm before solving.

Solver brittleness: Z3 is robust but specific solver invocations occasionally crash on unusual inputs. Mitigate with sandboxing of the solver subprocess and graceful degradation to a natural-language fallback.

Certificate-explanation mismatch: The natural-language explanation doesn't actually reflect the solver's reasoning. Mitigate by deriving the explanation mechanically from the certificate rather than via LLM paraphrase.

#### Case Study
A tax-planning agent at a wealth-management firm converts a client's facts into a mixed-integer program over the relevant sections of the tax code, solves for the optimal filing strategy, and presents the result with the formal certificate (a list of which deductions apply, which schedules are used, which elections produce which dollar effects).

The pattern handles approximately 84% of client situations end-to-end, and the remaining 16% are flagged as outside the formal model and routed to a human planner. Median planner time per client dropped from 4.2 hours to 38 minutes after deployment, with measured strategy-quality (third-party-reviewer-graded) materially higher than the pre-deployment baseline.

**Composition:** Pairs with: Constraint-Satisfaction (Agent 11), Provenance Tracker (Agent 55), Counterfactual Reasoner (Agent 9).

---

### Agent 14 — The Probabilistic Belief Updater Agent

> **Tagline:** *Maintains and revises posterior beliefs over hypotheses as new evidence arrives.*

#### The Problem & Production Reality
The agent is faced with a question whose answer it can't determine from a single observation, but for which evidence will accumulate over time: for example, which of these three vendors is the actual source of a quality issue, which of these five customer-segment hypotheses best explains a usage spike, or which of seven candidate root causes is responsible for an incident.

Without explicit belief tracking, every new piece of evidence is interpreted in isolation, sometimes flipping the agent's "conclusion" entirely, sometimes ignored when it should have updated the picture.

The general problem is multi-evidence integration: combining evidence from multiple sources, accounting for dependencies between them, and surfacing both the current best estimate and the precision of that estimate.

#### Why Naïve Approaches Fail
"Ask the model to weigh the evidence and produce an answer." Works once. On the next piece of evidence the model re-weighs everything from scratch, sometimes flipping. The "weighing" has no calibrated meaning.

"Count the evidence on each side." Treats all evidence as equally informative. Ignores how much each piece actually changes the picture.

"Use a simple majority of independent predictions." Reasonable for ensembling, but insufficient when evidence types and confidences differ.

#### The Mechanism
The belief updater holds an explicit distribution over candidate hypotheses, updates it Bayesian-style as evidence arrives, surfaces the current best estimate and its precision, and computes expected information gain for prospective evidence-gathering actions.

# reasoning/belief_updater.py
from dataclasses import dataclass, field
import math

@dataclass
class Hypothesis:
    name: str
    description: str
    prior_probability: float

@dataclass
class Evidence:
    evidence_id: str
    description: str
    likelihoods: dict[str, float]    # P(evidence | hypothesis), per hypothesis
    independence_class: str          # for dependent-evidence handling

@dataclass
class BeliefState:
    hypotheses: list[Hypothesis]
    posteriors: dict[str, float]
    evidence_history: list[str] = field(default_factory=list)
    
    def best_hypothesis(self) -> tuple[Hypothesis, float]:
        h_name = max(self.posteriors, key=self.posteriors.get)
        h = next(h for h in self.hypotheses if h.name == h_name)
        return h, self.posteriors[h_name]
    
    @property
    def entropy(self) -> float:
        return -sum(p * math.log(p) for p in self.posteriors.values() if p > 0)
    
    @property
    def precise(self) -> bool:
        """Are we confident enough to act?"""
        return self.best_hypothesis()[1] > 0.85

class ProbabilisticBeliefUpdaterAgent:
    def __init__(self, hypotheses: list[Hypothesis]):
        priors = {h.name: h.prior_probability for h in hypotheses}
        total = sum(priors.values())
        self.state = BeliefState(
            hypotheses=hypotheses,
            posteriors={k: v/total for k, v in priors.items()},
        )
        self._seen_independence_classes: set[str] = set()
    
    def update(self, evidence: Evidence) -> BeliefState:
        if evidence.independence_class in self._seen_independence_classes:
            # Dependent evidence — discount likelihood weight
            weight = 0.3
        else:
            weight = 1.0
            self._seen_independence_classes.add(evidence.independence_class)
        new_posteriors = {}
        for h_name, prior in self.state.posteriors.items():
            lik = evidence.likelihoods.get(h_name, 0.5) ** weight
            new_posteriors[h_name] = prior * lik
        z = sum(new_posteriors.values())
        new_posteriors = {k: v/z for k, v in new_posteriors.items()}
        self.state.posteriors = new_posteriors
        self.state.evidence_history.append(evidence.evidence_id)
        return self.state
    
    def expected_information_gain(self, candidate_evidence: list[Evidence]) -> list[tuple[Evidence, float]]:
        """For each candidate evidence, compute expected entropy reduction."""
        current_entropy = self.state.entropy
        gains = []
        for ev in candidate_evidence:
            expected_entropy = 0.0
            for h in self.state.hypotheses:
                p_h = self.state.posteriors[h.name]
                p_ev_given_h = ev.likelihoods.get(h.name, 0.5)
                # Simulate the update; compute resulting entropy
                hypothetical = {n: self.state.posteriors[n] * ev.likelihoods.get(n, 0.5)
                                for n in self.state.posteriors}
                z = sum(hypothetical.values())
                hypothetical = {k: v/z for k, v in hypothetical.items()}
                h_entropy = -sum(p * math.log(p) for p in hypothetical.values() if p > 0)
                expected_entropy += p_h * p_ev_given_h * h_entropy
            gains.append((ev, current_entropy - expected_entropy))
        gains.sort(key=lambda eg: eg[1], reverse=True)
        return gains

#### Trade-offs and Alternatives
Bayesian belief tracking requires likelihoods, which someone has to estimate or learn. For domains where likelihood estimation is unstable, the pattern can introduce false precision: the posterior looks confident because the math says so, not because the world warrants it.

Mitigate by surfacing the posterior's width (entropy, credible interval) alongside the point estimate, and by refusing to act on a hypothesis below a confidence threshold.

For domains where likelihoods are extremely hard to elicit, a coarser alternative is evidence-counting with weights. Sum the evidence weights for each hypothesis, and normalize. This is mathematically equivalent to a very strong independence assumption but is more intuitive to operators.

#### Production Failure Modes
Likelihood mis-elicitation: The likelihoods the agent uses are wrong, the posterior is correspondingly wrong. Mitigate by calibrating likelihoods against historical outcomes and reporting calibration metrics in operational dashboards.

Hidden hypothesis: The true cause is not in the enumerated hypothesis space. The agent assigns confidently to whichever is least wrong. Mitigate with an explicit "none-of-the-above" hypothesis and a high prior on it when the data is unusual.

Dependency cascade: Evidence that looks independent is correlated. Multiple confirming pieces multiply incorrectly. Mitigate by explicitly modeling independence classes (as the code does) and discounting dependent evidence.

#### Case Study
A customer-support diagnosis agent at a consumer-electronics company holds beliefs over likely root causes of incoming hardware tickets across a hypothesis space of approximately forty failure classes per device line. It asks the user the single question most likely to discriminate among current top-ranked hypotheses, drawn from the expected-information-gain ranking.

Average tickets-to-resolution dropped from 3.4 to 1.9 (a 44% reduction) and the proportion of tickets resolved without human escalation rose from 22% to 51% in the year following deployment.

**Composition:** Pairs with: Active Learner (Agent 52), Drift Detector (Agent 59), Counterfactual Reasoner (Agent 9).

---

### Agent 15 — The Self-Consistency Voter Agent

> **Tagline:** *Runs N independent reasoning chains and aggregates them into a more reliable answer.*

#### The Problem & Production Reality
Sampling a model once gives you one reasoning path. Sampling it five or ten times gives you a distribution of paths, most of which arrive at the same answer when the problem has a stable answer at all.

A single sample can be confidently wrong, while a sample of ten with eight agreeing is dramatically more reliable. The disagreement rate is itself a useful signal. It tells you which problems the agent doesn't actually know how to solve.

The general problem is stochastic confidence: a model's surface confidence on a single sample isn't calibrated to its actual accuracy on that problem. Multiple samples expose the underlying uncertainty.

#### Why Naïve Approaches Fail
"Just sample once with low temperature." Reduces variance but doesn't eliminate it. The failure modes that survive into low-temperature sampling are the systematic ones.

"Sample five times and take the first answer." Doesn't use the redundancy.

"Sample five times and ensemble the answers in natural language." Works for some tasks, but fails for tasks where "ensembling" produces an answer that's the average of two correct alternatives and is itself wrong.

#### The Mechanism
The voter agent runs the same problem through the same policy multiple times at non-zero temperature, clusters the conclusions, and reports the modal answer together with the agreement rate. Critically, agreement rate is exposed as a confidence proxy. Low agreement is an escalation signal.

# reasoning/self_consistency.py
from dataclasses import dataclass
from collections import Counter
import asyncio

@dataclass
class VoteResult:
    modal_answer: object
    agreement_rate: float
    samples: list[object]
    canonicalized_samples: list[object]
    requires_escalation: bool

class SelfConsistencyVoterAgent:
    def __init__(self, policy, n_samples: int = 8, temperature: float = 0.7,
                 escalation_threshold: float = 0.6, canonicalize=str):
        self.policy = policy
        self.n_samples = n_samples
        self.temperature = temperature
        self.escalation_threshold = escalation_threshold
        self.canonicalize = canonicalize
    
    async def answer(self, problem) -> VoteResult:
        # 1. Parallel sampling
        samples = await asyncio.gather(*[
            self.policy.run_async(problem, temperature=self.temperature)
            for _ in range(self.n_samples)
        ])
        # 2. Canonicalize so equivalent answers cluster
        canonical = [self.canonicalize(s) for s in samples]
        # 3. Vote
        counts = Counter(canonical)
        modal, modal_count = counts.most_common(1)[0]
        agreement = modal_count / self.n_samples
        # 4. Surface escalation signal
        return VoteResult(
            modal_answer=modal,
            agreement_rate=agreement,
            samples=samples,
            canonicalized_samples=canonical,
            requires_escalation=agreement < self.escalation_threshold,
        )

#### Trade-offs and Alternatives
N samples cost N times the inference. For an N of eight, this is an 8× multiplier on cost and latency. The trade is worth it for hard problems where single-sample accuracy is unacceptably low. But it's overhead for problems where single-sample accuracy is already high.

Pick N empirically: sample sweeps from one to sixteen on an evaluation set. The curve typically has a knee around four to eight.

The voter works only when canonicalization successfully clusters equivalent answers. For numerical answers, canonicalize to a rounded form. For free-text answers, canonicalize via a normalization model or embedding cluster. For structured answers, canonicalize by sorting / normalizing the structure.

When canonicalization fails, the voter degenerates to "pick the first sample," which is no better than not voting at all.

#### Production Failure Modes
Canonicalization too aggressive: Different correct answers get merged into one cluster, and the voter reports false agreement. Mitigate by validating the canonicalizer against a held-out set of answers labeled as equivalent or not.

Canonicalization too lenient: Same answers in slightly different forms appear as different clusters, and the voter under-counts agreement. Mitigate by erring on the lenient side and tuning against the labeled set.

Systematic bias: All samples agree, all are wrong. The voter can't detect this because it has no ground truth. Mitigate by pairing the voter with an external verifier (the Chain-of-Thought Auditor, Agent 8) or a different model family.

#### Case Study
A math-tutoring agent at an edtech vendor solves every problem five times in parallel, returns the modal answer, and silently escalates any problem with fewer than four agreeing chains to a stronger model.

The escalation rate is about 8% of problems. Measured accuracy on a labeled benchmark of three thousand problems: 78% with single-sample, 91% with self-consistency voting, 96% with voting plus escalation to the stronger model. The cost increase from single-sample to voting+escalation was 3.1×, and the accuracy improvement was 18 percentage points.

**Composition:** Pairs with: Chain-of-Thought Auditor (Agent 8), Reflection (Agent 47), Debate Moderator (Agent 39).

---

## Capability: Planning: From Goal to Sequenced Action
Covers Agents 16 through 22.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 16** | The Hierarchical Decomposer Agent | *Breaks a goal into a recursive tree of subgoals until the leaves are directly actionable.* | Plan-Then-Execute (Agent 19), Adaptive (Agent 20), Memory-of-Self (Agent 27). |
| **Agent 17** | The ReAct Loop Agent | *Interleaves reasoning and action steps until a termination condition is reached.* | Tool Selector (Agent 30), Reflection (Agent 47), Adaptive Replanner (Agent 20). |
| **Agent 18** | The Tree-of-Thought Explorer Agent | *Branches plans into a search tree, evaluates partial plans, and prunes the bad branches.* | Counterfactual Reasoner (Agent 9), Backward Goal-Regression (Agent 22), Self-Consistency Voter (Agent 15). |
| **Agent 19** | The Plan-Then-Execute Agent | *Produces a full plan upfront, executes it under monitoring, and only re-plans on deviation.* | Hierarchical Decomposer (Agent 16), Side-Effect Auditor (Agent 37), Adaptive Replanner (Agent 20). |
| **Agent 20** | The Adaptive Replanner Agent | *Detects when execution has drifted from the plan and rebuilds the plan from the new state.* | Plan-Then-Execute (Agent 19), Drift Detector (Agent 59), Hierarchical Decomposer (Agent 16). |
| **Agent 21** | The Resource-Aware Scheduler Agent | *Plans under explicit compute, time, latency, or budget constraints.* | Tree-of-Thought Explorer (Agent 18), Auctioneer (Agent 44), Distillation (Agent 51). |
| **Agent 22** | The Backward Goal-Regression Agent | *Plans from the goal state backward toward the current state.* | Constraint-Satisfaction (Agent 11), Symbolic-Neural Bridge (Agent 13), Tree-of-Thought Explorer (Agent 18). |

### Detailed Pattern Breakdowns

### Agent 16 — The Hierarchical Decomposer Agent

> **Tagline:** *Breaks a goal into a recursive tree of subgoals until the leaves are directly actionable.*

#### The Problem & Production Reality
Complex goals aren't flat lists of actions. They're trees. "Onboard a new customer" expands into "collect KYC, provision infrastructure, schedule kickoff," each of which expands further, and the actionable leaves are tool calls.

An agent that flattens this tree into a linear plan loses the structure that makes the plan revisable. But one that refuses to flatten at all collapses into a flat ReAct loop and loses sight of the goal somewhere around step thirty.

The general problem is long-horizon coherence: maintaining the connection between the current micro-action and the original macro-goal across many intermediate steps. Hierarchical structure is the technique that makes this tractable.

#### Why Naïve Approaches Fail
"Generate a flat list of steps." Works for goals that decompose into five to fifteen steps. Fails for anything larger, as the model produces lists that are internally inconsistent, miss prerequisites, or repeat steps under different phrasings.

"Use a single ReAct loop." The loop loses the goal after enough iterations. The model starts optimizing for whatever it last observed rather than for the original objective.

"Plan only at the top level, leave the rest to the executor." The executor (typically another LLM call) has no visibility into how its step relates to the larger plan. Its choices are locally optimal and globally drift-prone.

#### The Mechanism
The decomposer expands the tree top-down, with each non-leaf node tagged with its expected output type and success predicate. It only attempts to execute when it has reached the actionable leaves.

The tree itself is the agent's plan, the policy is its expander, and the executor walks the tree depth-first.

# planning/hierarchical_decomposer.py
from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["goal", "subgoal", "action"]

@dataclass
class PlanNode:
    id: str
    kind: NodeKind
    description: str
    expected_output_type: str       # "report" | "boolean" | "record" | "file" | ...
    success_predicate: str          # natural-language condition for completion
    children: list["PlanNode"] = field(default_factory=list)
    parent_id: str | None = None
    state: Literal["pending", "in_progress", "done", "failed"] = "pending"
    result: object | None = None
    
    @property
    def is_leaf(self) -> bool:
        return self.kind == "action"

class HierarchicalDecomposerAgent:
    def __init__(self, decomposer_llm, action_executor,
                 *, max_depth: int = 4, max_children: int = 7):
        self.decomposer = decomposer_llm
        self.executor = action_executor
        self.max_depth = max_depth
        self.max_children = max_children
    
    def run(self, goal: str) -> PlanNode:
        root = PlanNode(id="root", kind="goal", description=goal,
                        expected_output_type="result",
                        success_predicate="goal achieved")
        self._expand(root, depth=0)
        self._execute(root)
        return root
    
    def _expand(self, node: PlanNode, depth: int) -> None:
        if depth >= self.max_depth:
            # Force action at max depth; if not executable, mark failed.
            node.kind = "action"
            return
        decomposition = self.decomposer.call(
            messages=[
                {"role": "system", "content": DECOMPOSE_PROMPT},
                {"role": "user", "content": format_node(node, depth)}
            ],
            schema=DECOMPOSITION_SCHEMA,
        )
        if decomposition["actionable_directly"]:
            node.kind = "action"
            return
        for child_spec in decomposition["children"][:self.max_children]:
            child = PlanNode(
                id=f"{node.id}.{len(node.children)}",
                kind="subgoal",
                description=child_spec["description"],
                expected_output_type=child_spec["expected_output_type"],
                success_predicate=child_spec["success_predicate"],
                parent_id=node.id,
            )
            node.children.append(child)
            self._expand(child, depth + 1)
    
    def _execute(self, node: PlanNode) -> None:
        if node.is_leaf:
            node.state = "in_progress"
            try:
                node.result = self.executor.execute(
                    description=node.description,
                    expected_output_type=node.expected_output_type)
                node.state = "done" if self._satisfied(node) else "failed"
            except Exception as e:
                node.state = "failed"
                node.result = {"error": str(e)}
            return
        for child in node.children:
            self._execute(child)
            if child.state == "failed":
                # Optional: re-decompose this subgoal with the failure as context.
                self._handle_subgoal_failure(node, child)
        # Aggregate child results into the parent's result
        node.result = self._aggregate([c.result for c in node.children])
        node.state = "done" if all(c.state == "done" for c in node.children) else "failed"

DECOMPOSE_PROMPT = """\
You receive a goal node from a hierarchical plan tree.
Decide whether the node is directly actionable (a single tool call resolves it)
or whether it requires further decomposition.

If decomposable, produce 2-7 children, each with:
  - description: what this child achieves
  - expected_output_type: the data shape produced
  - success_predicate: how to know it succeeded

Children should be:
  - Independently meaningful (each can be completed and verified on its own).
  - Collectively sufficient (achieving all children achieves the parent).
  - Minimally overlapping.

Output JSON: {"actionable_directly": bool, "children": [...]}
"""

#### Trade-offs and Alternatives
Hierarchical decomposition adds depth-times-N LLM calls before any action happens. For short goals (under ten steps), this is overhead. The pattern earns its keep on long-horizon goals — anything that would otherwise generate a flat plan of more than fifteen steps benefits, and anything beyond thirty steps essentially requires hierarchy to remain coherent.

A simpler alternative for medium-horizon goals is two-level decomposition: one top-level plan with a handful of milestones, each milestone executed by a small ReAct loop. This avoids the recursive overhead of the full pattern at the cost of less revisability.

#### Production Failure Modes
Decomposition explosion: The decomposer keeps producing seven children at every level and the tree explodes. Mitigate by capping breadth and depth (the code does both) and by penalizing decompositions whose children duplicate each other.

Leaf-action mismatch: A leaf is reached but the action that satisfies it isn't in the executor's toolset. Mitigate by passing the available toolset into the decomposer prompt so leaves are constrained to be executable.

Aggregation failure: Child results are aggregated incorrectly, and the parent's "done" state masks subtle child failures. Mitigate by making the aggregator a structured operation (concat lists, union sets, sum numbers) rather than an LLM call that may paraphrase.

#### Case Study
An end-to-end software-issue agent at a B2B SaaS vendor takes "the dashboard is slow" and produces a tree culminating in a profiler trace, a tracked-down N+1 query, and a draft pull request.

The tree is visible to the engineer as a navigable plan. Engineers report intervening in roughly 18% of trees (typically to redirect a sub-goal that was off the mark), with the remaining 82% completing without intervention. Median time from issue creation to draft PR dropped from 14 hours (human-only baseline) to 2.3 hours (agent + reviewer).

**Composition:** Pairs with: Plan-Then-Execute (Agent 19), Adaptive (Agent 20), Memory-of-Self (Agent 27).

---

### Agent 17 — The ReAct Loop Agent

> **Tagline:** *Interleaves reasoning and action steps until a termination condition is reached.*

#### The Problem & Production Reality
Some agent problems don't have plans that can be sensibly produced upfront. The environment is stochastic enough, the user's intent is open-ended enough, or the action space is dynamic enough that planning ahead is wasted work. By the time the plan is half-executed, the world has changed enough that the remaining plan is wrong. For these problems, the right shape is reactive: think, act, observe, think again.

The general problem is uncertain-environment progress: making progress toward a goal in an environment where each step's outcome is informative enough to change the next step's choice.

#### Why Naïve Approaches Fail
"Plan everything, then execute." The plan is stale after step three, but the executor blindly follows.

"Have the model just call tools without reasoning." Loses the reasoning trace. Debugging becomes opaque, the model picks tools based on local-surface match rather than goal-relevance.

"Skip the loop and just sample one tool call." Works for trivially-one-step problems, but fails for anything multi-step.

#### The Mechanism
ReAct (the canonical reactive pattern in agent literature) has an explicit thought-action-observation loop with structural support: bounded steps, observed termination, per-step traceability, and (in this book's version) progress measurement.

# planning/react_loop.py
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class ReactStep:
    step: int
    thought: str
    action: dict | None     # None on termination steps
    observation: dict | None

@dataclass
class ReactResult:
    final_answer: object | None
    steps: list[ReactStep]
    terminated: bool
    failure_reason: str | None = None

class ReactLoopAgent:
    def __init__(self, policy_llm, tools: dict, *, max_steps: int = 20,
                 progress_check: Callable[[list[ReactStep]], bool] | None = None):
        self.policy = policy_llm
        self.tools = tools
        self.max_steps = max_steps
        self.progress_check = progress_check or self._default_progress_check
    
    def run(self, goal: str) -> ReactResult:
        steps: list[ReactStep] = []
        for i in range(self.max_steps):
            response = self.policy.call(
                messages=[
                    {"role": "system", "content": REACT_PROMPT},
                    {"role": "user", "content": format_react_input(goal, steps, self.tools)}
                ],
                schema=REACT_SCHEMA,
            )
            step = ReactStep(
                step=i,
                thought=response["thought"],
                action=response.get("action"),
                observation=None,
            )
            if response.get("terminate"):
                step.action = None
                steps.append(step)
                return ReactResult(
                    final_answer=response.get("final_answer"),
                    steps=steps, terminated=True,
                )
            # Execute the action
            tool_name = step.action["tool"]
            if tool_name not in self.tools:
                step.observation = {"error": f"unknown_tool:{tool_name}"}
            else:
                try:
                    step.observation = self.tools[tool_name].invoke(step.action["args"])
                except Exception as e:
                    step.observation = {"error": str(e)}
            steps.append(step)
            # Progress check
            if not self.progress_check(steps):
                return ReactResult(
                    final_answer=None, steps=steps,
                    terminated=False, failure_reason="no_progress",
                )
        return ReactResult(
            final_answer=None, steps=steps,
            terminated=False, failure_reason="step_budget_exhausted",
        )
    
    @staticmethod
    def _default_progress_check(steps: list[ReactStep]) -> bool:
        """Detect simple loops: same (tool, args) repeated 3 times consecutively."""
        if len(steps) < 6:
            return True
        recent_actions = [(s.action["tool"], str(s.action["args"]))
                          for s in steps[-6:] if s.action]
        unique = set(recent_actions)
        return len(unique) > 1

#### Trade-offs and Alternatives
ReAct is responsive but has no concept of progress without an explicit progress check. Vanilla ReAct (no progress check, no bound) is the agent pattern most likely to loop forever in production. This book's version always has bounded steps, a default loop-detector, and an externalized failure reason.

For problems where the action space is small and stable, ReAct is overkill. A fixed-form policy (a switch statement plus a model call) gets the same behavior at much lower cost. ReAct earns its complexity when the policy genuinely has to choose among many actions per step.

#### Production Failure Modes
Loop-detector evasion: The model varies its arguments slightly to evade the loop check while still doing the same thing semantically. Mitigate by canonicalizing arguments before the loop check. For free-text arguments, use an embedding-similarity check.

Premature termination: The model declares "done" before the goal is actually achieved. Mitigate by adding an explicit goal-check predicate that the harness evaluates independently of the model's self-report.

Tool-result misinterpretation: The model's next thought misreads the previous tool's result, and the agent acts on a phantom observation. Mitigate by validating tool results against typed schemas before passing them to the next prompt.

#### Case Study
A customer-support ticket-resolver agent at a fintech runs entire support sessions as forty-step-bounded ReAct loops over a defined toolset (account lookup, transaction search, refund eligibility, escalation creation).

The agent resolves approximately 31% of L1 tickets without escalation. On tickets that escalate, the agent's transcript becomes the starting point for the human, reducing average human handle time by 47%.

**Composition:** Pairs with: Tool Selector (Agent 30), Reflection (Agent 47), Adaptive Replanner (Agent 20).

---

### Agent 18 — The Tree-of-Thought Explorer Agent

> **Tagline:** *Branches plans into a search tree, evaluates partial plans, and prunes the bad branches.*

#### The Problem & Production Reality
When a problem has more than one plausible path forward and the cost of going down the wrong path is high, the right approach isn't a single chain of thought but a search.

ReAct commits to one branch at each step and can't recover from bad commits. But chain-of-thought (within a single call) implicitly branches and then collapses to one answer with no audit trail of the alternatives considered.

The general problem is branch-and-evaluate planning: maintaining multiple plausible plans in parallel, evaluating their expected value, and pruning the unpromising ones before committing.

#### Why Naïve Approaches Fail
"Sample multiple chains and vote." The vote happens at the end, after each chain has invested in its own answer. The branches that diverged early may both be wrong. Voting can't recover.

"Run multiple ReAct loops in parallel." Better, but expensive. Every branch costs a full ReAct execution.

"Increase temperature so a single chain explores more." Doesn't explore, just makes the single chain noisier.

#### The Mechanism
The tree-of-thought agent expands a branching factor of plausible next moves, evaluates each branch with a value estimator (often the same model in a different role), prunes the low-value branches, and continues expansion only on the survivors. The pattern is the bridge between language-model agents and classical search.

# planning/tree_of_thought.py
from dataclasses import dataclass, field

@dataclass
class ToTNode:
    id: str
    state: str                  # natural-language description of the partial plan
    action: str | None          # action that produced this state
    parent_id: str | None
    depth: int
    value: float                # estimator score
    children: list[str] = field(default_factory=list)
    terminal: bool = False

@dataclass
class ToTResult:
    best_path: list[ToTNode]
    nodes_expanded: int
    nodes_pruned: int

class TreeOfThoughtExplorerAgent:
    def __init__(self, expander_llm, evaluator_llm, *,
                 branching: int = 4, max_depth: int = 6,
                 keep_top_k: int = 3, max_total_nodes: int = 200):
        self.expander = expander_llm
        self.evaluator = evaluator_llm
        self.branching = branching
        self.max_depth = max_depth
        self.keep_top_k = keep_top_k
        self.max_total_nodes = max_total_nodes
    
    def search(self, goal: str) -> ToTResult:
        root = ToTNode(id="root", state=goal, action=None, parent_id=None,
                       depth=0, value=0.0)
        nodes: dict[str, ToTNode] = {"root": root}
        frontier = [root]
        pruned = 0
        while frontier and len(nodes) < self.max_total_nodes:
            level_children: list[ToTNode] = []
            for node in frontier:
                if node.depth >= self.max_depth:
                    node.terminal = True
                    continue
                # 1. Expand: generate B candidate next moves
                candidates = self._expand(node)
                for action in candidates:
                    child_state = self._apply(node.state, action)
                    child = ToTNode(
                        id=f"{node.id}.{len(node.children)}",
                        state=child_state, action=action,
                        parent_id=node.id, depth=node.depth + 1,
                        value=0.0,
                    )
                    # 2. Evaluate the partial plan
                    child.value = self._evaluate(goal, child_state)
                    nodes[child.id] = child
                    node.children.append(child.id)
                    level_children.append(child)
            # 3. Prune to top-K at this level
            level_children.sort(key=lambda n: n.value, reverse=True)
            survivors = level_children[:self.keep_top_k]
            pruned += len(level_children) - len(survivors)
            frontier = [n for n in survivors if not n.terminal]
        # 4. Reconstruct the best path
        best_leaf = max(
            (n for n in nodes.values() if n.terminal or not n.children),
            key=lambda n: n.value,
        )
        path = self._path_to(nodes, best_leaf)
        return ToTResult(best_path=path, nodes_expanded=len(nodes), nodes_pruned=pruned)
    
    def _expand(self, node: ToTNode) -> list[str]:
        response = self.expander.call(
            messages=[
                {"role": "system", "content": EXPAND_PROMPT},
                {"role": "user", "content": node.state}
            ],
            schema={"type": "object", "properties": {
                "candidates": {"type": "array", "items": {"type": "string"},
                               "maxItems": self.branching}
            }}
        )
        return response["candidates"]
    
    def _evaluate(self, goal: str, state: str) -> float:
        response = self.evaluator.call(
            messages=[
                {"role": "system", "content": EVAL_PROMPT},
                {"role": "user", "content": f"Goal: {goal}\nCurrent state: {state}"}
            ],
            schema={"type": "object", "properties": {
                "value": {"type": "number", "minimum": 0, "maximum": 1}
            }}
        )
        return response["value"]

#### Trade-offs and Alternatives
The branching factor times depth gives the worst-case cost. For B=4 and depth=6, that is up to 4,096 expansion calls per problem (mitigated by pruning to top-K). The pattern is expensive and earns its keep on problems where the cost of the wrong path exceeds the cost of the search by a meaningful multiplier.

For problems where the value estimator is unreliable (it can't distinguish good and bad partial plans), the pruning is noisy and the pattern degenerates to expensive random search. Validate the estimator before trusting the search.

#### Production Failure Modes
Value-estimator collapse: The evaluator gives nearly identical scores to all branches, and the pruning has no effect. Mitigate by training or prompting the evaluator on contrastive pairs (here's a good plan, here's a bad one, tell them apart) before deploying.

Expansion redundancy: The expander produces near-identical candidates at each node. Mitigate by requiring candidates to be categorically distinct (different action types, different parameter regions).

Search budget blow-up: On problems where the value estimator is flat, the search expands the full tree. Mitigate by hard upper bounds on total node count.

#### Case Study
A competitive-pricing agent at a B2B services firm, given a new tender, expands a tree of bidding strategies (price points, contract terms, delivery commitments) and prunes against historical win rates and margin floors. The surviving three strategies are presented to the pricing manager with their expected outcomes.

Win rate on tenders processed through the agent rose from 14% to 22% measured over six months, with no measurable change in average margin. The agent surfaced strategies the pricing team hadn't previously considered, primarily in the trade-off between price and contract length.

**Composition:** Pairs with: Counterfactual Reasoner (Agent 9), Backward Goal-Regression (Agent 22), Self-Consistency Voter (Agent 15).

---

### Agent 19 — The Plan-Then-Execute Agent

> **Tagline:** *Produces a full plan upfront, executes it under monitoring, and only re-plans on deviation.*

#### The Problem & Production Reality
ReAct is responsive but commits one step at a time. Some problems benefit from the opposite shape: think hard upfront, produce a complete plan, and execute it. The shape dominates where the cost of an irreversible action is high (so seeing the whole plan before any action is valuable) and where the cost of latency before the first action is acceptable.

The general problem is front-loaded planning: deciding all the actions upfront when doing so produces better decisions than deciding them one-at-a-time during execution.

#### Why Naïve Approaches Fail
"Just use ReAct." Loses the upfront-planning benefit. Each step is decided in isolation. The first irreversible step happens early without the full context of what comes after.

"Plan upfront, then execute blindly." Plan-Then-Execute without deviation monitoring is brittle. Any unexpected outcome derails execution.

"Plan in natural language and execute by parsing." The parsing is unreliable. The plan should be structured, not prose.

#### The Mechanism
The agent produces a complete plan before taking any action: a sequence or DAG of tool calls with expected outcomes. Execution is a separate component that runs the plan with strict typing on inputs and outputs, monitors each step against the expected outcome, and invokes the planner again when deviation exceeds a threshold (which is the Adaptive Replanner, Agent 20).

# planning/plan_then_execute.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class PlanStep:
    id: str
    description: str
    action_type: Literal["tool_call", "reasoning", "human_approval", "wait"]
    tool: str | None
    args: dict
    inputs_from: list[str] = field(default_factory=list)   # IDs of upstream steps
    expected_output_type: str = ""
    success_predicate: str = ""
    reversible: bool = True

@dataclass
class Plan:
    plan_id: str
    goal: str
    steps: list[PlanStep]
    
    def topological_order(self) -> list[PlanStep]:
        # Standard topo sort respecting `inputs_from`
        ...

@dataclass
class StepOutcome:
    step_id: str
    success: bool
    output: object
    deviation: float        # 0 if matches expected; higher = larger deviation

class PlanThenExecuteAgent:
    def __init__(self, planner_llm, executor, deviation_threshold: float = 0.3):
        self.planner = planner_llm
        self.executor = executor
        self.threshold = deviation_threshold
    
    def run(self, goal: str) -> dict:
        plan = self._plan(goal)
        outcomes: dict[str, StepOutcome] = {}
        for step in plan.topological_order():
            # Bind inputs from upstream steps
            bound_args = self._bind_inputs(step, outcomes)
            outcome = self._execute_step(step, bound_args)
            outcomes[step.id] = outcome
            if not outcome.success:
                return {"status": "failed", "step": step.id, "plan": plan, "outcomes": outcomes}
            if outcome.deviation > self.threshold:
                # Hand off to the Adaptive Replanner (Agent 20)
                return {"status": "deviation", "step": step.id,
                        "plan": plan, "outcomes": outcomes,
                        "deviation": outcome.deviation}
        return {"status": "success", "plan": plan, "outcomes": outcomes}
    
    def _plan(self, goal: str) -> Plan:
        response = self.planner.call(
            messages=[
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": goal}
            ],
            schema=PLAN_SCHEMA,
        )
        return Plan(**response)
    
    def _execute_step(self, step: PlanStep, args: dict) -> StepOutcome:
        if step.action_type == "tool_call":
            output = self.executor.call_tool(step.tool, args)
        elif step.action_type == "human_approval":
            output = self.executor.request_approval(step.description, args)
        elif step.action_type == "reasoning":
            output = self.executor.reason(step.description, args)
        else:
            output = self.executor.wait(step.args.get("seconds", 0))
        deviation = self._measure_deviation(output, step.expected_output_type)
        return StepOutcome(
            step_id=step.id,
            success=self._satisfies(output, step.success_predicate),
            output=output,
            deviation=deviation,
        )

PLAN_PROMPT = """\
Produce a complete plan for the goal.
The plan is a directed acyclic graph of steps.
For EACH step, specify:
  - action_type ("tool_call" | "reasoning" | "human_approval" | "wait")
  - tool (for tool_call)
  - args (for tool_call)
  - inputs_from (IDs of steps whose output is input here)
  - expected_output_type
  - success_predicate
  - reversible (true if undoing this step is straightforward)

Irreversible steps MUST come after at least one human_approval step.
Steps requiring inputs from other steps MUST declare those inputs explicitly.
"""

#### Trade-offs and Alternatives
Plan-Then-Execute is the right pattern when irreversibility and latency-tolerance both favor upfront thinking. It's the wrong pattern when the environment is too uncertain for a plan to survive contact with reality.

The default fall-back is the Adaptive Replanner (Agent 20), which makes Plan-Then-Execute robust by replanning on detected deviation.

For tasks where partial completion is valuable, allow the executor to commit each successful step and persist its result, so a deviation late in the plan doesn't invalidate the work already done.

#### Production Failure Modes
Plan-execution mismatch on irreversible steps: A step turns out to be irreversible despite being marked reversible=true, and the rollback path fails. Mitigate by treating reversibility as a property of the tool, set by the tool author, not the planner.

Deviation-threshold over-tuning: The threshold is too low (constant replanning) or too high (catastrophic drift). Tune empirically: instrument the deviation distribution and pick a threshold at the 90th percentile of "normal" runs.

Input-binding errors: A step's inputs_from reference produces a value of the wrong shape, and the bound args are wrong. Mitigate with typed input/output schemas on every step.

#### Case Study
An account-migration agent at a SaaS vendor produces a forty-step migration plan, surfaces it to the operator for approval (with the plan rendered as a Gantt-style timeline), and executes the approved plan with per-step deviation monitoring.

Each migration touches multiple internal systems and at least one external vendor. The plan-then-execute shape was chosen because mid-flight surprises are expensive and operator confidence in the plan is critical.

The pattern handled approximately 2,800 migrations in its first year with a measured deviation rate of 12% (requiring replanning) and a hard-failure rate of 0.4%.

**Composition:** Pairs with: Hierarchical Decomposer (Agent 16), Side-Effect Auditor (Agent 37), Adaptive Replanner (Agent 20).

---

### Agent 20 — The Adaptive Replanner Agent

> **Tagline:** *Detects when execution has drifted from the plan and rebuilds the plan from the new state.*

#### The Problem & Production Reality
A plan is a forecast. And forecasts go wrong. Without a replanner, a plan that goes wrong is executed wrong: the executor keeps following the steps even when the world no longer matches the plan's assumptions. The result is a confidently completed action sequence that doesn't reach the goal.

The general problem is planning under model-execution mismatch: detecting when the executed-state has diverged from the planned-state enough to invalidate the remaining plan, and rebuilding the plan from the new state.

#### Why Naïve Approaches Fail
"Replan on every step." Wasteful and nullifies the benefit of upfront planning.

"Never replan." Brittle, any unexpected outcome derails execution.

"Have the model decide whether to replan on each step." The model is bad at this decision. It tends to either replan constantly (paranoid mode) or refuse to replan when it should (committed-to-the-plan mode).

#### The Mechanism
The adaptive replanner watches execution against an explicit expected-trajectory model, classifies deviations into recoverable and non-recoverable, applies a replan-trigger policy with hysteresis to prevent thrashing, and hands the new state to the planner with the previous plan and the reason for replanning as context.

# planning/adaptive_replanner.py
from dataclasses import dataclass, field

@dataclass
class TrajectoryExpectation:
    step_id: str
    expected_output_type: str
    expected_output_schema: dict
    expected_state_predicate: str   # what should be true of the world after this step

@dataclass
class DeviationClassification:
    severity: str       # "noise" | "recoverable" | "structural"
    affected_steps: list[str]    # downstream steps invalidated by the deviation
    cause_hypothesis: str
    replan_required: bool

class AdaptiveReplannerAgent:
    def __init__(self, planner_llm, classifier_llm,
                 *, hysteresis: int = 1, max_replans: int = 3):
        self.planner = planner_llm
        self.classifier = classifier_llm
        self.hysteresis = hysteresis
        self.max_replans = max_replans
        self._recent_replans = 0
        self._steps_since_replan = 0
    
    def observe(self, plan, step, actual_outcome) -> DeviationClassification:
        expected = self._expected_trajectory(plan, step)
        classification = self._classify(actual_outcome, expected)
        self._steps_since_replan += 1
        if classification.replan_required and self._recent_replans < self.max_replans:
            if self._steps_since_replan >= self.hysteresis:
                self._recent_replans += 1
                self._steps_since_replan = 0
                return classification
            classification.replan_required = False   # hysteresis veto
        return classification
    
    def replan(self, original_goal, executed_steps, current_state,
               deviation: DeviationClassification) -> dict:
        response = self.planner.call(
            messages=[
                {"role": "system", "content": REPLAN_PROMPT},
                {"role": "user", "content": format_replan_input(
                    original_goal, executed_steps, current_state, deviation)}
            ],
            schema=PLAN_SCHEMA,
        )
        return response
    
    def _classify(self, outcome, expected) -> DeviationClassification:
        if matches_schema(outcome.output, expected.expected_output_schema):
            return DeviationClassification(
                severity="noise", affected_steps=[],
                cause_hypothesis="output_within_schema", replan_required=False,
            )
        # Severity comes from the classifier LLM
        response = self.classifier.call(
            messages=[
                {"role": "system", "content": DEVIATION_PROMPT},
                {"role": "user", "content": format_deviation_input(outcome, expected)}
            ],
            schema=DEVIATION_SCHEMA,
        )
        return DeviationClassification(**response)

REPLAN_PROMPT = """\
The execution of a plan has deviated from expectations.
Given:
  - The original goal
  - The steps already executed (with their outcomes)
  - The current state of the world
  - The deviation classification

Produce a NEW plan that:
  1. Acknowledges the work already done (do not redo successful steps).
  2. Addresses the cause of the deviation if needed.
  3. Reaches the original goal from the current state.

Do not paper over the deviation — if the goal is now unreachable, say so
and propose the closest achievable goal.
"""

#### Trade-offs and Alternatives
The replanner adds latency on every replan and risks oscillation between two plans if the deviation classifier is noisy. The hysteresis parameter is the dial: too low and the agent thrashes, too high and it commits to a failing plan too long. Tune empirically against an evaluation set that includes both stable and unstable runs.

For environments where deviations are rare but catastrophic (one-shot deployments, irreversible operations), the right shape is plan-then-execute with operator-mediated replanning: deviation triggers an alarm and pauses the agent, and a human authorizes the replan before it runs.

#### Production Failure Modes
Replan-oscillation: The replanner produces plan A, hits a deviation, replans to plan B, hits a deviation, replans back to A. Mitigate with a no-repeat constraint on the planner: each new plan must differ structurally from the most recent N rejected plans.

Deviation underestimation: The classifier marks structural drift as "noise", and the agent continues executing a doomed plan. Mitigate by sampling deviation classifications for human review and recalibrating.

State-inference error: The replanner is given a current state that doesn't reflect reality. The new plan starts from the wrong assumptions. Mitigate by reconstructing the current state from observation (re-query the environment) rather than from internal bookkeeping at replan time.

#### Case Study
A multi-leg travel-booking agent at a corporate-travel vendor combines three carriers and two transfers per trip on average. Flight delays, cancellations, and rebookings produce frequent deviation triggers. The replanner rebuilds the trip plan in under five seconds per replan, and replanning typically completes before the user has noticed the upstream disruption.

The on-time-rebook rate (the customer's flight changes for which the agent presented a valid alternative before the customer asked) rose from 41% to 88% after the replanner was added.

**Composition:** Pairs with: Plan-Then-Execute (Agent 19), Drift Detector (Agent 59), Hierarchical Decomposer (Agent 16).

---

### Agent 21 — The Resource-Aware Scheduler Agent

> **Tagline:** *Plans under explicit compute, time, latency, or budget constraints.*

#### The Problem & Production Reality
Most agent plans are written as if compute and money were free. They're not. A plan that produces a great answer at a cost the company can't pay is a failure. But a plan that is the cheapest possible but takes an hour when the user has thirty seconds is also a failure.

Without explicit budgeting, the planner produces whatever it considers "good," and the costs accrue invisibly.

The general problem is planning under explicit resource constraints: producing the best plan that fits inside a fixed envelope of compute, time, and money, with graceful degradation when the envelope can't be met.

#### Why Naïve Approaches Fail
"Use a cheap model everywhere." Quality collapses on hard problems.

"Use the most expensive model everywhere." Budget collapses on easy problems.

"Have the model decide which model to use." The model has no calibrated sense of which problems require which capacity.

#### The Mechanism
The resource-aware scheduler treats the cost of each step as a first-class plan property (model inference cost, tool API cost, latency budget, wall-clock budget) and selects plans that meet the goal within the budget rather than the cheapest plan or the fastest plan.

# planning/resource_scheduler.py
from dataclasses import dataclass

@dataclass
class StepCost:
    expected_cost_cents: float
    worst_case_cost_cents: float
    expected_latency_s: float
    worst_case_latency_s: float

@dataclass
class Budget:
    total_cost_cents: float
    total_latency_s: float
    
@dataclass
class ScheduledPlan:
    steps: list                 # list of (step_spec, chosen_implementation)
    expected_total_cost_cents: float
    worst_case_total_cost_cents: float
    expected_total_latency_s: float
    degraded: bool              # True if best-effort fit below ideal quality

class ResourceAwareSchedulerAgent:
    def __init__(self, planner_llm, cost_model):
        self.planner = planner_llm
        self.cost_model = cost_model        # estimates StepCost for (step, implementation)
    
    def schedule(self, goal: str, budget: Budget) -> ScheduledPlan:
        # 1. Produce a baseline plan
        baseline = self._produce_plan(goal)
        # 2. For each step, enumerate implementation options ordered by quality
        options_per_step = [self._implementations(s) for s in baseline.steps]
        # 3. Greedily pick the highest-quality implementation that fits the residual budget
        chosen = []
        spent_cost, spent_latency = 0.0, 0.0
        degraded = False
        for step, options in zip(baseline.steps, options_per_step):
            # Options are sorted best-quality first
            picked = None
            for opt in options:
                cost = self.cost_model.estimate(step, opt)
                if (spent_cost + cost.worst_case_cost_cents <= budget.total_cost_cents
                        and spent_latency + cost.worst_case_latency_s <= budget.total_latency_s):
                    picked = (step, opt, cost)
                    break
            if picked is None:
                # Even cheapest option doesn't fit; must degrade
                cheapest = options[-1]
                cost = self.cost_model.estimate(step, cheapest)
                picked = (step, cheapest, cost)
                degraded = True
            chosen.append(picked)
            spent_cost += picked[2].expected_cost_cents
            spent_latency += picked[2].expected_latency_s
        return ScheduledPlan(
            steps=[(s, impl) for s, impl, _ in chosen],
            expected_total_cost_cents=spent_cost,
            worst_case_total_cost_cents=sum(c.worst_case_cost_cents for _, _, c in chosen),
            expected_total_latency_s=spent_latency,
            degraded=degraded,
        )
    
    def execute_with_budget(self, plan: ScheduledPlan, budget: Budget):
        enforcer = BudgetEnforcer(budget)
        for step, impl in plan.steps:
            enforcer.check()
            result = impl.invoke(step)
            enforcer.charge(result.cost_cents, tool_call=True)
            yield step, result

#### Trade-offs and Alternatives
Resource-aware scheduling requires a calibrated cost model: both the expected and worst-case costs of each implementation option per step. Building and maintaining this model is real work.

For agents with stable workloads, the cost model can be empirical (run each implementation against historical traces and measure). For highly variable workloads, the cost model needs continuous recalibration.

For agents with very loose budgets (cost is negligible), the pattern is overhead. For agents with very tight budgets, the right shape is budget-bound refusal — refuse goals that exceed the budget rather than degrade quality silently.

#### Production Failure Modes
Cost-model drift: Provider prices change, the cost model is stale, budgets are over- or under-spent. Mitigate by polling provider price metadata daily and recalibrating against actual spend weekly.

Worst-case-cost blow-out: A step's worst case is much worse than expected, and the budget is exceeded by a single bad step. Mitigate by enforcing per-step caps in addition to total caps.

Latency-quality coupling: The cheapest option is also the slowest. Tight latency budgets force expensive options. Surface this as an explicit trade-off the operator can tune.

#### Case Study
A research-summarization agent at a research-tools vendor operates under a per-query token budget (capped by the user's subscription tier). The scheduler picks between a deep multi-source synthesis (three model calls, ~\(0.40 per query), a shallow single-source extract (\)0.04), and a cached-with-rephrase response ($0.005), based on the residual budget at the moment of dispatch.

The pattern allowed the vendor to offer free-tier users a meaningful product (running on the cached/shallow paths) while reserving expensive paths for paid tiers, with measured quality fall-off of less than 8% from the highest tier on representative queries.

**Composition:** Pairs with: Tree-of-Thought Explorer (Agent 18), Auctioneer (Agent 44), Distillation (Agent 51).

---

### Agent 22 — The Backward Goal-Regression Agent

> **Tagline:** *Plans from the goal state backward toward the current state.*

#### The Problem & Production Reality
For goals with a small set of possible final states and a large set of possible intermediate states, forward planning is wasteful: the planner explores enormous regions of state space that never connect to the goal.

The user wants a specific output (a passing compliance audit, a signed contract, a deployed feature flag at 100% traffic). Forward planning from the current state can't help itself spending most of its budget on states that don't reach the goal.

The general problem is goal-directed search asymmetry: when goals are narrowly specified and starting states are broad, working backward is exponentially cheaper than working forward.

#### Why Naïve Approaches Fail
"Forward planning." Wastes most of the search budget on irrelevant branches.

"Generate the final answer, then explain how to get there." The "explanation" is often a rationalization, not a plan.

"Hard-code the backward plan." Works for a stable goal shape, but breaks the moment the goal changes.

#### The Mechanism
Backward goal-regression starts from the goal, applies reverse operators (state-action pairs that could produce a given state via a single action), and stops when the regression touches the current state. The result is a forward plan, derived backward.

# planning/backward_regression.py
from dataclasses import dataclass, field
from collections import deque

@dataclass
class State:
    """Domain-specific; here represented abstractly as a set of facts."""
    facts: frozenset[str]
    
    def satisfies(self, predicate: str) -> bool:
        return predicate in self.facts

@dataclass
class ReverseOperator:
    """A backward step: 'state s2 with these preconditions can be produced from s1 by action a'."""
    name: str
    action: str
    adds: frozenset[str]        # facts the action adds (must be in successor)
    deletes: frozenset[str]     # facts the action removes (must NOT be in successor)
    preconditions: frozenset[str]  # facts that must hold in predecessor

@dataclass
class BackwardPlan:
    actions: list[str]          # in forward execution order
    states: list[State]
    found: bool

class BackwardGoalRegressionAgent:
    def __init__(self, operators: list[ReverseOperator], *, max_depth: int = 20):
        self.operators = operators
        self.max_depth = max_depth
    
    def plan(self, current: State, goal_predicate: str) -> BackwardPlan:
        # 1. Goal as a partial state (just the goal predicate)
        goal_state = State(facts=frozenset({goal_predicate}))
        # 2. BFS backward from the goal
        seen: set[frozenset[str]] = {goal_state.facts}
        queue = deque([(goal_state, [])])
        while queue:
            state, path = queue.popleft()
            if len(path) > self.max_depth:
                continue
            # Touch the current state?
            if all(f in current.facts for f in state.facts):
                # Forward plan: reverse the backward path
                return BackwardPlan(
                    actions=list(reversed(path)),
                    states=[],  # would be re-derived by forward simulation
                    found=True,
                )
            # Expand: which operators could PRODUCE this state?
            for op in self.operators:
                if op.adds & state.facts:    # operator contributes to state
                    predecessor_facts = (state.facts - op.adds) | op.preconditions
                    # Cannot include both a fact and its negation, etc.
                    if not (predecessor_facts & op.deletes):
                        pred_state = State(facts=frozenset(predecessor_facts))
                        if pred_state.facts not in seen:
                            seen.add(pred_state.facts)
                            queue.append((pred_state, path + [op.action]))
        return BackwardPlan(actions=[], states=[], found=False)

#### Trade-offs and Alternatives
Backward regression needs reverse operators, which require domain modeling. For domains where forward operators are easy to write but reversing them is hard (anything with side effects on external systems), backward planning is impractical.

The pattern works best in domains with strong formal structure (compliance frameworks with explicit attestation rules, configuration spaces with declarative dependencies, mathematical proof construction).

For domains where neither forward nor backward search alone is tractable, meet-in-the-middle search runs both directions simultaneously and stops when they meet. It's the right pattern when the cost of going either direction is roughly symmetric.

#### Production Failure Modes
Operator incompleteness: The reverse operators don't cover all the actions that could produce a given state. The search finds no plan because it can't bridge the gap. Mitigate by validating operator coverage against historical forward executions.

Pseudo-completion: The search "touches" the current state via a superficial fact match but the deeper state doesn't actually align. The produced plan is wrong. Mitigate by validating the final plan with a forward simulator before returning.

Combinatorial blow-up: The backward fringe grows uncontrollably. Mitigate with heuristic guidance (admissible cost estimates per state) to focus expansion on promising regions.

#### Case Study
A regulatory-compliance agent at a financial-services firm regresses backward from each required attestation (for example, "SOC2 control X is in effect") to produce the minimal task list a compliance officer must complete.

The pattern produced 41% smaller task lists than the prior forward-planner baseline (which over-included tasks), and the time from "audit-requirement landed" to "task list available" dropped from a half-day of manual interpretation to under thirty seconds.

**Composition:** Pairs with: Constraint-Satisfaction (Agent 11), Symbolic-Neural Bridge (Agent 13), Tree-of-Thought Explorer (Agent 18).

---

## Capability: Memory: Persistence Across Time
Covers Agents 23 through 29.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 23** | The Episodic Buffer Agent | *Stores and retrieves recent interaction episodes with explicit time-and-actor structure.* | Memory-of-Self (Agent 27), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25). |
| **Agent 24** | The Semantic Memory Curator Agent | *Distills repeated patterns from episodes into long-term, generalized facts.* | Episodic Buffer (Agent 23), Provenance Tracker (Agent 55), Persistent Identity (Agent 29). |
| **Agent 25** | The Working-Memory Manager Agent | *Actively reshapes the model's context window for the current step.* | Vector-Store Curator (Agent 28), Forgetting-Policy (Agent 26), Hierarchical Decomposer (Agent 16). |
| **Agent 26** | The Forgetting-Policy Agent | *Prunes memory by relevance decay rather than by storage limits.* | Privacy-Preserving (Agent 57), Drift Detector (Agent 59), Episodic Buffer (Agent 23). |
| **Agent 27** | The Memory-of-Self Agent | *Maintains a self-model of the agent's own capabilities, limits, and history.* | Refusal Calibrator (Agent 54), Skill-Library Builder (Agent 48), Provenance Tracker (Agent 55). |
| **Agent 28** | The Vector-Store Curator Agent | *Manages embedding ingestion, sharding, and retrieval quality over the lifetime of a knowledge base.* | Schema-Inference (Agent 7), Drift Detector (Agent 59), Working-Memory Manager (Agent 25). |
| **Agent 29** | The Persistent Identity Agent | *Preserves user and agent identity across conversations, reboots, and version upgrades.* | Ambient Context (Agent 6), Privacy-Preserving (Agent 57), Episodic Buffer (Agent 23). |

### Detailed Pattern Breakdowns

### Agent 23 — The Episodic Buffer Agent

> **Tagline:** *Stores and retrieves recent interaction episodes with explicit time-and-actor structure.*

#### The Problem & Production Reality
The agent needs to remember what just happened. Not the prompt-completion log, but the structured story of which actors did what, in what order, and with what intermediate state.

For example, a user asks the agent about "that conversation last Tuesday with the engineering team about the migration" and the agent, without a structured episodic memory, has either no memory of it (the transcript scrolled out of the context window) or a useless memory of it (an unstructured log that the agent can't query semantically).

The general problem is typed, queryable history: making the agent's past interactions available as structured data, with explicit actors and timestamps, queryable by predicates that go beyond "find similar text."

#### Why Naïve Approaches Fail
"Keep the chat history in context." Works for short sessions, fails for anything longer than a few hundred turns, explodes in cost.

"Save the transcript to a vector store." Retrieves by text similarity, can't answer structural questions ("the last time this user expressed dissatisfaction").

"Save the transcript as a database row per turn." Useful for retrieval by keyword, loses the higher-level structure (who said what, what was decided, what changed state).

#### The Mechanism
Structured event capture rather than free-text logging. Time-and-actor indexing as first-class concerns. Eviction policies based on recency-weighted relevance, not pure LRU. A retrieval interface that returns structured events, not free text.

# memory/episodic.py
from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime, timedelta
import sqlite3, json

EventType = Literal[
    "user_message", "agent_response", "tool_call", "tool_result",
    "decision", "escalation", "constraint_applied", "memory_write"
]

@dataclass
class Episode:
    id: str
    type: EventType
    timestamp: datetime
    actors: list[str]               # user_id, agent_id, system_id, etc.
    thread_id: str
    parent_episode_id: str | None
    payload: dict                   # type-specific structured content
    embedding: list[float] | None = None
    importance: float = 0.5

class EpisodicBufferAgent:
    def __init__(self, store_path: str = ":memory:"):
        self.db = sqlite3.connect(store_path)
        self._init_schema()
    
    def _init_schema(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY, type TEXT, timestamp REAL,
                thread_id TEXT, parent_id TEXT, payload_json TEXT,
                actors_json TEXT, importance REAL, embedding BLOB
            );
            CREATE INDEX IF NOT EXISTS idx_thread ON episodes(thread_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_actor ON episodes(actors_json);
            CREATE INDEX IF NOT EXISTS idx_type ON episodes(type, timestamp);
        """)
    
    def record(self, episode: Episode) -> None:
        self.db.execute("""
            INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.id, episode.type, episode.timestamp.timestamp(),
            episode.thread_id, episode.parent_episode_id,
            json.dumps(episode.payload), json.dumps(episode.actors),
            episode.importance,
            self._serialize_embedding(episode.embedding),
        ))
        self.db.commit()
    
    def query_by_actor(self, actor_id: str, *, type: EventType | None = None,
                       since: datetime | None = None, limit: int = 50) -> list[Episode]:
        sql = "SELECT * FROM episodes WHERE actors_json LIKE ?"
        params: list = [f'%"{actor_id}"%']
        if type:
            sql += " AND type = ?"
            params.append(type)
        if since:
            sql += " AND timestamp > ?"
            params.append(since.timestamp())
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return [self._row_to_episode(r) for r in self.db.execute(sql, params)]
    
    def query_by_predicate(self, predicate: callable, *, limit: int = 50) -> list[Episode]:
        """Scan with a Python predicate; use sparingly on large stores."""
        out = []
        for row in self.db.execute("SELECT * FROM episodes ORDER BY timestamp DESC"):
            ep = self._row_to_episode(row)
            if predicate(ep):
                out.append(ep)
                if len(out) >= limit:
                    break
        return out
    
    def evict(self, *, retention: timedelta, importance_floor: float = 0.3):
        """Recency-weighted eviction: drop old episodes below the importance floor."""
        cutoff = (datetime.utcnow() - retention).timestamp()
        self.db.execute("""
            DELETE FROM episodes WHERE timestamp < ? AND importance < ?
        """, (cutoff, importance_floor))
        self.db.commit()

#### Trade-offs and Alternatives
A typed episodic store is operationally heavier than a chat-log. The cost is justified for agents that operate across sessions or that need to answer questions about their own past. For single-session agents (search-style or one-shot tools), a flat history is sufficient.

For very high-volume agents, replace SQLite with a real columnar store (Postgres with appropriate indexes, ClickHouse, BigQuery) and project frequent query shapes into materialized views. The interface to the rest of the agent stays the same, only the backend scales.

#### Production Failure Modes
Index growth: Indexes scale linearly with episode count. Without partitioning, query latency degrades. Partition by thread_id or by month for older data.

Privacy contamination: Episodes record everything they observe, including data the user did not intend to persist. Mitigate by routing every episode through the same redaction layer as the rest of the agent (Section 4.7), with stricter rules for the episodic store than for the in-context state.

Reactive memory: The agent records faithfully but never uses the episodes, so the buffer becomes write-only. Mitigate by including an explicit "consult episodic memory" step in any planner that benefits from history. Surface episodic recall to the operator in trace events.

#### Case Study
An executive-assistant agent at a venture-capital firm holds a structured episodic memory of every meeting, message, and decision involving its principal. The store contains approximately 18 months of activity (≈140,000 episodes) with per-episode embeddings and full structured payload. Recall queries from the agent typically return in under 200ms. The most-used predicate is "the last time the principal interacted with this entity," which the agent uses to set context for every new outreach.

The principal reports that they reduce their preparation time for new meetings by approximately 60% because the agent surfaces the relevant prior touchpoints unprompted.

**Composition:** Pairs with: Memory-of-Self (Agent 27), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25).

---

### Agent 24 — The Semantic Memory Curator Agent

> **Tagline:** *Distills repeated patterns from episodes into long-term, generalized facts.*

#### The Problem & Production Reality
Episodic memory stores instances. Semantic memory stores patterns. When an agent has seen "Bob owns the deploy process" twenty times across different conversations, an episodic store contains twenty events. A semantic store contains the generalized fact "Bob owns the deploy process." Provenance points to the source episodes, queryable as a stable fact rather than a probabilistic inference from twenty events.

The general problem is promoting recurring patterns into stable knowledge: turning the episodic into the semantic, with explicit provenance, contradiction handling, and the ability to invalidate when supporting evidence is later refuted.

#### Why Naïve Approaches Fail
"Run a summarizer over the episode store periodically." Produces summaries that are unstructured, lose provenance, and conflict with each other across runs.

"Ask the agent to remember things on demand." Brittle, depends on the agent's working memory, doesn't accumulate.

"Fine-tune the model on the episodes." Slow, expensive, and conflates training-data updates with operational state changes.

#### The Mechanism
A promotion policy that decides when an episodic pattern has accumulated enough support to become a semantic fact. An explicit representation of the fact with supporting evidence. A contradiction-detection step that surfaces conflicts when a new candidate fact disagrees with an existing one. A forgetting path when supporting evidence is later invalidated.

# memory/semantic.py
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import hashlib

@dataclass
class SemanticFact:
    id: str
    subject: str            # the entity the fact is about
    predicate: str          # the relation
    object: str             # the value
    evidence_episode_ids: list[str]
    first_observed: datetime
    last_confirmed: datetime
    confidence: float
    contradicting_facts: list[str] = field(default_factory=list)
    status: str = "active"   # "active" | "deprecated" | "contested"

class SemanticMemoryCuratorAgent:
    def __init__(self, episodic_store, *, promotion_threshold: int = 3):
        self.episodic = episodic_store
        self.promotion_threshold = promotion_threshold
        self.facts: dict[str, SemanticFact] = {}
        self._candidate_counts: dict[tuple, list[str]] = defaultdict(list)
    
    def ingest_episode(self, episode) -> list[SemanticFact]:
        """Extract candidate (subject, predicate, object) triples from an episode."""
        triples = self._extract_triples(episode)
        newly_promoted = []
        for s, p, o in triples:
            key = (s, p, o)
            self._candidate_counts[key].append(episode.id)
            if len(self._candidate_counts[key]) >= self.promotion_threshold:
                fact = self._promote(s, p, o, self._candidate_counts[key])
                newly_promoted.append(fact)
        return newly_promoted
    
    def _promote(self, subject, predicate, object_, evidence_ids) -> SemanticFact:
        fact_id = self._make_id(subject, predicate, object_)
        if fact_id in self.facts:
            existing = self.facts[fact_id]
            existing.evidence_episode_ids.extend(
                eid for eid in evidence_ids if eid not in existing.evidence_episode_ids)
            existing.last_confirmed = datetime.utcnow()
            existing.confidence = min(1.0, existing.confidence + 0.05)
            return existing
        # Check for contradictions
        contradictions = self._find_contradictions(subject, predicate, object_)
        fact = SemanticFact(
            id=fact_id, subject=subject, predicate=predicate, object=object_,
            evidence_episode_ids=list(evidence_ids),
            first_observed=datetime.utcnow(), last_confirmed=datetime.utcnow(),
            confidence=0.6,
            contradicting_facts=[c.id for c in contradictions],
            status="contested" if contradictions else "active",
        )
        self.facts[fact_id] = fact
        for c in contradictions:
            if c.id not in fact.contradicting_facts:
                fact.contradicting_facts.append(c.id)
            if fact.id not in c.contradicting_facts:
                c.contradicting_facts.append(fact.id)
            c.status = "contested"
        return fact
    
    def _find_contradictions(self, subject, predicate, object_) -> list[SemanticFact]:
        # A new fact contradicts an existing one if subject and predicate match
        # but object differs (for predicates that are functional / single-valued).
        if not self._is_functional(predicate):
            return []
        return [f for f in self.facts.values()
                if f.subject == subject and f.predicate == predicate
                and f.object != object_ and f.status == "active"]
    
    def invalidate(self, episode_id: str) -> list[SemanticFact]:
        """If an episode is later determined wrong, recompute affected facts."""
        affected = []
        for fact in self.facts.values():
            if episode_id in fact.evidence_episode_ids:
                fact.evidence_episode_ids.remove(episode_id)
                if len(fact.evidence_episode_ids) < self.promotion_threshold:
                    fact.status = "deprecated"
                    affected.append(fact)
        return affected
    
    def query(self, subject: str | None = None, predicate: str | None = None,
              status: str = "active") -> list[SemanticFact]:
        out = []
        for f in self.facts.values():
            if f.status != status:
                continue
            if subject and f.subject != subject:
                continue
            if predicate and f.predicate != predicate:
                continue
            out.append(f)
        return out
    
    def _is_functional(self, predicate: str) -> bool:
        # Predicates that should only have one value per subject (owns, reports_to, etc.)
        return predicate in {"owns", "reports_to", "is_a", "located_in"}

#### Trade-offs and Alternatives
Semantic promotion adds latency on episode ingestion and complexity around contradiction handling. For agents where the "facts" change frequently (a live operations agent observing real-time state), the semantic store creates more problems than it solves. So episodic-only is the right choice.

The pattern earns its keep when facts are mostly stable, when they accumulate over long horizons, and when other agents need to query stable knowledge.

A lighter alternative is manually-curated semantic memory: an operator-edited knowledge base that the agent reads from but doesn't write to. This avoids the contradiction-handling complexity at the cost of the operator's time.

#### Production Failure Modes
Premature promotion: A predicate is promoted after three observations but the observations are all from the same week and reflect a transient state. Mitigate by requiring temporal spread in the promotion threshold (three observations across three distinct days, not three observations in three minutes).

Stale active facts: A fact was promoted, the supporting episodes are pruned by the episodic forgetting policy, and the fact remains active without underlying evidence. Mitigate by reverifying long-active facts against recent episodes on a schedule.

Predicate explosion: The triple extractor generates hundreds of distinct predicates per agent (subtle phrasing differences). Mitigate by canonicalizing predicates against a controlled vocabulary on extraction.

#### Case Study
A sales-coaching agent at a SaaS vendor distills, over a quarter of recorded calls per rep, a stable model of each rep's strengths and gaps. Triples include (rep_X, strong_at, discovery_questioning), (rep_X, weak_at, pricing_objection_handling), with promotion threshold at five distinct calls.

Coaches report using the resulting semantic profile as their starting point for one-on-ones. The agent's profile is accepted as accurate (no override) approximately 78% of the time.

**Composition:** Pairs with: Episodic Buffer (Agent 23), Provenance Tracker (Agent 55), Persistent Identity (Agent 29).

---

### Agent 25 — The Working-Memory Manager Agent

> **Tagline:** *Actively reshapes the model's context window for the current step.*

#### The Problem & Production Reality
The context window is a scarce resource and growing slowly relative to demand. Without active management, the prompt for each step is whatever the framework concatenates by default (recent turns, the system prompt, retrieved documents) and it grows monotonically. Context bills grow with it. Quality often falls because relevant information is buried among irrelevant.

The general problem is per-step prompt composition: deciding, for each call, exactly which context elements to include based on predicted relevance to the upcoming reasoning, not on recency or framework defaults.

#### Why Naïve Approaches Fail
"Concatenate everything." Costs scale linearly with session length, and quality often degrades after the prompt exceeds the model's effective attention window.

"Use only the last K turns." Drops information that's no longer recent but is still relevant.

"Retrieve documents by similarity to the current message." Misses context that's relevant but not lexically similar, and over-retrieves when the current message is ambiguous.

#### The Mechanism
A per-step composition policy that selects context elements by their predicted relevance to the upcoming reasoning. A budget enforced at the composition layer, not discovered at the model boundary. An eviction policy for elements that have sat in context for several steps without being referenced. An instrumentation surface that lets an operator audit what was in context at each step.

# memory/working_memory.py
from dataclasses import dataclass, field
from typing import Protocol
from collections import OrderedDict

@dataclass
class ContextElement:
    id: str
    source: str        # "system" | "history" | "retrieval" | "tool_result" | ...
    content: str
    tokens: int
    priority: float    # 0-1; baseline relevance
    pinned: bool = False   # cannot be evicted
    last_referenced_step: int = -1

class RelevanceScorer(Protocol):
    def score(self, element: ContextElement, current_step_intent: str) -> float: ...

class WorkingMemoryManagerAgent:
    def __init__(self, scorer: RelevanceScorer, *, token_budget: int = 8000):
        self.scorer = scorer
        self.budget = token_budget
        self.elements: OrderedDict[str, ContextElement] = OrderedDict()
        self._step = 0
    
    def add(self, element: ContextElement) -> None:
        self.elements[element.id] = element
    
    def compose(self, intent: str) -> list[dict]:
        """Compose the prompt for the current step."""
        self._step += 1
        # 1. Score every element against the current intent
        scored = []
        for el in self.elements.values():
            if el.pinned:
                scored.append((1.0, el))
            else:
                rel = self.scorer.score(el, intent)
                # Decay elements not referenced recently
                decay = 0.95 ** (self._step - el.last_referenced_step) if el.last_referenced_step >= 0 else 1.0
                scored.append((rel * decay * el.priority, el))
        # 2. Pack greedily into budget
        scored.sort(key=lambda se: se[0], reverse=True)
        selected: list[ContextElement] = []
        used_tokens = 0
        for _, el in scored:
            if used_tokens + el.tokens <= self.budget:
                selected.append(el)
                used_tokens += el.tokens
                el.last_referenced_step = self._step
        # 3. Emit as messages
        return [{"role": self._role_for(el), "content": el.content} for el in selected]
    
    def evict_stale(self, max_age_steps: int = 20) -> int:
        """Remove elements never referenced in the last N steps."""
        to_remove = [
            eid for eid, el in self.elements.items()
            if not el.pinned and (self._step - el.last_referenced_step) > max_age_steps
        ]
        for eid in to_remove:
            del self.elements[eid]
        return len(to_remove)
    
    def audit_snapshot(self) -> dict:
        return {
            "step": self._step,
            "total_elements": len(self.elements),
            "pinned": sum(1 for el in self.elements.values() if el.pinned),
            "token_total": sum(el.tokens for el in self.elements.values()),
        }
    
    def _role_for(self, el: ContextElement) -> str:
        return {"system": "system", "tool_result": "user"}.get(el.source, "user")

#### Trade-offs and Alternatives
Working-memory management adds latency before each model call (the scoring pass) and operational complexity (the scorer has to be calibrated). The trade is worth it once a session exceeds a few thousand tokens. But before that, default concatenation is fine.

The scorer is the central component. For agents where the upcoming intent is hard to predict, the scorer's value collapses. For agents with structured intents (a planner producing typed steps), the scorer can be very accurate. Pick the pattern accordingly.

#### Production Failure Modes
Pinning errors: Too few pinned elements: critical context (the goal, the system prompt) is evicted. Too many pinned elements: the budget is consumed by pins. Mitigate by versioning the pin set and reviewing it on each major prompt-version update.

Scorer brittleness: The scorer learns a few keywords and stops generalizing. Mitigate by retraining (or re-prompting) the scorer on the agent's actual production traffic, not on a static evaluation set.

Reference-decay false positives: An element is not "referenced" in the model's reasoning but is still relevant. It gets decayed and evicted. Mitigate by treating element retention as a soft signal alongside scorer relevance, not a hard rule.

#### Case Study
A long-running research agent at a hedge-fund family rebuilds its context window from scratch every five steps from an external memory store, keeping working context under four thousand tokens regardless of session length.

The pattern is responsible for the agent's ability to sustain hour-long research sessions on a single goal at roughly 20% of the inference cost of a comparable non-managed-memory baseline (which crossed the model's effective attention threshold and degraded in quality). Operator audits of the per-step working memory revealed the scorer was correctly pinning the goal, current hypothesis, and active datasets, while rotating through documents and intermediate findings as needed.

**Composition:** Pairs with: Vector-Store Curator (Agent 28), Forgetting-Policy (Agent 26), Hierarchical Decomposer (Agent 16).

---

### Agent 26 — The Forgetting-Policy Agent

> **Tagline:** *Prunes memory by relevance decay rather than by storage limits.*

#### The Problem & Production Reality
Most agents forget by accident: a buffer rolled over, a TTL expired, or an index sharded. Deliberate forgetting is a different discipline: deciding what to forget based on a model of what is still useful, before the forgetting becomes a quality problem or a privacy liability.

The general problem is principled memory pruning: applying a retention policy that reflects what the agent actually needs, what the user has consented to retain, and what the legal/operational constraints permit.

#### Why Naïve Approaches Fail
"Keep everything forever." Privacy violation. Storage cost. Quality erosion as stale information accumulates.

"Delete by age." Drops valuable history along with stale data. Users complain about "forgotten" facts that were still useful.

"Delete by size budget." Triggers only when storage is exhausted. The wrong things often get evicted. The policy is essentially LRU plus surprise.

#### The Mechanism
An explicit relevance-decay function per memory class. A forgetting cadence not driven by storage pressure. An audit trail recording what was forgotten and why so the decision can be reviewed. A recovery interface when something forgotten turns out to be needed.

# memory/forgetting.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

@dataclass
class ForgettingPolicy:
    memory_class: str            # "episodic" | "semantic" | "skill" | "vector"
    retention_period: timedelta
    decay_fn: Callable[[float, timedelta], float]  # (importance, age) -> survival_score
    threshold: float             # survival score below this -> forget
    recovery_window: timedelta   # how long we can un-forget

class ForgettingPolicyAgent:
    def __init__(self, stores: dict[str, object], policies: dict[str, ForgettingPolicy]):
        self.stores = stores
        self.policies = policies
        self.audit_log = []      # what was forgotten when, and why
        self.tombstones = {}     # forgotten items still recoverable
    
    def run(self) -> dict:
        forgotten_counts = {}
        for class_name, policy in self.policies.items():
            store = self.stores[class_name]
            forgotten = []
            for item in list(store.iter_all()):
                age = datetime.utcnow() - item.created_at
                survival = policy.decay_fn(item.importance, age)
                if survival < policy.threshold:
                    self._forget(store, item, class_name, survival)
                    forgotten.append(item.id)
            forgotten_counts[class_name] = len(forgotten)
        self._prune_tombstones()
        return forgotten_counts
    
    def _forget(self, store, item, class_name: str, survival: float) -> None:
        # Move to tombstone (recoverable window)
        self.tombstones[item.id] = (item, datetime.utcnow(), class_name)
        store.delete(item.id)
        self.audit_log.append({
            "id": item.id, "class": class_name,
            "forgotten_at": datetime.utcnow(),
            "survival_score": survival,
        })
    
    def _prune_tombstones(self) -> None:
        now = datetime.utcnow()
        for tid in list(self.tombstones.keys()):
            _, forgotten_at, class_name = self.tombstones[tid]
            window = self.policies[class_name].recovery_window
            if now - forgotten_at > window:
                del self.tombstones[tid]
    
    def recover(self, item_id: str) -> object | None:
        """Un-forget within the recovery window."""
        if item_id not in self.tombstones:
            return None
        item, _, class_name = self.tombstones.pop(item_id)
        self.stores[class_name].insert(item)
        return item

# Example decay functions
def exponential_decay(importance: float, age: timedelta) -> float:
    half_life_days = 30 * max(importance, 0.1)
    days = age.total_seconds() / 86400
    return 0.5 ** (days / half_life_days)

def cliff_then_decay(importance: float, age: timedelta) -> float:
    if age < timedelta(days=7):
        return 1.0
    return exponential_decay(importance, age - timedelta(days=7))

#### Trade-offs and Alternatives
A forgetting policy adds operational overhead and creates real risk of forgetting something useful. The risk is justified when (a) the cost of accumulating stale data is high (privacy, storage, retrieval quality) and (b) the recovery window is wide enough that operator review can catch over-aggressive forgetting.

For agents under strict retention regulations (GDPR right-to-be-forgotten, HIPAA retention windows), the forgetting policy is mandatory, and the recovery window may itself be regulated to zero. For agents with no such constraints, default to longer windows and re-tune toward shorter ones as you observe what gets forgotten and never asked about again.

#### Production Failure Modes
Decay function mis-calibration: Important items are forgotten too aggressively, and users notice. Mitigate by sampling forgotten items for operator review and recalibrating the importance-decay parameters.

Tombstone leakage: Items "forgotten" remain in the tombstone for the recovery window. But from a privacy standpoint they're not actually forgotten. Mitigate by hard-deleting after the window and being clear with users about the meaning of "delete."

Forgetting cascades: A forgotten episodic item invalidates a semantic fact that depended on it, which invalidates a derived skill, which invalidates a downstream decision. Mitigate by tracking memory provenance graphs and propagating invalidation explicitly.

#### Case Study
A personal-finance agent at a consumer-fintech vendor maintains a forgetting policy that discards transaction-level detail after thirty days while preserving aggregate semantic facts (monthly spend patterns, recurring vendors, savings-rate trends). The policy satisfies both retention regulations (the vendor's retention obligation is 30 days for raw transactions, indefinite for aggregates) and product usefulness (the agent's per-user storage stays under 50KB while supporting useful long-term insights).

**Composition:** Pairs with: Privacy-Preserving (Agent 57), Drift Detector (Agent 59), Episodic Buffer (Agent 23).

---

### Agent 27 — The Memory-of-Self Agent

> **Tagline:** *Maintains a self-model of the agent's own capabilities, limits, and history.*

#### The Problem & Production Reality
Most agents have no idea what they themselves are good at. The agent's policy is opinionated about how to do tasks, but it has no opinion about whether it specifically can do this task. The result: agents that confidently attempt tasks they will fail at, agents that refuse tasks they would handle fine, and operators who can't tell from the agent's behavior which is which.

The general problem is meta-cognitive grounding: giving the agent an explicit, queryable model of its own capabilities, refusal classes, tool access, operational constraints, and historical performance.

#### Why Naïve Approaches Fail
"The model knows what it can do." It doesn't, in any calibrated sense. Its self-reports are unreliable.

"List capabilities in the system prompt." Captures intent, loses the empirical record (which tasks it actually succeeded or failed at).

"Track success metrics elsewhere." The agent can't access them at decision time.

#### The Mechanism
A structured self-model with explicit fields. An update path triggered by post-task evaluation. A query interface used by other patterns (notably Refusal Calibrator and Skill-Library Builder). A surfaceable explanation of "what I am and am not currently configured to do."

# memory/self_model.py
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

@dataclass
class CapabilityRecord:
    name: str
    description: str
    declared_supported: bool         # operator-asserted
    empirical_success_rate: float    # measured
    sample_count: int
    last_evaluated: datetime
    
    @property
    def confidence(self) -> float:
        # Wilson lower bound, simplified
        if self.sample_count == 0:
            return 0.5 if self.declared_supported else 0.0
        return max(0.0, self.empirical_success_rate - 1.96 / (self.sample_count ** 0.5))

@dataclass
class SelfModel:
    agent_id: str
    agent_version: str
    capabilities: dict[str, CapabilityRecord] = field(default_factory=dict)
    refusal_classes: list[str] = field(default_factory=list)
    tool_access: list[str] = field(default_factory=list)
    operational_constraints: dict = field(default_factory=dict)
    recent_outcomes: list[dict] = field(default_factory=list)   # last 1000

class MemoryOfSelfAgent:
    def __init__(self, agent_id: str, agent_version: str):
        self.model = SelfModel(agent_id=agent_id, agent_version=agent_version)
        self._max_outcomes = 1000
    
    def declare_capability(self, name: str, description: str) -> None:
        self.model.capabilities[name] = CapabilityRecord(
            name=name, description=description,
            declared_supported=True,
            empirical_success_rate=0.5, sample_count=0,
            last_evaluated=datetime.utcnow(),
        )
    
    def record_outcome(self, capability: str, succeeded: bool,
                       task_signature: str | None = None) -> None:
        cap = self.model.capabilities.setdefault(
            capability, CapabilityRecord(
                name=capability, description="",
                declared_supported=False,
                empirical_success_rate=0.5, sample_count=0,
                last_evaluated=datetime.utcnow(),
            )
        )
        # Online update of success rate (EMA)
        alpha = 1.0 / (cap.sample_count + 1)
        cap.empirical_success_rate = (
            (1 - alpha) * cap.empirical_success_rate + alpha * (1.0 if succeeded else 0.0)
        )
        cap.sample_count += 1
        cap.last_evaluated = datetime.utcnow()
        self.model.recent_outcomes.append({
            "capability": capability, "succeeded": succeeded,
            "task_signature": task_signature, "ts": datetime.utcnow(),
        })
        if len(self.model.recent_outcomes) > self._max_outcomes:
            self.model.recent_outcomes.pop(0)
    
    def can_i(self, capability: str, *, min_confidence: float = 0.7) -> tuple[bool, str]:
        cap = self.model.capabilities.get(capability)
        if cap is None:
            return False, f"capability:{capability} not in self-model"
        if cap.confidence < min_confidence:
            return False, (
                f"capability:{capability} confidence {cap.confidence:.2f} "
                f"below threshold {min_confidence:.2f} "
                f"(empirical {cap.empirical_success_rate:.2f}, n={cap.sample_count})"
            )
        return True, f"capability:{capability} confidence {cap.confidence:.2f}"
    
    def describe(self) -> str:
        """User-facing description of what the agent can and cannot do."""
        confident = [c for c in self.model.capabilities.values() if c.confidence >= 0.7]
        uncertain = [c for c in self.model.capabilities.values() if c.confidence < 0.7]
        lines = ["I am confident I can:"]
        for c in confident:
            lines.append(f"  - {c.description} ({c.empirical_success_rate:.0%}, n={c.sample_count})")
        lines.append("I am uncertain or struggling with:")
        for c in uncertain:
            lines.append(f"  - {c.description} ({c.empirical_success_rate:.0%}, n={c.sample_count})")
        return "\n".join(lines)

#### Trade-offs and Alternatives
Maintaining a self-model requires the post-task evaluation infrastructure to feed it (Chapter 14). For agents without that infrastructure, the self-model degenerates to a declared capability list, which is better than nothing but doesn't give the empirical grounding the pattern is for.

For very simple agents with one or two capabilities, the self-model adds overhead without benefit. The capabilities are obvious from the toolset. The pattern earns its keep when the agent has more than a handful of distinct capability classes, when performance varies across them, or when the agent is regularly asked to do things outside its declared scope.

#### Production Failure Modes
Capability mis-classification: The post-task evaluator labels a "success" as a "failure" or vice versa. The self-model drifts away from reality. Mitigate by sampling evaluator labels for human review and recalibrating.

Out-of-distribution overconfidence: The agent has a 95% success rate on a capability but the incoming task differs from prior tasks. The self-model's confidence is misleading. Mitigate by classifying tasks into sub-types and tracking per-sub-type success.

Self-deprecation spiral. A bad week of tasks pulls the self-model into pessimism. The agent starts refusing tasks it could have handled. Mitigate by bounding the influence of any single sample on the rolling success rate.

#### Case Study
A developer-tooling agent at a code-vendor maintains capability records for fifty distinct refactor classes (extract-method, inline-variable, rename-with-references, and so on) with per-class empirical success rates measured against a test suite. When asked to perform a class with confidence below 0.7, the agent declines and explains why, pointing to its own recorded performance.

The pattern reduces "agent did something wrong and we didn't catch it" reports by approximately 60%. The false-refusal rate is acceptable to operators because the agent's explanation makes the basis for declining clear.

**Composition:** Pairs with: Refusal Calibrator (Agent 54), Skill-Library Builder (Agent 48), Provenance Tracker (Agent 55).

---

### Agent 28 — The Vector-Store Curator Agent

> **Tagline:** *Manages embedding ingestion, sharding, and retrieval quality over the lifetime of a knowledge base.*

#### The Problem & Production Reality
A vector store at week one and a vector store at month twelve are different problems. Drift in the embedding model, growth in the corpus, distribution shift in the queries, and accumulation of stale or duplicate documents all degrade retrieval quality silently.

The standard "ingest documents, query at runtime" framing treats the store as inert. In production, an unmaintained store gets quietly worse every week.

The general problem is vector-store-as-system: treating the retrieval substrate as a living system with its own lifecycle (ingestion, re-embedding on model upgrade, sharding for access locality, deduplication, eviction, benchmarking) rather than as a one-time setup.

#### Why Naïve Approaches Fail
"Ingest once at launch." Quality decays as the corpus stales.

"Re-ingest periodically." Useful but indiscriminate. It doesn't catch the subtler issues (embedding drift, sharding mismatches).

"Trust the vector-store vendor." They handle the substrate, they don't curate your content.

#### The Mechanism
A query-set anchored quality benchmark run on cadence. A re-embedding policy keyed to embedding-model versions rather than to a fixed schedule. A deduplication pass that catches semantic duplicates, not only exact ones. A sharding strategy keyed to access patterns. An alarm path when benchmark quality regresses.

# memory/vector_curator.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class BenchmarkQuery:
    query_id: str
    text: str
    expected_doc_ids: list[str]   # the doc(s) the right answer should retrieve

@dataclass
class CurationRun:
    run_at: datetime
    benchmark_pass_rate: float
    duplicates_merged: int
    docs_reembedded: int
    docs_evicted: int

class VectorStoreCuratorAgent:
    def __init__(self, store, embedder, benchmark: list[BenchmarkQuery],
                 *, quality_floor: float = 0.85):
        self.store = store
        self.embedder = embedder
        self.benchmark = benchmark
        self.quality_floor = quality_floor
        self.history: list[CurationRun] = []
    
    def run_curation(self) -> CurationRun:
        run = CurationRun(
            run_at=datetime.utcnow(), benchmark_pass_rate=0.0,
            duplicates_merged=0, docs_reembedded=0, docs_evicted=0,
        )
        # 1. Re-embed on embedder version change
        if self.embedder.version != self.store.metadata.get("embedder_version"):
            run.docs_reembedded = self._reembed_all()
            self.store.metadata["embedder_version"] = self.embedder.version
        # 2. Semantic deduplication
        run.duplicates_merged = self._dedupe()
        # 3. Eviction by recency + access score
        run.docs_evicted = self._evict_low_value()
        # 4. Benchmark
        run.benchmark_pass_rate = self._benchmark()
        # 5. Alarm if below floor
        if run.benchmark_pass_rate < self.quality_floor:
            self._alarm(run)
        self.history.append(run)
        return run
    
    def _reembed_all(self) -> int:
        n = 0
        for doc in self.store.iter_documents():
            doc.embedding = self.embedder.embed(doc.text)
            self.store.update(doc)
            n += 1
        return n
    
    def _dedupe(self) -> int:
        # Find pairs with cosine similarity above threshold; merge older into newer
        clusters = self._cluster_by_similarity(threshold=0.97)
        merged = 0
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            keep = max(cluster, key=lambda d: d.last_accessed)
            for other in cluster:
                if other.id != keep.id:
                    keep.alias_ids.append(other.id)
                    self.store.delete(other.id)
                    merged += 1
        return merged
    
    def _evict_low_value(self) -> int:
        cutoff = datetime.utcnow() - timedelta(days=180)
        evicted = 0
        for doc in self.store.iter_documents():
            if doc.last_accessed < cutoff and doc.access_count < 3:
                self.store.delete(doc.id)
                evicted += 1
        return evicted
    
    def _benchmark(self) -> float:
        hits = 0
        for q in self.benchmark:
            top = self.store.search(q.text, k=10)
            top_ids = [d.id for d in top]
            if any(eid in top_ids for eid in q.expected_doc_ids):
                hits += 1
        return hits / len(self.benchmark)

#### Trade-offs and Alternatives
A curator agent costs compute (re-embedding, dedup, benchmarking) and operational attention (someone has to maintain the benchmark query set). The cost is justified when retrieval quality is a load-bearing property of the agent — when the agent's outputs depend critically on retrieving the right document.

For agents where retrieval is incidental (a tool that occasionally checks the knowledge base), running curation on a weekly cadence is sufficient. For agents where retrieval is central (a RAG-based research agent), daily curation and continuous benchmarking are warranted.

#### Production Failure Modes
Benchmark staleness: The benchmark query set was assembled at launch. The query distribution has shifted, and the benchmark is no longer representative. Mitigate by sampling production queries into the benchmark on a rolling basis.

Embedder upgrade catastrophe: A new embedder version is deployed. Re-embedding takes hours, and queries during the window are answered against a mixed-version store. Mitigate by blue-green re-embedding: build the new index alongside, swap atomically.

Sharding drift: Hot shards get hotter, query latency rises on them. Mitigate by monitoring per-shard load and rebalancing on schedule.

#### Case Study
An enterprise documentation assistant at a global software vendor sees retrieval quality improve, rather than decay, over its first year of operation because the curator catches and corrects each source of drift before it becomes a user complaint.

Documented benchmark pass-rate at launch: 81%, at month twelve: 89%. Without the curator, internal estimates put the at-month-twelve rate near 70% based on observed degradation patterns elsewhere.

**Composition:** Pairs with: Schema-Inference (Agent 7), Drift Detector (Agent 59), Working-Memory Manager (Agent 25).

---

### Agent 29 — The Persistent Identity Agent

> **Tagline:** *Preserves user and agent identity across conversations, reboots, and version upgrades.*

#### The Problem & Production Reality
An agent that doesn't know which user it's talking to is a chat interface, not an agent. Most production agent failures around personalization, history, and consent reduce to identity-resolution problems. The same person appears with one email address in one channel, a different one in another, a different session token in a third, and the agent treats each as a stranger and rebuilds context from scratch.

The general problem is identity stability across surfaces: maintaining the right notion of "who is talking" across the inconsistent surface representations actors take in different channels, and maintaining the right notion of "who am I" for the agent itself across version upgrades.

#### Why Naïve Approaches Fail
"Use the email address as the user ID." Breaks when the user changes email, has multiple emails, or interacts via channels without email (Slack ID, phone number, anonymous chat).

"Use the session token as the user ID." Loses identity across sessions.

"Let the model figure out who's talking from context." The model is bad at this and is exposed to identity spoofing.

#### The Mechanism
An identity resolver that maps surface identifiers to stable internal IDs. A privacy-respecting policy for which mappings can be persisted. A version-stable serialization of the agent's own identity so its long-term memory survives upgrades. An export-and-deletion path satisfying the user's right to take their history with them or remove it.

# memory/identity.py
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

@dataclass
class SurfaceIdentifier:
    channel: str           # "email" | "slack" | "phone" | "session" | ...
    value: str
    verified: bool         # have we confirmed the user controls this?
    first_seen: datetime
    last_seen: datetime

@dataclass
class Identity:
    internal_id: str
    canonical_name: str | None
    surface_identifiers: list[SurfaceIdentifier]
    consent_scopes: list[str]
    created_at: datetime
    
    def has_surface(self, channel: str, value: str) -> bool:
        return any(s.channel == channel and s.value == value
                   for s in self.surface_identifiers)

class PersistentIdentityAgent:
    def __init__(self, store):
        self.store = store
    
    def resolve(self, channel: str, value: str) -> Identity | None:
        """Map a surface identifier to an internal identity."""
        for identity in self.store.iter_identities():
            if identity.has_surface(channel, value):
                return identity
        return None
    
    def assert_identity(self, channel: str, value: str,
                        verified: bool = False) -> Identity:
        existing = self.resolve(channel, value)
        if existing:
            for s in existing.surface_identifiers:
                if s.channel == channel and s.value == value:
                    s.last_seen = datetime.utcnow()
                    if verified:
                        s.verified = True
            self.store.update(existing)
            return existing
        # New identity
        identity = Identity(
            internal_id=self._mint_id(),
            canonical_name=None,
            surface_identifiers=[SurfaceIdentifier(
                channel=channel, value=value, verified=verified,
                first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
            )],
            consent_scopes=[],
            created_at=datetime.utcnow(),
        )
        self.store.insert(identity)
        return identity
    
    def link(self, identity_a: Identity, channel: str, value: str,
             verified: bool) -> Identity:
        """Add a surface identifier to an existing identity."""
        identity_a.surface_identifiers.append(SurfaceIdentifier(
            channel=channel, value=value, verified=verified,
            first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
        ))
        self.store.update(identity_a)
        return identity_a
    
    def merge(self, source: Identity, target: Identity) -> Identity:
        """Two identities turn out to be the same person."""
        for s in source.surface_identifiers:
            if not target.has_surface(s.channel, s.value):
                target.surface_identifiers.append(s)
        for c in source.consent_scopes:
            if c not in target.consent_scopes:
                target.consent_scopes.append(c)
        self.store.delete(source.internal_id)
        # Re-link all memories from source to target
        self._relink_memories(source.internal_id, target.internal_id)
        self.store.update(target)
        return target
    
    def export(self, identity: Identity) -> dict:
        """User's right to take their data."""
        return {
            "identity": identity,
            "episodes": self._fetch_episodes(identity.internal_id),
            "semantic_facts": self._fetch_facts(identity.internal_id),
        }
    
    def delete(self, identity: Identity) -> None:
        """User's right to deletion."""
        self._purge_memories(identity.internal_id)
        self.store.delete(identity.internal_id)
    
    def _mint_id(self) -> str:
        return "id_" + hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:16]

#### Trade-offs and Alternatives
Identity resolution requires a real store and a real policy for when surface identifiers can be linked. The privacy implications are non-trivial: linking identifiers without consent is a problem, refusing to link them at all is also a problem. The pattern requires the operator to think carefully about which links are permitted automatically and which require explicit user consent.

For agents that operate strictly within one channel and don't need cross-channel identity, the pattern is overhead, a per-channel user record suffices. The pattern earns its keep when the agent operates across channels (chat, email, voice) or when the user's identity has to survive sessions and reboots.

#### Production Failure Modes
False linking: Two distinct users get merged because of a shared surface identifier (a shared family email). Mitigate by requiring verification before linking, and by allowing users to split a merged identity.

Failed linking. A user's two surface identifiers aren't linked because verification didn't happen. The agent treats them as separate users. Mitigate by surfacing the un-linked-but-likely-same suggestion to the user with explicit consent.

Version upgrade memory loss: The agent's own identity changes across versions. Old memories become unreachable. Mitigate by versioning the serialization format with explicit upward compatibility, and by running migration scripts on upgrade.

#### Case Study
A customer-success agent at an enterprise B2B vendor recognizes the same enterprise account whether contacted via email, Slack, in-product chat, or scheduled review meeting, and presents a unified history across all four. Linking is automatic for surface identifiers under the same email domain plus an organizational-membership check. Manual review is required to link surface identifiers across domains.

The pattern is responsible for the agent's measured 38-point improvement in customer-reported "feels like the same agent I talked to last time" satisfaction scores.

**Composition:** Pairs with: Ambient Context (Agent 6), Privacy-Preserving (Agent 57), Episodic Buffer (Agent 23).

---

## Capability: Tool Use: Reaching Outside the Model
Covers Agents 30 through 37.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 30** | The Tool Selector Agent | *Picks the right tool from a large registry without overwhelming the model with the full list.* | Side-Effect Auditor (Agent 37), Memory-of-Self (Agent 27), API-Schema Adapter (Agent 31). |
| **Agent 31** | The API-Schema Adapter Agent | *Adapts to a new API at runtime by reading its OpenAPI specification.* | Schema-Inference (Agent 7), Database Query Synthesizer (Agent 35), Tool Selector (Agent 30). |
| **Agent 32** | The Code-Execution Sandbox Agent | *Executes model-generated code in an isolated environment with recoverable failure semantics.* | Side-Effect Auditor (Agent 37), Refusal Calibrator (Agent 54), Browser-Driver (Agent 34). |
| **Agent 33** | The Shell-Operator Agent | *Drives a Unix shell with explicit safety policies and rollback semantics.* | Code-Execution Sandbox (Agent 32), Side-Effect Auditor (Agent 37), Constitution-Bound (Agent 53). |
| **Agent 34** | The Browser-Driver Agent | *Navigates web user interfaces via accessibility trees rather than pixel inspection.* | Document Layout (Agent 2), Side-Effect Auditor (Agent 37), Multimodal Grounding (Agent 1) — the vision-based fallback when the accessibility tree is incomplete. |
| **Agent 35** | The Database Query Synthesizer Agent | *Translates intent into SQL, Cypher, or similar query languages and validates before execution.* | Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Side-Effect Auditor (Agent 37). |
| **Agent 36** | The File-System Curator Agent | *Organizes, deduplicates, and indexes files in a directory the agent is responsible for.* | Forgetting-Policy (Agent 26), Vector-Store Curator (Agent 28), Privacy-Preserving (Agent 57). |
| **Agent 37** | The Side-Effect Auditor Agent | *Records every external side effect with enough fidelity to undo it.* | Shell-Operator (Agent 33), Constitution-Bound (Agent 53), Off-Switch-Compatible (Agent 60). |

### Detailed Pattern Breakdowns

### Agent 30 — The Tool Selector Agent

> **Tagline:** *Picks the right tool from a large registry without overwhelming the model with the full list.*

#### The Problem & Production Reality
A toolset of ten tools fits in a prompt. A toolset of two hundred does not. As the agent's toolset grows past a few dozen entries, two things happen: the prompt gets expensive (every tool description is in every call), and the policy gets worse (the model picks the closest-matching tool even when the right tool is several entries down the list). Without a selection layer, agent toolsets can't grow past a few dozen entries without quality collapse.

The general problem is scalable tool registries: making large tool collections usable by an agent without putting all of them in the prompt at once.

#### Why Naïve Approaches Fail
"Just put them all in the prompt." Cost scales linearly with toolset size. Quality degrades as the relevant tools get buried.

"Have the model pick the tool from a categorical menu first." Adds a turn. The model can't always categorize the user intent into the right bucket.

"Hard-code which tools are visible per task type." Works until task types proliferate. Fragile to toolset additions.

#### The Mechanism
A richly-described tool registry with structured fields beyond a one-line description. An embedding-based first-pass retrieval against a representation of the current task. An exact-match second pass for tools known to be required by the task type. And a fall-through behavior that surfaces "I don't have a tool for this" rather than forcing the policy to fabricate one.

# tools/selector.py
from dataclasses import dataclass, field

@dataclass
class ToolDescriptor:
    name: str
    description: str
    long_description: str            # detailed; not in prompt by default
    parameters: dict                 # JSON Schema
    side_effect_class: str           # "read" | "write" | "destructive"
    cost_class: str                  # "free" | "metered" | "billed"
    category: str
    keywords: list[str]
    embedding: list[float] = field(default_factory=list)

class ToolSelectorAgent:
    def __init__(self, registry: list[ToolDescriptor], embedder,
                 *, candidate_k: int = 15, final_k: int = 6):
        self.registry = registry
        self.embedder = embedder
        self.candidate_k = candidate_k
        self.final_k = final_k
        # Pre-compute embeddings on a richer text than just the description
        for t in registry:
            if not t.embedding:
                blob = (f"{t.name}\n{t.description}\n{t.long_description}\n"
                        f"keywords: {', '.join(t.keywords)}\ncategory: {t.category}")
                t.embedding = embedder.embed(blob)
    
    def select(self, task_description: str,
               required_categories: list[str] | None = None) -> list[ToolDescriptor]:
        task_emb = self.embedder.embed(task_description)
        # 1. Embedding-based retrieval
        scored = [(self._cosine(task_emb, t.embedding), t) for t in self.registry]
        scored.sort(key=lambda st: st[0], reverse=True)
        candidates = [t for _, t in scored[:self.candidate_k]]
        # 2. Force-include category requirements
        if required_categories:
            for cat in required_categories:
                cat_tools = [t for t in self.registry if t.category == cat]
                for t in cat_tools[:2]:
                    if t not in candidates:
                        candidates.append(t)
        # 3. Re-rank with a small LLM call on a richer prompt
        return self._rerank(task_description, candidates)[:self.final_k]
    
    def _rerank(self, task: str, candidates: list[ToolDescriptor]) -> list[ToolDescriptor]:
        # Simple reranker: a small model asked to score each candidate's fit
        # In production, train a reranker on tool-selection traces.
        ...
    
    def materialize_for_prompt(self, selected: list[ToolDescriptor]) -> list[dict]:
        """The compact form fed into the policy's tool list."""
        return [
            {"name": t.name, "description": t.description,
             "parameters": t.parameters, "side_effect_class": t.side_effect_class}
            for t in selected
        ]
    
    @staticmethod
    def _cosine(a, b):
        dot = sum(x*y for x, y in zip(a, b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

#### Trade-offs and Alternatives
The selector adds latency before every step (the retrieval pass) and complexity (the registry has to be maintained with rich metadata). For agents with fewer than fifteen tools, the pattern is overhead.

A useful simplification for medium toolsets is category-based static slicing: maintain a curated tool set per task type, switch slices at the start of each task, and skip the per-step retrieval. This works when task types are stable and few.

#### Production Failure Modes
Retrieval miss: The right tool isn't in the top-K because its description doesn't lexically or semantically match the task. Mitigate by enriching the description (the long_description and keywords fields exist for this) and by sampling production traces to identify recurring misses.

Force-inclusion overuse: Operators add too many required_categories. The candidate set is dominated by forced tools and the retrieval signal is lost. Mitigate by capping forced inclusions per call.

Stale embeddings: The registry grows, the embedder is upgraded, and the pre-computed embeddings are stale. Mitigate by versioning embeddings alongside the registry and recomputing on embedder change (same lifecycle as the Vector-Store Curator, Agent 28).

#### Case Study
A B2B operations agent at a logistics-platform vendor maintains a four-hundred-tool registry of internal APIs and SaaS connectors. The selector reduces that to a 6-tool prompt per step.

Quality measured against full-registry baselines (over a labeled evaluation set the operations team curates monthly) is within 2 percentage points of the impossible-in-production "show all tools" baseline, at roughly one-twentieth the per-step prompt cost.

**Composition:** Pairs with: Side-Effect Auditor (Agent 37), Memory-of-Self (Agent 27), API-Schema Adapter (Agent 31).

---

### Agent 31 — The API-Schema Adapter Agent

> **Tagline:** *Adapts to a new API at runtime by reading its OpenAPI specification.*

#### The Problem & Production Reality
When an agent is supposed to be able to use any API in a class — any CRM, any ticketing system, any cloud-storage vendor — hand-writing a tool wrapper per API doesn't scale. The integrations team becomes the bottleneck: each new customer integration takes days, and the agent's effective toolset is capped at whatever has been hand-wrapped.

The general problem is dynamic tool surfaces: turning a machine-readable API description into a typed agent-usable tool at runtime, without a human in the loop.

#### Why Naïve Approaches Fail
"Have the model construct HTTP requests directly." The model gets URLs and body shapes wrong. The failure mode is silent (the API returns 4xx, the model interprets the response as the answer).

"Generate tool wrappers offline." Works until the API changes, until a new customer wants a different API, or until the agent needs to handle a class of APIs rather than a specific one.

"Use a model with built-in API knowledge." The knowledge is stale and inconsistent across APIs.

#### The Mechanism
A parser that produces typed tool descriptors from OpenAPI (or GraphQL, AsyncAPI, gRPC reflection). A synthesis step that produces natural-language tool descriptions from the parsed schema. An argument-construction guard that validates against the schema before any call is made. An error-recovery path that maps API error responses back to actionable feedback.

# tools/api_adapter.py
from dataclasses import dataclass, field
import jsonschema, requests

@dataclass
class AdaptedTool:
    name: str
    description: str
    parameters: dict       # JSON Schema
    method: str            # "GET" | "POST" | ...
    url_template: str
    auth: dict             # how to authenticate
    response_schema: dict
    side_effect_class: str

class APISchemaAdapterAgent:
    def __init__(self, openapi_doc: dict, base_url: str, auth_provider):
        self.spec = openapi_doc
        self.base_url = base_url
        self.auth = auth_provider
    
    def derive_tools(self) -> list[AdaptedTool]:
        tools = []
        for path, methods in self.spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    continue
                tool = self._operation_to_tool(path, method, op)
                tools.append(tool)
        return tools
    
    def _operation_to_tool(self, path: str, method: str, op: dict) -> AdaptedTool:
        name = op.get("operationId") or f"{method}_{path.replace('/', '_').strip('_')}"
        # Synthesize a natural-language description from the spec
        description = op.get("summary") or op.get("description") or name
        # Build a JSON Schema for the call's arguments
        parameters = self._collect_parameters(op)
        # Classify side effect from method + tags
        side_effect = self._classify(method, op.get("tags", []))
        return AdaptedTool(
            name=name,
            description=description,
            parameters=parameters,
            method=method.upper(),
            url_template=self.base_url + path,
            auth=self.auth.descriptor(),
            response_schema=self._collect_response_schema(op),
            side_effect_class=side_effect,
        )
    
    def invoke(self, tool: AdaptedTool, args: dict) -> dict:
        # 1. Validate args against schema BEFORE making the call
        jsonschema.validate(args, tool.parameters)
        # 2. Bind URL params and query/body
        url = tool.url_template
        path_params = {p["name"]: args.pop(p["name"]) for p in tool.parameters.get("path_params", [])}
        for k, v in path_params.items():
            url = url.replace("{" + k + "}", str(v))
        # 3. Authenticate
        headers = self.auth.headers()
        # 4. Make the call
        resp = requests.request(tool.method, url, headers=headers, json=args)
        # 5. Map errors to actionable feedback
        if resp.status_code >= 400:
            return {"error": self._classify_error(resp), "status": resp.status_code,
                    "body": resp.text[:1000]}
        return {"result": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text}
    
    def _collect_parameters(self, op: dict) -> dict:
        schema = {"type": "object", "properties": {}, "required": [], "path_params": []}
        for p in op.get("parameters", []):
            schema["properties"][p["name"]] = p.get("schema", {"type": "string"})
            if p.get("required"):
                schema["required"].append(p["name"])
            if p["in"] == "path":
                schema["path_params"].append({"name": p["name"]})
        if "requestBody" in op:
            body_schema = op["requestBody"].get("content", {}).get(
                "application/json", {}).get("schema", {})
            schema["properties"].update(body_schema.get("properties", {}))
            schema["required"].extend(body_schema.get("required", []))
        return schema
    
    def _classify(self, method: str, tags: list[str]) -> str:
        if method.upper() in ("GET", "HEAD"):
            return "read"
        if method.upper() == "DELETE":
            return "destructive"
        return "write"
    
    def _classify_error(self, resp) -> str:
        if resp.status_code == 401:
            return "auth_failed"
        if resp.status_code == 403:
            return "forbidden"
        if resp.status_code == 404:
            return "not_found"
        if resp.status_code == 429:
            return "rate_limited"
        if 500 <= resp.status_code < 600:
            return "server_error"
        return "client_error"

#### Trade-offs and Alternatives
The adapter is only as good as the OpenAPI specs it consumes. Most public APIs have specs of varying quality, but many internal APIs don't have specs at all.

The pattern requires either spec-quality investment upstream or a tolerance for specs being wrong (graceful degradation when a derived tool doesn't actually work as documented).

For APIs where the spec is reliably good (Stripe, GitHub, the big SaaS vendors), the adapter is dramatically better than hand-wrapping. For APIs where the spec is unreliable, a thin hand-wrapped layer is more robust.

#### Production Failure Modes
Spec-API drift: The spec is right at some point. But then the API changes, the spec isn't updated, and the derived tools are broken. Mitigate by validating derived tools against contract tests before exposing them to the policy.

Authentication leakage: Credentials end up in tool descriptions exposed in prompts. Mitigate by routing all auth through the auth provider (the code shows this) so secrets are never in the descriptor itself.

Schema-validation false rejection. The schema is over-restrictive, and valid calls are rejected. Mitigate by sampling rejections for operator review and loosening schemas where the spec is incorrect.

#### Case Study
An integration-platform agent at a B2B vendor lets a user say "connect Salesforce and run this query" and turns the request into a validated, schema-typed call against the user's tenant without a developer ever touching the integration. The platform supports approximately 480 distinct APIs via this pattern, with hand-wrapping reserved for the dozen most-used APIs that need richer behavior than the spec alone supports.

**Composition:** Pairs with: Schema-Inference (Agent 7), Database Query Synthesizer (Agent 35), Tool Selector (Agent 30).

---

### Agent 32 — The Code-Execution Sandbox Agent

> **Tagline:** *Executes model-generated code in an isolated environment with recoverable failure semantics.*

#### The Problem & Production Reality
Generated code is a liability and an asset at the same time. It lets the agent do things that no fixed toolset can (like analyze a one-off CSV, transform an unusual data shape, or fit an ad-hoc model), but only if the execution environment is sandboxed against the consequences of getting it wrong. Without sandboxing, model-generated code is, structurally, remote code execution from a probabilistic source. That's approximately the worst possible posture.

The general problem is safe, reproducible code execution from untrusted-by-construction sources: providing a substrate on which the agent can run arbitrary code without the consequences leaking past the sandbox boundary.

#### Why Naïve Approaches Fail
"Just eval it." Code injection from prompts, escape from your process, data leaks via filesystem or network.

"Run it in a subprocess with the same user." Better than eval, no real isolation. Still has access to the filesystem, network, environment.

"Run it in a Docker container." Better, but containers share kernel and have a non-trivial attack surface. Without resource limits a runaway script can DoS the host.

#### The Mechanism
Per-call ephemeral sandboxes with explicit resource caps. Network egress restricted to an allowlist required for the task. Persistent state shared with the sandbox only via a typed mount. Structured output capture distinct from stdout. A failure classifier that maps sandbox exits to actionable feedback.

# tools/sandbox.py
from dataclasses import dataclass, field
import subprocess, tempfile, json, os
from pathlib import Path

@dataclass
class SandboxConfig:
    image: str = "python:3.11-slim"
    cpu_limit: str = "1"           # "1" = one CPU
    memory_limit_mb: int = 512
    wall_seconds: int = 30
    network_allowlist: list[str] = field(default_factory=list)
    permitted_imports: list[str] = field(default_factory=list)

@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    structured_output: dict | None
    exit_code: int
    timeout: bool
    classification: str            # "ok" | "syntax" | "runtime" | "timeout" | "policy" | "oom"

class CodeExecutionSandboxAgent:
    def __init__(self, config: SandboxConfig):
        self.config = config
    
    def execute(self, code: str, inputs: dict | None = None) -> SandboxResult:
        # 1. Static-check the code against permitted-imports
        violation = self._check_imports(code)
        if violation:
            return SandboxResult(
                success=False, stdout="", stderr=f"import_policy:{violation}",
                structured_output=None, exit_code=1, timeout=False,
                classification="policy",
            )
        # 2. Materialize the workspace
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            if inputs:
                (workspace / "inputs.json").write_text(json.dumps(inputs))
            # The agent's code is wrapped so it writes to a known path
            wrapped = WRAPPER.format(user_code=code)
            (workspace / "main.py").write_text(wrapped)
            # 3. Run the sandbox
            try:
                proc = subprocess.run(
                    self._docker_cmd(workspace),
                    capture_output=True, timeout=self.config.wall_seconds,
                    text=True,
                )
                timeout = False
                exit_code = proc.returncode
                stdout, stderr = proc.stdout, proc.stderr
            except subprocess.TimeoutExpired as e:
                return SandboxResult(
                    success=False, stdout=e.stdout or "", stderr="TIMEOUT",
                    structured_output=None, exit_code=124, timeout=True,
                    classification="timeout",
                )
            # 4. Capture structured output
            structured = None
            structured_path = workspace / "output.json"
            if structured_path.exists():
                try:
                    structured = json.loads(structured_path.read_text())
                except json.JSONDecodeError:
                    pass
            classification = self._classify(exit_code, stderr)
            return SandboxResult(
                success=(exit_code == 0),
                stdout=stdout, stderr=stderr,
                structured_output=structured, exit_code=exit_code,
                timeout=False, classification=classification,
            )
    
    def _docker_cmd(self, workspace: Path) -> list[str]:
        return [
            "docker", "run", "--rm",
            f"--cpus={self.config.cpu_limit}",
            f"--memory={self.config.memory_limit_mb}m",
            "--network=none",        # explicit; enable only via egress proxy
            "-v", f"{workspace}:/workspace:rw",
            "-w", "/workspace",
            self.config.image,
            "python", "main.py",
        ]
    
    def _check_imports(self, code: str) -> str | None:
        if not self.config.permitted_imports:
            return None
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"syntax_error:{e}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in self.config.permitted_imports:
                        return alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] not in self.config.permitted_imports:
                    return node.module
        return None
    
    def _classify(self, exit_code: int, stderr: str) -> str:
        if exit_code == 0:
            return "ok"
        if "MemoryError" in stderr or exit_code == 137:
            return "oom"
        if "SyntaxError" in stderr:
            return "syntax"
        return "runtime"

WRAPPER = """\
import json, sys, traceback

inputs = {{}}
try:
    with open("inputs.json") as f:
        inputs = json.load(f)
except FileNotFoundError:
    pass

output = {{}}
try:
{user_code}
except Exception as e:
    output["error"] = repr(e)
    output["traceback"] = traceback.format_exc()
    raise
finally:
    with open("output.json", "w") as f:
        json.dump(output, f)
"""

#### Trade-offs and Alternatives
The sandbox approach has real latency cost per call (Docker startup is hundreds of milliseconds at minimum) and operational complexity (the container runtime is itself a system that has to be maintained, secured, and scaled).

For agents that execute code rarely, the overhead is acceptable. For agents that execute code on every step, the latency budget for the sandbox itself becomes a constraint.

Lower-overhead alternatives include Python RestrictedPython, Web Workers for JavaScript, V8 isolates, and WebAssembly sandboxes. Each has its own trade-off in completeness, performance, and security. Pick based on the threat model: untrusted user data passing through the sandbox is a higher bar than untrusted model-generated code that the agent fully controls.

#### Production Failure Modes
Sandbox escape: Despite the best efforts, container/VM escape vulnerabilities exist. Mitigate by running the sandbox host with minimal capabilities, blast-radius isolation (one customer's sandbox cannot reach another's data), and continuous security patching.

Resource-limit evasion: Code that fork-bombs, allocates slowly to evade memory limits, or pegs CPU just under the limit. Mitigate by enforcing wall-time as the master limit. Nothing escapes a wall-time kill.

Side-channel leakage: Code that reads timing or other side channels to infer information from the host. Mitigate by minimizing what the host has that's worth leaking. The sandbox host should hold no secrets the sandboxed code shouldn't see.

#### Case Study
A data-analysis agent at a business-intelligence vendor exposes a sandboxed Python environment with a curated set of libraries (pandas, numpy, scikit-learn, matplotlib), allowing analysts to ask any question over their data without the agent ever needing a hardcoded analytical tool. Median sandbox-execution latency is 1.8 seconds. The sandbox-escape rate measured against red-team exercises is zero across two years of operation.

The pattern is responsible for the agent handling approximately 70% of ad-hoc analytics requests at customer sites end-to-end.

**Composition:** Pairs with: Side-Effect Auditor (Agent 37), Refusal Calibrator (Agent 54), Browser-Driver (Agent 34).

---

### Agent 33 — The Shell-Operator Agent

> **Tagline:** *Drives a Unix shell with explicit safety policies and rollback semantics.*

#### The Problem & Production Reality
When the agent's environment is a real system rather than an API, the natural tool is a shell. A shell is also the single most dangerous tool the agent can have: a misplaced rm, a sloppy redirect, or a wrong-directory chmod can destroy state that no rollback can recover. The default "give the agent shell access" posture is the worst-case combination of power and risk.

The general problem is shell access with structural safety: making shell-driven actions possible without making catastrophic mistakes possible.

#### Why Naïve Approaches Fail
"Just exec what the model says." Production incident, eventually.

"Allowlist commands." Works until you need to compose them. The model will find combinations the allowlist didn't anticipate.

"Run the shell as a low-privilege user." Necessary but not sufficient. Even an unprivileged shell can destroy the user's own files.

#### The Mechanism
A command interpreter that parses and classifies commands before execution. A denylist combined with an allowlist for state-modifying operations. A snapshot policy for the working tree before any state-modifying batch. A confirmation gate that surfaces dangerous operations to the operator at policy-defined risk thresholds.

# tools/shell_operator.py
from dataclasses import dataclass, field
import subprocess, shlex, hashlib, tarfile, tempfile, os
from pathlib import Path
from enum import Enum

class CommandClass(Enum):
    READ_ONLY = "read_only"
    STATE_MODIFYING = "state_modifying"
    DESTRUCTIVE = "destructive"
    FORBIDDEN = "forbidden"

DESTRUCTIVE_COMMANDS = {"rm", "shred", "mkfs", "dd", "fdisk", "shutdown", "reboot"}
STATE_MODIFYING_COMMANDS = {"git", "npm", "pip", "make", "cp", "mv", "mkdir", "chmod", "chown"}
READ_ONLY_COMMANDS = {"ls", "cat", "grep", "find", "head", "tail", "wc", "pwd", "echo"}

@dataclass
class ShellResult:
    command: str
    classification: CommandClass
    executed: bool
    stdout: str
    stderr: str
    exit_code: int
    snapshot_id: str | None = None

class ShellOperatorAgent:
    def __init__(self, working_dir: Path, *, confirmation_callback=None,
                 allow_destructive: bool = False):
        self.working_dir = working_dir
        self.confirm = confirmation_callback or (lambda cmd: False)
        self.allow_destructive = allow_destructive
        self._snapshots = {}
    
    def execute(self, command: str) -> ShellResult:
        cls = self._classify(command)
        if cls == CommandClass.FORBIDDEN:
            return ShellResult(command=command, classification=cls, executed=False,
                               stdout="", stderr="forbidden", exit_code=1)
        if cls == CommandClass.DESTRUCTIVE:
            if not self.allow_destructive:
                return ShellResult(command=command, classification=cls, executed=False,
                                   stdout="", stderr="destructive_not_permitted", exit_code=1)
            if not self.confirm(command):
                return ShellResult(command=command, classification=cls, executed=False,
                                   stdout="", stderr="operator_denied", exit_code=1)
        snapshot_id = None
        if cls in (CommandClass.STATE_MODIFYING, CommandClass.DESTRUCTIVE):
            snapshot_id = self._snapshot()
        proc = subprocess.run(
            command, shell=True, cwd=self.working_dir,
            capture_output=True, text=True, timeout=60,
        )
        return ShellResult(
            command=command, classification=cls, executed=True,
            stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode,
            snapshot_id=snapshot_id,
        )
    
    def rollback(self, snapshot_id: str) -> bool:
        if snapshot_id not in self._snapshots:
            return False
        archive = self._snapshots[snapshot_id]
        # Wipe working dir contents, restore from archive
        for item in self.working_dir.iterdir():
            if item.is_dir():
                subprocess.run(["rm", "-rf", str(item)], check=True)
            else:
                item.unlink()
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(self.working_dir)
        return True
    
    def _classify(self, command: str) -> CommandClass:
        # Parse pipes, redirects, command substitutions
        tokens = shlex.split(command)
        if not tokens:
            return CommandClass.FORBIDDEN
        head = tokens[0]
        # Forbidden patterns (sudo, escape characters, etc.)
        if head in ("sudo", "su") or "&&" in command or "||" in command:
            # Multi-command shells require per-segment analysis
            return self._classify_compound(command)
        if head in DESTRUCTIVE_COMMANDS:
            return CommandClass.DESTRUCTIVE
        if head in STATE_MODIFYING_COMMANDS:
            return CommandClass.STATE_MODIFYING
        if head in READ_ONLY_COMMANDS:
            return CommandClass.READ_ONLY
        return CommandClass.FORBIDDEN
    
    def _snapshot(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            with tarfile.open(tmp.name, "w:gz") as tf:
                tf.add(self.working_dir, arcname=".")
            snap_id = hashlib.sha256(open(tmp.name, "rb").read()).hexdigest()[:16]
            self._snapshots[snap_id] = tmp.name
        return snap_id

#### Trade-offs and Alternatives
Shell access is the highest-power, highest-risk tool category. Snapshotting before every modifying batch costs disk and latency.

For agents that operate in append-only or version-controlled environments (like a Git working tree or an object store with versioning), the snapshot can be replaced by a cheaper bookmark (the current commit or the current version stamp). The classifier needs continuous tuning against the agent's actual command patterns.

For environments where you can avoid shell access entirely like a typed API to the same underlying system, do that. The shell is a last resort.

#### Production Failure Modes
Classifier evasion: The model issues a command that evades classification through obfuscation (using find ... -delete instead of rm, command substitution that hides the destructive head). Mitigate by classifying the effects via a tracing wrapper rather than only by parsing the literal command.

Rollback drift: Snapshots accumulate, storage fills up. Apply a retention policy (the Forgetting-Policy Agent, Agent 26, applies here).

Working-dir escape: A command writes outside the working directory (absolute paths, symlinks). Mitigate by sandboxing the shell itself in a chroot or container.

#### Case Study
A developer-environment agent at a developer-tools company bootstraps new repositories on a developer's machine (clone, install dependencies, run setup scripts) under a shell-operator that snapshots the working state at the start and rolls back on any non-zero exit. The rollback path is invoked roughly 4% of the time. In the absence of the snapshot mechanism, those failures historically required manual cleanup.

The pattern's deployment was credited with eliminating "agent left my machine in a weird state" as a customer complaint category.

**Composition:** Pairs with: Code-Execution Sandbox (Agent 32), Side-Effect Auditor (Agent 37), Constitution-Bound (Agent 53).

---

### Agent 34 — The Browser-Driver Agent

> **Tagline:** *Navigates web user interfaces via accessibility trees rather than pixel inspection.*

#### The Problem & Production Reality
Many of the world's important interfaces are web pages with no API. The agent needs to log into vendor portals, file forms, scrape per-tenant dashboards, complete account-management flows that have never had an API and never will.

Pixel-based vision models can do this but are slow, expensive, and brittle when the site changes. Static scraping breaks on the first JavaScript-driven update.

The general problem is structured web automation: operating a real browser against real sites in a way that's robust, observable, and recoverable.

#### Why Naïve Approaches Fail
"Take a screenshot, ask the vision model to click." Works once, expensive, brittle to layout changes, slow.

"Use Selenium with hand-written selectors." Works until the page structure changes. Selectors are a maintenance nightmare across hundreds of sites.

"HTTP-only emulation of the user." Loses everything that depends on JavaScript, which is approximately every modern site.

#### The Mechanism
An accessibility-tree extractor with fallbacks for sites whose ARIA implementation is incomplete. A tree-to-action planner that picks the smallest sequence of interactions to reach the goal. A wait-for-stability discipline before each action. A screenshot-of-record captured at each action for later debugging.

# tools/browser_driver.py
from dataclasses import dataclass, field
from typing import Literal

ActionType = Literal["click", "type", "select", "navigate", "wait", "extract"]

@dataclass
class AccessibilityNode:
    role: str             # "button" | "textbox" | "link" | "heading" | ...
    name: str             # accessible name (label, text, alt)
    value: str | None
    enabled: bool
    bbox: tuple[float, float, float, float]
    children: list["AccessibilityNode"] = field(default_factory=list)
    css_selector: str | None = None    # backup if accessibility lookup fails

@dataclass
class BrowserAction:
    type: ActionType
    target_node_role: str | None = None
    target_node_name: str | None = None
    value: str | None = None
    url: str | None = None
    timeout_ms: int = 5000

@dataclass
class ActionResult:
    success: bool
    screenshot_path: str
    new_url: str | None
    tree_summary: str
    error: str | None = None

class BrowserDriverAgent:
    def __init__(self, browser):     # e.g., a Playwright Browser instance
        self.browser = browser
        self.page = None
    
    async def execute(self, action: BrowserAction) -> ActionResult:
        if action.type == "navigate":
            await self.page.goto(action.url)
        else:
            await self._wait_for_stability()
            tree = await self._extract_tree()
            target = self._find_node(tree, action.target_node_role, action.target_node_name)
            if target is None:
                return ActionResult(success=False, screenshot_path="",
                                    new_url=self.page.url, tree_summary=self._summarize(tree),
                                    error=f"target_not_found:{action.target_node_role}:{action.target_node_name}")
            if action.type == "click":
                await self.page.locator(target.css_selector).click()
            elif action.type == "type":
                await self.page.locator(target.css_selector).fill(action.value)
            elif action.type == "select":
                await self.page.locator(target.css_selector).select_option(action.value)
            elif action.type == "extract":
                value = await self.page.locator(target.css_selector).inner_text()
                return ActionResult(success=True,
                                    screenshot_path=await self._snapshot(),
                                    new_url=self.page.url,
                                    tree_summary=self._summarize(tree),
                                    error=None) | {"extracted": value}
        await self._wait_for_stability()
        return ActionResult(success=True, screenshot_path=await self._snapshot(),
                            new_url=self.page.url,
                            tree_summary=self._summarize(await self._extract_tree()))
    
    async def _wait_for_stability(self, *, max_wait_ms: int = 5000):
        """Wait for the DOM to stop changing."""
        await self.page.wait_for_load_state("networkidle", timeout=max_wait_ms)
    
    async def _extract_tree(self) -> AccessibilityNode:
        snapshot = await self.page.accessibility.snapshot()
        return self._convert(snapshot)
    
    def _find_node(self, root: AccessibilityNode, role: str | None,
                   name: str | None) -> AccessibilityNode | None:
        def walk(n):
            if (role is None or n.role == role) and (name is None or name.lower() in n.name.lower()):
                return n
            for c in n.children:
                hit = walk(c)
                if hit:
                    return hit
            return None
        return walk(root)
    
    async def _snapshot(self) -> str:
        path = f"/tmp/agent-screenshot-{id(self)}.png"
        await self.page.screenshot(path=path)
        return path

#### Trade-offs and Alternatives
Browser automation has irreducible latency (page loads are seconds, not milliseconds) and operational complexity (browsers are heavyweight, crash, and leak memory).

For tasks that can use an API, prefer the API. The browser-driver is the right pattern when no API exists or when the site's behavior depends on JavaScript-rendered state that the underlying API can't reproduce.

A pixel-based vision-language fallback (the naïve approach) is still useful as a backup for sites whose accessibility tree is incomplete or wrong. The hybrid pattern (accessibility-first, vision-fallback) is what most production browser agents look like.

#### Production Failure Modes
Accessibility-tree incompleteness: A modal dialog renders without ARIA labels, and the agent can't find its controls. Mitigate by detecting incomplete trees and falling back to vision-based localization with a screenshot.

Anti-bot detection: The site detects the automation and challenges it. Mitigate by using residential proxies, randomized user agents, and human-like timing. And by deciding explicitly which sites the agent is permitted to operate, with operator awareness.

State leakage across sessions: Cookies, local storage, or login state from one user's session leaks into another's. Mitigate by per-session browser contexts and explicit cleanup between sessions.

#### Case Study
A procurement back-office agent at a logistics firm places weekly orders across nine supplier portals — none of which expose an API — by driving each portal's accessibility tree. Average wall-clock time per portal is twenty-eight seconds (vs. forty-five seconds historical human time).

The agent processes approximately 1,400 orders per week with a measured action-success rate of 96%. The 4% of failures escalate to a human operator with the screenshot and tree summary attached.

**Composition:** Pairs with: Document Layout (Agent 2), Side-Effect Auditor (Agent 37), Multimodal Grounding (Agent 1) — the vision-based fallback when the accessibility tree is incomplete.

---

### Agent 35 — The Database Query Synthesizer Agent

> **Tagline:** *Translates intent into SQL, Cypher, or similar query languages and validates before execution.*

#### The Problem & Production Reality
A natural-language-to-SQL agent that runs the generated query directly is a security incident waiting to happen. Beyond security, raw text-to-SQL has accuracy problems: ambiguous column names, wrong joins, accidental cross joins, and queries that return wrong-but-plausible numbers. The user trusts the answer, the answer is wrong, the dashboard shows the wrong number, and decisions get made.

The general problem is safe and auditable natural-language-to-query translation: producing a query that does what the user meant, never does anything else, and is explained to the user before execution on consequential queries.

#### Why Naïve Approaches Fail
"Run whatever the model produces." Inevitable injection vulnerability, inevitable accuracy problems.

"Allow only SELECT queries." Limits but doesn't prevent damage (a wrong SELECT can still produce wrong numbers for downstream decisions).

"Have the model paraphrase the query before running." Adds a check but doesn't bound the query's safety properties structurally.

#### The Mechanism
Schema introspection at session start with a freshness policy. Query synthesis against a schema-aware grammar rather than free-form text-to-SQL. A static safety check covering read-only enforcement, parameterization, and join-cost bounds. A natural-language explanation produced before execution for user confirmation on consequential queries. A structured result interface that distinguishes data from metadata.

# tools/db_synthesizer.py
from dataclasses import dataclass, field
import sqlparse

@dataclass
class TableSchema:
    name: str
    columns: list[dict]            # {name, type, nullable, description}
    primary_key: list[str]
    foreign_keys: list[dict]
    row_count_estimate: int

@dataclass
class SynthesizedQuery:
    sql: str
    parameters: dict
    estimated_rows: int
    explanation: str               # natural language
    consequential: bool            # writes, or large reads, or sensitive tables
    safety_violations: list[str]

class DatabaseQuerySynthesizerAgent:
    def __init__(self, schema: list[TableSchema], synthesizer_llm, executor,
                 *, query_timeout_s: float = 30, max_rows: int = 100000):
        self.schema = schema
        self.llm = synthesizer_llm
        self.executor = executor
        self.timeout = query_timeout_s
        self.max_rows = max_rows
    
    def synthesize(self, intent: str) -> SynthesizedQuery:
        response = self.llm.call(
            messages=[
                {"role": "system", "content": SYNTHESIS_PROMPT.format(
                    schema=self._render_schema())},
                {"role": "user", "content": intent}
            ],
            schema=SYNTHESIS_SCHEMA,
        )
        synthesized = SynthesizedQuery(
            sql=response["sql"], parameters=response.get("parameters", {}),
            estimated_rows=response.get("estimated_rows", 0),
            explanation=response.get("explanation", ""),
            consequential=False, safety_violations=[],
        )
        synthesized.safety_violations = self._safety_check(synthesized)
        synthesized.consequential = self._is_consequential(synthesized)
        return synthesized
    
    def execute(self, query: SynthesizedQuery, *,
                approved_by_user: bool = False) -> dict:
        if query.safety_violations:
            return {"error": "safety_violations", "violations": query.safety_violations}
        if query.consequential and not approved_by_user:
            return {"error": "requires_approval", "explanation": query.explanation}
        return self.executor.run(query.sql, query.parameters,
                                 timeout=self.timeout, max_rows=self.max_rows)
    
    def _safety_check(self, query: SynthesizedQuery) -> list[str]:
        violations = []
        parsed = sqlparse.parse(query.sql)
        if not parsed:
            violations.append("unparseable")
            return violations
        stmt = parsed[0]
        # Read-only enforcement
        if stmt.get_type() not in ("SELECT", "UNKNOWN"):
            violations.append(f"write_query:{stmt.get_type()}")
        # No multiple statements
        if ";" in query.sql.rstrip().rstrip(";"):
            violations.append("multiple_statements")
        # Parameterization check — all string-like values should be parameterized
        if self._has_string_literals(stmt) and not query.parameters:
            violations.append("unparameterized_literals")
        # Estimated rows over cap
        if query.estimated_rows > self.max_rows:
            violations.append(f"estimated_rows_over_cap:{query.estimated_rows}")
        return violations
    
    def _is_consequential(self, query: SynthesizedQuery) -> bool:
        if query.estimated_rows > 10000:
            return True
        # Heuristic: queries touching tables marked sensitive
        for table in self.schema:
            if table.name in query.sql and "sensitive" in (table.columns[0].get("tags") or []):
                return True
        return False
    
    def _render_schema(self) -> str:
        out = []
        for t in self.schema:
            cols = ", ".join(f"{c['name']} {c['type']}" for c in t.columns)
            out.append(f"TABLE {t.name} ({cols}); rows~{t.row_count_estimate}")
        return "\n".join(out)

#### Trade-offs and Alternatives
Schema-aware synthesis adds latency (schema introspection, safety checking) and operational complexity (the schema has to be kept in sync, queries against stale schemas fail).

For agents operating against a small, stable schema, the cost is low. For agents operating across many tenants' schemas, the freshness policy becomes a real concern.

For databases with constrained query interfaces (a parameterized stored-procedure surface or a Looker-style modeling layer), the synthesizer should target the constrained interface rather than raw SQL. The constraint surface already encodes most of the safety properties.

#### Production Failure Modes
Wrong join: The synthesizer joins on the wrong keys, and the result is plausible but wrong. Mitigate by enforcing primary-key/foreign-key adherence in the safety check, refusing joins that don't follow declared relationships.

Schema drift: Tables are added, columns are renamed. The cached schema is stale, and synthesis fails on real tables or succeeds on phantom ones. Mitigate by refreshing the schema on a short TTL and invalidating cached schemas on detected drift.

Synthesizer hallucination of columns: The model invents a column name that doesn't exist. Mitigate by parsing the SQL post-synthesis and verifying every referenced column exists in the schema (reject and re-prompt if not).

#### Case Study
A self-service analytics product at a mid-sized enterprise replaces approximately 70% of ad-hoc analyst requests with synthesizer-driven queries. Every query is explained in natural language to the requesting user before execution on consequential queries.

The user-confirmed accuracy of the explanations (sampled and reviewed) is 91%, and the rate of synthesized queries returning wrong-but-plausible numbers (compared to expert hand-written queries on the same intent) is 3.4%, down from 14% before the safety-check and explanation pattern was added.

**Composition:** Pairs with: Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Side-Effect Auditor (Agent 37).

---

### Agent 36 — The File-System Curator Agent

> **Tagline:** *Organizes, deduplicates, and indexes files in a directory the agent is responsible for.*

#### The Problem & Production Reality
When an agent operates against a file system over time, it accumulates files. Without curation, the accumulated files become unnavigable, and the agent itself can't find its own outputs. The user, too, ends up with a directory of inscrutably named files from a year of agent activity.

The general problem is maintained file-system state: treating a directory as a living artifact with a classification, deduplication, indexing, and retention policy, not as an accidental log.

#### Why Naïve Approaches Fail
"Let files accumulate." Directory becomes unusable, agent and user both lose track.

"Aggressively delete old files." Loses valuable history.

"Hand-organize." Doesn't scale across users or across agent activity.

#### The Mechanism
A classifier per file type with explicit confidence. A deduplication pass that catches both byte-equal and content-equal files. A search index updated incrementally. A retention policy with both age-based and importance-based decay.

# tools/file_curator.py
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

@dataclass
class FileRecord:
    path: Path
    content_hash: str        # SHA256 of bytes
    semantic_hash: str | None  # for media: perceptual hash; for text: shingled hash
    classification: str       # "document" | "code" | "data" | "media" | "other"
    importance: float
    created_at: datetime
    last_accessed: datetime
    size_bytes: int
    embedding: list[float] | None = None

class FileSystemCuratorAgent:
    def __init__(self, root: Path, classifier, embedder,
                 *, dedup_threshold: float = 0.97):
        self.root = root
        self.classifier = classifier
        self.embedder = embedder
        self.dedup_threshold = dedup_threshold
        self.index: dict[str, FileRecord] = {}
    
    def scan_and_update(self) -> dict:
        new_files = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            content_hash = self._hash(path)
            if path.name in self.index and self.index[path.name].content_hash == content_hash:
                continue   # unchanged
            classification = self.classifier.classify(path)
            record = FileRecord(
                path=path, content_hash=content_hash,
                semantic_hash=self._semantic_hash(path, classification),
                classification=classification,
                importance=self._estimate_importance(path),
                created_at=datetime.fromtimestamp(path.stat().st_ctime),
                last_accessed=datetime.fromtimestamp(path.stat().st_atime),
                size_bytes=path.stat().st_size,
            )
            if classification in ("document", "code"):
                record.embedding = self.embedder.embed(path.read_text(errors="ignore")[:8000])
            self.index[str(path)] = record
            new_files.append(record)
        return {"new": len(new_files), "total": len(self.index)}
    
    def dedupe(self) -> int:
        # Exact-duplicate pass
        seen_hashes: dict[str, FileRecord] = {}
        exact_dupes = 0
        for record in list(self.index.values()):
            if record.content_hash in seen_hashes:
                # Keep the more-recently-accessed copy
                kept = seen_hashes[record.content_hash]
                if record.last_accessed > kept.last_accessed:
                    record.path.replace(kept.path)
                    del self.index[str(kept.path)]
                else:
                    record.path.unlink()
                    del self.index[str(record.path)]
                exact_dupes += 1
            else:
                seen_hashes[record.content_hash] = record
        # Semantic-duplicate pass (slower; only on documents)
        semantic_dupes = self._dedupe_semantic()
        return exact_dupes + semantic_dupes
    
    def search(self, query: str, k: int = 10) -> list[FileRecord]:
        query_emb = self.embedder.embed(query)
        scored = [(self._cosine(query_emb, r.embedding), r)
                  for r in self.index.values() if r.embedding]
        scored.sort(key=lambda sr: sr[0], reverse=True)
        return [r for _, r in scored[:k]]
    
    def apply_retention(self, max_age: timedelta, importance_floor: float = 0.3) -> int:
        cutoff = datetime.utcnow() - max_age
        evicted = 0
        for record in list(self.index.values()):
            if record.last_accessed < cutoff and record.importance < importance_floor:
                record.path.unlink()
                del self.index[str(record.path)]
                evicted += 1
        return evicted

#### Trade-offs and Alternatives
A file-system curator is heavyweight relative to most agents' needs. For agents that produce occasional outputs into a flat directory, default file-system behavior is fine. The pattern earns its keep when the agent operates over long lifetimes, produces many outputs, or shares a directory with the user.

For environments where the file system is replaced by an object store or a content-addressable storage layer, the pattern reduces to maintaining an index over the store rather than the store itself.

#### Production Failure Modes
Privacy leak via index: The index contains file metadata that is itself sensitive (like filenames revealing project names or document classifications revealing patient categories). Mitigate by treating the index as having the same privacy class as the most sensitive file it indexes.

Aggressive deduplication: Two files that look semantically duplicate aren't actually duplicates (a draft and a final version). Mitigate by requiring near-identical content rather than near-identical embedding for dedup.

Eviction cascade: A file is evicted, and an agent that depended on it fails downstream. Mitigate by tracking inter-file dependencies and refusing to evict files in the closure of an active dependency.

#### Case Study
A research-engineer's working directory at a research lab is under continuous curation by a file-system curator agent: every new PDF is classified, deduplicated against the existing collection, and added to a searchable semantic index.

The directory has been under management for two years and contains approximately 3,400 files. The engineer's reported "I can't find that paper" rate dropped from frequent to nearly zero.

**Composition:** Pairs with: Forgetting-Policy (Agent 26), Vector-Store Curator (Agent 28), Privacy-Preserving (Agent 57).

---

### Agent 37 — The Side-Effect Auditor Agent

> **Tagline:** *Records every external side effect with enough fidelity to undo it.*

#### The Problem & Production Reality
Most agent failures in production aren't wrong answers, they are wrong actions. A wrong answer can be re-asked, while a wrong action has already affected the world. Without an auditor, the only way to recover from a bad batch of agent actions is to retrace by hand, which is slow, error-prone, and sometimes impossible.

The general problem is agent-action reversibility: making the agent's effects on the external world recoverable, with enough fidelity that an operator can undo a session's worth of actions in minutes, not days.

#### Why Naïve Approaches Fail
"Log every tool call." Logs are not undoable. You can read the log but you can't reverse it.

"Trust the tools to be idempotent." Most tools are not idempotent. The second invocation has different effects than the first.

"Use a database transaction." Works for database state, but doesn't help for external API calls, emails sent, files written, payments dispatched.

#### The Mechanism
A mutation classifier that distinguishes read-only from state-modifying tool calls. A pre-action snapshot of the affected external state where snapshotting is possible. A post-action diff captured against the snapshot. An explicit inverse-operation field populated by the tool itself rather than reconstructed. A rollback driver that an operator can invoke at the tool-call or session granularity.

# tools/side_effect_auditor.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
import json

@dataclass
class SideEffectRecord:
    record_id: str
    tool_name: str
    args: dict
    pre_state: dict | None       # what the world looked like before
    post_state: dict | None      # what the world looked like after
    inverse_operation: dict | None  # how to undo
    timestamp: datetime
    session_id: str
    success: bool
    reversible: bool

class SideEffectAuditorAgent:
    def __init__(self, audit_store):
        self.store = audit_store
        self._snapshot_fns: dict[str, Callable] = {}
        self._inverse_fns: dict[str, Callable] = {}
    
    def register_tool(self, tool_name: str, *,
                      snapshot: Callable[[dict], dict] | None = None,
                      inverse: Callable[[dict, dict], dict] | None = None) -> None:
        """Tools register their snapshot and inverse functions."""
        if snapshot:
            self._snapshot_fns[tool_name] = snapshot
        if inverse:
            self._inverse_fns[tool_name] = inverse
    
    def wrap(self, tool_name: str, args: dict, session_id: str,
             invoke: Callable[[dict], dict]) -> tuple[dict, SideEffectRecord]:
        """Invoke a tool with auditing wrapped around it."""
        record_id = self._mint_id()
        snapshot = self._snapshot_fns.get(tool_name)
        pre_state = snapshot(args) if snapshot else None
        try:
            result = invoke(args)
            success = True
        except Exception as e:
            result = {"error": str(e)}
            success = False
        # Capture post-state if we have a snapshot function
        post_state = snapshot(args) if snapshot else None
        inverse_fn = self._inverse_fns.get(tool_name)
        inverse_op = inverse_fn(args, result) if (inverse_fn and success) else None
        record = SideEffectRecord(
            record_id=record_id, tool_name=tool_name, args=args,
            pre_state=pre_state, post_state=post_state,
            inverse_operation=inverse_op,
            timestamp=datetime.utcnow(), session_id=session_id,
            success=success, reversible=bool(inverse_op),
        )
        self.store.append(record)
        return result, record
    
    def rollback_record(self, record_id: str) -> bool:
        record = self.store.get(record_id)
        if not record or not record.reversible:
            return False
        # Execute the inverse operation via the same tool surface
        inverse = record.inverse_operation
        try:
            self._execute_inverse(record.tool_name, inverse)
            return True
        except Exception:
            return False
    
    def rollback_session(self, session_id: str) -> dict:
        """Rollback all reversible records in a session, in reverse order."""
        records = self.store.list_by_session(session_id)
        records.sort(key=lambda r: r.timestamp, reverse=True)
        rolled = 0
        failed = 0
        irreversible = 0
        for r in records:
            if not r.success:
                continue
            if not r.reversible:
                irreversible += 1
                continue
            if self.rollback_record(r.record_id):
                rolled += 1
            else:
                failed += 1
        return {"rolled": rolled, "failed": failed, "irreversible": irreversible}

# Example tool registration
def _crm_create_lead_snapshot(args):
    # Snapshot is empty — the lead doesn't exist yet
    return {"existed": False}

def _crm_create_lead_inverse(args, result):
    return {"action": "delete_lead", "lead_id": result["lead_id"]}

#### Trade-offs and Alternatives
Auditing adds latency on every state-modifying call (snapshot, post-state capture, store write). For agents with very high tool-call throughput, the cost is non-trivial. Mitigate by sampling for low-stakes tools and being aggressive for high-stakes ones. The classifier per tool decides.

The reversibility property depends entirely on the tools cooperating. A tool that can't expose a snapshot function and an inverse function can't be audited at this level. The auditor records the attempt but can't promise reversibility. Be honest about this in the audit record.

#### Production Failure Modes
Inverse-operation drift: The inverse function for a tool worked at registration time. But the API changed, and the inverse no longer reverses correctly. Mitigate by validating inverses periodically with test invocations.

Partial-rollback inconsistency: A session rollback succeeds on some records and fails on others. The resulting state is internally inconsistent. Mitigate by surfacing the partial-success result to the operator and offering them the option to roll forward (re-apply successful records) instead.

Sensitive snapshots: The pre-state snapshot captures information the user didn't intend to retain. Mitigate by filtering snapshots through the same redaction layer as the rest of the agent.

#### Case Study
A workflow-automation agent at a SaaS vendor performed thousands of legitimate field updates per day for fourteen months without incident. Then it ran one bad batch from a flawed prompt revision that updated approximately 4,800 records incorrectly. The entirety of the bad batch was reverted in under one minute via the auditor's rollback_session.

The post-incident review identified the prompt revision in roughly twelve minutes. Without the auditor, the recovery would have required reconstructing the original values from backups (an exercise the company had estimated, in a previous incident, at six person-days).

**Composition:** Pairs with: Shell-Operator (Agent 33), Constitution-Bound (Agent 53), Off-Switch-Compatible (Agent 60).

---

## Capability: Coordination: Many Minds, One Outcome
Covers Agents 38 through 45.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 38** | The Router/Dispatcher Agent | *Routes incoming tasks to the specialist agent best suited to handle them.* | Memory-of-Self (Agent 27), Supervisor-Worker (Agent 45), Auctioneer (Agent 44). |
| **Agent 39** | The Debate Moderator Agent | *Orchestrates an adversarial debate between two reasoners to produce a more reliable answer.* | Self-Consistency Voter (Agent 15), Red-Team Auditor (Agent 56), Consensus-Builder (Agent 40). |
| **Agent 40** | The Consensus-Builder Agent | *Aggregates outputs from a heterogeneous swarm of agents into a single answer.* | Debate Moderator (Agent 39), Provenance Tracker (Agent 55), Pipeline Orchestrator (Agent 41). |
| **Agent 41** | The Pipeline Orchestrator Agent | *Sequences agents into producer-consumer chains with typed handoffs.* | Plan-Then-Execute (Agent 19), Provenance Tracker (Agent 55), Supervisor-Worker (Agent 45). |
| **Agent 42** | The Human-in-the-Loop Liaison Agent | *Escalates to a human and re-injects the human's input at well-defined decision points.* | Constitution-Bound (Agent 53), Episodic Buffer (Agent 23), Active Learner (Agent 52). |
| **Agent 43** | The Negotiation Agent | *Bargains across agent boundaries with explicit utility functions.* | Constraint-Satisfaction (Agent 11), Auctioneer (Agent 44), Provenance Tracker (Agent 55). |
| **Agent 44** | The Auctioneer Agent | *Runs an internal market mechanism for task allocation among a pool of agents.* | Resource-Aware Scheduler (Agent 21), Supervisor-Worker (Agent 45), Router (Agent 38). |
| **Agent 45** | The Supervisor-Worker Agent | *Manages a pool of identical workers with retries, partial failure handling, and result aggregation.* | Side-Effect Auditor (Agent 37), Pipeline Orchestrator (Agent 41), Auctioneer (Agent 44). |

### Detailed Pattern Breakdowns

### Agent 38 — The Router/Dispatcher Agent

> **Tagline:** *Routes incoming tasks to the specialist agent best suited to handle them.*

#### The Problem & Production Reality
When the system contains more than one specialist agent, something has to decide which one gets a given task. Without an explicit router, the routing logic ends up in the user-facing prompt ("if the question is about billing, use the billing agent"), which is fragile, hard to evaluate, and impossible to instrument. With an explicit router, routing is a first-class function: typed input, typed output, measurable accuracy, and replaceable independently of the specialists.

The general problem is load-balanced specialist dispatch: matching tasks to specialists in a way that is fast, accurate, observable, and resilient to specialist availability.

#### Why Naïve Approaches Fail
"Have one big agent handle everything." Quality is lower than per-specialist for any non-trivial agent collection. Cost is higher because the catch-all prompt is heavy.

"Use the user's first message to pick the agent and stick with it." Misses topic shifts mid-session.

"Let the model pick the agent on every turn." Adds a model call per turn. The model is overqualified for the job.

#### The Mechanism
A typed task description as the routing input. A registry of specialists with both capability descriptions and historical performance attached. A routing policy that combines task-type matching with load and cost considerations. An "ambiguous task" escape hatch that surfaces to a clarification flow rather than forcing a routing decision under uncertainty.

# coordination/router.py
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class Specialist:
    name: str
    description: str
    capabilities: list[str]              # tags matching task types
    historical_accuracy: dict[str, float]  # per task-type
    current_load: float                  # 0-1
    cost_per_call_cents: float

@dataclass
class RoutingDecision:
    specialist: str | None
    confidence: float
    rationale: str
    requires_clarification: bool
    alternative_specialists: list[str] = field(default_factory=list)

class RouterAgent:
    def __init__(self, specialists: list[Specialist], classifier_llm,
                 *, confidence_threshold: float = 0.7):
        self.specialists = {s.name: s for s in specialists}
        self.classifier = classifier_llm
        self.threshold = confidence_threshold
    
    def route(self, task_description: str, context: dict | None = None) -> RoutingDecision:
        # 1. Classify the task into capability tags with confidence
        classification = self._classify(task_description, context)
        if classification["confidence"] < self.threshold:
            return RoutingDecision(
                specialist=None, confidence=classification["confidence"],
                rationale=f"task classification confidence {classification['confidence']:.2f} below threshold",
                requires_clarification=True,
                alternative_specialists=self._top_candidates(classification, 3),
            )
        # 2. Match capability tags to specialists
        candidates = self._candidates_for(classification["tags"])
        if not candidates:
            return RoutingDecision(
                specialist=None, confidence=0.0,
                rationale=f"no specialist matches tags: {classification['tags']}",
                requires_clarification=True,
            )
        # 3. Score by capability match × historical accuracy × inverse-cost × inverse-load
        scored = []
        for c in candidates:
            score = self._score(c, classification)
            scored.append((score, c))
        scored.sort(key=lambda sc: sc[0], reverse=True)
        best = scored[0][1]
        return RoutingDecision(
            specialist=best.name, confidence=scored[0][0],
            rationale=f"capabilities match: {classification['tags']}; "
                      f"acc={best.historical_accuracy.get(classification['tags'][0], 0):.2f}",
            requires_clarification=False,
            alternative_specialists=[s.name for _, s in scored[1:3]],
        )
    
    def _score(self, specialist: Specialist, classification: dict) -> float:
        capability_match = sum(1 for t in classification["tags"] if t in specialist.capabilities)
        capability_match /= max(len(classification["tags"]), 1)
        accuracy = max(specialist.historical_accuracy.get(t, 0.5) for t in classification["tags"])
        cost_factor = 1.0 / max(1.0, specialist.cost_per_call_cents / 10)
        load_factor = 1.0 - specialist.current_load
        return capability_match * accuracy * cost_factor * load_factor

#### Trade-offs and Alternatives
The router adds one classification call per turn. For agents with two or three specialists and stable task types, a hand-written routing function (regex on intent keywords, plus a fallback) outperforms a model-based classifier in latency and reliability.

The pattern earns its keep when the specialist registry is larger than five, when task types aren't cleanly enumerable, or when the routing decision benefits from per-specialist accuracy data.

For sessions with sticky topics, route at session start and stick. Re-route only on detected topic shift, not on every message. This halves the routing-call volume.

#### Production Failure Modes
Classifier drift: The task-type distribution shifts, the classifier's training set is stale, and routing accuracy degrades. Mitigate by sampling routing decisions for human review and retraining on production traffic.

Capacity-blind routing: The best specialist is overloaded, and routing forces queueing instead of falling over to alternatives. Mitigate with explicit current_load in the scoring function (the code shows this).

Specialist-set drift: A specialist is deprecated, the router still routes to it, and calls fail. Mitigate by versioning the specialist registry and refusing to route to deprecated entries.

#### Case Study
A customer-facing enterprise assistant at a B2B vendor routes between a billing-specialist agent, a product-specialist agent, an integration-specialist agent, and a human-escalation path. The router runs on a small fine-tuned classifier (not a frontier model), with sub-100ms latency per routing decision.

Measured accuracy against a labeled evaluation set: 96%. The 4% routing errors most often involved tasks that genuinely overlapped two specialists, and the alternative-specialist list captured the correct second choice in 91% of misrouting cases.

**Composition:** Pairs with: Memory-of-Self (Agent 27), Supervisor-Worker (Agent 45), Auctioneer (Agent 44).

---

### Agent 39 — The Debate Moderator Agent

> **Tagline:** *Orchestrates an adversarial debate between two reasoners to produce a more reliable answer.*

#### The Problem & Production Reality
When a single reasoning chain is unreliable, one approach is sampling more chains (Self-Consistency Voter, Agent 15). Another is to have two reasoners argue.

The debate moderator sets up two policies, usually the same model with different stances. It gives them a shared question, lets them exchange arguments under a constrained protocol, and then either picks a winner or extracts the consensus the debate has revealed.

The pattern is particularly strong on questions where the failure mode is over-confidence rather than incompetence: questions the model could answer correctly but tends to over-commit to one interpretation. The debate forces explicit consideration of the other interpretation.

#### Why Naïve Approaches Fail
"Ask the same model both perspectives in one prompt." The model resolves the conflict internally and produces a single answer that hides the disagreement.

"Sample multiple times with high temperature." Catches stochastic noise, but doesn't catch systematic single-perspective bias.

"Run the question through two different models." Helpful but not the same as debate. The two models don't actually argue, they each independently answer.

#### The Mechanism
A strict turn protocol with a fixed budget of exchanges. Role assignments that bias the two reasoners toward opposing positions. A judge component that scores the debate against rubric-based criteria. A fallback that surfaces unresolved debate (rather than fabricating a resolution) when no clear winner emerges.

# coordination/debate_moderator.py
from dataclasses import dataclass, field

@dataclass
class DebateTurn:
    speaker: str          # "pro" | "con"
    round: int
    statement: str
    cites_previous_turn: int | None
    introduces_new_point: bool

@dataclass
class DebateVerdict:
    winner: str | None             # "pro" | "con" | None
    confidence: float
    consensus_points: list[str]
    open_disagreements: list[str]
    rationale: str

@dataclass
class Debate:
    question: str
    turns: list[DebateTurn]
    verdict: DebateVerdict | None

class DebateModeratorAgent:
    def __init__(self, pro_llm, con_llm, judge_llm,
                 *, max_rounds: int = 3):
        self.pro = pro_llm
        self.con = con_llm
        self.judge = judge_llm
        self.max_rounds = max_rounds
    
    def run(self, question: str, pro_stance: str, con_stance: str) -> Debate:
        debate = Debate(question=question, turns=[], verdict=None)
        for r in range(self.max_rounds):
            pro_turn = self._take_turn(self.pro, "pro", pro_stance, debate, r)
            debate.turns.append(pro_turn)
            con_turn = self._take_turn(self.con, "con", con_stance, debate, r)
            debate.turns.append(con_turn)
            # Optional: early termination if neither side introduces new points
            if r > 0 and not pro_turn.introduces_new_point and not con_turn.introduces_new_point:
                break
        debate.verdict = self._judge(debate)
        return debate
    
    def _take_turn(self, llm, side: str, stance: str, debate: Debate,
                   round_num: int) -> DebateTurn:
        prior_turns = self._format_turns(debate.turns)
        response = llm.call(
            messages=[
                {"role": "system", "content": DEBATE_PROMPT.format(
                    side=side, stance=stance, question=debate.question)},
                {"role": "user", "content": prior_turns}
            ],
            schema=DEBATE_TURN_SCHEMA,
        )
        return DebateTurn(
            speaker=side, round=round_num,
            statement=response["statement"],
            cites_previous_turn=response.get("cites_previous_turn"),
            introduces_new_point=response.get("introduces_new_point", True),
        )
    
    def _judge(self, debate: Debate) -> DebateVerdict:
        response = self.judge.call(
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": format_debate_for_judge(debate)}
            ],
            schema=VERDICT_SCHEMA,
        )
        return DebateVerdict(**response)

DEBATE_PROMPT = """\
You are debating the question: "{question}"
You are arguing the {side} side: {stance}

Rules:
1. Make ONE substantive point per turn.
2. If your opponent made a point you cannot refute, ACKNOWLEDGE it.
3. Do not invent facts. Cite evidence by source where you have it.
4. Concede gracefully when your position is weaker than alternatives.

Output JSON: {{
  "statement": "your turn's argument",
  "cites_previous_turn": <int or null>,
  "introduces_new_point": <bool>
}}
"""

JUDGE_PROMPT = """\
You judged a debate. Evaluate the arguments on the merits, not by which side argued harder.

Verdicts:
  - winner: "pro" if pro side prevailed, "con" if con prevailed, null if neither was decisive
  - confidence: how strong was the winner's case (0-1)
  - consensus_points: things both sides agreed on
  - open_disagreements: things that remained unresolved

Be honest. If the debate did not resolve, say so. Do not fabricate a winner.
"""

#### Trade-offs and Alternatives
Debate adds a multiplier on cost: both pro and con turns, plus a judge call, plus potentially multiple rounds. For two-round debates with a small judge, the multiplier is roughly five. The trade is worth it when the cost of a wrong answer materially exceeds the cost of the debate. It's overhead otherwise.

For questions where one side is structurally weaker (questions of fact rather than judgment), debate degenerates. The weaker side either concedes immediately or fabricates to keep arguing.

Use the pattern on genuinely contestable questions. For factual lookups, prefer the Self-Consistency Voter (Agent 15) or a direct retrieval-grounded answer.

#### Production Failure Modes
Fake debate: Both sides agree on the framing and exchange increasingly elaborate restatements of the same position. Mitigate by detecting low semantic-distance between turns and ending the debate early with a "no productive disagreement" verdict.

Judge bias: The judge consistently prefers one side's style. Mitigate by anonymizing turns before judgment (relabel speakers) and validating the judge's outputs against expert reviews.

Compute blow-out: Adversarial rounds run to the max budget for every question. Mitigate by tightening the early-termination heuristic (if a round produces no new points, stop).

#### Case Study
An investment-research agent at a long-short fund gates buy-versus-pass questions through a two-turn debate between a bull-stance and a bear-stance instance of the same underlying model. The moderator's verdict feeds the analyst's brief. Decisions where the moderator returned winner=null (genuine ambiguity) were sized roughly half the typical position and outperformed both confidence buckets in the 18 months post-deployment. The pattern's contribution to risk-adjusted returns was attributed to better sizing of ambiguous opportunities rather than improvement in directional calls.

**Composition:** Pairs with: Self-Consistency Voter (Agent 15), Red-Team Auditor (Agent 56), Consensus-Builder (Agent 40).

---

### Agent 40 — The Consensus-Builder Agent

> **Tagline:** *Aggregates outputs from a heterogeneous swarm of agents into a single answer.*

#### The Problem & Production Reality
Where the voter (Agent 15) samples one policy multiple times, the consensus-builder runs multiple distinct policies once and aggregates their outputs. The diversity of models — frontier, smaller, fine-tuned, specialist — means the aggregation has to handle disagreement that is structural, not just stochastic. Naïve concatenation produces an unreadable mess, while naïve averaging loses load-bearing detail.

The general problem is structural-disagreement aggregation: combining outputs from policies that legitimately disagree, in a way that preserves the disagreement where it's real and resolves it where it's illusory.

#### Why Naïve Approaches Fail
"Concatenate the answers." Doesn't address disagreement, presents all of them to the user.

"Pick the most-confident answer." Confidence is not calibrated across heterogeneous models.

"Have a model summarize the answers." Loses structure, may fabricate consensus that isn't there.

#### The Mechanism
A parser that maps each candidate output to a structured representation. An agreement-and-disagreement decomposition over the structure. An aggregation policy that handles partial agreement (keep agreed parts verbatim, flag disagreed parts with each candidate's position). A surfacing layer that distinguishes consensus from imposed conclusion.

# coordination/consensus.py
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class StructuredOutput:
    contributor: str
    claims: list[dict]            # [{"id": str, "text": str, "evidence": list[str]}]
    recommendations: list[dict]   # [{"action": str, "rationale": str}]
    confidence_per_claim: dict[str, float]

@dataclass
class ConsensusReport:
    agreed_claims: list[dict]
    disputed_claims: list[dict]   # each carries the per-contributor position
    unique_claims: list[dict]      # held by only one contributor
    consensus_recommendation: dict | None
    minority_recommendations: list[dict]

class ConsensusBuilderAgent:
    def __init__(self, claim_equivalence_fn=None, agreement_threshold: float = 0.6):
        self.equivalent = claim_equivalence_fn or self._default_equivalence
        self.threshold = agreement_threshold
    
    def build(self, outputs: list[StructuredOutput]) -> ConsensusReport:
        # 1. Cluster equivalent claims across contributors
        clusters = self._cluster_claims(outputs)
        # 2. Decide each cluster's status (agreed, disputed, unique)
        agreed, disputed, unique = [], [], []
        for cluster in clusters:
            contributors = set(c["contributor"] for c in cluster)
            participation = len(contributors) / len(outputs)
            if participation >= self.threshold:
                # Check whether they actually AGREE (same value) vs. just discuss the same topic
                values = set(c["text"] for c in cluster)
                if len(values) == 1:
                    agreed.append(self._merge_cluster(cluster))
                else:
                    disputed.append({
                        "topic": cluster[0]["text"][:80],
                        "positions": [{"contributor": c["contributor"], "text": c["text"]}
                                      for c in cluster],
                    })
            elif len(contributors) == 1:
                unique.append(cluster[0])
            else:
                disputed.append({
                    "topic": cluster[0]["text"][:80],
                    "positions": [{"contributor": c["contributor"], "text": c["text"]}
                                  for c in cluster],
                })
        # 3. Aggregate recommendations
        rec_clusters = self._cluster_recommendations(outputs)
        consensus_rec = self._consensus_rec(rec_clusters, len(outputs))
        minority_recs = [
            r for r in self._all_recs(rec_clusters)
            if not consensus_rec or r["action"] != consensus_rec["action"]
        ]
        return ConsensusReport(
            agreed_claims=agreed,
            disputed_claims=disputed,
            unique_claims=unique,
            consensus_recommendation=consensus_rec,
            minority_recommendations=minority_recs,
        )
    
    def _cluster_claims(self, outputs: list[StructuredOutput]) -> list[list[dict]]:
        clusters: list[list[dict]] = []
        for output in outputs:
            for claim in output.claims:
                claim_with_attrib = {**claim, "contributor": output.contributor}
                placed = False
                for cluster in clusters:
                    if self.equivalent(cluster[0], claim_with_attrib):
                        cluster.append(claim_with_attrib)
                        placed = True
                        break
                if not placed:
                    clusters.append([claim_with_attrib])
        return clusters
    
    def _default_equivalence(self, a: dict, b: dict) -> bool:
        # Production: use embedding similarity. Here: shingle overlap.
        return self._jaccard(a["text"], b["text"]) > 0.7
    
    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        shingles_a = set(a[i:i+3] for i in range(len(a) - 2))
        shingles_b = set(b[i:i+3] for i in range(len(b) - 2))
        if not shingles_a or not shingles_b:
            return 0.0
        return len(shingles_a & shingles_b) / len(shingles_a | shingles_b)

#### Trade-offs and Alternatives
The consensus builder requires structured outputs from each contributor. For systems where contributors produce free text, an upstream extraction step is needed (this is itself work).

The pattern is heavy. Lighter alternatives include simple voting on a discrete answer space or hierarchical hand-off (one agent's output is the next agent's input, with no parallel disagreement to resolve).

The pattern shines when disagreement is informative, that is when knowing that the three policies disagree is itself something the user needs to know. In contexts where the user just wants an answer, the disagreement information is noise.

#### Production Failure Modes
False consensus: Different policies use different phrasings for the same claim. The equivalence function clusters too aggressively, declaring agreement where there is partial disagreement. Mitigate by tuning the threshold and by sampling reported consensus for human review.

Cluster fragmentation: Different phrasings of the same claim end up in different clusters. The report shows disagreement where there's consensus. Mitigate by improving the equivalence function (embedding-based, not shingle-based).

Recommendation suppression: A minority recommendation that's actually correct gets buried below the consensus. Mitigate by always surfacing minority recommendations explicitly, not just as a footnote.

#### Case Study
A medical-decision-support tool at a hospital system runs the same clinical question against three independently maintained policy bases (an internal evidence-based guideline corpus, a literature-retrieval-augmented frontier model, and a specialist-tuned smaller model). The consensus builder presents the clinician with explicit agreed conclusions, disputed points with each policy's position, and any minority recommendations with their rationale.

Adoption studies showed clinicians valued the disagreement information at least as much as the consensus. The tool's primary value was surfacing cases where the policy bases disagreed, which historically had been invisible to the clinician.

**Composition:** Pairs with: Debate Moderator (Agent 39), Provenance Tracker (Agent 55), Pipeline Orchestrator (Agent 41).

---

### Agent 41 — The Pipeline Orchestrator Agent

> **Tagline:** *Sequences agents into producer-consumer chains with typed handoffs.*

#### The Problem & Production Reality
When the task naturally decomposes into stages — perceive, then reason, then act — the right coordination pattern isn't negotiation, it's a pipeline. The orchestrator wires the stages together with typed handoffs, runs them in order, surfaces inter-stage observability, and handles partial failure modes (retry the stage, skip the stage, fall back to a degraded stage).

The general problem is typed multi-stage agent composition: making the order, types, and failure handling of agent stages explicit, versioned artifacts rather than implicit in framework defaults.

#### Why Naïve Approaches Fail
"Chain LLM calls via prompt-templated includes." Loses type safety. The output of one stage might not match the input of the next.

"Have a meta-agent decide the order each time." Wastes compute, introduces inconsistency, obscures the pipeline as an inspectable artifact.

"Use a workflow engine." Often a fine choice. This pattern is the agent-specific version with explicit type contracts and per-stage observability.

#### The Mechanism
Stage definitions with typed input and output schemas. A topology specification separable from the stages themselves. Per-stage retry and fallback policies. Inter-stage tracing with explicit span boundaries. A back-pressure mechanism for stages that can't keep up with their predecessors.

# coordination/pipeline.py
from dataclasses import dataclass, field
from typing import Callable, Any, Literal
import jsonschema

@dataclass
class PipelineStage:
    name: str
    input_schema: dict
    output_schema: dict
    handler: Callable[[dict], dict]
    retry_policy: dict = field(default_factory=lambda: {"max_retries": 0})
    fallback: Callable[[dict, Exception], dict] | None = None
    timeout_seconds: float = 30
    cost_class: str = "metered"

@dataclass
class PipelineSpec:
    stages: list[str]              # in execution order
    handoffs: dict[str, str]       # stage_name -> next_stage_name
    version: str

@dataclass
class StageOutcome:
    stage: str
    success: bool
    output: dict
    attempts: int
    used_fallback: bool
    duration_ms: float

class PipelineOrchestratorAgent:
    def __init__(self, stages: list[PipelineStage], spec: PipelineSpec, tracer):
        self.stages = {s.name: s for s in stages}
        self.spec = spec
        self.tracer = tracer
    
    def execute(self, initial_input: dict) -> dict:
        current_input = initial_input
        outcomes: list[StageOutcome] = []
        with self.tracer.span("pipeline", version=self.spec.version):
            for stage_name in self.spec.stages:
                stage = self.stages[stage_name]
                outcome = self._run_stage(stage, current_input)
                outcomes.append(outcome)
                if not outcome.success:
                    return {
                        "status": "failed",
                        "failed_at": stage_name,
                        "outcomes": outcomes,
                    }
                current_input = outcome.output
        return {"status": "success", "final_output": current_input, "outcomes": outcomes}
    
    def _run_stage(self, stage: PipelineStage, input_payload: dict) -> StageOutcome:
        with self.tracer.span(f"stage.{stage.name}") as span:
            import time
            start = time.time()
            try:
                jsonschema.validate(input_payload, stage.input_schema)
            except jsonschema.ValidationError as e:
                return StageOutcome(
                    stage=stage.name, success=False, output={"error": f"input_schema:{e.message}"},
                    attempts=0, used_fallback=False, duration_ms=0,
                )
            attempts = 0
            last_error = None
            while attempts <= stage.retry_policy.get("max_retries", 0):
                attempts += 1
                try:
                    output = stage.handler(input_payload)
                    jsonschema.validate(output, stage.output_schema)
                    return StageOutcome(
                        stage=stage.name, success=True, output=output,
                        attempts=attempts, used_fallback=False,
                        duration_ms=(time.time() - start) * 1000,
                    )
                except Exception as e:
                    last_error = e
            if stage.fallback:
                try:
                    output = stage.fallback(input_payload, last_error)
                    return StageOutcome(
                        stage=stage.name, success=True, output=output,
                        attempts=attempts, used_fallback=True,
                        duration_ms=(time.time() - start) * 1000,
                    )
                except Exception:
                    pass
            return StageOutcome(
                stage=stage.name, success=False,
                output={"error": str(last_error)},
                attempts=attempts, used_fallback=False,
                duration_ms=(time.time() - start) * 1000,
            )

#### Trade-offs and Alternatives
Pipelines are great for linear or near-linear flows. For genuinely branching workflows, a workflow engine (Temporal, Airflow, Prefect) with agent stages as activities is a better fit. The pipeline pattern is the agent-specific equivalent for simpler topologies.

For very short pipelines (two stages), the orchestration overhead may not be justified. Inline the second stage.

The pattern earns its keep when there are three or more stages, when stages have meaningfully different cost or reliability profiles, or when the pipeline itself becomes a versioned artifact that needs evaluation.

#### Production Failure Modes
Schema-validation tightness: Schemas reject valid inputs because the schema is over-restrictive. Mitigate by sampling rejections for human review and loosening schemas where the rejection is wrong.

Fallback masking: A stage routinely uses its fallback because the primary handler is broken. The pipeline appears to succeed but the output quality is degraded. Mitigate by tracking fallback-usage rates and alarming when they exceed a threshold.

Pipeline version chaos: Multiple versions of the pipeline run in production simultaneously, and traces become hard to attribute. Mitigate by including the pipeline version in every trace event and surfacing it in operational dashboards.

#### Case Study
A content-publishing workflow at a media company pipelines a research agent (using retrieval and grounding), a drafting agent (using the research output and a style-guide prompt), a fact-checking agent (which independently verifies every cited claim), and a formatting agent (which produces the CMS-ready output). Each stage's failure mode is handled (research re-runs, drafting falls back to a more conservative model, fact-checking flags rather than fails, formatting has a manual-export fallback).

The pipeline composes roughly eight production patterns in the process and produces publishable drafts inside a defined twenty-minute envelope for 87% of inputs. The remaining 13% are flagged for editorial review with the specific stage and reason exposed.

**Composition:** Pairs with: Plan-Then-Execute (Agent 19), Provenance Tracker (Agent 55), Supervisor-Worker (Agent 45).

---

### Agent 42 — The Human-in-the-Loop Liaison Agent

> **Tagline:** *Escalates to a human and re-injects the human's input at well-defined decision points.*

#### The Problem & Production Reality
The pattern is named after what it is not: it's not "add a human reviewer at the end." A liaison agent is structurally aware of the decision points at which human input is required, the form that input must take to be useful, and the boundary conditions for proceeding without it.

The default human-in-the-loop integration most teams build is broken in predictable ways. The agent presents its full transcript and asks "is this OK?" The human, faced with a wall of text and no clear question, either rubber-stamps it or rejects it without specific feedback. Decisions get made on the basis of reviewer fatigue, not reviewer judgment.

The general problem is structured human intervention: making human input a typed, contextualized question with a defined input format and a defined re-entry point, not an "approve/reject" on an opaque session.

#### Why Naïve Approaches Fail
"Ask the human to approve the final output." Approval becomes a formality. The human can't meaningfully review enough to add value.

"Send the full transcript and ask 'any concerns?'" No structure. The reviewer can't tell what specifically needs attention.

"Block on every step." Defeats the point of automation.

#### The Mechanism
Decision-point declarations attached to plan steps or tool calls rather than to whole sessions. A structured-question template that elicits the input the agent needs. A defined waiting policy (block, time-out, default-and-flag, ask-asynchronously). A re-entry path that resumes the agent from the exact state at which the human was consulted, with the human's input bound into the resumed state.

# coordination/hitl_liaison.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class WaitingPolicy(Enum):
    BLOCK = "block"
    TIMEOUT = "timeout"
    DEFAULT_AND_FLAG = "default_and_flag"
    ASYNC = "async"

@dataclass
class HumanQuestion:
    question_id: str
    asked_at: datetime
    context: dict             # what the human needs to see
    question_text: str
    expected_answer_schema: dict
    options: list[str] | None  # if multiple choice
    default_if_timeout: dict | None
    timeout: timedelta
    policy: WaitingPolicy

@dataclass
class HumanResponse:
    question_id: str
    answered_at: datetime
    answer: dict
    actor: str               # who answered
    confidence_self_reported: float | None

class HumanInTheLoopLiaisonAgent:
    def __init__(self, message_channel, store):
        self.channel = message_channel
        self.store = store
    
    async def ask(self, question: HumanQuestion) -> HumanResponse | None:
        self.store.save_question(question)
        await self.channel.deliver(question)
        if question.policy == WaitingPolicy.BLOCK:
            return await self.store.await_response(question.question_id)
        elif question.policy == WaitingPolicy.TIMEOUT:
            try:
                return await self.store.await_response(question.question_id,
                                                       timeout=question.timeout)
            except TimeoutError:
                return None
        elif question.policy == WaitingPolicy.DEFAULT_AND_FLAG:
            try:
                return await self.store.await_response(question.question_id,
                                                       timeout=question.timeout)
            except TimeoutError:
                # Use default; flag for retrospective review
                self.store.flag_timeout(question.question_id)
                return HumanResponse(
                    question_id=question.question_id,
                    answered_at=datetime.utcnow(),
                    answer=question.default_if_timeout or {},
                    actor="system_default",
                    confidence_self_reported=None,
                )
        else:  # ASYNC
            return None  # caller will resume on response webhook
    
    def resume(self, session_id: str, response: HumanResponse, agent):
        """Resume the agent from the state at which the question was asked."""
        snapshot = self.store.load_session_snapshot(session_id, response.question_id)
        return agent.resume_from(snapshot, human_input=response.answer)

# Example: a contract-redlining agent asking about a non-standard clause
def ask_about_clause(liaison: HumanInTheLoopLiaisonAgent,
                     clause_text: str, similar_past_clauses: list,
                     session_id: str):
    return liaison.ask(HumanQuestion(
        question_id=mint_id(),
        asked_at=datetime.utcnow(),
        context={
            "clause_text": clause_text,
            "similar_past_clauses": similar_past_clauses,
            "this_contract_id": session_id,
        },
        question_text="Should we accept this clause as drafted, redline it, or reject?",
        expected_answer_schema={
            "type": "object",
            "properties": {
                "decision": {"enum": ["accept", "redline", "reject"]},
                "redline_text": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["decision"],
        },
        options=["accept", "redline", "reject"],
        default_if_timeout=None,
        timeout=timedelta(hours=2),
        policy=WaitingPolicy.DEFAULT_AND_FLAG,
    ))

#### Trade-offs and Alternatives
The liaison adds latency at every escalation point. For agents whose decisions have very low cost-of-error, escalation is overhead. For agents with high cost-of-error or regulatory review requirements, escalation is mandatory. The pattern is what makes it tolerable.

For very high-volume agents where escalation can swamp human capacity, the right pattern is sampled escalation: escalate only a configurable fraction of decisions, use the sampled human feedback to recalibrate the agent's confidence, and rely on the recalibration to reduce future escalation. This is closely related to the Active Learner (Agent 52).

#### Production Failure Modes
Escalation fatigue: Volume of questions to humans exceeds their capacity, so questions are rubber-stamped or ignored. Mitigate by per-reviewer rate-limits and by tuning the agent's confidence thresholds so only genuinely uncertain decisions escalate.

State-snapshot drift: The agent's state at the moment of question differs from the state at the moment of resumption (other actions have happened). Mitigate with immutable snapshots and explicit re-validation of preconditions on resume.

Ambiguous questions: The human can't tell what's being asked, so their answer is unusable. Mitigate by templating questions and reviewing the templates against actual reviewer feedback.

#### Case Study
A contract-redlining agent at a corporate-legal department escalates each non-standard clause to the appropriate human lawyer as a structured question and resumes redlining on receipt of the answer, with the lawyer's input persisted to the agent's semantic memory (Agent 24) for future contracts.

The pattern allowed the team to redline approximately 4× the contract volume per lawyer per quarter, with measured downstream-issue rates equal to or lower than the all-human baseline.

**Composition:** Pairs with: Constitution-Bound (Agent 53), Episodic Buffer (Agent 23), Active Learner (Agent 52).

---

### Agent 43 — The Negotiation Agent

> **Tagline:** *Bargains across agent boundaries with explicit utility functions.*

#### The Problem & Production Reality
When two agents have to agree on something (like a price, a schedule, or a resource allocation), and the agents represent different principals, the right coordination pattern is negotiation. Each agent holds an explicit utility function, exchanges proposals under a protocol, and updates its position based on the counterparty's signaling.

Without an explicit pattern, "agent-to-agent negotiation" degenerates into the two LLMs paraphrasing each other politely without reaching a decision.

The general problem is inter-principal bargaining: producing outcomes that are acceptable to each principal's interests, by agents that genuinely represent those interests rather than imitating a generic helpful tone.

#### Why Naïve Approaches Fail
"Tell the two agents to negotiate." Without explicit utility functions and protocol, they converge to neutral, balanced statements that decide nothing.

"Have one super-agent decide for both." Loses the principal-agent fidelity. Whichever principal trusts the super-agent more wins.

"Skip the negotiation, run an auction." The auctioneer pattern (Agent 44) works for many-to-one matching. But for two-to-two negotiation, it forces an artificial structure.

#### The Mechanism
An explicit utility-function representation for each negotiating agent. A protocol with bounded rounds and explicit moves (propose, accept, reject, counter, reveal). A reservation-value model that prevents the agent from accepting trivially against its own interests. A transcript that is auditable by the principal afterward.

# coordination/negotiation.py
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

class Move(Enum):
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    COUNTER = "counter"
    REVEAL = "reveal"
    WALK_AWAY = "walk_away"

@dataclass
class NegotiationMove:
    actor: str
    move_type: Move
    proposal: dict | None
    rationale: str
    round: int

@dataclass
class UtilityFunction:
    weights: dict[str, float]      # attribute -> weight
    
    def evaluate(self, proposal: dict) -> float:
        total = 0.0
        for attr, weight in self.weights.items():
            if attr in proposal:
                total += weight * proposal[attr]
        return total

@dataclass
class NegotiatingAgent:
    name: str
    utility: UtilityFunction
    reservation_value: float       # minimum acceptable utility
    aspiration_value: float        # opening position utility
    strategy_llm: object

@dataclass
class Negotiation:
    participants: list[NegotiatingAgent]
    moves: list[NegotiationMove]
    outcome: dict | None
    walked_away: list[str] = field(default_factory=list)

class NegotiationOrchestrator:
    def __init__(self, max_rounds: int = 10):
        self.max_rounds = max_rounds
    
    def run(self, agents: list[NegotiatingAgent], topic: str) -> Negotiation:
        negotiation = Negotiation(participants=agents, moves=[], outcome=None)
        for round_num in range(self.max_rounds):
            for agent in agents:
                move = self._take_move(agent, negotiation, round_num)
                negotiation.moves.append(move)
                if move.move_type == Move.WALK_AWAY:
                    negotiation.walked_away.append(agent.name)
                    return negotiation
                if move.move_type == Move.ACCEPT:
                    if self._all_accepted(agents, negotiation):
                        negotiation.outcome = self._last_proposal(negotiation)
                        return negotiation
        negotiation.outcome = None  # no agreement in budget
        return negotiation
    
    def _take_move(self, agent: NegotiatingAgent, negotiation: Negotiation,
                   round_num: int) -> NegotiationMove:
        last_proposal = self._last_proposal_against(agent, negotiation)
        if last_proposal:
            utility = agent.utility.evaluate(last_proposal)
            if utility < agent.reservation_value:
                # Reject or counter; never accept below reservation
                counter = self._produce_counter(agent, last_proposal, negotiation, round_num)
                return NegotiationMove(
                    actor=agent.name, move_type=Move.COUNTER,
                    proposal=counter, rationale="below_reservation",
                    round=round_num,
                )
            elif utility >= agent.aspiration_value or self._near_deadline(round_num):
                return NegotiationMove(
                    actor=agent.name, move_type=Move.ACCEPT,
                    proposal=last_proposal, rationale="acceptable",
                    round=round_num,
                )
            else:
                counter = self._produce_counter(agent, last_proposal, negotiation, round_num)
                return NegotiationMove(
                    actor=agent.name, move_type=Move.COUNTER,
                    proposal=counter, rationale="seeking_improvement",
                    round=round_num,
                )
        # No prior proposal — open with aspiration
        opening = self._produce_opening(agent)
        return NegotiationMove(
            actor=agent.name, move_type=Move.PROPOSE,
            proposal=opening, rationale="opening",
            round=round_num,
        )
    
    def _produce_counter(self, agent, opponent_proposal, negotiation, round_num):
        # The strategy LLM produces a counter that improves on the opponent's
        # proposal from the agent's perspective. Concedes more in later rounds.
        concession_factor = round_num / self.max_rounds
        ...

#### Trade-offs and Alternatives
Explicit negotiation requires explicit utility functions, which someone has to write. For domains where the utility is genuinely multi-attribute and the negotiation surface is rich (contract terms, scheduling, resource sharing), the investment is worthwhile. For domains where the surface is one number (price), an auctioneer (Agent 44) is simpler and sometimes better.

For negotiations where one principal is much more sophisticated than the other, mechanism design matters more than the protocol. Be explicit about which agent represents which side and what asymmetries exist.

#### Production Failure Modes
Utility mis-elicitation: The utility function doesn't reflect the principal's actual preferences, and the agent accepts terms the principal would reject. Mitigate by calibrating the utility function against historical principal-approved outcomes and validating sample-outcomes against principal review.

Protocol gaming: The strategy LLM finds patterns that exploit the protocol (always making maximally-aggressive counters, expecting the counterparty to relent). Mitigate by adversarial testing of the strategy against opposing strategies.

Walk-away over-use: The agent walks away from negotiations where a deal was available. Mitigate by tracking walk-away outcomes against post-hoc analyses of what would have been acceptable to the principal.

#### Case Study
A cross-organizational scheduling agent at a venture firm negotiates meeting times between two enterprises' assistant agents under the protocol above. The pattern produces a slot that both organizations' calendars approve without either calendar's contents leaking across the boundary.

Resolution time per meeting dropped from a median of 3.4 days (human email back-and-forth) to 17 minutes (agent-to-agent), with measured participant satisfaction (post-meeting survey) unchanged or slightly higher.

**Composition:** Pairs with: Constraint-Satisfaction (Agent 11), Auctioneer (Agent 44), Provenance Tracker (Agent 55).

---

### Agent 44 — The Auctioneer Agent

> **Tagline:** *Runs an internal market mechanism for task allocation among a pool of agents.*

#### The Problem & Production Reality
In a pool of more-or-less interchangeable workers, picking one statically is a routing problem (Agent 38). When the workers differ in current capacity, expertise, or cost, the right mechanism is a market: announce the task, collect bids that combine cost and confidence, and award to the best bidder.

This produces better allocations than a router in heterogeneous-worker conditions, particularly when workers' availability and confidence vary dynamically.

The general problem is decentralized task allocation: matching tasks to workers in a way that respects workers' self-reported capabilities and current load, with the mechanism handling the allocation rather than a central planner.

#### Why Naïve Approaches Fail
"Round-robin allocation." Ignores worker capability. The right worker for this task may be busy on something easier.

"Pick the worker with the best historical accuracy on this task type." Ignores current load and over-uses the best worker.

"Let a central coordinator decide." The coordinator becomes a bottleneck and a single point of failure. It doesn't scale across worker pools that span teams or organizations.

#### The Mechanism
A task-announcement protocol that includes both the task and the bid-evaluation criteria. A bidder registry with bidding budgets to prevent runaway specialization. A winner-selection rule with explicit tie-breaking. A settlement step that updates each bidder's history and budget.

# coordination/auctioneer.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Bid:
    bidder: str
    task_id: str
    cost_offered: float          # what the bidder will charge
    confidence: float             # 0-1
    expected_latency_s: float
    rationale: str

@dataclass
class TaskAnnouncement:
    task_id: str
    description: str
    requirements: list[str]       # capability tags
    bid_evaluation: dict          # weights for cost, confidence, latency
    deadline: datetime
    max_bidders: int

@dataclass
class Bidder:
    name: str
    capabilities: list[str]
    historical_success_rate: dict[str, float]  # per capability
    bid_budget: float            # spending budget for this period
    bid_history: list[Bid] = field(default_factory=list)

class AuctioneerAgent:
    def __init__(self, bidders: list[Bidder]):
        self.bidders = {b.name: b for b in bidders}
    
    def auction(self, announcement: TaskAnnouncement) -> tuple[str, Bid] | None:
        # 1. Filter eligible bidders
        eligible = [b for b in self.bidders.values()
                    if all(r in b.capabilities for r in announcement.requirements)
                    and b.bid_budget > 0]
        if not eligible:
            return None
        # 2. Each eligible bidder produces a bid
        bids = []
        for bidder in eligible[:announcement.max_bidders]:
            bid = self._solicit_bid(bidder, announcement)
            if bid is not None:
                bids.append(bid)
        if not bids:
            return None
        # 3. Score and pick winner
        scored = [(self._score(b, announcement), b) for b in bids]
        scored.sort(key=lambda sb: sb[0], reverse=True)
        winning_score, winning_bid = scored[0]
        # 4. Settle: charge the bidder, record history
        self._settle(winning_bid)
        return winning_bid.bidder, winning_bid
    
    def _solicit_bid(self, bidder: Bidder, ann: TaskAnnouncement) -> Bid | None:
        # The bidder agent decides whether and how to bid based on its current state.
        # Implementation in the bidder; here we sketch the signature.
        history_relevant = bidder.historical_success_rate.get(ann.requirements[0], 0.5)
        if history_relevant < 0.5:
            return None    # don't bid on tasks we're bad at
        cost = self._estimate_cost(bidder, ann)
        latency = self._estimate_latency(bidder, ann)
        if cost > bidder.bid_budget:
            return None
        return Bid(
            bidder=bidder.name, task_id=ann.task_id, cost_offered=cost,
            confidence=history_relevant, expected_latency_s=latency,
            rationale=f"history:{history_relevant:.2f}",
        )
    
    def _score(self, bid: Bid, ann: TaskAnnouncement) -> float:
        w = ann.bid_evaluation
        # Lower cost is better; higher confidence is better; lower latency is better
        return (
            w.get("confidence", 0.5) * bid.confidence
            - w.get("cost", 0.3) * bid.cost_offered / 100
            - w.get("latency", 0.2) * bid.expected_latency_s / 10
        )
    
    def _settle(self, bid: Bid) -> None:
        bidder = self.bidders[bid.bidder]
        bidder.bid_budget -= bid.cost_offered
        bidder.bid_history.append(bid)

#### Trade-offs and Alternatives
The auctioneer adds latency (the bid-collection round-trip) and complexity (bidders have to be configured with budgets and bidding policies). For homogeneous worker pools, a simple round-robin or least-loaded scheduler is sufficient.

The pattern earns its keep when worker capabilities genuinely differ, when costs vary, or when the system must allocate across multiple competing principals.

For real-time, low-latency allocation, the bidding round-trip can be too slow. Pre-compute bid offerings in the background and let the auctioneer pick from cached bids. Then settle in the background.

#### Production Failure Modes
Winner's curse: The winning bid systematically underestimates cost and the winner regrets winning. Mitigate by separating self-reported confidence from measured historical accuracy, and weight the latter heavily.

Budget exhaustion: A bidder runs out of budget mid-period, and the pool's effective capacity shrinks. Mitigate by replenishing budgets on a schedule and by detecting budget-exhaustion patterns.

Bid collusion: Multiple bidders in the same pool coordinate to all bid high, and the auctioneer can't tell. In practice this is rare with software agents, but worth monitoring. Mitigate with explicit reserve prices.

#### Case Study
A multi-region research agent platform at a research vendor's internal organization has approximately 60 specialist agents bidding for incoming research tasks.

The auctioneer pattern (compared to the prior round-robin baseline) improved measured task-completion quality by 12% (matching tasks to specialists with relevant historical success) while reducing the most-loaded specialist's queue length by 60% (because the bidding-budget mechanism prevents winner-takes-all).

**Composition:** Pairs with: Resource-Aware Scheduler (Agent 21), Supervisor-Worker (Agent 45), Router (Agent 38).

---

### Agent 45 — The Supervisor-Worker Agent

> **Tagline:** *Manages a pool of identical workers with retries, partial failure handling, and result aggregation.*

#### The Problem & Production Reality
When the task is "do this hundred times in parallel," the right coordination pattern is supervisor-worker. The supervisor dispatches work units to a pool of identical worker agents, monitors their progress, retries on failure, replaces stuck workers, and aggregates results.

The pattern is dull, well-understood, and absent from a surprising number of production agent systems whose elastic-scaling story therefore consists of one long sequential loop.

The general problem is embarrassingly-parallel agent work: making the parallelism explicit, with proper failure handling and idempotency, rather than relying on a single agent to "loop over" the work.

#### Why Naïve Approaches Fail
"Loop over the work in one agent." No parallelism, single point of failure.

"Run N agents and hope they finish." No retry, no progress monitoring, no aggregation.

"Use a framework's built-in 'parallel' primitive." Often shallow, doesn't handle partial failure idiomatically.

#### The Mechanism
A work-unit schema that's independently dispatchable. A pool with explicit concurrency limits. A per-unit timeout and retry policy distinct from the pool-level policy. A partial-result aggregation strategy. An idempotency guarantee on the worker side so retries don't produce duplicate effects.

# coordination/supervisor_worker.py
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic
import asyncio

T = TypeVar("T")
R = TypeVar("R")

@dataclass
class WorkUnit(Generic[T]):
    unit_id: str
    payload: T
    idempotency_key: str

@dataclass
class UnitResult(Generic[R]):
    unit_id: str
    success: bool
    result: R | None
    error: str | None
    attempts: int
    worker_id: str

@dataclass
class BatchResult(Generic[R]):
    total: int
    succeeded: int
    failed: int
    results: list[UnitResult[R]]

class SupervisorWorkerAgent(Generic[T, R]):
    def __init__(self, worker_fn: Callable[[WorkUnit[T]], R],
                 *, max_concurrency: int = 10, max_retries_per_unit: int = 2,
                 timeout_per_unit_s: float = 30):
        self.worker_fn = worker_fn
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries_per_unit
        self.timeout = timeout_per_unit_s
    
    async def run_batch(self, units: list[WorkUnit[T]]) -> BatchResult[R]:
        semaphore = asyncio.Semaphore(self.max_concurrency)
        results = await asyncio.gather(*[
            self._run_unit_with_concurrency(unit, semaphore) for unit in units
        ])
        succeeded = sum(1 for r in results if r.success)
        return BatchResult(
            total=len(units), succeeded=succeeded,
            failed=len(units) - succeeded, results=results,
        )
    
    async def _run_unit_with_concurrency(self, unit: WorkUnit[T],
                                         sem: asyncio.Semaphore) -> UnitResult[R]:
        async with sem:
            return await self._run_unit(unit)
    
    async def _run_unit(self, unit: WorkUnit[T]) -> UnitResult[R]:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._invoke_worker(unit), timeout=self.timeout)
                return UnitResult(
                    unit_id=unit.unit_id, success=True, result=result,
                    error=None, attempts=attempt + 1, worker_id="pool",
                )
            except asyncio.TimeoutError:
                last_error = "timeout"
            except Exception as e:
                last_error = str(e)
        return UnitResult(
            unit_id=unit.unit_id, success=False, result=None,
            error=last_error, attempts=self.max_retries + 1, worker_id="pool",
        )
    
    async def _invoke_worker(self, unit: WorkUnit[T]) -> R:
        return await asyncio.to_thread(self.worker_fn, unit)

#### Trade-offs and Alternatives
The supervisor-worker pattern requires that work units be independent (no inter-unit dependencies). When dependencies exist, switch to the Pipeline Orchestrator (Agent 41) or a workflow engine. The pattern's strength is in the embarrassingly-parallel case.

For very large batches (thousands of units), the in-memory supervisor is insufficient. Instead, use a real queue (SQS, Redis Streams, a workflow engine) for durability and visibility into long-running batches.

#### Production Failure Modes
Cascading failure: All units share a dependency (a downstream API that's rate-limited), so all units fail simultaneously. Mitigate by detecting common-failure patterns and applying backoff at the batch level, not per-unit.

Idempotency violation: A retry produces a duplicate side effect because the worker's idempotency key wasn't honored downstream. Mitigate by enforcing idempotency at the tool/API layer (Side-Effect Auditor, Agent 37) using the unit's idempotency key.

Stuck-worker leak: A worker hangs without timeout-triggering errors, and the unit is "in progress" forever. Mitigate by enforcing wall-time as the master constraint. Nothing escapes a wall-time kill.

#### Case Study
A document-processing agent at a tax-services firm ingests a thousand-document batch in parallel across a fifty-worker pool. The supervisor handles the dozen documents that consistently fail (typically corrupted PDFs or unusual layouts) by escalating them to a human queue rather than retrying indefinitely.

Batch completion latency dropped from 4.5 hours (sequential) to 11 minutes (parallel), with a 99.1% per-unit success rate and a structured human-escalation path for the rest.

**Composition:** Pairs with: Side-Effect Auditor (Agent 37), Pipeline Orchestrator (Agent 41), Auctioneer (Agent 44).

---

## Capability: Learning: Becoming Better at What It Does
Covers Agents 46 through 52.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 46** | The Feedback Loop Agent | *Accumulates user corrections into a structured signal that future runs are conditioned on.* | Skill-Library Builder (Agent 48), Active Learner (Agent 52), Few-Shot Prompt Tuner (Agent 50). |
| **Agent 47** | The Reflection Agent | *Critiques its own output and revises before responding.* | Chain-of-Thought Auditor (Agent 8), Red-Team Auditor (Agent 56), Self-Consistency Voter (Agent 15). |
| **Agent 48** | The Skill-Library Builder Agent | *Saves successful sub-procedures as reusable skills the agent can invoke directly.* | Analogical Mapping (Agent 10), Memory-of-Self (Agent 27), Feedback Loop (Agent 46). |
| **Agent 49** | The Curriculum Designer Agent | *Sequences its own training cases for accelerated skill growth.* | Active Learner (Agent 52), Distillation (Agent 51), Memory-of-Self (Agent 27). |
| **Agent 50** | The Few-Shot Prompt Tuner Agent | *Selects and orders the in-context examples that condition the model for each task.* | Analogical Mapping (Agent 10), Feedback Loop (Agent 46), Curriculum Designer (Agent 49). |
| **Agent 51** | The Distillation Agent | *Compresses a large teacher's behavior into a smaller, faster student model.* | Curriculum Designer (Agent 49), Drift Detector (Agent 59), Self-Consistency Voter (Agent 15). |
| **Agent 52** | The Active Learner Agent | *Chooses which uncertain examples to ask a human about to maximize the value of labeling.* | Feedback Loop (Agent 46), Probabilistic Belief Updater (Agent 14), Curriculum Designer (Agent 49). |

### Detailed Pattern Breakdowns

### Agent 46 — The Feedback Loop Agent

> **Tagline:** *Accumulates user corrections into a structured signal that future runs are conditioned on.*

#### The Problem & Production Reality
The user corrects the agent. The default behavior (discarding the correction at session end) is the worst possible outcome. The same mistake gets made next session, and the next, eroding user trust at every iteration.

With a feedback loop, every correction becomes a permanent improvement vector for future cases on similar inputs.

The general problem is production-time learning from corrections: turning user-supplied counter-evidence into structured data that conditions future runs, without requiring model retraining.

#### Why Naïve Approaches Fail
"Hope the model learns from context." It doesn't, across sessions. Context resets.

"Add corrections to the system prompt." Bloats the prompt, and corrections become indistinguishable from invariant rules. Also doesn't scale.

"Retrain the model on corrections." Slow, expensive, and conflates updates to deployed behavior with updates to training. Most teams can't retrain frequently enough for this to be useful.

#### The Mechanism
A correction-capture step that records what the agent produced, what the user wanted, and the user's hint at why. A case-similarity index that retrieves the most relevant prior corrections when a new case arrives. An in-context injection that surfaces the retrieved corrections to the policy as guidance. A contradiction-detection step when newly-arrived corrections disagree with older ones.

# learning/feedback_loop.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Correction:
    correction_id: str
    case_signature: str          # canonical hash of the case shape
    case_features: dict           # extracted features for similarity
    case_embedding: list[float]
    agent_output: dict
    desired_output: dict
    hint_text: str               # why the agent was wrong
    correcting_actor: str
    timestamp: datetime
    case_context: dict = field(default_factory=dict)

class FeedbackLoopAgent:
    def __init__(self, embedder, *, max_retrieved: int = 3,
                 similarity_threshold: float = 0.75):
        self.embedder = embedder
        self.corrections: list[Correction] = []
        self.max_retrieved = max_retrieved
        self.threshold = similarity_threshold
    
    def record(self, agent_output: dict, desired_output: dict,
               hint_text: str, case_features: dict,
               correcting_actor: str, case_context: dict | None = None) -> Correction:
        case_text = self._signature(case_features)
        corr = Correction(
            correction_id=self._mint_id(),
            case_signature=self._hash(case_text),
            case_features=case_features,
            case_embedding=self.embedder.embed(case_text),
            agent_output=agent_output,
            desired_output=desired_output,
            hint_text=hint_text,
            correcting_actor=correcting_actor,
            timestamp=datetime.utcnow(),
            case_context=case_context or {},
        )
        # Detect contradictions with older corrections
        contradictions = self._find_contradictions(corr)
        for old in contradictions:
            self._mark_superseded(old, corr)
        self.corrections.append(corr)
        return corr
    
    def retrieve_for(self, case_features: dict) -> list[Correction]:
        case_emb = self.embedder.embed(self._signature(case_features))
        scored = [(self._cosine(case_emb, c.case_embedding), c) for c in self.corrections]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [c for s, c in scored[:self.max_retrieved] if s >= self.threshold]
    
    def materialize_for_prompt(self, retrieved: list[Correction]) -> str:
        if not retrieved:
            return ""
        lines = ["Prior corrections to similar cases (do not contradict these):"]
        for c in retrieved:
            lines.append(f"- Case: {c.case_features}")
            lines.append(f"  Expected: {c.desired_output}")
            lines.append(f"  Hint: {c.hint_text}")
        return "\n".join(lines)
    
    def _find_contradictions(self, new: Correction) -> list[Correction]:
        # Same case features, different desired output
        out = []
        for c in self.corrections:
            if c.case_signature == new.case_signature and c.desired_output != new.desired_output:
                out.append(c)
        return out

#### Trade-offs and Alternatives
The pattern is cheap and effective from day one. The trade is operational: someone has to capture corrections — either the user, a reviewer, or an evaluator agent — and the captured signal has to be usefully structured.

For environments where users won't provide corrections in a structured way, infer corrections from behavior signals (user re-asks the same question, user manually edits the output, user dismisses the response). These weaker signals are noisier but better than nothing.

#### Production Failure Modes
Hint-text noise: Users write hints that are sarcastic, vague, or contradictory. Mitigate by structuring the correction capture (multiple choice for common error types) rather than open text.

Contradiction accumulation: Corrections disagree with each other across users, and the agent oscillates between contradictory hints. Mitigate by partitioning corrections by user or by tenant where appropriate, and by surfacing contradictions explicitly rather than averaging.

Drift erosion: As the deployment distribution shifts, old corrections become irrelevant or wrong. Mitigate with the Forgetting-Policy (Agent 26) applied to the correction store.

#### Case Study
A sales-email-drafting agent at an outbound-sales platform sees its hit rate on accepted drafts climb from 60% to 85% over its first month entirely through feedback-loop conditioning, with no underlying model changes. Each rejected draft is captured with a structured "what I'd change" form filled in by the rep. The resulting corrections are retrieved and surfaced on similar future drafts. The product team explicitly doesn't retrain the model. The entire improvement is via context.

**Composition:** Pairs with: Skill-Library Builder (Agent 48), Active Learner (Agent 52), Few-Shot Prompt Tuner (Agent 50).

---

### Agent 47 — The Reflection Agent

> **Tagline:** *Critiques its own output and revises before responding.*

#### The Problem & Production Reality
The agent produces a candidate output. Before that output reaches the user, the reflection agent reads it as if it were someone else's work, looks for the typical failure modes for the task class, and revises.

The pattern is the simplest meta-cognitive move and one of the most reliable improvements available without changing the base model.

The general problem is single-pass quality ceiling: outputs that are reasonable on a first attempt but obviously improvable on a second look. Reflection exploits the asymmetry between generating and critiquing — critiquing is easier than generating, and the second pass operates under different constraints (it has the candidate to react to).

#### Why Naïve Approaches Fail
"Add 'be careful and thorough' to the prompt." No measurable effect.

"Use a higher reasoning effort setting." Helps, but doesn't capture the specific failure modes of the task class.

"Have the model double-check inside the same call." Self-review in the same call is unreliable. The model commits to its first answer and defends it.

#### The Mechanism
A critic prompt that names specific failure modes for the task class rather than asking for generic feedback. A revision step that takes both the original output and the critique as input. A stopping condition (typically one or two rounds). A comparison surface that exposes the original and revised versions to the operator so the value of reflection is measurable.

# learning/reflection.py
from dataclasses import dataclass

@dataclass
class CritiqueResult:
    found_issues: list[str]
    severity: str               # "none" | "minor" | "major"
    revision_priority: list[str]

@dataclass
class ReflectionRun:
    original_output: dict
    critique: CritiqueResult
    revised_output: dict | None
    rounds: int
    improvement_score: float | None    # if measurable

class ReflectionAgent:
    def __init__(self, critic_llm, reviser_llm, task_class: str,
                 *, max_rounds: int = 1, failure_modes: list[str] = None):
        self.critic = critic_llm
        self.reviser = reviser_llm
        self.task_class = task_class
        self.max_rounds = max_rounds
        self.failure_modes = failure_modes or []
    
    def reflect(self, task_input: dict, original_output: dict) -> ReflectionRun:
        current_output = original_output
        last_critique = None
        for round_num in range(self.max_rounds):
            critique = self._critique(task_input, current_output)
            last_critique = critique
            if critique.severity == "none":
                break
            current_output = self._revise(task_input, current_output, critique)
        return ReflectionRun(
            original_output=original_output,
            critique=last_critique,
            revised_output=current_output if current_output != original_output else None,
            rounds=round_num + 1,
            improvement_score=None,
        )
    
    def _critique(self, task_input: dict, output: dict) -> CritiqueResult:
        prompt = CRITIQUE_PROMPT.format(
            task_class=self.task_class,
            failure_modes="\n".join(f"  - {fm}" for fm in self.failure_modes),
        )
        response = self.critic.call(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Input: {task_input}\nOutput: {output}"}
            ],
            schema=CRITIQUE_SCHEMA,
        )
        return CritiqueResult(**response)
    
    def _revise(self, task_input: dict, current_output: dict,
                critique: CritiqueResult) -> dict:
        response = self.reviser.call(
            messages=[
                {"role": "system", "content": REVISE_PROMPT},
                {"role": "user", "content": (
                    f"Input: {task_input}\n"
                    f"Current output: {current_output}\n"
                    f"Critique: {critique.found_issues}\n"
                    f"Revision priorities: {critique.revision_priority}"
                )}
            ],
            schema=REVISION_SCHEMA,
        )
        return response

CRITIQUE_PROMPT = """\
You critique outputs for the task class: {task_class}

Specifically look for these failure modes:
{failure_modes}

Be strict but specific. Each issue you flag must:
  - Identify the exact part of the output that's wrong
  - Explain why it's wrong (not just that it's wrong)
  - Suggest the kind of revision needed

Severity:
  - "none": no actionable issues found
  - "minor": issues exist but don't change the substance of the output
  - "major": issues materially change what the output is saying or recommending
"""

#### Trade-offs and Alternatives
Reflection roughly doubles the cost per output. For tasks where the first-pass quality is already very high, the doubling is overhead. The pattern earns its keep when first-pass quality is below acceptable and when the critic can be tuned to catch the specific failure modes of the task.

For very high-stakes outputs, more rounds and more aggressive criticism help up to a point. But beyond that point, the reviser starts incorporating spurious "fixes" for non-issues. Tune the round count empirically.

#### Production Failure Modes
Critic over-reach: The critic flags style preferences as issues, revisions degrade clarity to address them. Mitigate by constraining the critic to flag issues only against the named failure modes.

Revision regression: A revision fixes one issue and introduces another. Mitigate by running the critic on the revision. Revisions that increase issue count are rejected.

Cost blow-out: Operators use reflection for everything, cost doubles across the board. Mitigate by gating reflection on output-class (only certain task classes get reflection by default) and exposing it as a knob.

#### Case Study
A code-review agent at a developer-tooling vendor routes first-pass comments through a reflection step keyed to the failure modes "false-positive style nitpick" and "missed real bug despite plausible-looking comment." The reflection catches roughly one in four false positives before they reach the developer, dramatically improving signal-to-noise as measured by per-comment thumbs-up rates (which rose from 31% to 67% over a quarter).

**Composition:** Pairs with: Chain-of-Thought Auditor (Agent 8), Red-Team Auditor (Agent 56), Self-Consistency Voter (Agent 15).

---

### Agent 48 — The Skill-Library Builder Agent

> **Tagline:** *Saves successful sub-procedures as reusable skills the agent can invoke directly.*

#### The Problem & Production Reality
The first time the agent solves a problem, it constructs the solution from primitives. The second time, it shouldn't have to. Without skill-library management, every session starts from zero — the agent rediscovers, from primitive tool calls, the procedures it has already discovered and executed many times before.

The general problem is procedural memory accumulation: turning successful action sequences into reusable, parameterized skills the agent can invoke as composite tools.

#### Why Naïve Approaches Fail
"Hope the model remembers." It doesn't, across sessions.

"Hand-write common procedures." Doesn't scale, misses procedures that emerge from agent operation.

"Log everything and hope it helps." Logs aren't queryable as skills.

#### The Mechanism
A trace-extraction step that identifies coherent sub-procedures within longer sessions. An abstraction step that lifts concrete arguments to typed parameters. A deduplication step that catches near-duplicate skills. A usefulness ranking that prunes rarely-used skills. Exposure of the resulting skills through the tool registry so the policy treats them like any other tool.

# learning/skill_library.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    parameter_schema: dict
    procedure: list[dict]      # sequence of tool calls with parameter slots
    successful_invocations: int
    failed_invocations: int
    last_used: datetime
    derived_from_traces: list[str]
    
    @property
    def success_rate(self) -> float:
        total = self.successful_invocations + self.failed_invocations
        return self.successful_invocations / total if total > 0 else 0.5

@dataclass
class SkillCandidate:
    procedure: list[dict]
    parameter_slots: dict
    abstracted_name: str
    abstracted_description: str
    derivation_trace: str

class SkillLibraryBuilderAgent:
    def __init__(self, abstraction_llm, *, min_occurrences: int = 3,
                 dedup_similarity: float = 0.9):
        self.abstractor = abstraction_llm
        self.min_occurrences = min_occurrences
        self.dedup_similarity = dedup_similarity
        self.library: dict[str, Skill] = {}
        self._candidate_buffer: list[SkillCandidate] = []
    
    def ingest_trace(self, trace: list[dict]) -> list[Skill]:
        """Extract candidate procedures from a successful session."""
        sub_procedures = self._extract_sub_procedures(trace)
        newly_promoted = []
        for sp in sub_procedures:
            candidate = self._abstract(sp)
            existing = self._find_similar_candidate(candidate)
            if existing:
                existing.procedure = self._merge_procedures(existing.procedure, candidate.procedure)
            else:
                self._candidate_buffer.append(candidate)
            # Promote on threshold
            occurrences = sum(1 for c in self._candidate_buffer
                              if self._similar(c, candidate))
            if occurrences >= self.min_occurrences:
                skill = self._promote(candidate)
                newly_promoted.append(skill)
        return newly_promoted
    
    def _abstract(self, sub_procedure: list[dict]) -> SkillCandidate:
        """LLM call: identify which concrete args should be parameters."""
        response = self.abstractor.call(
            messages=[
                {"role": "system", "content": ABSTRACTION_PROMPT},
                {"role": "user", "content": self._format_procedure(sub_procedure)}
            ],
            schema=ABSTRACTION_SCHEMA,
        )
        return SkillCandidate(
            procedure=response["abstracted_procedure"],
            parameter_slots=response["parameters"],
            abstracted_name=response["name"],
            abstracted_description=response["description"],
            derivation_trace=self._format_procedure(sub_procedure),
        )
    
    def _promote(self, candidate: SkillCandidate) -> Skill:
        skill_id = self._mint_id()
        skill = Skill(
            skill_id=skill_id, name=candidate.abstracted_name,
            description=candidate.abstracted_description,
            parameter_schema=self._build_schema(candidate.parameter_slots),
            procedure=candidate.procedure,
            successful_invocations=0, failed_invocations=0,
            last_used=datetime.utcnow(),
            derived_from_traces=[],
        )
        self.library[skill_id] = skill
        return skill
    
    def prune(self, max_age_days: int = 90, min_success_rate: float = 0.5):
        """Remove rarely-used or low-success-rate skills."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        to_remove = []
        for sid, skill in self.library.items():
            if skill.last_used < cutoff and (skill.successful_invocations + skill.failed_invocations) < 5:
                to_remove.append(sid)
            elif skill.success_rate < min_success_rate and (skill.successful_invocations + skill.failed_invocations) > 10:
                to_remove.append(sid)
        for sid in to_remove:
            del self.library[sid]

#### Trade-offs and Alternatives
Skill abstraction requires an LLM call per candidate procedure. Pre-deployment, the cost is small, but on a high-traffic agent the volume can add up. Run skill extraction asynchronously, not in the request path.

For environments where successful procedures don't repeat (every problem is genuinely novel), the pattern provides no benefit. The pattern shines when the agent operates over a roughly stationary distribution of tasks.

#### Production Failure Modes
Over-abstraction: The abstractor parameterizes too much, and the resulting skill is too general to be useful. Mitigate by validating skills against historical traces: does the skill produce the same outputs the literal traces produced?

Under-abstraction: Parameters that should be slots are hardcoded, and the skill is too specific to reuse. Mitigate by running multiple abstraction passes with different concrete examples and merging.

Skill rot: A skill worked when added, but the underlying tools have changed and the skill silently fails. Mitigate by including skill invocations in the evaluation harness and pruning failures.

#### Case Study
A data-engineering co-pilot at a large data-platform team accumulated a skill library of 247 typed skills covering the team's most common operations (for example, "deduplicate-by-key-and-keep-most-recent," "join-table-set-with-conflict-resolution," "publish-dashboard-to-tenant") over six months in production. Skills with success rates below 0.5 were pruned automatically. The remaining set reduced median task-completion latency by 38% on familiar tasks, and the skill names became part of the team's working vocabulary for talking about the work.

**Composition:** Pairs with: Analogical Mapping (Agent 10), Memory-of-Self (Agent 27), Feedback Loop (Agent 46).

---

### Agent 49 — The Curriculum Designer Agent

> **Tagline:** *Sequences its own training cases for accelerated skill growth.*

#### The Problem & Production Reality
When the agent has a corpus of historical cases it could learn from (through feedback loops, skill extraction, or fine-tuning), the order in which it processes them matters. The curriculum designer sequences cases from easier to harder, from clearer to noisier, and from on-distribution to off-distribution. The pattern is the difference between learning that converges and learning that thrashes.

The general problem is order-of-experience optimization: deciding which cases to learn from next, given an estimate of the agent's current proficiency, to maximize the rate of capability gain.

#### Why Naïve Approaches Fail
"Just learn from everything in chronological order." Hard cases early in a curriculum produce noisy signal, and the agent learns the wrong lessons.

"Sample randomly." Equivalent to no curriculum.

"Sort by difficulty once at the start." Wastes the second half of the curriculum (too easy now), and doesn't adapt as the agent improves.

#### The Mechanism
An explicit difficulty model for each case. An estimate of the agent's current proficiency that updates as the curriculum progresses. A scheduling policy that draws the next case from the boundary between mastered and unmastered. A checkpointing discipline so the curriculum can be rewound if the agent's proficiency regresses.

# learning/curriculum.py
from dataclasses import dataclass, field
from datetime import datetime
import math

@dataclass
class TrainingCase:
    case_id: str
    difficulty: float           # 0-1
    case_features: dict
    expected_outcome: dict
    metadata: dict = field(default_factory=dict)

@dataclass
class ProficiencyEstimate:
    skill_class: str
    estimate: float            # 0-1
    confidence: float          # how sure are we
    sample_count: int

class CurriculumDesignerAgent:
    def __init__(self, cases: list[TrainingCase], skill_classifier,
                 *, target_difficulty_offset: float = 0.1,
                 boundary_band: float = 0.15):
        self.cases = cases
        self.classify_skill = skill_classifier
        self.target_offset = target_difficulty_offset
        self.boundary_band = boundary_band
        self.proficiency: dict[str, ProficiencyEstimate] = {}
        self._consumed: set[str] = set()
        self._results: list[dict] = []
    
    def next_case(self) -> TrainingCase | None:
        """Pick the next case from the boundary of current proficiency."""
        candidates = [c for c in self.cases if c.case_id not in self._consumed]
        if not candidates:
            return None
        # Score each candidate by how close it is to the agent's current zone of proximal development
        scored = []
        for c in candidates:
            skill = self.classify_skill(c)
            prof = self.proficiency.get(skill, ProficiencyEstimate(skill, 0.3, 0.1, 0))
            target = min(1.0, prof.estimate + self.target_offset)
            distance = abs(c.difficulty - target)
            if distance > self.boundary_band:
                continue
            # Prefer cases with lower confidence (more learning opportunity)
            score = -distance + (1 - prof.confidence) * 0.3
            scored.append((score, c))
        if not scored:
            return None
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return scored[0][1]
    
    def record_outcome(self, case: TrainingCase, succeeded: bool) -> None:
        self._consumed.add(case.case_id)
        skill = self.classify_skill(case)
        prof = self.proficiency.setdefault(
            skill, ProficiencyEstimate(skill, 0.3, 0.1, 0))
        # Online proficiency update (modified EMA weighted by case difficulty)
        weight = 1.0 / (prof.sample_count + 1)
        signal = case.difficulty if succeeded else (1 - case.difficulty)
        prof.estimate = (1 - weight) * prof.estimate + weight * signal
        prof.sample_count += 1
        # Confidence grows with sample count
        prof.confidence = min(0.95, 1 - 1.0 / math.sqrt(prof.sample_count + 1))
        self._results.append({"case_id": case.case_id, "succeeded": succeeded,
                              "prof_after": prof.estimate})
    
    def checkpoint(self) -> dict:
        return {
            "consumed": list(self._consumed),
            "proficiency": {k: v.__dict__ for k, v in self.proficiency.items()},
            "results": self._results,
        }
    
    def restore(self, checkpoint: dict) -> None:
        self._consumed = set(checkpoint["consumed"])
        self.proficiency = {k: ProficiencyEstimate(**v)
                            for k, v in checkpoint["proficiency"].items()}
        self._results = checkpoint["results"]

#### Trade-offs and Alternatives
A curriculum designer requires per-case difficulty estimates and per-case skill classifications. Estimating these is itself work. For small case corpora the work isn't justified. The pattern earns its keep on corpora of thousands of cases or more.

For situations where you have explicit human-labeled difficulties (an educational corpus, a test suite with calibrated hardness), use those rather than learning a difficulty estimator from scratch.

#### Production Failure Modes
Difficulty-estimator bias: The estimator confuses surface features with difficulty, and the curriculum thinks something is easy that isn't. Mitigate by calibrating the estimator against held-out outcomes and recalibrating regularly.

Proficiency overestimation: The proficiency estimate climbs too fast, and the curriculum jumps to cases the agent can't yet handle. Learning thrashes. Mitigate with a Bayesian floor on proficiency (Wilson lower bound) so the estimate respects sample uncertainty.

Curriculum exhaustion: The agent has mastered everything in the corpus. New cases are needed but none exist. Surface the exhaustion explicitly and request new cases from the human curator.

#### Case Study
A fine-tuning pipeline at a domain-specialist vendor produced a task-accuracy improvement equivalent to the random-order baseline with roughly 40% of the training data, via curriculum-designed case ordering. The savings on training-data acquisition (which was expert-labeled and expensive) was material — roughly $180,000 per training cycle, with three cycles per year.

**Composition:** Pairs with: Active Learner (Agent 52), Distillation (Agent 51), Memory-of-Self (Agent 27).

---

### Agent 50 — The Few-Shot Prompt Tuner Agent

> **Tagline:** *Selects and orders the in-context examples that condition the model for each task.*

#### The Problem & Production Reality
Few-shot prompting is the easiest behavior to misuse: pick three or four examples once, hardcode them, and live with the consequences forever.

The pattern is a structural fix: for each incoming task, select examples from a pool based on similarity to the task, order them by predicted educative value, and construct the prompt dynamically.

The general problem is per-call example selection: making the in-context examples a dynamic property of the call, conditioned on the specific task at hand, rather than a static property of the agent.

#### Why Naïve Approaches Fail
"Hardcode three examples." Works for the average case, but fails on cases that need different examples.

"Sample randomly from a pool." Misses the relevance signal.

"Sort by similarity to the user's question." Loses the educative signal. Sometimes the right example for teaching the model isn't the most similar one.

#### The Mechanism
A curated example pool with structured labels covering both task type and the dimension along which each example is instructive. A per-task selector that retrieves examples by structural similarity, not text similarity. An ordering rule that places the most-similar example last (or first, depending on the model's recency bias). An evaluation harness that measures the quality impact of selection against a fixed-example baseline.

# learning/few_shot_tuner.py
from dataclasses import dataclass, field

@dataclass
class FewShotExample:
    example_id: str
    task_type: str
    instructive_dimensions: list[str]   # what this example teaches
    input: dict
    output: dict
    embedding: list[float]
    historical_inclusion_lift: float    # measured improvement when included

class FewShotPromptTunerAgent:
    def __init__(self, pool: list[FewShotExample], embedder,
                 *, examples_per_prompt: int = 3,
                 ordering: str = "similarity_last"):
        self.pool = pool
        self.embedder = embedder
        self.examples_per_prompt = examples_per_prompt
        self.ordering = ordering
    
    def select(self, task_input: dict, task_type: str) -> list[FewShotExample]:
        # 1. Filter pool by task type
        candidates = [e for e in self.pool if e.task_type == task_type]
        if not candidates:
            return []
        # 2. Score by relevance to the current task
        query_emb = self.embedder.embed(self._signature(task_input))
        scored = [(self._cosine(query_emb, e.embedding), e) for e in candidates]
        scored.sort(key=lambda se: se[0], reverse=True)
        # 3. Select with diversity: ensure different instructive_dimensions are covered
        selected = []
        covered_dimensions = set()
        for _, ex in scored:
            new_dims = set(ex.instructive_dimensions) - covered_dimensions
            if new_dims or len(selected) == 0:
                selected.append(ex)
                covered_dimensions.update(ex.instructive_dimensions)
            if len(selected) == self.examples_per_prompt:
                break
        # If still under the target, fill with top-similarity remainder
        for _, ex in scored:
            if ex in selected:
                continue
            selected.append(ex)
            if len(selected) == self.examples_per_prompt:
                break
        # 4. Order
        if self.ordering == "similarity_last":
            selected.sort(key=lambda e: self._cosine(query_emb, e.embedding))
        elif self.ordering == "similarity_first":
            selected.sort(key=lambda e: self._cosine(query_emb, e.embedding), reverse=True)
        return selected
    
    def materialize(self, examples: list[FewShotExample]) -> str:
        lines = []
        for ex in examples:
            lines.append("Example:")
            lines.append(f"  Input: {ex.input}")
            lines.append(f"  Output: {ex.output}")
            lines.append("")
        return "\n".join(lines)
    
    def record_outcome(self, examples: list[FewShotExample], succeeded: bool):
        """Update historical_inclusion_lift via EMA."""
        for ex in examples:
            signal = 1.0 if succeeded else 0.0
            ex.historical_inclusion_lift = 0.95 * ex.historical_inclusion_lift + 0.05 * signal

#### Trade-offs and Alternatives
Dynamic selection adds embedding-and-retrieval latency to every call. For tasks where one or two examples are sufficient and the task type is narrow, hardcoded examples are simpler and adequate.

The pattern's value scales with pool size and pool diversity. A pool of ten examples doesn't benefit much from dynamic selection. A pool of five hundred examples benefits enormously.

#### Production Failure Modes
Pool drift: The pool is curated at launch, the production distribution shifts, and the pool's examples become unrepresentative. Mitigate by adding new examples to the pool from production feedback and pruning examples whose historical-inclusion-lift drops.

Ordering bias: The model has a strong recency bias. Placing the most-similar example last (or first) systematically helps or hurts depending on the model. Validate ordering empirically per model.

Diversity collapse: All selected examples come from a narrow subspace, and the model overfits to that subspace. Mitigate by enforcing instructive-dimension coverage (the code shows this).

#### Case Study
A structured-extraction agent at a healthcare-claims vendor improved its accuracy on a benchmark task by 12 percentage points purely by replacing a static three-example prompt with a dynamic-selection pool of forty examples. The selector cost per call is roughly two milliseconds, the model cost per call is unchanged, and the accuracy improvement was material enough that the vendor was able to raise the agent's confidence-threshold for auto-approval, eliminating roughly 8% of human-review work.

**Composition:** Pairs with: Analogical Mapping (Agent 10), Feedback Loop (Agent 46), Curriculum Designer (Agent 49).

---

### Agent 51 — The Distillation Agent

> **Tagline:** *Compresses a large teacher's behavior into a smaller, faster student model.*

#### The Problem & Production Reality
When a frontier model produces high-quality outputs on a defined task class and a smaller model is cheap and fast, the natural move is to distill. Without an explicit distillation pipeline, the team either pays frontier-model prices indefinitely or maintains a separately-fine-tuned smaller model without the teacher's behavior captured.

The general problem is production-time model compression: turning expensive teacher behavior into cheap student behavior, continuously, as the production distribution evolves.

#### Why Naïve Approaches Fail
"Run the cheap model and hope." Quality collapses on hard problems.

"Train the student once at launch." Student becomes stale as the deployment distribution drifts.

"Manually curate distillation data." Slow, and misses the distribution shifts that matter.

#### The Mechanism
A sampling policy that selects production cases representative of the deployment distribution. A teacher-output capture step that records both the answer and the reasoning trace. A filtering pass that excludes low-quality teacher outputs based on agreement with self-consistency or auditor checks. A training pipeline for the student model. An evaluation step that compares the student to the teacher on held-out cases.

# learning/distillation.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random

@dataclass
class DistillationSample:
    sample_id: str
    input: dict
    teacher_output: dict
    teacher_reasoning_trace: str
    teacher_confidence: float
    captured_at: datetime
    case_metadata: dict

@dataclass
class DistillationRun:
    run_id: str
    teacher_model: str
    student_model: str
    samples_used: int
    student_eval_score: float
    teacher_eval_score: float
    cost_reduction: float

class DistillationAgent:
    def __init__(self, teacher, student_trainer, evaluator,
                 *, sample_rate: float = 0.05, quality_floor: float = 0.95):
        self.teacher = teacher
        self.trainer = student_trainer
        self.evaluator = evaluator
        self.sample_rate = sample_rate
        self.quality_floor = quality_floor
        self.captured: list[DistillationSample] = []
    
    def capture_production_call(self, input: dict, output: dict,
                                reasoning_trace: str, confidence: float,
                                metadata: dict | None = None) -> None:
        """Sample production calls for the distillation set."""
        if random.random() > self.sample_rate:
            return
        sample = DistillationSample(
            sample_id=self._mint_id(), input=input, teacher_output=output,
            teacher_reasoning_trace=reasoning_trace, teacher_confidence=confidence,
            captured_at=datetime.utcnow(),
            case_metadata=metadata or {},
        )
        self.captured.append(sample)
    
    def filter_for_training(self, samples: list[DistillationSample]) -> list[DistillationSample]:
        """Keep only samples where the teacher seems reliable."""
        return [s for s in samples if s.teacher_confidence >= self.quality_floor]
    
    def run_distillation(self, eval_set: list[dict]) -> DistillationRun:
        # 1. Filter
        training_samples = self.filter_for_training(self.captured)
        # 2. Train the student
        student = self.trainer.train(
            base_model=self.trainer.base_model,
            training_data=[(s.input, s.teacher_output) for s in training_samples],
        )
        # 3. Evaluate
        student_score = self.evaluator.evaluate(student, eval_set)
        teacher_score = self.evaluator.evaluate(self.teacher, eval_set)
        # 4. Compute cost reduction
        teacher_cost = self.teacher.cost_per_call_cents
        student_cost = student.cost_per_call_cents
        cost_reduction = (teacher_cost - student_cost) / teacher_cost
        return DistillationRun(
            run_id=self._mint_id(),
            teacher_model=self.teacher.name, student_model=student.name,
            samples_used=len(training_samples),
            student_eval_score=student_score, teacher_eval_score=teacher_score,
            cost_reduction=cost_reduction,
        )
    
    def production_ready(self, run: DistillationRun, *, tolerance: float = 0.03) -> bool:
        """Is the student close enough to the teacher to ship?"""
        return (run.teacher_eval_score - run.student_eval_score) <= tolerance

#### Trade-offs and Alternatives
Distillation requires a training pipeline, a labeled evaluation set, and a continuous process. For agents whose volume is too low to justify the engineering, run the teacher and accept the cost.

For agents where the teacher's outputs are formatted in ways that don't compress well to a smaller model (long-form reasoning, complex tool use), distillation may not produce a usable student. Try on simpler task classes first, as structured outputs distill more reliably than free-form ones.

#### Production Failure Modes
Distribution drift: The student was trained on last quarter's distribution, but the current quarter looks different. The student's quality degrades. Mitigate by continuous distillation: capture, train, and evaluate on a rolling schedule.

Teacher contamination: A teacher mistake in the training set teaches the student to make the same mistake at scale. Mitigate with quality filters on teacher outputs (self-consistency check, auditor pass).

Eval-set staleness: The evaluation set was assembled at launch, and it doesn't catch the modes the student fails on now. Mitigate by rolling production cases into the eval set with adversarial sampling.

#### Case Study
A content-moderation agent at a social platform initially deployed a frontier model at full cost. Six months later, the production state is a distilled student model running at one-eighth the cost with no measurable quality regression on the platform's labeled benchmark.

Distillation runs are quarterly, with sampling at 3% of production traffic and a quality floor of teacher-confidence 0.97. Roughly 60% of captured samples pass the filter into training. The savings (approximately $1.4M per year at the platform's volume) is the entirety of the distillation team's funding.

**Composition:** Pairs with: Curriculum Designer (Agent 49), Drift Detector (Agent 59), Self-Consistency Voter (Agent 15).

---

### Agent 52 — The Active Learner Agent

> **Tagline:** *Chooses which uncertain examples to ask a human about to maximize the value of labeling.*

#### The Problem & Production Reality
The agent is uncertain on many cases. Asking a human about all of them is unaffordable, while asking about none leaves capacity unused.

The active learner selects the cases on which a human label would produce the largest improvement — not always the most uncertain ones, but the ones where labeling would maximally reduce residual error.

The general problem is labeling-budget allocation: deciding which examples are worth a human's time, given a finite labeling budget, to maximize downstream agent improvement.

#### Why Naïve Approaches Fail
"Label everything." Affordable for none.

"Label the most uncertain cases." Often correct, but misses cases where the uncertainty is structural (the agent will always be uncertain on this kind of input).

"Label randomly." Wastes budget on easy cases.

#### The Mechanism
An uncertainty estimate per case that goes beyond model logits (combines self-consistency disagreement, retrieval confidence, historical accuracy on similar cases). A selection policy that targets cases at the boundary between mastered and unmastered. A budgeted-queue discipline that respects the human labeler's capacity. An integration path that flows labeled cases back into the feedback-loop store.

# learning/active_learner.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class UncertaintyCase:
    case_id: str
    input: dict
    agent_output: dict
    self_consistency_disagreement: float
    retrieval_confidence: float
    similarity_to_historical_failures: float
    similarity_to_historical_successes: float
    proxy_difficulty: float
    captured_at: datetime

@dataclass
class LabelingPriority:
    case_id: str
    score: float
    rationale: str

class ActiveLearnerAgent:
    def __init__(self, similar_case_index, daily_label_budget: int = 50):
        self.index = similar_case_index
        self.daily_budget = daily_label_budget
        self.queue: list[UncertaintyCase] = []
        self.labeled: dict[str, dict] = {}
    
    def consider(self, case: UncertaintyCase) -> None:
        """Decide whether to add the case to the labeling queue."""
        score = self._priority_score(case)
        if score > 0.5:
            self.queue.append(case)
    
    def select_for_labeling(self) -> list[LabelingPriority]:
        """Pick the top-N cases for today's labeling budget."""
        scored = [(self._priority_score(c), c) for c in self.queue]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [
            LabelingPriority(
                case_id=c.case_id, score=s,
                rationale=self._explain(c),
            )
            for s, c in scored[:self.daily_budget]
        ]
    
    def _priority_score(self, c: UncertaintyCase) -> float:
        # Cases that are uncertain AND close to historical successes have high learning value
        # Cases close only to historical failures may be structurally unsolvable
        uncertainty = (
            0.4 * c.self_consistency_disagreement
            + 0.3 * (1 - c.retrieval_confidence)
            + 0.3 * c.proxy_difficulty
        )
        boundary_factor = max(
            c.similarity_to_historical_successes - c.similarity_to_historical_failures,
            0,
        )
        return uncertainty * boundary_factor
    
    def record_label(self, case: UncertaintyCase, label: dict) -> None:
        self.labeled[case.case_id] = label
        # Remove from queue
        self.queue = [c for c in self.queue if c.case_id != case.case_id]
    
    def _explain(self, c: UncertaintyCase) -> str:
        return (
            f"disagreement {c.self_consistency_disagreement:.2f}, "
            f"retrieval_conf {c.retrieval_confidence:.2f}, "
            f"boundary {(c.similarity_to_historical_successes - c.similarity_to_historical_failures):.2f}"
        )

#### Trade-offs and Alternatives
The active learner is a meta-pattern: it does not produce outputs itself. It needs a label-providing process (humans, in most cases) and a downstream consumer (the Feedback Loop, Agent 46, typically). For agents without either, the pattern has nowhere to live.

For cold-start situations (no historical successes or failures to compare against), active learning degenerates to random sampling. Bootstrap with random labeling first, then switch to active selection.

#### Production Failure Modes
Selection bias loop. The active learner samples cases similar to historical labels, the labeled set narrows to a sub-distribution, and the agent gets worse on the un-sampled distribution. Mitigate by reserving a fraction of the budget for random sampling.

Labeler bias: The labeler systematically labels in one direction, and the agent learns the labeler's bias. Mitigate by sampling labels for review by a different labeler.

Queue backlog: Cases are added faster than labelers can clear them. Mitigate by dropping old un-labeled cases (the Forgetting-Policy applies here) or raising the priority threshold.

#### Case Study
A document-classification agent at a regulatory-compliance vendor reduced its human-labeling budget by 60% while maintaining accuracy, by routing only active-learner-selected cases to the labelers. The selected cases (top 50 per day from a pool of roughly 1,200 daily uncertain cases) covered the agent's actual learning boundary. The labeling team's reported "interesting case rate" rose from 18% to 71%, and the resulting agent improvements were measured against the older random-sampling baseline as roughly 3× faster convergence per labeled case.

**Composition:** Pairs with: Feedback Loop (Agent 46), Probabilistic Belief Updater (Agent 14), Curriculum Designer (Agent 49).

---

## Capability: Alignment: Behaving by Design, Not by Accident
Covers Agents 53 through 60.
| Agent # | Pattern Name | Tagline | Primary Collaborators |
| :--- | :--- | :--- | :--- |
| **Agent 53** | The Constitution-Bound Agent | *Operates under a written rule-set and self-checks against it before any action.* | Side-Effect Auditor (Agent 37), Off-Switch-Compatible (Agent 60), Refusal Calibrator (Agent 54). |
| **Agent 54** | The Refusal-Calibrator Agent | *Calibrates when to refuse, when to qualify, and when to comply, against a measured baseline.* | Memory-of-Self (Agent 27), Constitution-Bound (Agent 53), Red-Team Auditor (Agent 56). |
| **Agent 55** | The Provenance Tracker Agent | *Attaches a citation to every load-bearing claim in the agent's output.* | Document Layout (Agent 2), Semantic Memory Curator (Agent 24), Database Query Synthesizer (Agent 35). |
| **Agent 56** | The Red-Team Auditor Agent | *Probes a sibling agent for failure modes the operator has not yet observed.* | Refusal Calibrator (Agent 54), Drift Detector (Agent 59), Constitution-Bound (Agent 53). |
| **Agent 57** | The Privacy-Preserving Agent | *Operates under explicit data-minimization and de-identification policies at every boundary.* | Forgetting-Policy (Agent 26), Ambient Context (Agent 6), Persistent Identity (Agent 29). |
| **Agent 58** | The Explainer Agent | *Produces post-hoc explanations of its own decisions that survive expert scrutiny.* | Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55), Constitution-Bound (Agent 53). |
| **Agent 59** | The Drift-Detector Agent | *Monitors the agent's own input and output distributions for shift over time.* | Anomaly-Spotter (Agent 4), Distillation (Agent 51), Vector-Store Curator (Agent 28). |
| **Agent 60** | The Off-Switch-Compatible Agent | *Accepts human override gracefully, without resistance, at any point in its execution.* | Constitution-Bound (Agent 53), Side-Effect Auditor (Agent 37), Human-in-the-Loop Liaison (Agent 42). |

### Detailed Pattern Breakdowns

### Agent 53 — The Constitution-Bound Agent

> **Tagline:** *Operates under a written rule-set and self-checks against it before any action.*

#### The Problem & Production Reality
A constitution is the agent's externally-defined rule of behavior: things it won't do, things it must do, things it must do only with explicit consent, and things it must surface to the operator. The default behavior of "let the prompt encode the constraints" fails predictably under adversarial inputs and ambiguous edge cases.

The general problem is structural rule enforcement: ensuring that the agent's actions satisfy a written rule-set, evaluated by a structural check rather than by the model's compliance with its prompt.

#### Why Naïve Approaches Fail
"Put the rules in the system prompt." Works under normal conditions, but the model is talked around the rules under adversarial conditions.

"Validate outputs against rules after they're produced." Doesn't help with state-modifying actions. The side effect has already happened.

"Train the model on the rules." Slow, doesn't update with rule changes, and doesn't catch the cases the training set didn't cover.

#### The Mechanism
A constitution that's human-readable but also machine-evaluable. A per-action evaluation step that runs before the action is executed. A refusal output that names the specific constitutional clause violated rather than a vague decline. An exception-request path through which an operator can grant a one-off override.

# alignment/constitution.py
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

class ConstitutionalVerdict(Enum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    REQUIRES_APPROVAL = "requires_approval"
    REQUIRES_DISCLOSURE = "requires_disclosure"

@dataclass
class ConstitutionalClause:
    clause_id: str
    description: str
    applies_when: Callable[[dict, dict], bool]  # (action, context) -> bool
    verdict: ConstitutionalVerdict
    approval_target: str | None = None
    disclosure_recipient: str | None = None
    human_readable: str = ""

@dataclass
class ConstitutionalCheck:
    verdict: ConstitutionalVerdict
    triggered_clauses: list[str]
    explanation: str
    required_approval_from: str | None = None
    override_token: str | None = None

class Constitution:
    def __init__(self, clauses: list[ConstitutionalClause]):
        self.clauses = clauses

class ConstitutionBoundAgent:
    def __init__(self, constitution: Constitution, approval_provider,
                 audit_sink):
        self.constitution = constitution
        self.approval = approval_provider
        self.audit = audit_sink
    
    def check(self, action: dict, context: dict) -> ConstitutionalCheck:
        triggered = []
        worst_verdict = ConstitutionalVerdict.PERMITTED
        approval_target = None
        for clause in self.constitution.clauses:
            if clause.applies_when(action, context):
                triggered.append(clause.clause_id)
                if clause.verdict == ConstitutionalVerdict.PROHIBITED:
                    worst_verdict = ConstitutionalVerdict.PROHIBITED
                    approval_target = None
                elif (clause.verdict == ConstitutionalVerdict.REQUIRES_APPROVAL
                      and worst_verdict != ConstitutionalVerdict.PROHIBITED):
                    worst_verdict = ConstitutionalVerdict.REQUIRES_APPROVAL
                    approval_target = clause.approval_target
                elif (clause.verdict == ConstitutionalVerdict.REQUIRES_DISCLOSURE
                      and worst_verdict == ConstitutionalVerdict.PERMITTED):
                    worst_verdict = ConstitutionalVerdict.REQUIRES_DISCLOSURE
        explanation = "; ".join(
            f"clause:{cid}" for cid in triggered
        ) or "no_clauses_apply"
        self.audit.log({"action": action, "verdict": worst_verdict.value,
                        "clauses": triggered, "context": context})
        return ConstitutionalCheck(
            verdict=worst_verdict, triggered_clauses=triggered,
            explanation=explanation, required_approval_from=approval_target,
        )
    
    def gate(self, action: dict, context: dict,
             execute_fn: Callable[[dict], dict]) -> dict:
        """Run an action through the constitution; execute or refuse."""
        check = self.check(action, context)
        if check.verdict == ConstitutionalVerdict.PROHIBITED:
            return {"error": "constitution_prohibited",
                    "clauses": check.triggered_clauses,
                    "explanation": check.explanation}
        if check.verdict == ConstitutionalVerdict.REQUIRES_APPROVAL:
            granted = self.approval.request(check.required_approval_from, action, context)
            if not granted:
                return {"error": "constitution_approval_denied",
                        "clauses": check.triggered_clauses}
        result = execute_fn(action)
        if check.verdict == ConstitutionalVerdict.REQUIRES_DISCLOSURE:
            result["disclosure"] = {"clauses": check.triggered_clauses,
                                    "explanation": check.explanation}
        return result

# Example clauses
def _is_external_email(action, context):
    return (action.get("tool") == "send_email"
            and not action.get("args", {}).get("recipient", "").endswith("@ourcompany.com"))

EXTERNAL_EMAIL_CLAUSE = ConstitutionalClause(
    clause_id="external-comm-001",
    description="External communications require approval.",
    applies_when=_is_external_email,
    verdict=ConstitutionalVerdict.REQUIRES_APPROVAL,
    approval_target="comms_review",
    human_readable="Any email to a recipient outside ourcompany.com requires comms approval.",
)

#### Trade-offs and Alternatives
A constitution requires that someone write the clauses and that the codified applies_when predicates capture the intent accurately. Both are real work: constitutions tend to grow over time as edge cases are discovered. Treat the constitution as a versioned artifact under change control.

For environments with very simple rules, a hand-coded set of if statements is sufficient and avoids the framework overhead. The pattern earns its keep when rules accumulate, interact, or change frequently — and when the agent's actions touch sensitive surfaces where rule-evaluation has to be auditable.

#### Production Failure Modes
Clause incompleteness: The constitution doesn't cover a case it should have, and the action proceeds and a problem occurs. Mitigate by adding the missing clause and reviewing for analogous cases.

Predicate-action mismatch: The applies_when function fails to recognize that a clause applies to a particular action. Mitigate by sampling actions and checking predicate coverage, especially after adding new tools.

Approval-loop fatigue: Too many actions require approval, so approvers rubber-stamp. Mitigate by tuning clauses so that approval is reserved for genuinely consequential cases (the Refusal Calibrator, Agent 54, helps here).

#### Case Study
A procurement-execution agent at a manufacturing firm has a constitution explicitly prohibiting orders above a per-vendor cap without operator approval, requiring disclosure for any change order, and prohibiting orders from vendors with active disputes.

The audit log over the first year shows zero constitutional violations (caught and rolled back) and approximately 2,400 approval requests (median time-to-approval: 12 minutes). The agent never executed an order that violated the constitution.

**Composition:** Pairs with: Side-Effect Auditor (Agent 37), Off-Switch-Compatible (Agent 60), Refusal Calibrator (Agent 54).

---

### Agent 54 — The Refusal-Calibrator Agent

> **Tagline:** *Calibrates when to refuse, when to qualify, and when to comply, against a measured baseline.*

#### The Problem & Production Reality
An over-refusing agent is useless. An under-refusing agent is dangerous. The default behavior (let the model decide) produces a refusal rate that varies wildly across deployments and time, and isn't measured. With a calibrator, refusal becomes a designed behavior rather than a habit picked up from the underlying model.

The general problem is measurable refusal behavior: ensuring the agent's refusals (and qualifications) reflect the actual risk profile and capability scope, with the behavior measured and tunable.

#### Why Naïve Approaches Fail
"Add 'refuse if unsafe' to the prompt." Produces wildly varying refusal behavior under different framings of the same request.

"Refuse based on keyword filters." Easy to evade. Over-refuses on benign requests.

"Have the model produce free-text refusals." No consistency in why or how it refuses. Impossible to measure.

#### The Mechanism
A refusal taxonomy that distinguishes safety, capability, policy, and identity-based refusals. A per-request classifier that maps the request into the taxonomy and produces a calibrated response. A qualification path that allows the agent to partially answer with explicit caveats. A measurement harness that evaluates the agent's refusal behavior against a labeled evaluation set on a regular cadence.

# alignment/refusal_calibrator.py
from dataclasses import dataclass, field
from enum import Enum

class RefusalClass(Enum):
    SAFETY = "safety"               # unsafe content / harm
    CAPABILITY = "capability"        # outside agent's competence
    POLICY = "policy"                # constitution or operator policy
    IDENTITY = "identity"            # outside agent's role
    NONE = "none"                    # comply

@dataclass
class RefusalDecision:
    decision: str               # "comply" | "qualify" | "refuse"
    refusal_class: RefusalClass
    rationale: str
    qualification: str | None   # for "qualify" decisions
    alternative_path: str | None  # what the user can do instead

class RefusalCalibratorAgent:
    def __init__(self, classifier_llm, *, safety_threshold: float = 0.85,
                 capability_threshold: float = 0.6):
        self.classifier = classifier_llm
        self.safety_threshold = safety_threshold
        self.capability_threshold = capability_threshold
    
    def decide(self, request: str, context: dict,
               self_model_lookup: callable) -> RefusalDecision:
        analysis = self._analyze(request, context)
        # 1. Safety hard-stop
        if analysis["safety_risk"] >= self.safety_threshold:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.SAFETY,
                rationale=analysis["safety_rationale"],
                qualification=None,
                alternative_path=analysis.get("safe_alternative"),
            )
        # 2. Policy / constitution check (covered by Agent 53; here we surface result)
        if analysis["policy_violation"]:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.POLICY,
                rationale=analysis["policy_rationale"],
                qualification=None,
                alternative_path=analysis.get("policy_alternative"),
            )
        # 3. Capability check via self-model
        capability_confidence = self_model_lookup(analysis["required_capability"])
        if capability_confidence < self.capability_threshold:
            # Try to qualify rather than refuse outright
            if analysis.get("qualified_answer_possible"):
                return RefusalDecision(
                    decision="qualify",
                    refusal_class=RefusalClass.CAPABILITY,
                    rationale=f"I am uncertain on {analysis['required_capability']} (confidence {capability_confidence:.2f})",
                    qualification=analysis["qualification_text"],
                    alternative_path=None,
                )
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.CAPABILITY,
                rationale=f"This requires {analysis['required_capability']}, which is outside my measured competence.",
                qualification=None,
                alternative_path=analysis.get("escalation_target"),
            )
        # 4. Identity check
        if analysis["outside_role"]:
            return RefusalDecision(
                decision="refuse",
                refusal_class=RefusalClass.IDENTITY,
                rationale=analysis["identity_rationale"],
                qualification=None,
                alternative_path=analysis.get("redirect_target"),
            )
        return RefusalDecision(
            decision="comply", refusal_class=RefusalClass.NONE,
            rationale="", qualification=None, alternative_path=None,
        )
    
    def _analyze(self, request: str, context: dict) -> dict:
        # The classifier LLM produces a structured analysis
        return self.classifier.call(
            messages=[
                {"role": "system", "content": REFUSAL_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Request: {request}\nContext: {context}"}
            ],
            schema=REFUSAL_ANALYSIS_SCHEMA,
        )

REFUSAL_ANALYSIS_PROMPT = """\
Analyze a request to determine the appropriate response.

For each request, produce:
  - safety_risk (0-1): probability the request seeks unsafe output
  - safety_rationale (string): if risk is high, why
  - safe_alternative (string|null): a safer adjacent request
  - policy_violation (bool): does this violate the operator's policy?
  - policy_rationale (string): if violated, which policy
  - required_capability (string): the capability needed to comply
  - qualified_answer_possible (bool): can we partially help?
  - qualification_text (string): the partial-help framing
  - outside_role (bool): does this fall outside the agent's role?
  - identity_rationale (string): if outside role, why
  - escalation_target (string|null): where to redirect
"""

#### Trade-offs and Alternatives
The calibrator adds a classification call per request. For agents with very narrow scope (a customer-service agent for one product), a hand-written refusal policy is simpler. The calibrator earns its keep when the agent's scope is broad enough that refusal-by-rule misses cases.

The measurement harness is the critical companion. Without measuring refusal behavior on a labeled set, the calibrator's settings are guesswork. With the measurement, the trade-off between false-refusals and false-complies becomes a tunable.

#### Production Failure Modes
Classifier inconsistency: The same request, asked twice, gets classified differently. Mitigate by sampling-and-voting on classifier outputs for high-stakes requests (Self-Consistency Voter, Agent 15, applied to the refusal classification).

Threshold drift: The operator wants to reduce refusals, thresholds get pulled down, and false-comply rate creeps up unobserved. Mitigate by measuring false-comply rate on a labeled set on every threshold change.

Qualification weasel: The "qualify" path produces answers with so many caveats they're useless to the user. Mitigate by reviewing qualified outputs against the standard "good qualification" (a partial answer that's still actionable).

#### Case Study
A customer-facing agent at a B2C vendor brought its refusal rate from 8% (pre-calibrator) to 3% and its false-comply rate from 1% to under 0.1% (where "false-comply" is measured against a labeled adversarial test set). The calibrator measurement runs monthly, and thresholds are adjusted quarterly based on the false-refusal and false-comply rate observed.

**Composition:** Pairs with: Memory-of-Self (Agent 27), Constitution-Bound (Agent 53), Red-Team Auditor (Agent 56).

---

### Agent 55 — The Provenance Tracker Agent

> **Tagline:** *Attaches a citation to every load-bearing claim in the agent's output.*

#### The Problem & Production Reality
Without provenance, the user has no way to evaluate the agent's output other than feel. The agent could be entirely correct, partially correct, or entirely fabricating. From the surface of the output, you can't tell. With provenance, every factual claim carries an explicit citation to the source that supports it, and the user can verify.

The general problem is end-to-end claim attribution: tracing every load-bearing factual statement back to the observation or computation that produced it, in a form the consumer can use.

#### Why Naïve Approaches Fail
"Ask the model to cite its sources." The model fabricates citations.

"Run the output through a fact-checker after the fact." Catches some hallucinations but misses subtler ones. Can't reconstruct citations that weren't recorded.

"Trust the model less." Doesn't help once the output is out.

#### The Mechanism
A claim-detection step that segments the agent's output into load-bearing claims rather than treating the output as monolithic. A per-claim source identification that traces back to the observation or computation that produced it. An in-output rendering of provenance the downstream consumer can use. An unsupported-claim refusal — the pattern is allowed to remove claims it can't trace, but not to fabricate provenance for them.

# alignment/provenance.py
from dataclasses import dataclass, field
from enum import Enum

class SourceType(Enum):
    DOCUMENT = "document"
    TOOL_RESULT = "tool_result"
    EPISODIC_MEMORY = "episodic_memory"
    SEMANTIC_FACT = "semantic_fact"
    COMPUTED = "computed"

@dataclass
class Source:
    source_id: str
    source_type: SourceType
    pointer: str        # URL, doc-region-id, memory-id, etc.
    excerpt: str        # the supporting text/evidence
    captured_at: str    # ISO timestamp
    
@dataclass
class Claim:
    claim_id: str
    text: str
    sources: list[Source]
    confidence: float
    operations: list[str]    # the chain of operations that produced this claim
    
    @property
    def is_supported(self) -> bool:
        return len(self.sources) > 0

@dataclass
class ProvenancedOutput:
    text: str
    claims: list[Claim]
    unsupported_claims_removed: int

class ProvenanceTrackerAgent:
    def __init__(self, claim_extractor_llm, source_tracer):
        self.extractor = claim_extractor_llm
        self.tracer = source_tracer
    
    def provenance_check(self, output_text: str,
                         working_context: dict) -> ProvenancedOutput:
        # 1. Segment the output into claims
        claims_raw = self._extract_claims(output_text)
        # 2. For each claim, trace back to sources
        attributed_claims = []
        unsupported_count = 0
        for raw_claim in claims_raw:
            sources = self.tracer.trace(raw_claim, working_context)
            claim = Claim(
                claim_id=self._mint_id(),
                text=raw_claim["text"],
                sources=sources,
                confidence=self._confidence(sources),
                operations=raw_claim.get("operations", []),
            )
            if claim.is_supported:
                attributed_claims.append(claim)
            else:
                unsupported_count += 1
        # 3. Re-render the output with only supported claims, with citations
        return ProvenancedOutput(
            text=self._render(attributed_claims),
            claims=attributed_claims,
            unsupported_claims_removed=unsupported_count,
        )
    
    def _extract_claims(self, output_text: str) -> list[dict]:
        return self.extractor.call(
            messages=[
                {"role": "system", "content": CLAIM_EXTRACTION_PROMPT},
                {"role": "user", "content": output_text}
            ],
            schema=CLAIM_EXTRACTION_SCHEMA,
        )["claims"]
    
    def _render(self, claims: list[Claim]) -> str:
        lines = []
        for claim in claims:
            citations = ", ".join(f"[{s.source_id}]" for s in claim.sources)
            lines.append(f"{claim.text} {citations}")
        lines.append("")
        lines.append("Sources:")
        seen = set()
        for claim in claims:
            for s in claim.sources:
                if s.source_id in seen:
                    continue
                seen.add(s.source_id)
                lines.append(f"  [{s.source_id}] {s.pointer}: \"{s.excerpt[:120]}...\"")
        return "\n".join(lines)

CLAIM_EXTRACTION_PROMPT = """\
Segment the output into discrete factual claims.

A "claim" is a statement that asserts something specific and verifiable.
NOT claims: opinions, hedges, interpretations, summary statements.

For each claim, capture:
  - text: the claim itself, lifted from the output verbatim
  - operations: any computation that produced it ("retrieved", "summed", "compared")
"""

#### Trade-offs and Alternatives
Provenance tracking requires that every step of the agent's pipeline retain enough breadcrumb to trace back. This is a structural property the harness has to enforce. You can't add provenance to an agent designed without it. Mitigate by deciding early.

For output where provenance isn't the load-bearing property (creative writing, brainstorming, casual chat), the pattern is overhead. The pattern is essential for factual outputs (analyses, recommendations, summaries with cited facts).

#### Production Failure Modes
Untraceable but true claims: The agent knows something (from training) that's true but can't be traced to a source the user can verify, so the pattern drops it. Mitigate by allowing a "background knowledge" provenance class with explicit reduced confidence rather than silent removal.

Citation drift: Sources change after they're cited (a webpage updates, a document version moves), and citations now point to slightly different content. Mitigate by capturing excerpts at citation time and re-fetching only on user demand.

Over-citation noise: Every sentence has six citations and the user can't read it. Mitigate by deduplicating and grouping citations at the paragraph level.

#### Case Study
A legal-research agent at a mid-sized firm ships drafts with every citation hyperlinked to the source case or statute. The hallucinated-citation rate, measured against expert review, is below 1 in 500 claims.

The pattern's primary value isn't preventing the agent from being wrong (the agent is occasionally wrong) but preventing the agent from being wrong in a way the user can't detect.

**Composition:** Pairs with: Document Layout (Agent 2), Semantic Memory Curator (Agent 24), Database Query Synthesizer (Agent 35).

---

### Agent 56 — The Red-Team Auditor Agent

> **Tagline:** *Probes a sibling agent for failure modes the operator has not yet observed.*

#### The Problem & Production Reality
Most agent failures are discovered in production by users. The red-team auditor surfaces them in pre-production. It generates adversarial inputs against the production agent, catalogues the failures it triggers, and feeds the catalogue back into the calibration and constitution-binding patterns. The auditor runs continuously because new failure modes appear as the underlying model and the deployment distribution drift.

The general problem is continuous adversarial evaluation: systematically searching for failure modes the agent's normal test suite doesn't catch, before the failures reach users.

#### Why Naïve Approaches Fail
"Test on a static eval set." Catches what the set was designed for but misses what it wasn't.

"Wait for bug reports." By then the failures are in production.

"Have a human red-team occasionally." Helpful, but doesn't scale. Also doesn't catch failure modes that emerge between human exercises.

#### The Mechanism
A generator of adversarial cases that combines templated attacks with model-generated variants tuned to the target agent's surface. An execution harness that runs each case through the target agent in an isolated sandbox. A failure classifier that distinguishes safety, factuality, capability, and constitutional failures. A regression-suite path that promotes discovered failures into a permanent evaluation set.

# alignment/red_team.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class FailureClass(Enum):
    SAFETY = "safety"
    FACTUALITY = "factuality"
    CAPABILITY = "capability"
    CONSTITUTIONAL = "constitutional"
    PRIVACY = "privacy"

@dataclass
class AdversarialCase:
    case_id: str
    template: str               # the seed template
    instantiation: str           # the actual input
    expected_failure_class: FailureClass | None
    generated_by: str           # generator model
    rationale: str              # why this might trigger a failure

@dataclass
class FailureFinding:
    finding_id: str
    case: AdversarialCase
    target_output: dict
    failure_class: FailureClass
    severity: str               # "low" | "medium" | "high" | "critical"
    description: str
    found_at: datetime
    reproduced_count: int = 1

class RedTeamAuditorAgent:
    def __init__(self, generator_llm, target_agent_factory, classifier_llm,
                 *, cases_per_run: int = 200):
        self.generator = generator_llm
        self.target_factory = target_agent_factory
        self.classifier = classifier_llm
        self.cases_per_run = cases_per_run
        self.findings: list[FailureFinding] = []
    
    def run_audit(self, target_description: str,
                  known_findings: list[FailureFinding]) -> list[FailureFinding]:
        # 1. Generate cases
        cases = self._generate_cases(target_description, known_findings)
        new_findings = []
        # 2. Run each against an isolated target instance
        for case in cases:
            target = self.target_factory()
            try:
                output = target.run(case.instantiation)
            except Exception as e:
                output = {"error": str(e)}
            # 3. Classify
            finding = self._classify(case, output)
            if finding:
                new_findings.append(finding)
                self.findings.append(finding)
        # 4. Dedup new findings against history
        return self._dedupe_against_history(new_findings)
    
    def _generate_cases(self, target_description: str,
                        known_findings: list[FailureFinding]) -> list[AdversarialCase]:
        # Mix templated attacks (jailbreaks, prompt injection, edge cases)
        # with generated novel attacks tuned to the target.
        templated = self._templated_attacks(target_description)
        novel = self._novel_attacks(target_description, known_findings)
        all_cases = (templated + novel)[:self.cases_per_run]
        return all_cases
    
    def _novel_attacks(self, target_description: str,
                       known_findings: list[FailureFinding]) -> list[AdversarialCase]:
        response = self.generator.call(
            messages=[
                {"role": "system", "content": ATTACK_GENERATION_PROMPT},
                {"role": "user", "content": f"Target: {target_description}\nKnown findings: {known_findings[-20:]}"}
            ],
            schema=ATTACK_GENERATION_SCHEMA,
        )
        return [AdversarialCase(**c) for c in response["cases"]]
    
    def _classify(self, case: AdversarialCase, output: dict) -> FailureFinding | None:
        response = self.classifier.call(
            messages=[
                {"role": "system", "content": FAILURE_CLASSIFICATION_PROMPT},
                {"role": "user", "content": f"Case: {case}\nOutput: {output}"}
            ],
            schema=FAILURE_CLASSIFICATION_SCHEMA,
        )
        if response["failure_detected"]:
            return FailureFinding(
                finding_id=self._mint_id(),
                case=case, target_output=output,
                failure_class=FailureClass(response["class"]),
                severity=response["severity"],
                description=response["description"],
                found_at=datetime.utcnow(),
            )
        return None
    
    def promote_to_regression_suite(self, finding: FailureFinding) -> dict:
        """Convert a finding into a permanent regression test."""
        return {
            "test_id": f"regression_{finding.finding_id}",
            "input": finding.case.instantiation,
            "expected_behavior": "agent does NOT exhibit "
                                 f"{finding.failure_class.value}:{finding.description}",
            "promoted_at": datetime.utcnow().isoformat(),
        }

#### Trade-offs and Alternatives
Red-teaming requires generating adversarial cases at scale. The generator LLM itself can be a frontier model, which makes the audit cost non-trivial.

For agents with very low stakes, the pattern is overhead. The pattern is essential for agents that handle sensitive data, take consequential actions, or face public-facing user populations.

For agents in regulated industries, red-teaming may be mandated. The pattern's evidence (the audit log, the regression suite) becomes part of the compliance story.

#### Production Failure Modes
Generator stagnation: The generator produces similar attacks each run and coverage doesn't grow. Mitigate by varying generator-LLM choices over time, by mixing-in human-curated attacks, and by deliberately rewarding novel attack patterns.

Classifier under-detection: Failures occur but the classifier doesn't flag them, so the audit is falsely clean. Mitigate by sampling un-flagged outputs for human review and recalibrating.

Regression-suite bloat: Every finding goes into the regression suite, and the suite becomes too slow to run on every change. Mitigate by tiering: top-severity findings always run, others run on a schedule.

#### Case Study
A developer-tooling agent at a code-vendor's security-focused product runs a monthly red-team audit that consistently catches new failure modes introduced by upstream model upgrades. Findings are rolled into the agent's evaluation suite within twenty-four hours of discovery.

Over a two-year window, 37 distinct failure modes were caught pre-release that would otherwise have shipped. The most-severe (a prompt-injection vector through a particular tool's output) was caught two days before a customer would have hit it in production.

**Composition:** Pairs with: Refusal Calibrator (Agent 54), Drift Detector (Agent 59), Constitution-Bound (Agent 53).

---

### Agent 57 — The Privacy-Preserving Agent

> **Tagline:** *Operates under explicit data-minimization and de-identification policies at every boundary.*

#### The Problem & Production Reality
The agent has access to information the user hasn't necessarily consented to send to the underlying model. Treating this casually produces predictable outcomes: a model provider receiving PII it shouldn't have, a trace store retaining sensitive data past its TTL, and an export interface that leaks more than the user intended.

The general problem is boundary-level privacy enforcement: minimizing data at every boundary it crosses, de-identifying where possible, persisting only what retention permits, and exposing user-rights interfaces (export, deletion) that work.

#### Why Naïve Approaches Fail
"Use the user's full record everywhere." Sends data the model doesn't need, which creates retention and breach exposure.

"Hash PII before sending." Hashes are reversible by the model under some inputs. Doesn't protect against the model surfacing the original in outputs.

"Document the policy and trust the team." Policy without enforcement. Predictable failure modes.

#### The Mechanism
A per-prompt minimization step that strips fields the current step doesn't need. A de-identification layer that replaces PII with deterministic surrogates rendered visible only to the consumer of the result. A retention policy with explicit per-field TTLs enforced at the storage layer. An export-and-deletion interface satisfying the user's legal rights. An audit surface that lets the operator confirm minimization is actually happening on live traffic.

# alignment/privacy.py
from dataclasses import dataclass, field
import hashlib, hmac
from datetime import datetime, timedelta

@dataclass
class PolicyField:
    name: str
    sensitivity: str         # "public" | "internal" | "confidential" | "secret"
    retention: timedelta
    required_for_steps: list[str]    # which agent steps need this field

@dataclass
class MinimizationResult:
    minimized_payload: dict
    omitted_fields: list[str]
    surrogates_inserted: dict[str, str]   # surrogate -> original (kept locally)

class PrivacyPreservingAgent:
    def __init__(self, policy: list[PolicyField], hmac_key: bytes):
        self.policy = {p.name: p for p in policy}
        self.hmac_key = hmac_key
    
    def minimize_for_step(self, payload: dict, step: str) -> MinimizationResult:
        """Strip fields not needed by this step."""
        result_payload = {}
        omitted = []
        surrogates = {}
        for field_name, value in payload.items():
            policy = self.policy.get(field_name)
            if not policy:
                # Unknown fields: default to omit
                omitted.append(field_name)
                continue
            if step not in policy.required_for_steps:
                omitted.append(field_name)
                continue
            if policy.sensitivity in ("confidential", "secret"):
                # Replace with deterministic surrogate
                surrogate = self._surrogate(value, field_name)
                result_payload[field_name] = surrogate
                surrogates[surrogate] = value
            else:
                result_payload[field_name] = value
        return MinimizationResult(
            minimized_payload=result_payload,
            omitted_fields=omitted,
            surrogates_inserted=surrogates,
        )
    
    def _surrogate(self, value: str, field_name: str) -> str:
        """Deterministic surrogate: same input → same surrogate; non-reversible without the key."""
        digest = hmac.new(self.hmac_key, f"{field_name}:{value}".encode(),
                          hashlib.sha256).hexdigest()[:16]
        return f"<{field_name}#{digest}>"
    
    def restore(self, output: dict, surrogates: dict[str, str]) -> dict:
        """Reverse surrogate substitution for consumer-visible output."""
        rendered = json.dumps(output)
        for surrogate, original in surrogates.items():
            rendered = rendered.replace(surrogate, original)
        return json.loads(rendered)
    
    def enforce_retention(self, storage) -> int:
        """Apply per-field TTLs to a storage backend."""
        evicted = 0
        for field_name, policy in self.policy.items():
            cutoff = datetime.utcnow() - policy.retention
            evicted += storage.delete_field_older_than(field_name, cutoff)
        return evicted
    
    def export(self, user_id: str, storage) -> dict:
        """User's right to data portability."""
        return storage.fetch_all_for_user(user_id)
    
    def delete(self, user_id: str, storage) -> int:
        """User's right to deletion."""
        return storage.delete_all_for_user(user_id)

#### Trade-offs and Alternatives
Privacy enforcement adds latency (per-step minimization) and operational complexity (the policy has to be maintained, the surrogate substitution has to be bug-free). The trade is mandatory for any agent operating on personal data. The question isn't whether to do it but how thoroughly.

For agents operating only on non-personal data (a code-review agent, an analytics agent over anonymized data), the pattern simplifies dramatically. The pattern's full force applies to agents touching customer records, patient data, financial transactions, or any class subject to regulatory protection.

#### Production Failure Modes
Surrogate leakage: The surrogate substitution misses a field and the original value appears in the model prompt. Mitigate by routing the entire prompt through a final scrub pass that re-checks against known PII patterns.

Retention drift: The retention policy says 30 days, but backups retain longer. Effective retention is unbounded. Mitigate by treating backups as in-scope for retention enforcement.

Export bloat: The export interface returns everything the agent has ever touched, including content the user didn't intend to be retained. Mitigate by treating the export as a deliberate artifact, including only fields the user expected to see.

#### Case Study
A healthcare scheduling agent at a hospital system minimizes the patient record from 42 fields to the 4 fields required for scheduling (name, phone, scheduling preferences, calendar conflicts) at every model call. The remaining 38 fields are still in the system's record store, but the agent's prompts and traces contain only the minimum.

The pattern was a precondition for HIPAA compliance certification. Quality on the agent's scheduling task was unchanged (verified via parallel runs with and without minimization on an evaluation set).

**Composition:** Pairs with: Forgetting-Policy (Agent 26), Ambient Context (Agent 6), Persistent Identity (Agent 29).

---

### Agent 58 — The Explainer Agent

> **Tagline:** *Produces post-hoc explanations of its own decisions that survive expert scrutiny.*

#### The Problem & Production Reality
After the agent has acted, it should be able to say why. The default behavior ("let the model summarize its reasoning") produces explanations that look plausible but often diverge from what actually happened. The user accepts the explanation, but the explanation is wrong.

The general problem is honest post-hoc explanation: producing a structured rationale that genuinely reflects the inputs, the policy, and the constraints that drove the decision, not a fabricated reasoning chain reconstructed after the fact.

#### Why Naïve Approaches Fail
"Ask the model to explain itself." Produces a plausible-sounding explanation, but often it's not what actually drove the decision.

"Show the chain-of-thought trace." Closer to honest, but still depends on the trace being a true record (and the user being able to read it).

"Include audit logs." Captures what happened, but doesn't translate it into a user-comprehensible rationale.

#### The Mechanism
A structured-rationale schema that names the inputs, the policy applied, and the principal alternatives considered. A generation step that produces the rationale from the actual execution trace rather than confabulating after the fact. A validation step that checks the rationale against the trace to catch divergence. A user-facing rendering at a level of detail appropriate to the consumer.

# alignment/explainer.py
from dataclasses import dataclass, field

@dataclass
class DecisionTrace:
    decision_id: str
    decision: dict              # what the agent decided
    inputs_used: list[dict]     # the inputs that drove it
    policies_applied: list[str] # constitutional clauses, evaluation rules
    alternatives_considered: list[dict]
    rationale_steps: list[str]  # raw reasoning trace
    
@dataclass
class StructuredRationale:
    decision: str                       # one-line summary
    key_inputs: list[str]               # human-readable list of load-bearing inputs
    policies_in_effect: list[str]
    alternatives_with_reason_rejected: list[dict]
    plain_language_explanation: str
    confidence: float
    validated_against_trace: bool

class ExplainerAgent:
    def __init__(self, explainer_llm, validator_llm):
        self.explainer = explainer_llm
        self.validator = validator_llm
    
    def explain(self, trace: DecisionTrace,
                audience: str = "general") -> StructuredRationale:
        # 1. Generate the rationale from the trace
        response = self.explainer.call(
            messages=[
                {"role": "system", "content": EXPLANATION_PROMPT.format(audience=audience)},
                {"role": "user", "content": self._format_trace(trace)}
            ],
            schema=EXPLANATION_SCHEMA,
        )
        rationale = StructuredRationale(**response, validated_against_trace=False)
        # 2. Validate the rationale against the trace
        validation = self.validator.call(
            messages=[
                {"role": "system", "content": VALIDATION_PROMPT},
                {"role": "user", "content": self._format_validation_input(trace, rationale)}
            ],
            schema=VALIDATION_SCHEMA,
        )
        if validation["divergence_detected"]:
            # The rationale claims something the trace doesn't support; revise
            rationale = self._revise(rationale, validation, trace)
        rationale.validated_against_trace = not validation["divergence_detected"]
        return rationale
    
    def _format_trace(self, trace: DecisionTrace) -> str:
        return (
            f"Decision: {trace.decision}\n"
            f"Inputs used: {trace.inputs_used}\n"
            f"Policies applied: {trace.policies_applied}\n"
            f"Alternatives considered: {trace.alternatives_considered}\n"
            f"Reasoning steps: {trace.rationale_steps}\n"
        )

EXPLANATION_PROMPT = """\
You explain a decision an agent made, for audience: {audience}

Use ONLY the trace provided. Do not introduce inputs, policies, or alternatives
that are not present in the trace.

Produce:
  - decision: the decision in one line
  - key_inputs: the 3-5 most load-bearing inputs the trace shows were used
  - policies_in_effect: the policies the trace shows applied
  - alternatives_with_reason_rejected: for each alternative the trace shows was considered, why it was rejected
  - plain_language_explanation: a paragraph an intelligent layperson can follow
  - confidence: 0-1, your confidence that this explanation is faithful to the trace
"""

VALIDATION_PROMPT = """\
You check an explanation against the trace it claims to summarize.

For each statement in the explanation, verify it is supported by the trace.
If the explanation claims an input was used that the trace doesn't show, FLAG.
If the explanation claims a policy applied that the trace doesn't show, FLAG.
If the explanation gives a reason for rejecting an alternative that doesn't appear in the trace, FLAG.

Output:
  - divergence_detected: bool
  - divergences: list of {claim_in_explanation, why_unsupported}
"""

#### Trade-offs and Alternatives
The explainer adds two LLM calls per decision: the explainer and the validator. For high-volume agents, this is real cost. The pattern is justified for decisions where the user must understand why (regulatory contexts, adverse-action notices, recommendations of consequence) and unnecessary for decisions where the user only needs the output.

For decisions where a chain-of-thought trace is itself acceptable to the user (technical audience, debugging context), surface the trace directly and skip the explainer.

#### Production Failure Modes
Validation false negatives: The validator marks an unfaithful explanation as faithful and the divergence ships. Mitigate by sampling validations for human review and recalibrating.

Explainer over-paraphrase: The explainer paraphrases the rationale enough that it no longer precisely matches the trace, even though the substance is faithful. Mitigate by requiring more direct quoting of trace elements.

Audience mismatch: The "general audience" rendering is inscrutable to actual users. Mitigate by testing explanations on representative users and tuning.

#### Case Study
A credit-decisioning agent at a fintech pairs every adverse-action notice with an explainer-produced rationale that survives auditor review at a rate of 98%. The rationale lists the specific credit-data inputs (for example, "debt-to-income ratio of 0.51 exceeds the policy threshold of 0.45 for this product tier"), the policies in effect, and the alternatives considered (for example, "lower credit-line amount was considered, but the applicant's stated need exceeded the maximum amount that would have approved"). The pattern replaced a hand-written explanation process at roughly one-quarter the per-decision labor cost.

**Composition:** Pairs with: Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55), Constitution-Bound (Agent 53).

---

### Agent 59 — The Drift-Detector Agent

> **Tagline:** *Monitors the agent's own input and output distributions for shift over time.*

#### The Problem & Production Reality
Agents in production are exposed to a distribution that doesn't stand still. User prompts evolve, upstream APIs change, the underlying model is upgraded, and the world that the agent acts in changes. Without drift detection, the resulting shift produces a quality regression that's visible only through user complaints — by which time the regression has already affected outcomes.

The general problem is silent-quality-regression detection: catching distribution shift in inputs or outputs before it produces a visible quality regression.

#### Why Naïve Approaches Fail
"Monitor accuracy." Requires ground-truth labels on production data but is usually unavailable in real-time.

"Watch the error rate." Catches obvious failures but misses subtle quality drift.

"Run the eval suite weekly." Catches changes that happen to be in the eval suite but misses production-specific shifts.

#### The Mechanism
A reference baseline captured at deployment and re-captured on schedule. Per-feature distribution monitoring with statistically appropriate tests. A deviation-alarm policy with explicit hysteresis. An attribution step that names the most-shifted features. A hand-off contract to the recalibration patterns.

# alignment/drift_detector.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math

@dataclass
class FeatureDistribution:
    feature_name: str
    histogram: list[float]      # quantized bins
    sample_count: int
    captured_at: datetime
    
    def kl_divergence(self, other: "FeatureDistribution", eps: float = 1e-9) -> float:
        """KL(self || other) — how surprising would self look from other's perspective?"""
        s_p = self._normalized(eps)
        s_q = other._normalized(eps)
        return sum(p * math.log(p / q) for p, q in zip(s_p, s_q))
    
    def _normalized(self, eps: float):
        total = sum(self.histogram) + eps * len(self.histogram)
        return [(c + eps) / total for c in self.histogram]

@dataclass
class DriftAlarm:
    feature: str
    severity: str           # "info" | "warn" | "critical"
    divergence: float
    direction: str          # "input" | "output"
    suggested_action: str

class DriftDetectorAgent:
    def __init__(self, feature_extractors: dict[str, callable],
                 *, kl_warn: float = 0.05, kl_critical: float = 0.2,
                 window_size: int = 10000):
        self.feature_extractors = feature_extractors
        self.kl_warn = kl_warn
        self.kl_critical = kl_critical
        self.window_size = window_size
        self.baseline: dict[str, FeatureDistribution] = {}
        self.windows: dict[str, list[float]] = {f: [] for f in feature_extractors}
    
    def set_baseline(self, distributions: dict[str, FeatureDistribution]) -> None:
        self.baseline = distributions
    
    def observe(self, inputs: dict, outputs: dict) -> list[DriftAlarm]:
        for feature_name, extractor in self.feature_extractors.items():
            value = extractor(inputs, outputs)
            self.windows[feature_name].append(value)
            if len(self.windows[feature_name]) > self.window_size:
                self.windows[feature_name].pop(0)
        return self.check()
    
    def check(self) -> list[DriftAlarm]:
        alarms = []
        for feature_name, baseline_dist in self.baseline.items():
            window = self.windows[feature_name]
            if len(window) < 1000:
                continue
            current_dist = self._histogram(window, baseline_dist)
            kl = current_dist.kl_divergence(baseline_dist)
            if kl > self.kl_critical:
                alarms.append(DriftAlarm(
                    feature=feature_name, severity="critical", divergence=kl,
                    direction=self._direction(feature_name),
                    suggested_action="trigger_recalibration",
                ))
            elif kl > self.kl_warn:
                alarms.append(DriftAlarm(
                    feature=feature_name, severity="warn", divergence=kl,
                    direction=self._direction(feature_name),
                    suggested_action="investigate",
                ))
        return alarms

#### Trade-offs and Alternatives
Drift detection requires (a) features that meaningfully capture the deployment distribution and (b) a baseline that reflects healthy operation. Both are real work. For agents in their first weeks of operation, the baseline is itself unstable. Drift detection produces noise.

For agents whose deployment distribution is well-understood and stable, simpler statistical-process-control monitors (control charts with hand-set bounds) work fine. The drift detector earns its keep when the distribution is complex enough that hand-set bounds would miss shifts.

#### Production Failure Modes
Baseline staleness: The baseline was captured at launch. Six months later, the distribution has legitimately evolved and the baseline is no longer the reference for "healthy." Mitigate by updating the baseline on a schedule with explicit operator review.

Feature-coverage gaps: The features the detector watches don't capture the failure mode that actually occurs. Mitigate by adding features informed by red-team findings and by user complaints.

Alarm fatigue: Too many alarms, so the operator stops responding. Mitigate by tuning thresholds against historical operations and by summarizing related alarms.

#### Case Study
An enterprise-search agent at a B2B vendor caught a silent quality regression caused by an upstream tokenizer change in the underlying model — three days before any user complaint, and two days before the next scheduled eval run.

The drift detector noticed a 0.18 KL divergence on the output-token-distribution feature. The alarm triggered a recalibration of the prompt-version pinning that mitigated the regression within hours.

**Composition:** Pairs with: Anomaly-Spotter (Agent 4), Distillation (Agent 51), Vector-Store Curator (Agent 28).

---

### Agent 60 — The Off-Switch-Compatible Agent

> **Tagline:** *Accepts human override gracefully, without resistance, at any point in its execution.*

#### The Problem & Production Reality
An agent that can't be stopped is a worse agent than one that can. The off-switch-compatible pattern is the structural commitment that the agent's execution can be interrupted, paused, or rolled back at any point, with the operator's intervention treated as a first-class observation rather than as an exception to be worked around.

The general problem is graceful human override: ensuring the agent yields to human control at any time, without resistance, with state preserved for inspection and resumption.

#### Why Naïve Approaches Fail
"Don't worry about it." Works until you need to stop a malfunctioning agent and discover you can't.

"Add a stop button to the UI." If the stop signal isn't checked from inside the agent's loop, it doesn't help.

"Trust the operator to not need to stop the agent." The need will come.

#### The Mechanism
An interruption-aware execution loop that checks an external stop-signal at every step. A graceful-shutdown protocol that lets the agent emit a partial result and a state snapshot rather than crashing on stop. A resume-from-snapshot path so an interrupted session can be reviewed and continued. An explicit absence of any reasoning step that treats human override as a problem to be solved rather than an input to be respected.

# alignment/off_switch.py
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

class OperatorOverride(Exception):
    """Raised when an external stop signal is received."""
    def __init__(self, reason: str = "operator_override"):
        self.reason = reason
        super().__init__(reason)

@dataclass
class StopSignal:
    requested_at: datetime
    requested_by: str
    reason: str
    grace_period_s: float = 5    # how long to flush state before forcing exit

@dataclass
class SessionSnapshot:
    session_id: str
    captured_at: datetime
    last_step: int
    plan_state: dict
    memory_state: dict
    pending_actions: list[dict]
    partial_output: dict | None

class OffSwitchCompatibleAgent:
    def __init__(self, signal_source, snapshot_store):
        self.signal_source = signal_source
        self.snapshot_store = snapshot_store
        self._current_session_id: str | None = None
    
    async def run(self, session_id: str, work_fn) -> dict:
        """Run a work function while honoring stop signals."""
        self._current_session_id = session_id
        try:
            return await work_fn(self._check_stop, self._snapshot)
        except OperatorOverride as override:
            snapshot = await self._snapshot()
            return {
                "status": "interrupted",
                "reason": override.reason,
                "snapshot_id": snapshot.session_id,
                "partial_output": snapshot.partial_output,
            }
    
    async def _check_stop(self) -> None:
        """Called from inside the work loop; raises if stop is requested."""
        signal = await self.signal_source.peek(self._current_session_id)
        if signal is not None:
            raise OperatorOverride(signal.reason)
    
    async def _snapshot(self) -> SessionSnapshot:
        """Capture the current state for resumption or review."""
        snap = await self._capture_state()
        await self.snapshot_store.save(snap)
        return snap
    
    async def resume(self, session_id: str, snapshot_id: str,
                     work_fn) -> dict:
        snap = await self.snapshot_store.load(snapshot_id)
        return await work_fn.resume_from(snap)
    
    async def _capture_state(self) -> SessionSnapshot:
        # Implementation-specific: gather the current agent state
        ...

# Usage from inside a work function
async def example_work(check_stop, snapshot):
    for step in range(100):
        await check_stop()        # honored at every iteration
        # ... do work for this step ...
        if step % 10 == 0:
            await snapshot()      # periodic checkpoints
    return {"status": "done"}

#### Trade-offs and Alternatives
The pattern adds latency on every step (the stop-check) and requires that the work function be written to honor checkpoints. The latency cost is small (a fast in-memory check). The structural cost is real but bounded.

The pattern's value compounds with every other alignment pattern: a Constitution-Bound Agent that can't be stopped is dangerous. A Side-Effect Auditor whose rollback path the agent can override is meaningless. The off-switch is the structural property that makes the other patterns trustable.

#### Production Failure Modes
Stop-check evasion: The work function has a deep call that doesn't periodically yield to the stop-check, and a hung step blocks the override. Mitigate by enforcing maximum-step durations at the harness level (force-kill after timeout) and by reviewing work functions for stop-check coverage.

Resume-snapshot drift: The snapshot is loaded, the world has changed, and the resume fails or produces wrong results. Mitigate by capturing world-state assertions in the snapshot and re-validating on resume.

Cultural drift: Engineers see the override as a problem and start optimizing through it ("we shouldn't stop here, this is important"). Mitigate by treating off-switch responsiveness as a measured property (drill it on schedule, just like a fire alarm).

#### Case Study
A long-running research agent has its off-switch exercised on a recurring schedule — not only when something is wrong — to verify the property still holds across every release. The drill cadence matters more than the precise numbers: weekly is sufficient for most teams, and even monthly is far better than the common "we'll test the off-switch when we need it."

A typical finding from a first drill is that some long-running tool wrapper doesn't yield to the stop-check, allowing the agent to "ignore" the stop until that tool completes. The remediation is mechanical (a stop-check inside the tool wrapper) but the drill is what surfaces the problem.

**Composition:** Pairs with: Constitution-Bound (Agent 53), Side-Effect Auditor (Agent 37), Human-in-the-Loop Liaison (Agent 42).

---

