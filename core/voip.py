"""
VoIP Service for PhoneTracker CLI

Handles phone call operations using Twilio API.
"""

import time
from typing import Optional, Literal
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


CallStatus = Literal['answered', 'busy', 'no-answer', 'failed', 'canceled', 'timeout']


class VoIPService:
    """
    VoIP service for making and managing phone calls via Twilio.
    
    Attributes:
        client: Twilio REST client
        from_number: The phone number to call from
        current_call: Reference to the current active call
    """
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Initialize the VoIP service with Twilio credentials.
        
        Args:
            account_sid: Twilio Account SID (starts with AC...)
            auth_token: Twilio Auth Token
            from_number: Phone number to call from (must be a Twilio number)
        """
        if not account_sid or not auth_token:
            raise VoIPError("Twilio credentials not provided")
        
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        self.current_call = None
    
    def make_call(self, to_number: str, timeout: int = 60) -> 'CallHandler':
        """
        Initiate a call to the target number.
        
        Args:
            to_number: Phone number to call (E.164 format, e.g., +1234567890)
            timeout: Call timeout in seconds (default: 60)
            
        Returns:
            CallHandler object for managing the call
            
        Raises:
            VoIPError: If call initiation fails
        """
        try:
            # Use Twilio's demo TwiML for a simple greeting
            # In production, you'd host your own TwiML endpoint
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url='http://demo.twilio.com/docs/voice.xml',
                status_callback_method='POST',
                timeout=timeout
            )
            self.current_call = call
            return CallHandler(call, self.client)
        except TwilioRestException as e:
            raise VoIPError(f"Failed to make call: {e.msg}")
        except Exception as e:
            raise VoIPError(f"Unexpected error making call: {str(e)}")
    
    def get_call_status(self, call_sid: str) -> str:
        """
        Get the current status of a call.
        
        Args:
            call_sid: The SID of the call to check
            
        Returns:
            Call status string
        """
        try:
            call = self.client.calls(call_sid).fetch()
            return call.status
        except TwilioRestException as e:
            raise VoIPError(f"Failed to get call status: {e.msg}")


class CallHandler:
    """
    Handler for managing an active phone call.
    
    Provides methods to wait for call answer, check status, and hang up.
    """
    
    def __init__(self, call, client: Client):
        """
        Initialize the call handler.
        
        Args:
            call: Twilio Call object
            client: Twilio REST client
        """
        self.call = call
        self.client = client
        self.sid = call.sid
    
    def wait_for_answer(self, max_wait: int = 60, poll_interval: int = 2) -> CallStatus:
        """
        Poll call status until answered or timeout.
        
        Args:
            max_wait: Maximum time to wait in seconds (default: 60)
            poll_interval: Time between status checks in seconds (default: 2)
            
        Returns:
            Call status: 'answered', 'busy', 'no-answer', 'failed', 'canceled', or 'timeout'
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                call = self.client.calls(self.sid).fetch()
                
                if call.status == 'in-progress':
                    return 'answered'
                elif call.status in ['busy', 'no-answer', 'failed', 'canceled', 'completed']:
                    return call.status
                
                time.sleep(poll_interval)
            except TwilioRestException as e:
                raise VoIPError(f"Error checking call status: {e.msg}")
        
        # Timeout - try to cancel the call
        try:
            self.client.calls(self.sid).update(status='canceled')
        except Exception:
            pass
        
        return 'timeout'
    
    def get_status(self) -> str:
        """Get the current status of the call."""
        try:
            call = self.client.calls(self.sid).fetch()
            return call.status
        except TwilioRestException as e:
            raise VoIPError(f"Failed to get call status: {e.msg}")
    
    def hangup(self) -> bool:
        """
        End the current call.
        
        Returns:
            True if successfully hung up, False otherwise
        """
        try:
            self.client.calls(self.sid).update(status='completed')
            return True
        except TwilioRestException as e:
            # Call might already be completed
            if 'already' in str(e.msg).lower():
                return True
            raise VoIPError(f"Could not hang up call: {e.msg}")
        except Exception as e:
            return False
    
    @property
    def call_sid(self) -> str:
        """Return the call SID."""
        return self.sid


class VoIPError(Exception):
    """Exception raised for VoIP-related errors."""
    pass
