"""
main.py — Backend Logic
=======================
Pure Python. No Flask, no HTTP, no UI.
Contains all three memory-management simulators.
project.py imports from this file and calls its functions directly.
"""

import collections
from collections import namedtuple


# ---------------------------------------------------------------------------
# Paging Simulator
# ---------------------------------------------------------------------------

class PagingSimulator:
    """Fixed-size page frames, FIFO or LRU replacement."""

    def __init__(self, total_memory: int = 32, page_size: int = 4):
        self.total_memory = total_memory
        self.page_size = page_size
        self.num_frames = total_memory // page_size
        self._reset_state()

    def _reset_state(self):
        self.memory = [None] * self.num_frames   # Each slot: (process_id, page_num) or None
        self.page_table: dict = {}               # {pid: [(page_num, frame|-1), ...]}
        self.disk: dict = {}                     # evicted pages
        self.algorithm = "FIFO"
        self._fifo_queue = collections.deque()   # FIFO: insertion order
        self._lru_counter: dict = {}             # LRU: frame -> last-access counter
        self._access_clock = 0
        self.page_faults = 0
        self.last_fault_frame = None             # frame index of most-recent fault (for flash)

    # ---- public API -------------------------------------------------------

    def set_algorithm(self, algorithm: str):
        """Switch between 'FIFO' and 'LRU'. Resets tracking structures."""
        if algorithm not in ("FIFO", "LRU"):
            raise ValueError(f"Unknown algorithm: {algorithm!r}. Use 'FIFO' or 'LRU'.")
        self.algorithm = algorithm
        self._fifo_queue.clear()
        self._lru_counter.clear()
        self._access_clock = 0

    def simulate_page_request(self, process_id: str, page_num: int):
        """
        Handle a single page request.
        - If the page is already in a frame: hit → update LRU counter if needed.
        - If not: page fault → evict, load, update structures.
        """
        process_id = str(process_id)
        page = (process_id, page_num)

        # Check if already in memory
        for frame_idx, occupant in enumerate(self.memory):
            if occupant == page:
                # Hit
                if self.algorithm == "LRU":
                    self._access_clock += 1
                    self._lru_counter[frame_idx] = self._access_clock
                self.last_fault_frame = None
                return

        # ---- Page fault (page not in RAM) ----
        # Only count as a page fault when RAM is full and eviction is needed
        ram_had_free = None in self.memory

        if ram_had_free:
            # Free frame available — no eviction, not a "page fault" in the
            # classic sense (just a cold miss / compulsory miss)
            frame_idx = self.memory.index(None)
            self.last_fault_frame = None   # no flash — not a true fault
        else:
            # RAM full → must evict → this is the true page fault
            self.page_faults += 1
            frame_idx = self._evict()
            self.last_fault_frame = frame_idx

        # Load page into frame
        self.memory[frame_idx] = page
        self.last_fault_frame = frame_idx

        # Update tracking structures
        if self.algorithm == "FIFO":
            self._fifo_queue.append(frame_idx)
        else:
            self._access_clock += 1
            self._lru_counter[frame_idx] = self._access_clock

        # Update page table
        if process_id not in self.page_table:
            self.page_table[process_id] = []
        # Update existing entry or add new one
        for i, (pn, _) in enumerate(self.page_table[process_id]):
            if pn == page_num:
                self.page_table[process_id][i] = (page_num, frame_idx)
                return
        self.page_table[process_id].append((page_num, frame_idx))

    def reset(self):
        """Clear all state, keeping algorithm choice."""
        algo = self.algorithm
        self._reset_state()
        self.algorithm = algo

    def get_state(self) -> dict:
        """Return a plain-dict snapshot for the GUI to consume."""
        frames_count = self.num_frames
        used = sum(1 for f in self.memory if f is not None)
        return {
            "frames":          list(self.memory),
            "page_table":      {pid: list(pages) for pid, pages in self.page_table.items()},
            "page_faults":     self.page_faults,
            "memory_used_pct": (used * 100) // frames_count if frames_count else 0,
            "last_fault_frame": self.last_fault_frame,
            "num_frames":      frames_count,
        }

    # ---- private helpers --------------------------------------------------

    def _evict(self) -> int:
        """Choose a victim frame and remove its page. Returns the freed frame index."""
        if self.algorithm == "FIFO":
            victim_frame = self._fifo_queue.popleft()
        else:  # LRU
            victim_frame = min(self._lru_counter, key=self._lru_counter.get)
            del self._lru_counter[victim_frame]

        old_page = self.memory[victim_frame]
        if old_page is not None:
            self.disk[old_page] = True
            old_pid, old_pn = old_page
            if old_pid in self.page_table:
                for i, (pn, _) in enumerate(self.page_table[old_pid]):
                    if pn == old_pn:
                        self.page_table[old_pid][i] = (pn, -1)   # -1 = on disk
                        break

        self.memory[victim_frame] = None
        return victim_frame


# ---------------------------------------------------------------------------
# Segmentation Simulator
# ---------------------------------------------------------------------------

Segment = namedtuple("Segment", ["process_id", "segment_id", "size", "base"])


class SegmentationSimulator:
    """Variable-size memory segments, first-fit allocation, FIFO or LRU replacement."""

    def __init__(self, total_memory: int = 32):
        self.total_memory = total_memory
        self._reset_state()

    def _reset_state(self):
        self.segments: list[Segment] = []              # allocated segments
        self.free_blocks: list[tuple] = [(0, self.total_memory)]  # (base, size)
        self.segment_table: dict = {}                  # {pid: [Segment, ...]}
        self.algorithm = "FIFO"
        self._fifo_queue: collections.deque = collections.deque()
        self._lru_counter: dict = {}                   # (pid, sid) -> counter
        self._access_clock = 0
        self.allocation_failures = 0
        self.last_allocation: tuple | None = None      # (base, size) of last alloc

    def set_algorithm(self, algorithm: str):
        if algorithm not in ("FIFO", "LRU"):
            raise ValueError(f"Unknown algorithm: {algorithm!r}.")
        self.algorithm = algorithm
        self._fifo_queue.clear()
        self._lru_counter.clear()
        self._access_clock = 0

    def allocate_segment(self, process_id: str, segment_id: int, size: int) -> bool:
        """
        Try to allocate a segment of the given size.
        Returns True on success, False on failure (no contiguous block).
        """
        process_id = str(process_id)

        # If segment already exists for this process+id, treat as an access
        key = (process_id, segment_id)
        if process_id in self.segment_table:
            for seg in self.segment_table[process_id]:
                if seg.segment_id == segment_id:
                    self._touch(key)
                    self.last_allocation = None
                    return True

        # Find first-fit free block
        block = self._find_free_block(size)
        if block is None:
            # Try to evict until enough space
            if not self._evict_for_size(size):
                self.allocation_failures += 1
                self.last_allocation = None
                return False
            block = self._find_free_block(size)
            if block is None:
                self.allocation_failures += 1
                self.last_allocation = None
                return False

        base, _ = block
        self._consume_free_block(base, size)

        seg = Segment(process_id, segment_id, size, base)
        self.segments.append(seg)
        if process_id not in self.segment_table:
            self.segment_table[process_id] = []
        self.segment_table[process_id].append(seg)

        if self.algorithm == "FIFO":
            self._fifo_queue.append(key)
        else:
            self._access_clock += 1
            self._lru_counter[key] = self._access_clock

        self.last_allocation = (base, size)
        return True

    def reset(self):
        algo = self.algorithm
        self._reset_state()
        self.algorithm = algo

    def get_state(self) -> dict:
        used = sum(s.size for s in self.segments)
        # Build segment_table as list-of-tuples for the GUI
        seg_table = {}
        for pid, segs in self.segment_table.items():
            seg_table[pid] = [(s.process_id, s.segment_id, s.size, s.base) for s in segs]
        return {
            "memory_state":       [(s.base, s.size, s.process_id, s.segment_id) for s in self.segments],
            "segment_table":      seg_table,
            "free_blocks":        list(self.free_blocks),
            "allocation_failures": self.allocation_failures,
            "memory_used_pct":    (used * 100) // self.total_memory if self.total_memory else 0,
            "last_allocation":    self.last_allocation,
        }

    # ---- private helpers --------------------------------------------------

    def _touch(self, key):
        if self.algorithm == "LRU":
            self._access_clock += 1
            self._lru_counter[key] = self._access_clock

    def _find_free_block(self, size: int):
        for block in self.free_blocks:
            if block[1] >= size:
                return block
        return None

    def _consume_free_block(self, base: int, size: int):
        for i, (b, s) in enumerate(self.free_blocks):
            if b == base:
                if s == size:
                    self.free_blocks.pop(i)
                else:
                    self.free_blocks[i] = (b + size, s - size)
                return

    def _free_segment(self, seg: Segment):
        """Release a segment back to free blocks and merge adjacent blocks."""
        self.segments.remove(seg)
        pid = seg.process_id
        if pid in self.segment_table:
            self.segment_table[pid] = [s for s in self.segment_table[pid] if s.segment_id != seg.segment_id]
            if not self.segment_table[pid]:
                del self.segment_table[pid]
        self.free_blocks.append((seg.base, seg.size))
        self.free_blocks.sort(key=lambda b: b[0])
        # Merge adjacent free blocks
        merged = [self.free_blocks[0]]
        for base, size in self.free_blocks[1:]:
            prev_base, prev_size = merged[-1]
            if prev_base + prev_size == base:
                merged[-1] = (prev_base, prev_size + size)
            else:
                merged.append((base, size))
        self.free_blocks = merged

    def _evict_for_size(self, needed: int) -> bool:
        """Evict segments until there is a contiguous free block >= needed."""
        for _ in range(len(self.segments)):
            if self._find_free_block(needed):
                return True
            if not self._evict_one():
                break
        return self._find_free_block(needed) is not None

    def _evict_one(self) -> bool:
        if not self.segments:
            return False
        if self.algorithm == "FIFO":
            if not self._fifo_queue:
                return False
            key = self._fifo_queue.popleft()
        else:
            if not self._lru_counter:
                return False
            key = min(self._lru_counter, key=self._lru_counter.get)
            del self._lru_counter[key]
        pid, sid = key
        if pid in self.segment_table:
            for seg in list(self.segment_table[pid]):
                if seg.segment_id == sid:
                    self._free_segment(seg)
                    return True
        return False


# ---------------------------------------------------------------------------
# Virtual Memory Simulator
# ---------------------------------------------------------------------------

class VirtualMemorySimulator:
    """
    Paging with a swap partition.
    Flow: every new page is first placed in swap, then brought into RAM on first access.
    A page fault is counted only when RAM is full and eviction is needed.
    """

    def __init__(self, total_memory: int = 32, page_size: int = 4, swap_size: int = 64):
        self.total_memory = total_memory
        self.page_size = page_size
        self.swap_size = swap_size
        self.num_frames = total_memory // page_size
        self.num_swap_frames = swap_size // page_size
        self._reset_state()

    def _reset_state(self):
        self.memory = [None] * self.num_frames         # RAM frames
        self.swap   = [None] * self.num_swap_frames    # Swap space
        self.page_table: dict = {}                     # {pid: [(page_num, loc_idx, in_ram)]}
        self.algorithm = "FIFO"
        self._fifo_queue = collections.deque()
        self._lru_counter: dict = {}
        self._access_clock = 0
        self.page_faults = 0       # only counted when RAM full → eviction required
        self.swap_operations = 0   # swap-in + swap-out moves
        self.last_fault_frame = None
        self.last_action = ""      # human-readable description of what just happened

    def set_algorithm(self, algorithm: str):
        if algorithm not in ("FIFO", "LRU"):
            raise ValueError(f"Unknown algorithm: {algorithm!r}.")
        self.algorithm = algorithm
        self._fifo_queue.clear()
        self._lru_counter.clear()
        self._access_clock = 0

    def simulate_page_request(self, process_id: str, page_num: int):
        process_id = str(process_id)
        page = (process_id, page_num)

        # ── RAM hit ─────────────────────────────────────────────────────────
        for frame_idx, occupant in enumerate(self.memory):
            if occupant == page:
                if self.algorithm == "LRU":
                    self._access_clock += 1
                    self._lru_counter[frame_idx] = self._access_clock
                self.last_fault_frame = None
                self.last_action = f"HIT — P{process_id} pg{page_num} already in RAM frame {frame_idx}"
                return

        # ── Check swap ──────────────────────────────────────────────────────
        swap_idx = None
        for i, occupant in enumerate(self.swap):
            if occupant == page:
                swap_idx = i
                break

        # ── Page is completely new → stage in swap first ─────────────────
        if swap_idx is None:
            # Find a free swap slot
            if None in self.swap:
                swap_idx = self.swap.index(None)
                self.swap[swap_idx] = page
                self.swap_operations += 1
                self.last_action = f"NEW — P{process_id} pg{page_num} staged to Swap[{swap_idx}]"
            # else swap also full — just proceed to load into RAM directly
            # (edge case; in practice swap >> RAM)

        # ── Now bring page from swap into RAM ────────────────────────────
        ram_had_free = None in self.memory

        if ram_had_free:
            frame_idx = self.memory.index(None)
            # No eviction — no page fault
            self.last_fault_frame = None
            action_prefix = f"SWAP-IN — P{process_id} pg{page_num} Swap[{swap_idx}]→RAM[{frame_idx}]"
        else:
            # RAM full → page fault → must evict
            self.page_faults += 1
            frame_idx = self._evict_to_swap()
            self.last_fault_frame = frame_idx
            action_prefix = (f"FAULT — RAM full, evicted to swap, "
                             f"P{process_id} pg{page_num} → RAM[{frame_idx}]")

        # Move from swap into RAM
        self.memory[frame_idx] = page
        if swap_idx is not None:
            self.swap[swap_idx] = None
            self.swap_operations += 1

        self.last_action = action_prefix

        if self.algorithm == "FIFO":
            self._fifo_queue.append(frame_idx)
        else:
            self._access_clock += 1
            self._lru_counter[frame_idx] = self._access_clock

        # Update page table
        if process_id not in self.page_table:
            self.page_table[process_id] = []
        for i, (pn, loc, in_ram) in enumerate(self.page_table[process_id]):
            if pn == page_num:
                self.page_table[process_id][i] = (page_num, frame_idx, True)
                return
        self.page_table[process_id].append((page_num, frame_idx, True))

    def reset(self):
        algo = self.algorithm
        self._reset_state()
        self.algorithm = algo

    def get_state(self) -> dict:
        used = sum(1 for f in self.memory if f is not None)
        return {
            "memory_frames":   list(self.memory),
            "swap_space":      list(self.swap),
            "page_table":      {pid: list(entries) for pid, entries in self.page_table.items()},
            "page_faults":     self.page_faults,
            "swap_operations": self.swap_operations,
            "memory_used_pct": (used * 100) // self.num_frames if self.num_frames else 0,
            "last_fault_frame": self.last_fault_frame,
            "num_frames":      self.num_frames,
            "num_swap_frames": self.num_swap_frames,
            "last_action":     getattr(self, "last_action", ""),
        }

    # ---- private helpers --------------------------------------------------

    def _evict_to_swap(self) -> int:
        """Choose a victim RAM frame, move its page to swap, return the freed frame."""
        if self.algorithm == "FIFO":
            victim_frame = self._fifo_queue.popleft()
        else:
            victim_frame = min(self._lru_counter, key=self._lru_counter.get)
            del self._lru_counter[victim_frame]

        old_page = self.memory[victim_frame]
        self.memory[victim_frame] = None

        # Find a free swap slot
        if None in self.swap:
            swap_slot = self.swap.index(None)
            self.swap[swap_slot] = old_page
            self.swap_operations += 1
            # Mark page-table entry as in swap
            if old_page is not None:
                old_pid, old_pn = old_page
                if old_pid in self.page_table:
                    for i, (pn, _, __) in enumerate(self.page_table[old_pid]):
                        if pn == old_pn:
                            self.page_table[old_pid][i] = (pn, swap_slot, False)
                            break

        return victim_frame


# ---------------------------------------------------------------------------
# Input parsing helpers (pure logic — no UI)
# ---------------------------------------------------------------------------

def parse_paging_input(raw: str) -> list[tuple]:
    """
    '0,1,2,1,0' → [(1, 0), (1, 1), (1, 2), (1, 1), (1, 0)]
    All pages belong to process "1" (single-process simulation).
    """
    parts = [x.strip() for x in raw.replace(" ", ",").split(",") if x.strip()]
    if not parts:
        raise ValueError("No input provided.")
    return [(1, int(p)) for p in parts]


def parse_segmentation_input(raw: str) -> list[tuple]:
    """
    '0:4,1:8,2:10' → [(1, 0, 4), (1, 1, 8), (1, 2, 10)]
    Format: seg_id:size_kb pairs.
    """
    parts = [x.strip() for x in raw.replace(" ", ",").split(",") if x.strip()]
    if not parts:
        raise ValueError("No input provided.")
    result = []
    for item in parts:
        if ":" not in item:
            raise ValueError(f"Expected seg_id:size, got {item!r}")
        seg_id, size = item.split(":", 1)
        result.append((1, int(seg_id), int(size)))
    return result
