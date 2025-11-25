from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from settings import config

llm = ChatOpenAI(temperature=0.6, model_name=config.ENGINE, openai_api_key=config.OPENAI_API_KEY)

tool_names = ['wikipedia']
tools = load_tools(tool_names, llm=llm)

prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
{agent_scratchpad}"""
)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    handle_parsing_errors=True
)


def wikipedia_question(question, self=None):
    print(f'Question: {question}')
    try:
        result = agent_executor.invoke({"input": question})
        return result.get("output", "No answer found.")
    except Exception as e:
        print(f"Wiki Error: {e}")
        return f"Error searching wiki: {str(e)}"
