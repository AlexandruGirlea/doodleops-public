"""
Used both by app_api and app_ai.
"""

from typing import Optional

from pydantic import BaseModel


class LLMCost(BaseModel):
	simple_conversation: int = 0
	web_research: int = 0
	web_search: int = 0
	respond_with_sound: int = 0
	text_to_text_translation: int = 0

	# media input costs
	document_input_processing: int = 0
	image_input_processing: int = 0
	sound_input_processing: int = 0

	# media generation:
	generate_video: int = 0
	image_generation: int = 0


class TwilioPublisherMsg(BaseModel):
	phone_number: str
	username: Optional[str] = None
	msg: Optional[str] = None
	media_url: Optional[str] = None
	media_type: Optional[str] = None
	timestamp: int
	has_metered_subscription: bool = False
	user_credits_bought_remaining: int = 0
	subscriptions_monthly_credit_remaining: int = 0
	all_llm_costs: LLMCost = LLMCost()
	
	# write example for fastapi
	class Config:
		schema_extra = {
			"example": {
				"phone_number": "+1234567890",
				"username": "user1",
				"msg": "Hello",
				"media_url": "https://www.example.com/image.jpg",
				"media_type": "image/jpeg",
				"timestamp": 1628600000,
				"has_metered_subscription": False,
				"all_llm_costs": {
					"simple_conversation": 1,
					"web_research": 2,
					"image_generation": 3,
				}
			}
		}


class LLMGraphResponse(BaseModel):
	message: str
	is_error: bool = False
	total_call_cost: int = 0
	
	class Config:
		schema_extra = {
			"example": {
				"message": "Hello",
				"is_error": False,
				"total_call_cost": 1,
			}
		}
