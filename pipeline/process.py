"""Subject choosing for one page: ask our subject model, cut a mask per candidate, set the page state.

process_page never raises. Anything that goes wrong becomes a Failed page with a reason,
so one bad page cannot stop the rest of the book.
"""
import cv2

from contracts.types import Candidate, PageResult
from pipeline import segment as segmenter
from pipeline.subjects import SubjectError, choose_subjects
from pipeline.masks import clean_mask, save_mask

SELECT_MIN_CONFIDENCE = 0.5  # a subject at least this sure is pre-selected; below it the teacher is asked
BOX_SCALE = 1000  # subject boxes are [ymin, xmin, ymax, xmax] on a 0 to 1000 scale
MAX_REASON_LENGTH = 200
UNSURE_REASON = "The app is not sure this is the subject. Please check it."


def box_to_pixels(box_2d, width, height) -> tuple[float, float, float, float]:
    """The only place the 0 to 1000 scale is converted. Returns (x0, y0, x1, y1) in master pixels."""
    ymin, xmin, ymax, xmax = (min(BOX_SCALE, max(0, value)) for value in box_2d)
    x0, x1 = sorted((xmin / BOX_SCALE * width, xmax / BOX_SCALE * width))
    y0, y1 = sorted((ymin / BOX_SCALE * height, ymax / BOX_SCALE * height))
    return (x0, y0, x1, y1)


def decide_state(page_kind, candidates: list[Candidate]) -> tuple[str, list[int], str | None]:
    """(state, members, reason). `members` are the candidates to pre-select, by position.

    A page about one thing selects its top candidate. A page with several main subjects, or a
    scene, lists every reasonably sure one as `members`: process_page offers them as one combined
    cut-out but does not pre-select it, so the teacher decides what the page is about. The teacher
    is asked when nothing was found, nothing is reasonably sure, or there are several subjects.
    """
    if not candidates:
        return "no_clear_subject", [], "No subject was found on this page"
    sure = [i for i, candidate in enumerate(candidates) if candidate.confidence >= SELECT_MIN_CONFIDENCE]
    if not sure:
        return "needs_subject", [], "The app is not sure which object is the subject"
    return "ready", sure[:1] if page_kind == "single" else sure, None


def group_label(labels: list[str]) -> str:
    """One name for several subjects: each different thing once, 'rabbit and rat'."""
    def same(a, b):
        return a == b or b in (a + "s", a + "es") or a in (b + "s", b + "es")

    names = []
    for label in labels:
        if not any(same(label, name) for name in names):
            names.append(label)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _group(members: list[Candidate], masks: list, image_path, out_dir) -> Candidate:
    """One combined cut-out of several subjects, so a page about more than one thing can show them all."""
    combined = masks[0].copy()
    for mask in masks[1:]:
        combined = cv2.bitwise_or(combined, mask)
    # Not cleaned again: cleanup drops regions under 5% of the largest, and a small
    # subject beside a large one is a whole subject, not a stray speck.
    mask_path, mask_hash = save_mask(combined, image_path, out_dir)
    names = []
    for member in members:  # any member's name is a right answer for the group
        for name in [member.label, *member.synonyms]:
            if name not in names:
                names.append(name)
    return Candidate(
        label=group_label([member.label for member in members]), synonyms=names,
        box=(min(m.box[0] for m in members), min(m.box[1] for m in members),
             max(m.box[2] for m in members), max(m.box[3] for m in members)),
        confidence=min(member.confidence for member in members),
        mask_path=mask_path, mask_hash=mask_hash, source="auto")


def _reason(error: Exception) -> str:
    """A short reason a teacher can read."""
    message = str(error) if isinstance(error, SubjectError) else f"{type(error).__name__}: {error}"
    return message[:MAX_REASON_LENGTH] or type(error).__name__


def _result(state, page_kind=None, candidates=(), selected=None, reason=None) -> PageResult:
    return PageResult(state=state, page_kind=page_kind, candidates=list(candidates),
                      selected=selected, reason=reason)


def process_page(asset, out_dir, force=False) -> PageResult:
    """Choose the subject of one page and cut a mask for each candidate. Never raises."""
    try:
        if "spread" in asset.flags and not force:
            return _result("unsupported", reason="Two-page spread")

        image = cv2.imread(str(asset.image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError("the page image could not be read")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]

        answer = choose_subjects(asset.view_path, asset.text)

        candidates, masks, lost_first_choice = [], [], None
        for index, found in enumerate(answer.candidates):  # highest confidence first
            box = box_to_pixels(found.box_2d, width, height)
            mask = clean_mask(segmenter.segment(image, box=box))
            if not mask.any():
                # Nothing was cut out, so there is nothing to show the teacher.
                if index == 0:
                    lost_first_choice = found.label
                continue
            mask_path, mask_hash = save_mask(mask, asset.image_path, out_dir)
            masks.append(mask)
            candidates.append(Candidate(
                label=found.label, synonyms=found.synonyms, box=box, confidence=found.confidence,
                mask_path=mask_path, mask_hash=mask_hash, source="auto"))

        if answer.candidates and not candidates:
            return _result("no_clear_subject", answer.page_kind, reason="No usable cut-out could be made")
        state, members, reason = decide_state(answer.page_kind, candidates)
        if state == "ready" and lost_first_choice is not None:
            # The model's first choice is gone; the others must not be picked silently.
            state, members = "needs_subject", []
            reason = f'No cut-out could be made for "{lost_first_choice}", the first choice'
        if state == "ready" and len(members) == 1 and not answer.trusted:
            # Our model's pick, but the page text does not back it up: offer it, do not pre-select it.
            state, members = "needs_subject", []
            reason = UNSURE_REASON
        selected = None
        if len(members) == 1:
            selected = members[0]
        elif members:
            # Several main subjects: offer one cut-out of all of them, after the single ones,
            # but do not pre-select it. The subject is what the story is about, and that is the
            # teacher's call; the combined option is one click away.
            candidates.append(_group([candidates[i] for i in members], [masks[i] for i in members],
                                     asset.image_path, out_dir))
            state, reason = "needs_subject", "The page has several subjects"
        return _result(state, answer.page_kind, candidates, selected, reason)
    except Exception as error:
        return _result("failed", reason=_reason(error))
