"""
ChatVertexAI does not call tools yet. It might do it in the future.
"""
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview.vision_models import ImageGenerationModel
from langchain_google_vertexai import ChatVertexAI
from google import genai
from google.genai import types

from core.settings import GCP_PROJECT_ID, GCP_LOCATION

# Vertex AI - GCP
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

# generate images
vertex_ai_image3_model = ImageGenerationModel.from_pretrained(
	"imagen-3.0-generate-002"
)

media_understanding_vertexai = GenerativeModel("gemini-2.0-flash-001")

lite_llm_vertexai = ChatVertexAI(
	model="gemini-2.0-flash-lite",
	temperature=0,
	max_tokens=600,
	max_retries=3,
)

base_llm_vertexai = ChatVertexAI(
	model="gemini-2.0-flash",
	temperature=0,
	max_tokens=1000,
	max_retries=3,
)

genai_client = genai.Client(
	vertexai=True,
	project=GCP_PROJECT_ID,
	location='us-central1',
	http_options=types.HttpOptions(api_version='v1')
)
