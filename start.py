# MIT License
# (c) 2023 Takahiro Hashimoto
import heapq
import numpy as np
from enum import Enum
from datetime import datetime, timedelta, time
from abc import ABC, abstractmethod
from typing import List, Tuple


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
        input()
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
        self.average_interval_min = 180
        self.stdiv_interval_min = 30
        self.last_fed = None
        self.interval = None
        self.fed(current_time)

    def fed(self, current_time: datetime):
        self.last_fed = current_time

        interval_min = np.random.normal(self.average_interval_min, self.stdiv_interval_min)
        self.interval = timedelta(minutes=interval_min)

    def is_hungry(self, current_time: datetime) -> bool:
        return current_time - self.last_fed >= self.interval


class Event(ABC):
    """Abstruct base class for events."""

    def __init__(self, name: str, priority: int):
        self.name = name

        # Smaller numbers (>= 0) have higher priority
        self.priority = priority

        self.duration = None

        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()

    @abstractmethod
    def is_ready(self, current_time: datetime) -> bool:
        """True when event should be processed."""
        pass

    @abstractmethod
    def process(self, current_time: datetime, time_step: timedelta):
        """Process new or suspended event for a specified duration."""
        pass

    @abstractmethod
    def pause(self, current_time: datetime):
        """Suspend ongoing event."""
        pass

    @abstractmethod
    def finalize(self):
        pass


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

    def notify_freetime(self, duration: timedelta):
        self._freetime += duration

    def notify_feeding(self):
        self._feeding_count += 1

    def notify_intervention(self):
        self._intervention_count += 1

    def try_print(self, now: datetime, step: timedelta):
        if now.day != (now + step).day:
            self._print()
            self._reset()


class Meal(Event):
    def __init__(self, now: datetime, name: str, priority: int, schedule: time, durations, skip_today=False):
        super().__init__(name, priority)
        self.daily_schedule = schedule
        self.prep_duration = timedelta(minutes=durations[0])
        self.eating_duration = timedelta(minutes=durations[1])
        self.cleanup_duration = timedelta(minutes=durations[2])
        self.duration = self.prep_duration + self.eating_duration + self.cleanup_duration

        self.next_schedule = datetime(now.year, now.month, now.day, self.daily_schedule.hour, self.daily_schedule.minute)
        if skip_today:
            self.next_schedule += timedelta(days=1)

    def is_ready(self, now: timedelta) -> bool:
        assert self.status == EventStatus.PENDING, "Event status should be PENDING"
        past_due_time = now >= self.next_schedule
        if past_due_time:
            self.status = EventStatus.READY
            return True
        else:
            return False

    def process(self, now: datetime, time_step: timedelta):
        assert self.status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self.time_elapsed += time_step

        if self.status == EventStatus.PAUSED:
            log_event(now, self.name, f"Resume {self.name} event.")
        self.status = EventStatus.RUNNING

        if self.time_elapsed == time_step:
            log_event(now, self.name, f"Start preparing. Takes {self.prep_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration:
            log_event(now + time_step, self.name, f"Start eating. Takes {self.eating_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.eating_duration:
            log_event(now + time_step, self.name, f"Start cleaning up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.status = EventStatus.COMPLETED
            log_event(now + time_step, self.name, f"{self.name} event is completed.")

    def pause(self, now: datetime):
        assert self.status == EventStatus.RUNNING, "Event status should be RUNNING"
        self.status = EventStatus.PAUSED
        log_event(now, self.name, "Suspend the event.", False)

    def finalize(self):
        assert self.status == EventStatus.COMPLETED, "Event status should be COMPLETED"
        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()
        self.next_schedule += timedelta(days=1)


class Sleep(Event):
    def __init__(self, now: datetime, skip_today=False):
        super().__init__("Sleep", 5)
        self.daily_schedule = time(hour=23, minute=0)
        self.duration = timedelta(hours=7)

        self.next_schedule = datetime(now.year, now.month, now.day, self.daily_schedule.hour, self.daily_schedule.minute)
        if skip_today:
            self.next_schedule += timedelta(days=1)

    def is_ready(self, current_time: datetime) -> bool:
        assert self.status == EventStatus.PENDING, "Event status should be PENDING"
        past_due_time = current_time >= self.next_schedule
        if past_due_time:
            self.status = EventStatus.READY
            return True
        else:
            return False

    def process(self, current_time: datetime, time_step: timedelta):
        assert self.status in [
            EventStatus.READY,
            EventStatus.RUNNING,
            EventStatus.PAUSED,
        ], "Event status should be one of READY, RUNNING, or PAUSED"
        self.time_elapsed += time_step

        if self.status == EventStatus.PAUSED:
            log_event(current_time, self.name, "Start sleeping again.")
        self.status = EventStatus.RUNNING

        if self.time_elapsed == time_step:
            log_event(current_time, self.name, "Start sleeping. Good night!!")

        if self.time_elapsed == self.duration:
            self.status = EventStatus.COMPLETED
            log_event(current_time + time_step, self.name, f"Bedtime is over. Good morning!!")

    def pause(self, current_time: datetime):
        assert self.status == EventStatus.RUNNING, "Event status should be RUNNING"
        self.status = EventStatus.PAUSED
        log_event(current_time, self.name, "Get up in the middle.", False)

    def finalize(self):
        assert self.status == EventStatus.COMPLETED, "Event status should be COMPLETED"
        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()
        self.next_schedule += timedelta(days=1)


class Laundry(Event):
    """Gather clothes, measure and add detergent to the drum, and start the laundry machine."""

    def __init__(self):
        super().__init__()
        self.priority = 4
        self.schedule = time(hour=9, minute=0)
        self.duration = timedelta(minutes=10)

        # Once washing is complete, Airer event will be triggered
        self.washing_duration = timedelta(minutes=120)


class Airer(Event):
    """Once washing is complete, hang clothes on an airer and hold dried clothes."""

    def __init__(self):
        self.priority = 4
        self.hanging_duration = timedelta(minutes=10)
        self.holding_duration = timedelta(minutes=20)
        self.duration = self.hanging_duration + self.holding_duration


class MilkFeeding(Event):
    def __init__(self, baby: Baby, reporter: DailyReporter):
        super().__init__("Milk Feeding", 0)
        self.prep_duration = timedelta(minutes=10)
        self.feeding_duration = timedelta(minutes=30)
        self.cleanup_duration = timedelta(minutes=5)
        self.duration = self.prep_duration + self.feeding_duration + self.cleanup_duration
        self._reporter = reporter

        self.baby = baby

    def is_ready(self, current_time: datetime) -> bool:
        if self.baby.is_hungry(current_time):
            self.status = EventStatus.READY
            return True
        return False

    def process(self, current_time: datetime, time_step: timedelta):
        self.time_elapsed += time_step

        if self.time_elapsed == time_step:
            log_event(
                current_time, self.name, f"Baby is crying. Start preparing milk. Takes {self.prep_duration.seconds//60} min."
            )

        if self.time_elapsed == self.prep_duration:
            log_event(current_time + time_step, self.name, f"Start feeding. Takes {self.feeding_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.feeding_duration:
            self._reporter.notify_feeding()
            log_event(current_time + time_step, self.name, f"Start clean up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.baby.fed(current_time + time_step)
            log_event(current_time + time_step, self.name, "The event is completed.")
            self.status = EventStatus.COMPLETED

    def pause(self, current_time: datetime):
        pass

    def finalize(self):
        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()


class EventManager:
    """
    Managing events, checking their conditions, and processing events based on their priority.
    """

    def __init__(self, reporter: DailyReporter):
        self.count = 0
        self.events_to_check: List[Event] = []
        self.event_queue: List[Tuple[int, int, Event]] = []
        self.ongoing_event: Event = None
        self._reporter = reporter

    def add_event(self, event: Event):
        self.events_to_check.append(event)

    def check_conditions(self, now: datetime, step: timedelta) -> bool:
        for event in self.events_to_check:
            if event.is_ready(now):
                heapq.heappush(self.event_queue, (event.priority, self.count, event))
                self.events_to_check.remove(event)
                self.count += 1

        if len(self.event_queue) == 0:
            # Free time
            self._reporter.notify_freetime(step)
            return False
        else:
            return True

    def process_next_event(self, current_time: datetime, step: timedelta):
        # Get the highest priority event
        _, _, event = self.event_queue[0]

        # If priority is changed, suspend the old event and start a new one.
        if type(event) != type(self.ongoing_event) and self.ongoing_event != None:
            self.ongoing_event.pause(current_time)
            self._reporter.notify_intervention()
        self.ongoing_event = event
        event.process(current_time, step)

        if event.status == EventStatus.COMPLETED:
            # Move event from the waiting list to the check list
            self.ongoing_event = None
            _, _, event = heapq.heappop(self.event_queue)
            event.finalize()
            self.events_to_check.append(event)


def main():
    now = datetime(2023, 4, 2, 7, 0)
    baby = Baby(now)
    reporter = DailyReporter()

    breakfast = Meal(now, "Breakfast", 5, time(8, 0), (15, 10, 10))
    lunch = Meal(now, "Lunch", 5, time(12, 0), (30, 15, 10))
    dinner = Meal(now, "Dinner", 5, time(18, 0), (45, 30, 15))
    events = [breakfast, lunch, dinner, MilkFeeding(baby, reporter), Sleep(now)]

    event_manager = EventManager(reporter)
    for event in events:
        event_manager.add_event(event)

    # Simulate 2 days
    time_step = timedelta(minutes=1)
    log_message(now, "Starting a life with a baby...")
    for _ in range(60 * 24 * 2):
        has_satisfied_event = event_manager.check_conditions(now, time_step)

        if has_satisfied_event:
            event_manager.process_next_event(now, time_step)

        # Print daily event summary at the final step of the day
        reporter.try_print(now, time_step)

        now += time_step


if __name__ == "__main__":
    main()
