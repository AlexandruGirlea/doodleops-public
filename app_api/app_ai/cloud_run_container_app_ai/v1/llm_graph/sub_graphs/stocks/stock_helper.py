from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from llm_graph.utils.llm_models import lite_llm_vertexai

response_schemas = [
	ResponseSchema(
		name="stock_symbol", type="str",
		description=(
			"A US stock symbol like AAPL, MSFT, TSLA, etc. Only the symbol "
			"should be provided without any additional information or characters."
		)
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
get_stock_symbol_format_instructions = output_parser.get_format_instructions()

stock_symbol_template = PromptTemplate(
	input_variables=["history", "new_message", "format_instructions"],
	template="""
		You are a helpful AI stock bot.
		Your single job is to look at the conversation history and the latest
		user message and identify the stock Symbol the user is interested in.

		Example response can look like:
		- "stock_symbol": "AAPL",
		or like this:
		- "stock_symbol": "BRK-B",
		
		Do not use other characters or words. Just the stock symbol. Do not use
		points, commas, or any other characters. Just the stock symbol and dash
		if it is needed.
		
		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"

		ONLY for US stocks. If the user wants information about a non-US stock
		return empty string.
		"""
)

get_stock_symbol_chain = stock_symbol_template | lite_llm_vertexai | output_parser
