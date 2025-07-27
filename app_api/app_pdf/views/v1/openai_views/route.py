from fastapi import APIRouter

v1_view_pdf_router_openai = APIRouter(
		tags=["App PDFs OpenAI"],
		responses={404: {"description": "Not found"}},
	)
