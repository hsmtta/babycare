# MIT License
# (c) 2023 Takahiro Hashimoto
import heapq
import sys
import numpy as np
from enum import Enum
from datetime import datetime, timedelta, time
from abc import ABC, abstractmethod
from typing import List, Tuple

NUM_MINS = 60
NUM_HOURS = 24


def format_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    h, remainder = divmod(total_seconds, 3600)
    m = remainder // 60
    return f"{h:02d}:{m:02d}"


def log_message(dt: datetime, message: str, pause=True):
    dt_str = dt.strftime("%Y-%m-%d %I:%M %p")
    print(dt_str, "|", message, end="", flush=True)
    if pause:
        # Press enter to proceed
        user_input = input()
        if user_input.lower() == "q":
            print("Exiting the program...")
            sys.exit(1)
    else:
        print(flush=True)


def log_event(dt: datetime, event_name: str, message: str, pause=True):
    log_message(dt, event_name + " | " + message, pause)


class EventStatus(Enum):
    PENDING = 0
    READY = 1
    RUNNING = 2
    PAUSED = 3
    COMPLETED = 4


class Baby:
    def __init__(self, current_time: datetime):
        self._average_interval_min = 180
        self._stdiv_interval_min = 30
        self._last_fed = None
        self._interval = None
        self.fed(current_time)

    def fed(self, current_time: datetime):
        self._last_fed = current_time

        interval_min = np.random.normal(self._average_interval_min, self._stdiv_interval_min)
        self._interval = timedelta(minutes=interval_min)

    def is_hungry(self, current_time: datetime) -> bool:
        return current_time - self._last_fed >= self._interval


class DailyReporter:
    def __init__(self):
        self._freetime = timedelta()
        self._feeding_count = 0
        self._intervention_count = 0

    def _print(self):
        print("----------DAILY SUMMARY----------")
        freetime_str = format_timedelta(self._freetime)
        print(f"# milk feeding: {self._feeding_count}")
        print(f"# intervention: {self._intervention_count}")
        print(f"Freetime: {freetime_str}")
        print("---------------------------------")

    def _reset(self):
        self.__init__()

    def update_freetime(self, duration: timedelta):
        self._freetime += duration

    def update_feeding(self):
        self._feeding_count += 1

    def update_intervention(self):
        self._intervention_count += 1

    def try_print(self, now: datetime, step: timedelta):
        if now.day != (now + step).day:
            self._print()
            self._reset()


class Event(ABC):
    """Abstruct base class for events."""

    def __init__(self, name: str, priority: int):
        self._name = name

        # Smaller numbers (>= 0) have higher priority
        self._priority = priority

        self._duration = None

        self._status = EventStatus.PENDING
        self._time_elapsed = timedelta()

    @property
    def priority(self):
        return self._priority

    @abstractmethod
    def is_ready(self, current_time: datetime) -> bool:
        """True when event is ready to be queued"""
        pass

    @abstractmethod
    def process(self, current_time: datetime, time_step: timedelta):
        """Process event for a specified duration."""
        pass

    @abstractmethod
    def pause(self, current_time: datetime):
        """Pause ongoing event."""
        pass

    @abstractmethod
    def finalize(self):
        pass


class Airer(Event):
    """Once washing is complete, hang clothes on an airer and hold dried clothes."""

    def __init__(self):
        super().__init__("Airer", 5)
        self._hanging_duration = timedelta(minutes=10)
        self._holding_duration = timedelta(minutes=20)
        self._duration = self._hanging_duration + self._holding_duration
        self._schedule = None

    def notify_washing(self, end_schedule: datetime):
        self._schedule = end_schedule

    def is_ready(self, now: datetime) -> bool:
        assert self._status == EventStatus.PENDING, "Event status should be PENDING"
        if self._schedule is None:
            return False

        past_due_time = now >= self._schedule
        if past_due_time:
            self._status = EventStatus.READY
            return True
        else:
            return False

    def process(self, now: datetime, step: timedelta):
        assert self._status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self._time_elapsed += step

        if self._status == EventStatus.PAUSED:
            log_event(now, self._name, "Resume event.")
        self._status = EventStatus.RUNNING

        if self._time_elapsed == step:
            log_event(
                now, self._name, f"Washing finished. Start hanging clothes. Takes {self._hanging_duration.seconds//60} min."
            )

        if self._time_elapsed == self._hanging_duration:
            log_event(
                now + step, self._name, f"Start holding dried clothes. Takes {self._holding_duration.seconds//60} min."
            )

        if self._time_elapsed == self._duration:
            self._status = EventStatus.COMPLETED
            log_event(now + step, self._name, f"Event completed.")

    def pause(self, now: datetime):
        assert self._status == EventStatus.RUNNING, "Event status should be RUNNING"
        self._status = EventStatus.PAUSED
        log_event(now, self._name, "Get up in the middle.", False)

    def finalize(self):
        assert self._status == EventStatus.COMPLETED, "Event status should be COMPLETED"
        self._status = EventStatus.PENDING
        self._time_elapsed = timedelta()
        self._schedule = None


class MilkFeeding(Event):
    def __init__(self, baby: Baby, reporter: DailyReporter):
        super().__init__("Milk Feeding", 0)
        self._prep_duration = timedelta(minutes=10)
        self._feeding_duration = timedelta(minutes=30)
        self._cleanup_duration = timedelta(minutes=5)
        self._duration = self._prep_duration + self._feeding_duration + self._cleanup_duration
        self._reporter = reporter

        self._baby = baby

    def is_ready(self, now: datetime) -> bool:
        if self._baby.is_hungry(now):
            self._status = EventStatus.READY
            return True
        return False

    def process(self, now: datetime, step: timedelta):
        self._time_elapsed += step

        if self._time_elapsed == step:
            log_event(now, self._name, f"Baby is crying. Start preparing milk. Takes {self._prep_duration.seconds//60} min.")

        if self._time_elapsed == self._prep_duration:
            log_event(now + step, self._name, f"Start feeding. Takes {self._feeding_duration.seconds//60} min.")

        if self._time_elapsed == self._prep_duration + self._feeding_duration:
            self._reporter.update_feeding()
            log_event(now + step, self._name, f"Start clean up. Takes {self._cleanup_duration.seconds//60} min.")

        if self._time_elapsed == self._duration:
            self._baby.fed(now + step)
            log_event(now + step, self._name, "The event is completed.")
            self._status = EventStatus.COMPLETED

    def pause(self, now: datetime):
        pass

    def finalize(self):
        self._status = EventStatus.PENDING
        self._time_elapsed = timedelta()


class DailyEvent(Event):
    def __init__(self, now: datetime, name: str, priority: int, schedule: time, skip_today=False):
        super().__init__(name, priority)
        self._daily_schedule = schedule
        self._next_schedule = datetime(now.year, now.month, now.day, self._daily_schedule.hour, self._daily_schedule.minute)
        if skip_today:
            self._next_schedule += timedelta(days=1)

    def is_ready(self, now: timedelta) -> bool:
        assert self._status == EventStatus.PENDING, "Event status should be PENDING"
        past_due_time = now >= self._next_schedule
        if past_due_time:
            self._status = EventStatus.READY
            return True
        else:
            return False

    def pause(self, now: datetime):
        assert self._status == EventStatus.RUNNING, "Event status should be RUNNING"
        self._status = EventStatus.PAUSED
        log_event(now, self._name, "Suspend the event.", False)

    def finalize(self):
        assert self._status == EventStatus.COMPLETED, "Event status should be COMPLETED"
        self._status = EventStatus.PENDING
        self._time_elapsed = timedelta()
        self._next_schedule += timedelta(days=1)


class Meal(DailyEvent):
    def __init__(self, now: datetime, name: str, priority: int, schedule: time, durations, skip_today=False):
        super().__init__(now, name, priority, schedule, skip_today)
        self._prep_duration = timedelta(minutes=durations[0])
        self._eating_duration = timedelta(minutes=durations[1])
        self._cleanup_duration = timedelta(minutes=durations[2])
        self._duration = self._prep_duration + self._eating_duration + self._cleanup_duration

    def process(self, now: datetime, time_step: timedelta):
        assert self._status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self._time_elapsed += time_step

        if self._status == EventStatus.PAUSED:
            log_event(now, self._name, f"Resume {self._name} event.")
        self._status = EventStatus.RUNNING

        if self._time_elapsed == time_step:
            log_event(now, self._name, f"Start preparing. Takes {self._prep_duration.seconds//60} min.")
        elif self._time_elapsed == self._prep_duration:
            log_event(now + time_step, self._name, f"Start eating. Takes {self._eating_duration.seconds//60} min.")
        elif self._time_elapsed == self._prep_duration + self._eating_duration:
            log_event(now + time_step, self._name, f"Start cleaning up. Takes {self._cleanup_duration.seconds//60} min.")
        elif self._time_elapsed == self._duration:
            self._status = EventStatus.COMPLETED
            log_event(now + time_step, self._name, f"{self._name} event is completed.")


class Sleep(DailyEvent):
    def __init__(self, now: datetime, skip_today=False):
        super().__init__(now, "Sleep", 5, time(hour=23, minute=0), skip_today)
        self._duration = timedelta(hours=8)

    def process(self, now: datetime, step: timedelta):
        assert self._status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self._time_elapsed += step

        if self._status == EventStatus.PAUSED:
            log_event(now, self._name, "Start sleeping again.")
        self._status = EventStatus.RUNNING

        if self._time_elapsed == step:
            log_event(now, self._name, "Start sleeping. Good night!!")
        elif self._time_elapsed == self._duration:
            self._status = EventStatus.COMPLETED
            log_event(now + step, self._name, f"Bedtime is over. Good morning!!")


class Laundry(DailyEvent):
    """Gather clothes, measure and add detergent to the drum, and start the laundry machine."""

    def __init__(self, now: datetime, airer_event: Airer, skip_today=False):
        super().__init__(now, "Laundry", 5, time(hour=9, minute=0), skip_today)
        self._duration = timedelta(minutes=10)
        self._airer_event = airer_event

        # Once washing is complete, Airer event will be triggered
        self._washing_duration = timedelta(minutes=120)

    def process(self, now: datetime, step: timedelta):
        assert self._status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self._time_elapsed += step

        if self._status == EventStatus.PAUSED:
            log_event(now, self._name, "Resume event.")
        self._status = EventStatus.RUNNING

        if self._time_elapsed == step:
            log_event(now, self._name, "Gather clothes and put it to the dram.")
        elif self._time_elapsed == self._duration:
            self._status = EventStatus.COMPLETED
            self._airer_event.notify_washing(now + step + self._washing_duration)
            log_event(
                now + step, self._name, f"Start washing machine. Washing duration: {self._washing_duration.seconds//60} min."
            )


class EventManager:
    """
    Managing events, checking their conditions, and processing events based on their priority.
    """

    def __init__(self, reporter: DailyReporter):
        self._count = 0
        self._events_to_check: List[Event] = []
        self._event_queue: List[Tuple[int, int, Event]] = []
        self._ongoing_event: Event = None
        self._reporter = reporter

    def _check_conditions(self, now: datetime, step: timedelta) -> bool:
        for event in self._events_to_check:
            if event.is_ready(now):
                heapq.heappush(self._event_queue, (event.priority, self._count, event))
                self._events_to_check.remove(event)
                self._count += 1

        if len(self._event_queue) == 0:
            # Free time
            self._reporter.update_freetime(step)
            return False
        else:
            return True

    def _process_next_event(self, now: datetime, step: timedelta):
        # Get the highest priority event
        _, _, event = self._event_queue[0]

        # If priority is changed, suspend the old event and start a new one.
        if type(event) != type(self._ongoing_event) and self._ongoing_event != None:
            self._ongoing_event.pause(now)
            self._reporter.update_intervention()
        self._ongoing_event = event
        event.process(now, step)

        if event._status == EventStatus.COMPLETED:
            # Move event from the waiting list to the check list
            self._ongoing_event = None
            _, _, event = heapq.heappop(self._event_queue)
            event.finalize()
            self._events_to_check.append(event)

    def add_event(self, event: Event):
        self._events_to_check.append(event)

    def process(self, now: datetime, step: timedelta):
        queue_is_not_empty = self._check_conditions(now, step)

        if queue_is_not_empty:
            self._process_next_event(now, step)


def main():
    now = datetime(2023, 4, 2, 7, 0)
    baby = Baby(now)
    reporter = DailyReporter()

    breakfast = Meal(now, "Breakfast", 5, time(8, 0), (15, 10, 10))
    lunch = Meal(now, "Lunch", 5, time(12, 0), (30, 15, 10))
    dinner = Meal(now, "Dinner", 5, time(18, 0), (45, 30, 15))
    airer = Airer()
    laundry = Laundry(now, airer)
    events = [breakfast, lunch, dinner, airer, laundry, MilkFeeding(baby, reporter), Sleep(now)]

    event_manager = EventManager(reporter)
    for event in events:
        event_manager.add_event(event)

    # Simulate 3 days
    NUM_DAYS = 3
    time_step = timedelta(minutes=1)
    log_message(now, "Starting a life with a baby...")
    for _ in range(NUM_MINS * NUM_HOURS * NUM_DAYS):
        event_manager.process(now, time_step)

        # Report daily event summary at the final step of the day
        reporter.try_print(now, time_step)

        now += time_step


if __name__ == "__main__":
    main()
