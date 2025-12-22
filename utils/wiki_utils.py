from settings import config

# Lazy initialization to avoid import errors at module level
_agent_executor = None

def _get_agent_executor():
    """Lazy initialization of the agent executor"""
    global _agent_executor
    if _agent_executor is not None:
        return _agent_executor
    
    try:
        from langchain.agents.load_tools import load_tools
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain.prompts import PromptTemplate
        # Try langchain_openai first, fall back to langchain.chat_models
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            from langchain.chat_models import ChatOpenAI
        
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
        _agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True
        )
        return _agent_executor
    except ImportError as e:
        raise ImportError(f"Failed to import langchain components: {e}. Make sure langchain packages are installed correctly.")

def wikipedia_question(question, self=None):
    print(f'Question: {question}')
    try:
        agent_executor = _get_agent_executor()
        result = agent_executor.invoke({"input": question})
        return result.get("output", "No answer found.")
    except Exception as e:
        print(f"Wiki Error: {e}")
        return f"Error searching wiki: {str(e)}"
