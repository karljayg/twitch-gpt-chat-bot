from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI
from settings import config

llm = OpenAI(temperature=0.6, openai_api_key=config.OPENAI_API_KEY)

tool_names = ['wikipedia']
tools = load_tools(tool_names, llm=llm)

prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="You are a helpful assistant that can answer questions using Wikipedia.\n\nQuestion: {input}\n\nAvailable tools: {tool_names}\n\nTools: {tools}\n\n{agent_scratchpad}"
)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


def wikipedia_question(question, self):
    print(f'Question: {question}')
    return agent_executor.invoke({"input": question})["output"]
