"""In-memory state seam — holds live domain state injected at server startup (Story 1.3)."""
from atc_mcp.domain.models import Flight, Schedule


class AppState:
    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}
        self.latest_schedule: Schedule | None = None

    def add_flight(self, flight: Flight) -> None:
        """Append flight to the queue. Caller is responsible for duplicate checks."""
        self.flights[flight.flight_number] = flight

    def get_flight(self, flight_number: str) -> Flight | None:
        """Return the flight or None if not found."""
        return self.flights.get(flight_number)

    def replace_flights_after_schedule(self, updated_flights: dict[str, Flight]) -> None:
        """Replace the entire flights dict atomically after a schedule run.

        Preserves insertion order of the incoming dict. The caller (generate_schedule
        tool handler in Story 3.x) builds updated_flights by iterating self.flights
        in order and constructing new Flight instances via model_copy().
        """
        self.flights = updated_flights

    def set_latest_schedule(self, schedule: Schedule) -> None:
        """Store the result of the latest generate_schedule call."""
        self.latest_schedule = schedule

    def reset(self) -> None:
        """Clear all state (used by tests and future restart scenarios)."""
        self.flights = {}
        self.latest_schedule = None


state = AppState()
