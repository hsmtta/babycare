# MIT License
# (c) 2023 Takahiro Hashimoto
import heapq
import numpy as np
from enum import Enum
from datetime import datetime, timedelta, time
from abc import ABC, abstractmethod
from typing import List, Tuple

def log_message(time: datetime, message: str, pause = True):
    formatted_time = time.strftime('%Y-%m-%d %I:%M %p')
    print(formatted_time, "|",  message, end="", flush=True)
    if pause: 
        # Press enter to proceed
        input()
    else:
        print(flush=True)

def log_event(time: datetime, event_name: str, message: str, pause=True):
    log_message(time, event_name + " | " + message, pause)

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

    def __init__(self):
        # Smaller numbers (>= 0) have higher priority
        self.priority = 0

        # Scheculed time that the event expected to be happen
        self.schedule = None

        self.duration = None

        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()

    @abstractmethod
    def enqueue_required(self, current_time: datetime) -> bool:
        """True when event should be processed."""
        pass

    @abstractmethod
    def process(self, current_time: datetime, time_step: timedelta):
        """Process new or suspended event for a specified duration."""
        pass

    @abstractmethod
    def suspend(self, current_time: datetime):
        """Suspend ongoing event."""
        pass

    @abstractmethod
    def finalize(self):
        pass

class BreakFast(Event):
    def __init__(self):
        super().__init__()
        self.name = "Breakfast"
        self.priority = 5
        self.schedule = time(hour=8, minute=0)
        self.prep_duration = timedelta(minutes=15)
        self.eating_duration = timedelta(minutes=10)
        self.cleanup_duration = timedelta(minutes=10)
        self.duration = self.prep_duration + self.eating_duration + self.cleanup_duration
        
        self.current_date = None
        self.completed_today = False

    def reset(self):
        self.completed_today = False

    def enqueue_required(self, current_time: datetime) -> bool:
        # Reset event completion when day is changed
        if self.current_date != current_time.date():
            self.current_date = current_time.date()
            self.reset()

        time_in_today = time(hour=current_time.hour, minute=current_time.minute)
        is_past_due_time = time_in_today >= self.schedule
        return is_past_due_time and self.status == EventStatus.PENDING and not self.completed_today

    def process(self, current_time: datetime, time_step: timedelta):
        self.time_elapsed += time_step

        if self.status == EventStatus.PAUSED:
            log_event(current_time, self.name, "Resume breakfast event.")
        self.status = EventStatus.RUNNING
        
        if self.time_elapsed == time_step:
            log_event(current_time, self.name, f"Start preparing. Takes {self.prep_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration:
            log_event(current_time + time_step, self.name, f"Start eating. Takes {self.eating_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.eating_duration:
            log_event(current_time + time_step, self.name, f"Start cleaning up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.status = EventStatus.COMPLETED
            log_event(current_time + time_step, self.name, "Breakfast event is completed.")

    def suspend(self, current_time: datetime):
        self.status = EventStatus.PAUSED
        log_event(current_time, self.name, "Suspend the event.", False)

    def finalize(self):
        self.status = EventStatus.PENDING
        self.completed_today = True
        self.time_elapsed = timedelta()

class Lunch(Event):
    def __init__(self):
        super().__init__()
        self.name = "Lunch"
        self.priority = 5
        self.schedule = time(hour=12, minute=0)
        self.prep_duration = timedelta(minutes=30)
        self.eating_duration = timedelta(minutes=15)
        self.cleanup_duration = timedelta(minutes=10)
        self.duration = self.prep_duration + self.eating_duration + self.cleanup_duration

        self.current_date = None
        self.completed_today = False

    def reset(self):
        self.completed_today = False

    def enqueue_required(self, current_time: datetime) -> bool:
        # Reset event completion when day is changed
        if self.current_date != current_time.date():
            self.current_date = current_time.date()
            self.reset()

        time_in_today = time(hour=current_time.hour, minute=current_time.minute)
        is_past_due_time = time_in_today >= self.schedule
        return is_past_due_time and self.status == EventStatus.PENDING and not self.completed_today

    def process(self, current_time: datetime, time_step: timedelta):
        self.time_elapsed += time_step

        if self.status == EventStatus.PAUSED:
            log_event(current_time, self.name, "Resume Lunch event.")
        self.status = EventStatus.RUNNING

        if self.time_elapsed == time_step:
            log_event(current_time, self.name, f"Start preparing. Takes {self.prep_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration:
            log_event(current_time + time_step, self.name, f"Start eating. Takes {self.eating_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.eating_duration:
            self.is_log_cleanup = True
            log_event(current_time + time_step, self.name, f"Start cleaning up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.status = EventStatus.COMPLETED
            log_event(current_time + time_step, self.name, "Lunch event is completed.")

    def suspend(self, current_time: datetime):
        self.status = EventStatus.PAUSED
        log_event(current_time, self.name, "Suspend the event.", False)

    def finalize(self):
        self.status = EventStatus.PENDING
        self.completed_today = True
        self.time_elapsed = timedelta()

class Dinner(Event):
    def __init__(self):
        super().__init__()
        self.name = "Dinner"
        self.priority = 5
        self.schedule = time(hour=18, minute=0)
        self.prep_duration = timedelta(minutes=45)
        self.eating_duration = timedelta(minutes=30)
        self.cleanup_duration = timedelta(minutes=15)
        self.duration = self.prep_duration + self.eating_duration + self.cleanup_duration

        self.current_date = None
        self.completed_today = False

    def reset(self):
        self.completed_today = False

    def enqueue_required(self, current_time: datetime) -> bool:
        # Reset event completion when day is changed
        if self.current_date != current_time.date():
            self.current_date = current_time.date()
            self.reset()

        time_in_today = time(hour=current_time.hour, minute=current_time.minute)
        is_past_due_time = time_in_today >= self.schedule
        return is_past_due_time and self.status == EventStatus.PENDING and not self.completed_today

    def process(self, current_time: datetime, time_step: timedelta):
        self.time_elapsed += time_step

        if self.status == EventStatus.PAUSED:
            log_event(current_time, self.name, "Resume Dinner event.")
        self.status = EventStatus.RUNNING

        if self.time_elapsed == time_step:
            log_event(current_time, self.name, f"Start preparing. Takes {self.prep_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration:
            log_event(current_time + time_step, self.name, f"Start eating. Takes {self.eating_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.eating_duration:
            log_event(current_time + time_step, self.name, f"Start cleaning up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.status = EventStatus.COMPLETED
            log_event(current_time + time_step, self.name, "Dinner event is completed.")

    def suspend(self, current_time: datetime):
        self.status = EventStatus.PAUSED
        log_event(current_time, self.name, "Suspend the event.", False)
    
    def finalize(self):
        self.status = EventStatus.PENDING
        self.completed_today = True
        self.time_elapsed = timedelta()

class Sleep():
    def __init__(self):
        super().__init__()
        self.name = "Sleep"
        self.priority = 5
        self.schedule = time(hour=0, minute=0)

    def enqueue_required(self, current_time: datetime) -> bool:
        # Reset event completion when day is changed
        if self.current_date != current_time.date():
            self.current_date = current_time.date()
            self.reset()

        time_in_today = time(hour=current_time.hour, minute=current_time.minute)
        is_past_due_time = time_in_today >= self.schedule
        return is_past_due_time and self.status == EventStatus.PENDING

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
    def __init__(self, baby: Baby):
        super().__init__()
        self.name = "Milk Feeding"
        self.priority = 0
        self.prep_duration = timedelta(minutes=10)
        self.feeding_duration = timedelta(minutes=30)
        self.cleanup_duration = timedelta(minutes=5)
        self.duration = self.prep_duration + self.feeding_duration + self.cleanup_duration

        self.baby = baby

    def enqueue_required(self, current_time: datetime) -> bool:
        return self.baby.is_hungry(current_time)

    def process(self, current_time: datetime, time_step: timedelta):
        self.time_elapsed += time_step

        if self.time_elapsed == time_step:
            log_event(current_time, self.name, f"Baby is crying. Start preparing milk. Takes {self.prep_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration:
            log_event(current_time + time_step, self.name, f"Start feeding. Takes {self.feeding_duration.seconds//60} min.")

        if self.time_elapsed == self.prep_duration + self.feeding_duration:
            log_event(current_time + time_step, self.name, f"Start clean up. Takes {self.cleanup_duration.seconds//60} min.")

        if self.time_elapsed == self.duration:
            self.baby.fed(current_time + time_step)
            log_event(current_time + time_step, self.name, "The event is completed.")
            self.status = EventStatus.COMPLETED

    def suspend(self, current_time: datetime):
        pass

    def finalize(self):
        self.status = EventStatus.PENDING
        self.time_elapsed = timedelta()

class EventManager:
    """
    Managing events, checking their conditions, and processing events based on their priority.
    """

    def __init__(self):
        self.count = 0
        self.events_to_check: List[Event] = []
        self.event_queue: List[Tuple[int, int, Event]] = []
        self.ongoing_event: Event = None

    def register_event(self, event: Event):
        self.events_to_check.append(event)

    def check_conditions(self, current_time: datetime) -> bool:
        for event in self.events_to_check:
            if event.enqueue_required(current_time):
                heapq.heappush(self.event_queue, (event.priority, self.count, event))
                event.status = EventStatus.READY
                self.events_to_check.remove(event)
                self.count += 1

        return len(self.event_queue) > 0

    def process_next_event(self, current_time: datetime, step: timedelta):
        # Get the highest priority event
        _, _, event = self.event_queue[0]

        # If priority is changed, suspend the old event and start a new one.
        if type(event) != type(self.ongoing_event) and self.ongoing_event != None:
            self.ongoing_event.suspend(current_time)
        self.ongoing_event = event
        event.process(current_time, step)

        if event.status == EventStatus.COMPLETED:
            # Move event from the waiting list to the check list
            self.ongoing_event = None
            _, _, event = heapq.heappop(self.event_queue)
            event.finalize()
            self.events_to_check.append(event)

def main():
    # Feed baby now
    current_time = datetime(2023, 4, 2, 7, 0)
    log_message(current_time, "Starting a life with a baby...")

    baby = Baby(current_time)

    events = [BreakFast(), Lunch(), Dinner(), MilkFeeding(baby)]
    event_manager = EventManager()
    for event in events:
        event_manager.register_event(event)

    # Simulate 2 days
    time_step = timedelta(minutes=1)
    for _ in range(60 * 24 * 2):
        has_satisfied_event = event_manager.check_conditions(current_time)

        if has_satisfied_event:
            event_manager.process_next_event(current_time, time_step)

        current_time += time_step

if __name__ == "__main__":
    main()
