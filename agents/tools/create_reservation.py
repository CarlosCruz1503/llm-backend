import logging

from google.genai import types

from agents.tools.base import BaseTool
from restaurant.services.reservation import NoTableAvailableError, ReservationService, parse_reservation_datetime
from restaurant.services.restaurant import get_default_restaurant

logger = logging.getLogger(__name__)


class CreateReservationTool(BaseTool):

    name: str = "create_reservation"

    description: str = (
        "Creates a restaurant reservation. Automatically assigns any table that is "
        "free at the requested hour and big enough for the party; it never asks the "
        "caller to pick a specific table."
    )

    def get_name(self):
        return self.name

    def execute(self, date_time: str, n_persons: int, customer_name: str, customer_phone: str | None = None, notes: str | None = None):
        restaurant = get_default_restaurant()
        if restaurant is None:
            return "Sorry, I couldn't create the reservation: the restaurant hasn't been set up yet."

        try:
            reservation_date = parse_reservation_datetime(date_time)
            reservation = ReservationService().create_reservation(
                restaurant=restaurant,
                reservation_date=reservation_date,
                party_size=n_persons,
                customer_name=customer_name,
                customer_phone=customer_phone,
                notes=notes,
            )
        except (ValueError, NoTableAvailableError) as e:
            return f"Sorry, I couldn't create that reservation: {e}"
        except Exception:
            logger.exception("Failed to create a reservation")
            return "Sorry, something went wrong while creating the reservation."

        message = (
            f"Reservation confirmed for {customer_name} on {reservation.reservation_date:%Y-%m-%d %H:%M} "
            f"for {n_persons} guest(s) at table {reservation.table.number}."
        )
        if notes:
            message += f" Notes: {notes}"
        return message

    def schema(self):
        function = types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "date_time": {"type": "string", "description": "The day and hour for the reservation (e.g., '2024-07-29 20:00'); this has to be a date_time string."},
                    "n_persons": {"type": "integer", "description": "Quantity of persons that will be in the reservation"},
                    "customer_name": {"type": "string", "description": "Name to book the reservation under"},
                    "customer_phone": {"type": "string", "description": "Customer's phone number, if given"},
                    "notes": {"type": "string", "description": "Any additional note about the reservation if its for a birthday, special ocassion, grade or something like that"},
                },
                "required": ["date_time", "n_persons", "customer_name"],
            },
        )
        return types.Tool(function_declarations=[function])
