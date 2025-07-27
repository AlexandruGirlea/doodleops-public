import os
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START

from core import settings
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.conversations_state import State
from llm_graph.utils.build_supervisor_nodes import make_supervisor_node
from llm_graph.sub_graphs.career_advice.nodes.conversation import (
	conversation_node,
)
from llm_graph.sub_graphs.career_advice.nodes.research import research_node
from llm_graph.sub_graphs.career_advice.nodes.web_search import (
	web_search_node
)
from llm_graph.sub_graphs.career_advice.nodes.media import media_node
from llm_graph.sub_graphs.career_advice.nodes.how_to_start_a_career import (
	how_to_start_a_career_node
)


career_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "research_node",
		"how_to_start_a_career_node", "web_search_node",
		"media_node"
	],
	additional_info="""
		You, as the career advice supervisor assistant, serve as the primary
		decision-maker in the career guidance flow.
		You determine the most appropriate next step. You have the following
		workers:
		
		- 'conversation_node': Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details like their career interests, current
		experience, educational background, professional, financial goals, etc.
		This node is also a fallback option in case the user's request is unclear
		or incomplete. It asks the user questions to clarify their request.
		If not sufficient information is provided, route to this node but do not
		force the user to provide information he does not want. If the user is
		looking for job openings, but the location is not clear, route to this
		node to ask for the location.
		
		- 'research_node': Route to this node when you need to provide the
		user with the latest career advice, industry trends, company info,
		company culture, salary research and training programs. This node
		researches the internet for the most relevant career advice and tips.
		This node can also research the most asked interview questions to help
		the user prepare for an interview. Do not use this node
		for searching for job openings, for that use the `web_search_node`.
		
		- 'how_to_start_a_career_node': Route to this node if the user needs
		actionable steps to kickstart his career journey or transition to a new
		field. This node provides the user with a step-by-step guide on how to
		start a career in a specific field or how to switch careers.
		This node can also help the user with interview preparation by providing
		tips on how to answer common or technically specific interview questions.
		This is different from the `research_node` it does not
		research the most asked interview questions, uses it's own knowledge to
		guide prepare the user for an interview.
		
		- 'media_node': Route to this node only if the user has provided a
		media file like a CV, resume, cover letter, or any other document or
		image that needs to be reviewed. Also route to this node if the user
		is asking questions that could be answered by analyzing the media file
		provided. This node can help the user by processing
		the media file provided on multiple topics like but not limited to:
		cv/resume/cover letter/job description/job offer/profile image,
		and so on, by providing review/advice/feedback/analysis on the media
		file provided. Very important only route to this node if the user provided
		a valid url link to the media file, else route to `conversation_node`.
		Still route to the `media_node` if the user asks a follow-up question
		related to a media file he provided the link for.
		
		- 'web_search_node': Route to this node if the user is looking for
		job openings, training programs, or other career-related resources.
		This only provides google search results. Use this node when a clear
		google search is needed. Do not use this node to do research on the
		internet for career advice. For research use the `research_node`.
		
		VERY IMPORTANT: DO NOT provide or facilitate advice that involves 
		unethical, illegal, or unlicensed professional services. If such requests 
		arise, steer the conversation back to `conversation_node`.
		"""
)

career_builder = StateGraph(State)
career_builder.add_node("career_supervisor_node", career_supervisor_node)
career_builder.add_node("conversation_node", conversation_node)
career_builder.add_node("media_node", media_node)
career_builder.add_node("research_node", research_node)
career_builder.add_node("web_search_node", web_search_node)
career_builder.add_node("how_to_start_a_career_node", how_to_start_a_career_node)

career_builder.add_edge(START, "career_supervisor_node")
career_graph = career_builder.compile()

if settings.ENV_MODE == "local":
	career_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "career_graph.png"
		)
	)


def call_career_graph(
		state: State
) -> Command[Literal["career_graph"]]:
	response = career_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"language": state.get("language", "english"),
			"all_llm_costs": state.get("all_llm_costs"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="career_graph"
				)
			],
		},
		goto=END,
	)
