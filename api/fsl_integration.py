import requests
import json
import logging
from typing import Optional, Dict, Any
from settings import config

logger = logging.getLogger(__name__)

class FSLIntegration:
    def __init__(self, api_url: str, api_token: str, reviewer_weight: float = 1.0):
        self.api_url = api_url
        self.api_token = api_token
        self.reviewer_weight = reviewer_weight
        
    def create_reviewer(self, twitch_username: str) -> Optional[Dict[str, Any]]:
        """
        Create a new FSL reviewer account for a Twitch user.
        
        Args:
            twitch_username: The Twitch username (without 'twitch_' prefix)
            
        Returns:
            Dict with API response or None if failed
        """
        try:
            reviewer_name = f"twitch_{twitch_username}"
            
            payload = {
                "action": "create_reviewer",
                "data": {
                    "name": reviewer_name,
                    "weight": self.reviewer_weight
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            url = f"{self.api_url}?token={self.api_token}"
            
            logger.info(f"Creating FSL reviewer for {reviewer_name}")
            response = requests.post(url, headers=headers, json=payload, timeout=10, verify=config.FSL_VERIFY_SSL)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"FSL API response for create_reviewer: {result}")
                return result
            else:
                logger.error(f"FSL API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"FSL API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"FSL API response not valid JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in FSL integration: {e}")
            return None
    
    def check_reviewer_exists(self, twitch_username: str) -> bool:
        """
        Check if a reviewer account already exists for a Twitch user.
        Since get_reviewer action doesn't exist in the API, we'll try to create
        and see if it fails with an "already exists" error.
        
        Args:
            twitch_username: The Twitch username (without 'twitch_' prefix)
            
        Returns:
            True if reviewer exists, False otherwise
        """
        try:
            reviewer_name = f"twitch_{twitch_username}"
            
            payload = {
                "action": "create_reviewer",
                "data": {
                    "name": reviewer_name,
                    "weight": self.reviewer_weight
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            url = f"{self.api_url}?token={self.api_token}"
            
            logger.info(f"Checking if FSL reviewer exists by attempting creation: {reviewer_name}")
            response = requests.post(url, headers=headers, json=payload, timeout=10, verify=config.FSL_VERIFY_SSL)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"FSL API response for existence check: {result}")
                
                # If creation succeeds, reviewer didn't exist before
                if result.get('success', False):
                    logger.info(f"FSL reviewer {reviewer_name} did not exist (creation succeeded)")
                    return False
                else:
                    # Check if the error indicates reviewer already exists
                    error_msg = str(result.get('error', '')).lower()
                    if any(phrase in error_msg for phrase in ['already exists', 'already exist', 'duplicate', 'exists']):
                        logger.info(f"FSL reviewer {reviewer_name} already exists (creation failed with exists error)")
                        return True
                    else:
                        # Some other error, assume doesn't exist
                        logger.info(f"FSL reviewer {reviewer_name} creation failed with other error: {error_msg}")
                        return False
            else:
                logger.error(f"FSL API error checking reviewer existence: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"FSL API request failed checking reviewer existence: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"FSL API response not valid JSON checking reviewer existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking FSL reviewer existence: {e}")
            return False
    
    def get_reviewer_link(self, twitch_username: str) -> Optional[str]:
        """
        Get the voting link for a reviewer account.
        Since get_reviewer_link action doesn't exist in the API, we'll try to create
        the reviewer and extract the link from the creation response.
        
        Args:
            twitch_username: The Twitch username (without 'twitch_' prefix)
            
        Returns:
            Voting URL string or None if failed
        """
        try:
            reviewer_name = f"twitch_{twitch_username}"
            
            payload = {
                "action": "create_reviewer",
                "data": {
                    "name": reviewer_name,
                    "weight": self.reviewer_weight
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            url = f"{self.api_url}?token={self.api_token}"
            
            logger.info(f"Getting FSL reviewer link by attempting creation: {reviewer_name}")
            response = requests.post(url, headers=headers, json=payload, timeout=10, verify=config.FSL_VERIFY_SSL)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"FSL API response for link retrieval: {result}")
                
                if result.get('success', False):
                    # Creation succeeded, extract link from response
                    voting_link = result.get('data', {}).get('link')
                    if voting_link:
                        logger.info(f"Got FSL reviewer link from creation response: {voting_link}")
                        return voting_link
                    else:
                        logger.warning(f"FSL reviewer created but no link in response")
                        return None
                else:
                    # Check if this is an "already exists" error
                    error_msg = str(result.get('error', '')).lower()
                    if any(phrase in error_msg for phrase in ['already exists', 'already exist', 'duplicate', 'exists']):
                        logger.info(f"FSL reviewer {reviewer_name} already exists, but can't get link (API limitation)")
                        return None
                    else:
                        logger.error(f"FSL API returned error getting link: {result}")
                        return None
            else:
                logger.error(f"FSL API error getting link: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"FSL API request failed getting link: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"FSL API response not valid JSON getting link: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting FSL reviewer link: {e}")
            return None 