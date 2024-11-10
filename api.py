# TODO: This code might be a bit cleaned up and refactored, moved to .env, remove comments, improve logging.
from typing import Annotated
from datetime import datetime, timedelta
import pytz
from livekit.agents import llm
import logging
import requests
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("calendar-availability")
logger.setLevel(logging.INFO)

class CalendarAssistant(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()

        self.api_url = os.getenv('CAL_API_URL')
        self.api_key = os.getenv('CAL_API_KEY')
        self.event_type_id = os.getenv('CAL_EVENT_TYPE_ID')
        if not all([self.api_url, self.api_key, self.event_type_id]):
            raise ValueError("Missing required environment variables")

    @llm.ai_callable(description="Get available calendar slots starting from a specific UTC date and time.")
    def get_available_slots(
        self,
        dateTime: Annotated[str, llm.TypeInfo(description="This property represents the date and time of the booking proposed by speaker converted to UTC format. For example, if user is in 'Europe/Warsaw' (UTC+1) summer time and wants to book at 16:00 their time, the dateTime should be provided as 15:00 UTC: '2024-10-30T15:00:00Z'. The correct format is yyyy-MM-dd'T'HH:mm:ss'Z'.")],
        timezone: Annotated[str, llm.TypeInfo(description="User's IANA timezone (e.g., 'Europe/Warsaw').")],
    ) -> str:
        logger.info("Checking availability for datetime: %s in timezone: %s", dateTime, timezone)
        
        try:
            # Parse input time and calculate end time (3 days window)
            start_time = datetime.strptime(dateTime, "%Y-%m-%dT%H:%M:%SZ")
            logger.info(f"Parsed datetime object: {start_time}")
            end_time = start_time + timedelta(days=3)
            logger.info(f"Datetime type: {type(start_time)}")

            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "eventTypeId": self.event_type_id
            }

            logger.info("Request params: %s", params)

            # Make API request
            response = requests.get(self.api_url, headers=headers, params=params)

            logger.info("API response: %s", response.text)

            response.raise_for_status()

            # Parse the JSON response
            data = response.json()

            # Access the slots data
            slots_data = data.get('data', {}).get('slots', {})

            # Initialize an empty list for all slots
            all_slots = []

            # Flatten the slots into a single list
            for date, slots_on_date in slots_data.items():
                for slot in slots_on_date:
                    all_slots.append(slot)

            if not all_slots:
                return f"No available slots found for the next 3 days starting from {dateTime}"

            # TODO: Implement a more user-friendly response(maybe with better prompt there will be no need for that)
            local_tz = pytz.timezone(timezone)
            formatted_slots = []

            for slot in all_slots:
                slot_time_str = slot['time']
                start = datetime.strptime(slot_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                start = start.replace(tzinfo=pytz.utc).astimezone(local_tz)
                formatted_slot = start.strftime('%Y-%m-%d %H:%M')
                formatted_slots.append(formatted_slot)

            logger.info("Available slots in user's timezone: %s", formatted_slots)
            return f"Available time slots in your timezone ({timezone}):\n" + "\n".join(formatted_slots)

        except Exception as e:
            logger.error("Error checking availability: %s", str(e))
            return "Sorry, I couldn't check the calendar availability at this moment."

    @llm.ai_callable(description="Book a call with a person for a specific UTC date and time.")
    def book_call(
        self,
        startTime: Annotated[str, llm.TypeInfo(description="The agreed date and time for the meeting in UTC format. Must be in format: yyyy-MM-dd'T'HH:mm:ss'Z', for example: '2024-10-28T07:00:00Z'")],
        name: Annotated[str, llm.TypeInfo(description="The full name of the person booking the meeting")],
        email: Annotated[str, llm.TypeInfo(description="Valid email address of the person booking the meeting")],
        timezone: Annotated[str, llm.TypeInfo(description="The attendee's IANA timezone (e.g., 'Europe/Warsaw', 'Asia/Nicosia')")],
    ) -> str:
        logger.info("Attempting to book call for: %s (%s) at %s in timezone: %s", 
                   name, email, startTime, timezone)
        
        try:
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "cal-api-version": "2024-08-13",
                "Content-Type": "application/json"
            }
            
            payload = {
                "start": startTime,
                "eventTypeId": int(self.event_type_id),
                "attendee": {
                    "name": name,
                    "email": email,
                    "timeZone": timezone
                }
            }

            logger.info("Request payload: %s", payload)

            # Make API request
            response = requests.post(
                "https://api.cal.com/v2/bookings",
                headers=headers, 
                json=payload
            )

            logger.info("API response status: %s", response.status_code)
            logger.info("API response body: %s", response.text)

            response.raise_for_status()

            # Parse the response
            booking_data = response.json()
            
            # Convert UTC time to attendee's timezone for display
            meeting_time = datetime.strptime(startTime, "%Y-%m-%dT%H:%M:%SZ")
            local_time = meeting_time.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(timezone))
            formatted_time = local_time.strftime('%Y-%m-%d %H:%M')

            return (
                f"Meeting successfully booked!\n"
                f"Date and time (in your timezone): {formatted_time}\n"
                f"Attendee: {name}\n"
                f"Email: {email}\n"
                f"Timezone: {timezone}"
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to book the meeting: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred while booking the meeting: {str(e)}"
            logger.error(error_msg)
            return error_msg